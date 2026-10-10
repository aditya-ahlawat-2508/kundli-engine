"""FastAPI service. All time inputs are explicit. Birth data is never logged; charts are stored locally only."""
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from .chart import current_dasha, generate, to_dict
from .config import EngineConfig
from .errors import AmbiguousLocalTime, AmbiguousPlace, KundliError, NonexistentLocalTime, PlaceNotFound
from .geo import candidates
from .predict.llm import AnthropicClient, answer
from .render import north_indian, pdf_report, south_indian
from .render.common import view_for
from .service import aware, delete_chart, get_chart, make_birth, save_chart

app = FastAPI(title="kundli-engine", version="0.1.0")
WEB = Path(__file__).parent / "web" / "index.html"


class KundliRequest(BaseModel):
    name: str
    date: str
    time: str | None = None
    place: str | None = None
    place_choice: int | None = None
    fold: int | None = None
    lat: float | None = None
    lon: float | None = None
    tz: str | None = None
    config: dict[str, Any] = {}


class AskRequest(BaseModel):
    question: str
    as_of: str
    from_: str | None = None
    to: str | None = None
    language: str = "en"
    use_llm: bool = False


def _chart(cid: str):
    k = get_chart(cid)
    if k is None:
        raise HTTPException(404, "chart not found")
    return k


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return WEB.read_text(encoding="utf-8")


@app.get("/places")
def places(q: str = Query(min_length=2)) -> list[dict[str, Any]]:
    return [{"index": i, **p.model_dump()} for i, p in enumerate(candidates(q, online=False)[:15])]


@app.post("/kundli")
def create(req: KundliRequest) -> JSONResponse:
    try:
        birth = make_birth(req.name, req.date, req.time, req.place, req.place_choice, req.fold, req.lat, req.lon, req.tz)
        k = generate(birth, EngineConfig(**req.config))
    except AmbiguousPlace as e:
        return JSONResponse({"error": "ambiguous_place", "candidates": [
            {"index": i, **p.model_dump()} for i, p in enumerate(e.candidates)]}, status_code=409)
    except (AmbiguousLocalTime, NonexistentLocalTime) as e:
        return JSONResponse({"error": "local_time", "detail": str(e)}, status_code=409)
    except PlaceNotFound:
        raise HTTPException(404, "place not found") from None
    except (KundliError, ValueError) as e:
        raise HTTPException(422, str(e)) from None
    return JSONResponse({"id": save_chart(k), "kundli": to_dict(k)})


@app.get("/kundli/{cid}")
def read(cid: str) -> dict[str, Any]:
    return to_dict(_chart(cid))


@app.delete("/kundli/{cid}")
def remove(cid: str) -> dict[str, bool]:
    if not delete_chart(cid):
        raise HTTPException(404, "chart not found")
    return {"deleted": True}


@app.get("/kundli/{cid}/charts/{varga}.svg")
def svg(cid: str, varga: str, style: str = "north") -> Response:
    k = _chart(cid)
    try:
        view = view_for(k, varga)
        body = (north_indian if style == "north" else south_indian).render(view)
    except (KeyError, ValueError) as e:
        raise HTTPException(422, f"cannot render {varga}: {e}") from None
    return Response(body, media_type="image/svg+xml")


@app.get("/kundli/{cid}/dasha")
def dasha(cid: str, date: str, system: str = "vimshottari", levels: int = 4) -> dict[str, Any]:
    k = _chart(cid)
    return {"date": date, "system": system, "stack": current_dasha(k, aware(date), system, levels)}


@app.get("/kundli/{cid}/report.pdf")
def report(cid: str, style: str = "north") -> Response:
    return Response(pdf_report.build_pdf(_chart(cid), style=style), media_type="application/pdf")


@app.post("/kundli/{cid}/ask")
def ask(cid: str, req: AskRequest) -> dict[str, Any]:
    k = _chart(cid)
    client = AnthropicClient() if req.use_llm else None
    return answer(k, req.question, aware(req.as_of), aware(req.from_) if req.from_ else None,
                  aware(req.to) if req.to else None, client, req.language)
