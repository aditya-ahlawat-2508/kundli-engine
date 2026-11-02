"""Shreya, the LLM astrologer. The model gets the system prompt in prompts/shreya_system.txt and ONE tool,
check_user_question_servicability, which is answered from the kundli engine (never from the model's memory).
Needs ANTHROPIC_API_KEY. Model: SHREYA_MODEL (default claude-sonnet-5-5)."""
import datetime as dt
import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from zoneinfo import ZoneInfo

from kundli.chart import current_dasha, to_dict
from kundli.compat.normalize import engine_config
from kundli.service import aware
from kundli.transits import ingresses, positions_on, sade_sati_status

IST = ZoneInfo("Asia/Kolkata")
PROMPT = (Path(__file__).parent / "prompts" / "shreya_system.txt").read_text(encoding="utf-8")
MODEL = os.environ.get("SHREYA_MODEL", "claude-sonnet-5-5")
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
TOPICS = {  # topic -> (houses, karakas, varga)
    "career": ([10, 6, 2, 11], ["Sun", "Saturn", "Mercury", "Jupiter"], "D10"),
    "marriage": ([7, 2, 11], ["Venus", "Jupiter", "Mars"], "D9"),
    "love": ([5, 7, 11], ["Venus", "Moon", "Mars"], "D9"),
    "money": ([2, 11, 5, 9, 6, 8, 12], ["Jupiter", "Venus", "Mercury"], "D2"),
    "property": ([4, 11], ["Mars", "Venus", "Moon"], "D4"),
    "family": ([2, 4, 5], ["Jupiter", "Moon"], "D7"),
    "children": ([5, 9], ["Jupiter"], "D7"),
    "health": ([1, 6, 8], ["Sun", "Moon", "Mars"], "D1"),
    "general": ([1, 5, 9, 10, 7, 2, 11], ["Jupiter", "Saturn", "Moon"], "D1"),
}
TOOL = {
    "name": "check_user_question_servicability",
    "description": "Call on EVERY turn with the topic of the user's latest message. Returns the user's fresh kundli facts "
                   "(planets, house lords, dashas with past/current/future labels, transits, yogas/doshas) and a verdict.",
    "input_schema": {"type": "object", "properties": {
        "topic": {"type": "string", "enum": list(TOPICS) + ["other"]},
        "question": {"type": "string", "description": "the user's question in their own words"}},
        "required": ["topic", "question"]},
}


def _status(start: str, end: str, now: dt.datetime) -> str:
    return "past" if end < now.isoformat() else "future" if start > now.isoformat() else "current"


def _periods(k: dict, now: dt.datetime, years: int = 9) -> list[dict]:
    """Maha and antar periods that are current or start within `years`, each labelled by comparing real dates to now."""
    out, horizon = [], (now + dt.timedelta(days=365 * years)).isoformat()
    for m in k["dashas"]["vimshottari"]["mahadashas"]:
        if m["end_utc"] < now.isoformat() or m["start_utc"] > horizon:
            continue
        out.append({"level": "maha", "lord": m["lord"], "from": m["start_local"][:7], "to": m["end_local"][:7],
                    "status": _status(m["start_utc"], m["end_utc"], now)})
        for a in m.get("children", []):
            if a["end_utc"] >= now.isoformat() and a["start_utc"] <= horizon:
                out.append({"level": "antar", "in_maha": m["lord"], "lord": a["lord"], "from": a["start_local"][:7],
                            "to": a["end_local"][:7], "status": _status(a["start_utc"], a["end_utc"], now)})
    return out


def servicability(kd, topic: str, question: str, now: dt.datetime, exhausted: bool) -> dict:
    if exhausted:
        return {"verdict": "usage_exhausted"}
    k = to_dict(kd)
    t = topic if topic in TOPICS else None
    if t is None:
        return {"verdict": "unserviceable", "reason": "topic is outside astrology scope (see SCOPE)"}
    houses, karakas, varga = TOPICS[t]
    lagna = k["lagna"]["sign"]
    cfg = engine_config({})
    by_name = {p["name"]: p for p in k["planets"]}
    house_sign = lambda h: (lagna + h - 1) % 12

    def pl(p):
        return {"sign": p["sign_name"], "house": p["house"], "nakshatra": p["nakshatra_name"], "dignity": p["dignity"],
                "retrograde": p["retrograde"], "combust": p["combust"], "rules_houses": p["lord_of_houses"],
                f"{varga}_sign": SIGNS[p["varga_signs"][varga]]}

    topic_houses = {}
    for h in houses:
        lord = SIGN_LORD[house_sign(h)]
        lp = by_name.get(lord)
        topic_houses[str(h)] = {"sign": SIGNS[house_sign(h)], "lord": lord,
                                "lord_in": {"house": lp["house"], "sign": lp["sign_name"], "dignity": lp["dignity"]} if lp else None,
                                "occupants": [p["name"] for p in k["planets"] if p["house"] == h]}
    stack = current_dasha(kd, now, "vimshottari", 3)
    sat = positions_on(now, cfg)
    moon = by_name["Moon"]
    transits_now = {}
    for name, v in sat.items():
        if name in ("Saturn", "Jupiter", "Rahu", "Ketu", "Mars"):
            sign = int(v.sidereal_lon // 30)
            transits_now[name] = {"sign": SIGNS[sign], "from_lagna_house": (sign - lagna) % 12 + 1, "retrograde": v.retrograde}
    upcoming = []
    for planet in ("Saturn", "Jupiter", "Rahu"):
        for ev in ingresses(planet, now.astimezone(dt.timezone.utc), now.astimezone(dt.timezone.utc) + dt.timedelta(days=730), cfg):
            upcoming.append({"planet": planet, "enters": ev["to_sign_name"], "date": ev["utc"][:10], "house_from_lagna": (ev["to_sign"] - lagna) % 12 + 1,
                             "retrograde_reentry": not ev["direct"]})
    upcoming.sort(key=lambda e: e["date"])
    return {
        "verdict": "serviceable", "topic": t, "now": now.isoformat(timespec="minutes"), "current_month": now.strftime("%Y-%m"),
        "lagna": k["lagna"]["sign_name"], "moon": {"sign": moon["sign_name"], "nakshatra": moon["nakshatra_name"]},
        "houses_for_topic": topic_houses,
        "karaka_planets": {n: pl(by_name[n]) for n in karakas if n in by_name},
        "functional_nature": k["functional_nature"],
        "dasha_now": [{"level": s["level"], "lord": s["lord"], "until": s["end_local"][:10]} for s in stack],
        "dasha_periods_labelled_by_real_dates": _periods(k, now),
        "transits_now": transits_now, "upcoming_ingresses_24m": upcoming,
        "sade_sati": sade_sati_status(moon["sign"], SIGNS.index(transits_now["Saturn"]["sign"])),
        "yogas_present": [y["name"] for y in k["yogas"] if y.get("present") and y.get("effective")][:12],
        "manglik_effective": bool(k["doshas"].get("manglik", {}).get("effective", False)) if isinstance(k["doshas"].get("manglik"), dict) else None,
        "kalsarpa": bool(k["doshas"].get("kaal_sarpa", {}).get("full", False)),
    }


# ---- rate limit + conversation loop ----
_HITS: dict[str, deque] = defaultdict(deque)


def rate_ok(key: str, limit: int = 40, window: int = 3600) -> bool:
    q, now = _HITS[key], time.time()
    while q and q[0] < now - window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def system_text(profile: dict, now: dt.datetime) -> str:
    prof = f'{profile.get("name") or "Guest"}, born {profile["date"]} {profile.get("time") or "time unknown"}, {profile["place"]}'
    return (PROMPT.replace("{user_info}", prof).replace("{profiles}", prof).replace("{missing}", "none" if profile.get("time") else "birth time")
            .replace("{active_profile}", prof).replace("{time}", now.strftime("%A %d %B %Y, %H:%M IST")))


def clean(text: str) -> list[str]:
    text = text.replace("\\n", "\n").replace("*", "").strip()
    bubbles = [b.strip() for b in text.split("///") if b.strip()]
    return bubbles[:2] or ["Abhi system mein thodi takneeki dikkat aa rahi hai. Kripya ek baar phir koshish kijiye 🙏"]


def run_chat(client, kd, profile: dict, messages: list[dict], exhausted: bool, now: dt.datetime | None = None) -> list[str]:
    now = now or dt.datetime.now(IST)
    msgs = [{"role": m["role"], "content": m["content"][:600]} for m in messages[-20:]]
    system = system_text(profile, now)
    for _ in range(4):
        r = client.messages.create(model=MODEL, max_tokens=700, system=system, tools=[TOOL], messages=msgs)
        calls = [b for b in r.content if getattr(b, "type", "") == "tool_use"]
        if not calls:
            return clean("".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", "") == "text"))
        msgs.append({"role": "assistant", "content": r.content})
        results = []
        for c in calls:
            try:
                out = servicability(kd, c.input.get("topic", "other"), c.input.get("question", ""), now, exhausted)
            except Exception:  # noqa: BLE001 - the prompt defines the user-facing TOOL ERROR line
                out = {"verdict": "error"}
            results.append({"type": "tool_result", "tool_use_id": c.id, "content": json.dumps(out, ensure_ascii=False)})
        msgs.append({"role": "user", "content": results})
    return clean("")


# ---- Azure OpenAI (same prompt, same tool, OpenAI function-calling format) ----
def _oa_tool() -> dict:
    return {"type": "function", "function": {"name": TOOL["name"], "description": TOOL["description"], "parameters": TOOL["input_schema"]}}


def run_chat_azure(client, deployment: str, kd, profile: dict, messages: list[dict], exhausted: bool,
                   now: dt.datetime | None = None) -> list[str]:
    now = now or dt.datetime.now(IST)
    msgs = [{"role": "system", "content": system_text(profile, now)}]
    msgs += [{"role": m["role"], "content": m["content"][:600]} for m in messages[-20:]]
    for _ in range(4):
        r = client.chat.completions.create(model=deployment, messages=msgs, tools=[_oa_tool()], max_completion_tokens=900)
        m = r.choices[0].message
        if not getattr(m, "tool_calls", None):
            return clean(m.content or "")
        msgs.append({"role": "assistant", "content": m.content or "",
                     "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                    for c in m.tool_calls]})
        for c in m.tool_calls:
            try:
                a = json.loads(c.function.arguments or "{}")
                out = servicability(kd, a.get("topic", "other"), a.get("question", ""), now, exhausted)
            except Exception:  # noqa: BLE001
                out = {"verdict": "error"}
            msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(out, ensure_ascii=False)})
    return clean("")


def azure_client():
    """AzureOpenAI client from the standard variables, or None when not configured."""
    key, ep = os.environ.get("AZURE_OPENAI_API_KEY"), os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not (key and ep):
        return None
    from openai import AzureOpenAI
    return AzureOpenAI(api_key=key, azure_endpoint=ep, api_version=os.environ.get("OPENAI_API_VERSION", "2025-01-01-preview"), timeout=45.0)
