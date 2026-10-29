"""Growth features: event tracking + funnel, upcoming festivals, date-reminder (nudge) engine with guardrails.
Storage is SQLite (KUNDLI_DB, default ./data/ta.db). On Render's free plan the disk is ephemeral: use a Postgres/disk for real."""
import datetime as dt
import os
import sqlite3
import time
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from kundli.api import app as engine
from kundli.chart import to_dict
from kundli.compat.normalize import engine_config
from kundli.transits import ingresses

DB = Path(os.environ.get("KUNDLI_DB", "data/ta.db"))
router = APIRouter()
PLANET_HI = {"Saturn": "Shani", "Jupiter": "Guru", "Rahu": "Rahu", "Ketu": "Ketu"}
CONCERN_HOUSES = {"career": (10, 6), "marriage": (7, 5), "money": (2, 11), "foreign": (12, 9)}
CONCERN_WORD = {"career": "job/career", "marriage": "shaadi", "money": "paise", "foreign": "videsh yatra"}
CRISIS = ("death", "marta", "mar gaya", "marna", "suicide", "khudkushi", "cancer", "hospital", "bimari", "ill")
MAX_PER_MONTH = 2


def db() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS events(ts REAL, sid TEXT, name TEXT, lang TEXT, topic TEXT, path TEXT);
    CREATE TABLE IF NOT EXISTS nudge_users(id TEXT PRIMARY KEY, name TEXT, date TEXT, time TEXT, place TEXT, concern TEXT,
        optin INTEGER, stopped INTEGER DEFAULT 0, crisis INTEGER DEFAULT 0, created REAL);
    CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, ts REAL, message TEXT, trigger TEXT);
    """)
    return c


# ---------- event tracking ----------
class Event(BaseModel):
    name: str = Field(max_length=40, pattern=r"^[a-z0-9_]+$")
    sid: str = Field(max_length=40)
    lang: str = Field("", max_length=4)
    topic: str = Field("", max_length=20)
    path: str = Field("", max_length=60)


@router.post("/api/event", status_code=204)
def event(e: Event) -> None:
    with db() as c:
        c.execute("INSERT INTO events VALUES(?,?,?,?,?,?)", (time.time(), e.sid, e.name, e.lang, e.topic, e.path))


FUNNEL = ["page_view", "form_start", "form_complete", "snapshot_shown", "cta_click", "payment_start", "payment_done",
          "report_download", "milan_done", "chat_started", "free_chat_started", "wa_click"]


@router.get("/api/funnel")
def funnel(request: Request, days: int = 7, token: str = "") -> dict:
    need = os.environ.get("FUNNEL_TOKEN")
    if need and token != need:
        raise HTTPException(401, "token required")
    since = time.time() - days * 86400
    with db() as c:
        rows = c.execute("SELECT name, COUNT(*) n, COUNT(DISTINCT sid) u FROM events WHERE ts>? GROUP BY name", (since,)).fetchall()
        by_topic = c.execute("SELECT topic, COUNT(DISTINCT sid) u FROM events WHERE ts>? AND name='page_view' GROUP BY topic", (since,)).fetchall()
    got = {r["name"]: {"events": r["n"], "users": r["u"]} for r in rows}
    top = got.get("page_view", {}).get("users", 0)
    steps = [{"step": s, **got.get(s, {"events": 0, "users": 0}),
              "pct_of_visitors": round(100 * got.get(s, {"users": 0})["users"] / top, 1) if top else 0} for s in FUNNEL]
    return {"days": days, "funnel": steps, "landing_topics": {r["topic"] or "home": r["u"] for r in by_topic}}


# ---------- upcoming festivals (from the engine's festival rules) ----------
_FEST: dict[str, list[str]] = {}


@router.get("/api/festivals")
async def festivals(days: int = 60) -> list[dict]:
    days = min(max(days, 1), 120)
    out, today = [], dt.date.today()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=engine), base_url="http://e") as c:
        for i in range(days):
            d = (today + dt.timedelta(days=i)).isoformat()
            if d not in _FEST:
                r = await c.post("/compat/panchang_festival", json={"date": d, "lat": 28.65195, "lon": 77.23149, "tz": "Asia/Kolkata"})
                _FEST[d] = [f["name"] for f in r.json()["data"].get("festivals", [])] if r.status_code == 200 else []
            out += [{"date": d, "name": n} for n in _FEST[d]]
    return out


# ---------- date reminders (nudges) ----------
class OptIn(BaseModel):
    name: str = Field(max_length=60)
    date: str
    time: str | None = None
    place: str
    concern: str = Field(pattern="^(career|marriage|money|foreign)$")
    consent: bool


@router.post("/api/nudge/optin")
def optin(o: OptIn) -> dict:
    if not o.consent:
        raise HTTPException(422, "consent_required")
    uid = uuid.uuid4().hex[:12]
    with db() as c:
        c.execute("INSERT INTO nudge_users(id,name,date,time,place,concern,optin,created) VALUES(?,?,?,?,?,?,1,?)",
                  (uid, o.name, o.date, o.time, o.place, o.concern, time.time()))
    return {"id": uid, "stop": f"/api/nudge/stop/{uid}"}


@router.post("/api/nudge/stop/{uid}")
@router.get("/api/nudge/stop/{uid}")
def stop(uid: str) -> dict:
    with db() as c:
        n = c.execute("UPDATE nudge_users SET stopped=1 WHERE id=?", (uid,)).rowcount
    if not n:
        raise HTTPException(404, "unknown id")
    return {"stopped": True}


class Flag(BaseModel):
    text: str = Field(max_length=2000)


@router.post("/api/nudge/chat-flag/{uid}")
def chat_flag(uid: str, f: Flag) -> dict:
    """Call this with each chat transcript. A crisis word permanently blocks nudges for that user."""
    hit = any(w in f.text.lower() for w in CRISIS)
    if hit:
        with db() as c:
            c.execute("UPDATE nudge_users SET crisis=1 WHERE id=?", (uid,))
    return {"crisis_flagged": hit}


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def build_message(u: sqlite3.Row, as_of: dt.date, horizon: int = 21) -> dict:
    from .app import Person, build  # local import avoids a cycle
    kd, _ = build(Person(name=u["name"], date=u["date"], time=u["time"], place=u["place"]))
    k = to_dict(kd)
    lagna = k["lagna"]["sign"]
    cfg = engine_config({})
    s = dt.datetime.combine(as_of, dt.time(), tzinfo=dt.timezone.utc)
    want = CONCERN_HOUSES[u["concern"]]
    for planet in ("Saturn", "Jupiter", "Rahu"):
        for ev in ingresses(planet, s, s + dt.timedelta(days=horizon), cfg):
            house = (ev["to_sign"] - lagna) % 12 + 1
            if house in want:
                d = ev["utc"][:10]
                txt = (f'{u["name"]}, pichli baar aapne {CONCERN_WORD[u["concern"]]} ke baare mein poocha tha. '
                       f'{d} ko {PLANET_HI[planet]} ka gochar aapke {ordinal(house)} house mein ho raha hai. '
                       f'Iska aapke faisle par kya asar hoga, yeh Shreya ke saath 10 min mein dekhein. '
                       f'[Chat shuru karein] [Call shuru karein]  Band karne ke liye: STOP')
                return {"message": txt, "trigger": f"{planet} -> {ev['to_sign_name']} on {d} (house {house})"}
    return {"skip": "no_relevant_transit"}


def guard(u: sqlite3.Row, c: sqlite3.Connection, now: float) -> str | None:
    if not u["optin"]:
        return "no_opt_in"
    if u["stopped"]:
        return "stopped"
    if u["crisis"]:
        return "crisis_flagged_chat"
    month_ago = now - 30 * 86400
    if c.execute("SELECT COUNT(*) FROM outbox WHERE user_id=? AND ts>?", (u["id"], month_ago)).fetchone()[0] >= MAX_PER_MONTH:
        return "monthly_cap_reached"
    return None


@router.get("/api/nudge/preview/{uid}")
def preview(uid: str, as_of: str | None = None) -> dict:
    with db() as c:
        u = c.execute("SELECT * FROM nudge_users WHERE id=?", (uid,)).fetchone()
        if not u:
            raise HTTPException(404, "unknown id")
        why = guard(u, c, time.time())
        return {"skip": why} if why else build_message(u, dt.date.fromisoformat(as_of) if as_of else dt.date.today())


@router.post("/api/nudge/run")
def run_daily(request: Request) -> dict:
    """The daily job. 'Sends' into the outbox table; plug a WhatsApp provider in where marked."""
    need = os.environ.get("FUNNEL_TOKEN")
    if need and request.headers.get("x-token") != need:
        raise HTTPException(401, "token required")
    sent = skipped = 0
    with db() as c:
        for u in c.execute("SELECT * FROM nudge_users").fetchall():
            if guard(u, c, time.time()):
                skipped += 1
                continue
            m = build_message(u, dt.date.today())
            if "message" in m:
                c.execute("INSERT INTO outbox(user_id,ts,message,trigger) VALUES(?,?,?,?)", (u["id"], time.time(), m["message"], m["trigger"]))
                sent += 1  # <- WhatsApp provider call goes here
            else:
                skipped += 1
    return {"queued": sent, "skipped": skipped}
