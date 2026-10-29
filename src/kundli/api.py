"""FastAPI service. All time inputs are explicit. Birth data is never logged; charts are stored locally only."""
import hmac
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from . import ops
from .chart import current_dasha, generate, to_dict
from .compat.normalize import engine_config
from .compat.router import ENGINE_LOCK
from .compat.router import router as compat_router
from .errors import AmbiguousLocalTime, AmbiguousPlace, KundliError, NonexistentLocalTime, PlaceNotFound
from .geo import candidates
from .predict.llm import AnthropicClient, answer
from .render import north_indian, pdf_report, south_indian
from .render.common import view_for
from .service import aware, delete_chart, get_chart, make_birth, save_chart


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    ops.warm_up()
    yield


app = FastAPI(title="kundli-engine", version="0.2.0", lifespan=lifespan)


@app.middleware("http")
async def access_log(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Structured access log: route template, method, status, duration. No query string, body, address or path values."""
    t0 = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    ops.log_access(getattr(route, "path", "unmatched"), request.method, response.status_code, (time.perf_counter() - t0) * 1000.0)
    return response

WEB = Path(__file__).parent / "web" / "index.html"
app.include_router(compat_router)


class KundliRequest(BaseModel):
    name: str = Field(max_length=120)
    date: str = Field(max_length=32)
    time: str | None = Field(None, max_length=32)
    place: str | None = Field(None, max_length=200)
    place_choice: int | None = Field(None, ge=0, le=100)
    fold: Literal[0, 1] | None = None
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    tz: str | None = Field(None, max_length=64)
    config: dict[str, Any] = {}


class AskRequest(BaseModel):
    question: str = Field(max_length=2000)
    as_of: str = Field(max_length=40)
    from_: str | None = Field(None, max_length=40)
    to: str | None = Field(None, max_length=40)
    language: str = Field("en", max_length=8)
    use_llm: bool = False


def _chart(cid: str):
    k = get_chart(cid)
    if k is None:
        raise HTTPException(404, "chart not found")
    return k


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, Any]:
    """Engine version, config hash and content version (public; no request data)."""
    return ops.version_info()


@app.get("/ops/shadow")
def ops_shadow(x_ops_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Per-endpoint shadow diff rates and cutover readiness. Disabled (404) unless KUNDLI_OPS_TOKEN is set."""
    token = os.environ.get("KUNDLI_OPS_TOKEN")
    if not token:
        raise HTTPException(404, "not found")
    if not x_ops_token or not hmac.compare_digest(x_ops_token, token):
        raise HTTPException(401, "invalid token")
    return ops.shadow_report()


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
        with ENGINE_LOCK:
            k = generate(birth, engine_config(req.config))
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
def svg(cid: str, varga: str, style: Literal["north", "south"] = "north") -> Response:
    k = _chart(cid)
    try:
        view = view_for(k, varga)
        body = (north_indian if style == "north" else south_indian).render(view)
    except (KeyError, ValueError) as e:
        raise HTTPException(422, f"cannot render {varga}: {e}") from None
    return Response(body, media_type="image/svg+xml")


@app.get("/kundli/{cid}/dasha")
def dasha(cid: str, date: str, system: Literal["vimshottari", "yogini"] = "vimshottari",
          levels: int = Query(4, ge=1, le=5)) -> dict[str, Any]:
    k = _chart(cid)
    try:
        stack = current_dasha(k, aware(date), system, levels)
    except (KundliError, ValueError) as e:
        raise HTTPException(422, str(e)) from None
    return {"date": date, "system": system, "stack": stack}


@app.get("/kundli/{cid}/report.pdf")
def report(cid: str, style: Literal["north", "south"] = "north") -> Response:
    with ENGINE_LOCK:
        return Response(pdf_report.build_pdf(_chart(cid), style=style), media_type="application/pdf")


@app.post("/kundli/{cid}/ask")
def ask(cid: str, req: AskRequest) -> dict[str, Any]:
    k = _chart(cid)
    client = AnthropicClient() if req.use_llm else None
    try:
        with ENGINE_LOCK:
            return answer(k, req.question, aware(req.as_of), aware(req.from_) if req.from_ else None,
                          aware(req.to) if req.to else None, client, req.language)
    except (KundliError, ValueError) as e:
        raise HTTPException(422, str(e)) from None
