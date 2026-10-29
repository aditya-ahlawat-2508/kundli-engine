"""Times Astro gateway: serves the website and turns engine output into website-ready JSON.
Run:  uv run uvicorn gateway.app:app --port 8000
No LLM key needed. Wallet / payments / calls / auth are NOT here (they need vendors)."""
import datetime as dt
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from kundli import ops
from kundli.api import app as engine
from kundli.chart import current_dasha, generate, to_dict
from kundli.compat.normalize import engine_config
from kundli.compat.router import ENGINE_LOCK
from kundli.errors import AmbiguousPlace, KundliError, PlaceNotFound
from kundli.geo import candidates
from kundli.render import pdf_report
from kundli.service import aware, make_birth

STATIC = Path(__file__).parent / "static"
LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
DELHI = {"lat": 28.65195, "lon": 77.23149, "tz": "Asia/Kolkata", "name": "Delhi"}


@asynccontextmanager
async def lifespan(_a):  # type: ignore[no-untyped-def]
    ops.warm_up()
    yield


app = FastAPI(title="timesastro-gateway", lifespan=lifespan)
app.mount("/engine", engine)  # full engine API stays reachable (docs at /engine/docs)


def resolve_place(q: str) -> dict:
    """City text -> lat/lon/tz. Offline GeoNames; India preferred. Tries the full text, each comma part, then each word."""
    q = q.strip()
    tries = [q] + [x.strip() for x in q.split(",")] + [w for w in q.replace(",", " ").split() if len(w) >= 3]
    for t in dict.fromkeys(x for x in tries if len(x) >= 2):
        c = candidates(t, online=False)
        if c:
            p = sorted(c, key=lambda p: (p.country != "India", -(p.population or 0)))[0]
            return {"lat": p.lat, "lon": p.lon, "tz": p.tz, "name": p.name}
    raise HTTPException(404, "place_not_found")


class Person(BaseModel):
    name: str = Field("", max_length=120)
    date: str
    time: str | None = None
    place: str = Field(max_length=200)


def build(p: Person):
    pl = resolve_place(p.place)
    try:
        birth = make_birth(p.name or "Guest", p.date, p.time or "12:00", None, None, None, pl["lat"], pl["lon"], pl["tz"])
        with ENGINE_LOCK:
            return generate(birth, engine_config({})), pl
    except (KundliError, ValueError) as e:
        raise HTTPException(422, str(e)) from None


def sign_of_house(k: dict, h: int) -> int:
    return (k["lagna"]["sign"] + h - 1) % 12


def occupants(k: dict, h: int) -> list[str]:
    return [p["name"] for p in k["planets"] if p["house"] == h and p["name"] in
            ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")]


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "engine": ops.version_info().get("engine_version")}


@app.get("/api/places")
def places(q: str = Query(min_length=2)) -> list[dict]:
    return [{"name": p.name, "admin1": p.admin1, "country": p.country} for p in candidates(q, online=False)[:8]]


@app.post("/api/snapshot")
def snapshot(p: Person) -> dict:
    """Real chart facts + a deliberately partial teaser (facts, no timing verdicts) for the free kundli card."""
    kd, pl = build(p)
    k = to_dict(kd)
    today = dt.date.today().isoformat()
    stack = current_dasha(kd, aware(today), "vimshottari", 2)
    maha = stack[0]
    antar = stack[1] if len(stack) > 1 else None
    h10, h7, h2, h11 = (occupants(k, h) for h in (10, 7, 2, 11))
    lord = lambda h: LORDS[sign_of_house(k, h)]
    moon = next(x for x in k["planets"] if x["name"] == "Moon")
    with ENGINE_LOCK:
        from kundli.doshas import manglik as _m  # noqa: F401  (import check only)
    mars = next(x for x in k["planets"] if x["name"] == "Mars")
    manglik = mars["house"] in (1, 2, 4, 7, 8, 12)
    return {
        "approx_time": not p.time,
        "place": pl["name"],
        "facts": {
            "lagna": k["lagna"]["sign_name"], "moon_sign": moon["sign_name"], "nakshatra": moon["nakshatra_name"],
            "maha": maha["lord"], "maha_end": maha["end_local"][:10], "antar": antar["lord"] if antar else None,
            "antar_end": antar["end_local"][:10] if antar else None, "manglik": manglik,
            "h10": h10, "h10_lord": lord(10), "h7": h7, "h7_lord": lord(7), "h2_lord": lord(2), "h11_lord": lord(11),
            "h11": h11, "h2": h2,
        },
    }


class Pair(BaseModel):
    boy: Person
    girl: Person


@app.post("/api/milan")
async def milan(pr: Pair) -> dict:
    def bd(p: Person) -> dict:
        pl = resolve_place(p.place)
        return {"date": p.date, "time": p.time or "12:00", "lat": pl["lat"], "lon": pl["lon"], "tz": pl["tz"]}
    body = {"boy": bd(pr.boy), "girl": bd(pr.girl)}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=engine), base_url="http://e") as c:
        r = await c.post("/compat/match_ashtakoot_points", json=body)
        if r.status_code != 200:
            raise HTTPException(r.status_code, r.text[:300])
        d = r.json()["data"]
        m = await c.post("/compat/match_manglik_report", json=body)
    out = {"total": d["total"], "max": d["max"], "kootas": d["kootas"], "verdict": d.get("verdict"),
           "tables_verified": d.get("tables_verified"), "approx_time": not (pr.boy.time and pr.girl.time)}
    if m.status_code == 200:
        out["manglik"] = m.json()["data"]
    return out


@app.get("/api/panchang")
async def panchang(date: str | None = None, place: str | None = None) -> dict:
    pl = resolve_place(place) if place else DELHI
    body = {"date": date or dt.date.today().isoformat(), "lat": pl["lat"], "lon": pl["lon"], "tz": pl["tz"]}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=engine), base_url="http://e") as c:
        r = await c.post("/compat/basic_panchang", json=body)
        f = await c.post("/compat/panchang_festival", json=body)
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text[:300])
    d = r.json()["data"]
    t = lambda s: s[11:16] if s else None
    return {"place": pl["name"], "date": body["date"], "vara": d["vara"]["name"],
            "tithi": f'{d["tithi"]["paksha"]} {d["tithi"]["name"]}', "tithi_end": t(d["tithi"]["end_local"]),
            "nakshatra": d["nakshatra"]["name"], "nakshatra_end": t(d["nakshatra"]["end_local"]),
            "yoga": d["yoga"]["name"], "karana": d["karana"]["name"], "month": d["hindu_month"]["name"],
            "sunrise": t(d["rise_set"]["sunrise"]), "sunset": t(d["rise_set"]["sunset"]),
            "moonrise": t(d["rise_set"]["moonrise"]),
            "festivals": [x["name"] for x in (f.json()["data"].get("festivals", []) if f.status_code == 200 else [])]}


@app.get("/api/report.pdf")
def report(date: str, place: str, time: str | None = None, name: str = "Guest") -> Response:
    kd, _ = build(Person(name=name, date=date, time=time, place=place))
    with ENGINE_LOCK:
        pdf = pdf_report.build_pdf(kd, style="north")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=kundli.pdf"})


@app.get("/api/chart.svg")
def chart_svg(date: str, place: str, time: str | None = None, style: str = "north") -> Response:
    from kundli.render import north_indian, south_indian
    from kundli.render.common import view_for
    kd, _ = build(Person(date=date, time=time, place=place))
    return Response((north_indian if style == "north" else south_indian).render(view_for(kd, "D1")), media_type="image/svg+xml")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html")
