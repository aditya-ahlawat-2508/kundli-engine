"""Server-rendered pages: trust pages, computed daily horoscope (/rashifal), free full kundli (/kundli).
No templating dependency; every page is plain HTML (SEO-readable, ~5 KB CSS, no web fonts)."""
from __future__ import annotations

import datetime as dt
import html
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from kundli.chart import current_dasha, to_dict
from kundli.compat.normalize import engine_config
from kundli.compat.router import ENGINE_LOCK
from kundli.service import aware
from kundli.transits import positions_on

router = APIRouter()
BASE = "https://times-astro-live.onrender.com"
e = html.escape

SIGNS = [("aries", "Aries", "मेष"), ("taurus", "Taurus", "वृषभ"), ("gemini", "Gemini", "मिथुन"),
         ("cancer", "Cancer", "कर्क"), ("leo", "Leo", "सिंह"), ("virgo", "Virgo", "कन्या"),
         ("libra", "Libra", "तुला"), ("scorpio", "Scorpio", "वृश्चिक"), ("sagittarius", "Sagittarius", "धनु"),
         ("capricorn", "Capricorn", "मकर"), ("aquarius", "Aquarius", "कुंभ"), ("pisces", "Pisces", "मीन")]
SLUGS = [s[0] for s in SIGNS]

CSS = """
:root{--bg:#FFFBF5;--card:#fff;--fg:#1A1714;--muted:#5E574F;--line:#EADFD1;--acc:#F28C1E;--ink:#B45309;--band:#FDF4E8}
:root[data-theme=dark]{--bg:#13100E;--card:#211B17;--fg:#F4EEE8;--muted:#BDB2A6;--line:#3A312A;--acc:#F29A3A;--ink:#F5B26B;--band:#1C1714}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#13100E;--card:#211B17;--fg:#F4EEE8;--muted:#BDB2A6;--line:#3A312A;--acc:#F29A3A;--ink:#F5B26B;--band:#1C1714}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI","Noto Sans Devanagari",Roboto,sans-serif}
a{color:var(--ink)}header{border-bottom:1px solid var(--line);background:var(--card)}
.w{max-width:960px;margin:0 auto;padding:0 16px}.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0;flex-wrap:wrap}
.logo{font-weight:800;font-size:20px;text-decoration:none;color:var(--fg)}.logo b{color:var(--acc)}
nav{display:flex;gap:14px;flex-wrap:wrap;font-size:14px;align-items:center}nav a{text-decoration:none;color:var(--fg)}nav a:hover{color:var(--ink)}
button,.btn{background:var(--acc);color:#1A1208;border:0;border-radius:10px;padding:11px 18px;font:600 15px inherit;cursor:pointer;text-decoration:none;display:inline-block}
.ghost{background:transparent;color:var(--fg);border:1px solid var(--line);padding:6px 10px;border-radius:8px;font-size:13px}
main{padding:24px 0 48px}h1{font-size:28px;line-height:1.25;margin:.2em 0 .4em}h2{font-size:20px;margin:1.4em 0 .4em}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:12px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.sign{display:block;text-align:center;text-decoration:none;color:var(--fg);padding:14px 8px;background:var(--card);border:1px solid var(--line);border-radius:12px}
.sign:hover{border-color:var(--acc)}.sign b{display:block;font-size:17px}.sign span{color:var(--muted);font-size:13px}
.muted{color:var(--muted);font-size:14px}.bar2{height:10px;background:var(--line);border-radius:6px;overflow:hidden}.bar2 i{display:block;height:100%;background:var(--acc)}
.row{display:grid;grid-template-columns:90px 1fr 44px;gap:10px;align-items:center;margin:8px 0}
label{display:block;font-size:14px;margin:10px 0 4px;color:var(--muted)}input,select{width:100%;padding:11px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--fg);font:inherit}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:7px 6px;border-bottom:1px solid var(--line);text-align:left}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:13px;background:var(--band);border:1px solid var(--line)}
.cta{background:var(--band);border:1px solid var(--line);border-radius:14px;padding:18px;margin:22px 0;text-align:center}
footer{border-top:1px solid var(--line);padding:22px 0;font-size:13px;color:var(--muted)}footer a{margin-right:14px}
.chart svg{max-width:100%;height:auto}.err{background:#FCE9E7;color:#A0281C;padding:10px 12px;border-radius:10px;margin:10px 0}
@media(max-width:560px){.two{grid-template-columns:1fr}.row{grid-template-columns:70px 1fr 40px}h1{font-size:23px}}
"""

THEME_JS = """<script>(function(){try{var t=localStorage.getItem('ta-theme');if(t)document.documentElement.dataset.theme=t}catch(e){}})();
function tt(){var d=document.documentElement,n=(d.dataset.theme==='dark'||(!d.dataset.theme&&matchMedia('(prefers-color-scheme:dark)').matches))?'light':'dark';d.dataset.theme=n;try{localStorage.setItem('ta-theme',n)}catch(e){}}</script>"""


def page(title: str, body: str, desc: str = "", path: str = "", lang: str = "en") -> HTMLResponse:
    hi = lang == "hi"
    nav = [("/rashifal" + ("?lang=hi" if hi else ""), "राशिफल" if hi else "Rashifal"), ("/kundli", "Free Kundli"),
           ("/#milan", "Kundli Milan"), ("/panchang/delhi", "Panchang"), ("/tools/moon-sign", "Moon Sign"), ("/astrologers", "Astrologers"), ("/", "Chat with Shreya")]
    links = "".join(f'<a href="{u}">{t}</a>' for u, t in nav)
    foot = " ".join(f'<a href="{u}">{t}</a>' for u, t in
                    [("/about", "About"), ("/contact", "Contact"), ("/privacy", "Privacy"), ("/terms", "Terms"), ("/refund", "Refund policy")])
    return HTMLResponse(f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | Times Astro</title>
<meta name="description" content="{e(desc)}"><link rel="canonical" href="{BASE}{path}">
<meta name="theme-color" content="#F28C1E">{THEME_JS}<style>{CSS}</style></head><body>
<header><div class="w bar"><a class="logo" href="/">Times<b>Astro</b></a><nav>{links}
<button class="ghost" onclick="tt()" aria-label="Toggle day / night">☀/☾</button></nav></div></header>
<main><div class="w">{body}</div></main>
<footer><div class="w"><p>{foot}</p><p>Astrology is guidance for reflection, not a substitute for medical, legal or financial advice.
Calculations use the Swiss Ephemeris (Lahiri ayanamsa).</p></div></footer></body></html>""")


# ---------------------------------------------------------------- trust pages
TRUST = {
    "about": ("About Times Astro", "Who runs Times Astro and how the astrology is calculated.", """
<h1>About Times Astro</h1>
<p>Times Astro is an astrology service from the Times Astro AI product team. Your kundli, panchang and kundli milan are
calculated by our own engine on the Swiss Ephemeris, using the Lahiri ayanamsa and Vimshottari dasha.</p>
<h2>How the guidance works</h2>
<p><b>Shreya</b> (chat) and <b>Jyoti</b> (call) are AI astrologers. They answer from your computed chart and the current planetary
transits. They are not human astrologers, and we say so on every screen. Astrology offers perspective, not certainty.</p>
<h2>What is free</h2>
<p>Your full kundli, the daily rashifal, panchang and your first chat answer are free.</p>"""),
    "contact": ("Contact us", "How to reach Times Astro support.", """
<h1>Contact us</h1>
<p>For help with a chat, a report or a payment, write to <a href="mailto:support@timesastro.example">support@timesastro.example</a>
(replace with your support address before launch). Please include the phone number or email you used and the time of the problem.</p>
<p>We reply within one working day.</p>"""),
    "privacy": ("Privacy policy", "What Times Astro collects and why.", """
<h1>Privacy policy</h1>
<p>We collect what you type to get a reading: name, date, time and place of birth, your questions, and basic usage events
(pages opened, buttons pressed) so we can fix what is broken. We use birth details only to compute your chart.</p>
<h2>Messages and reminders</h2>
<p>We message you only if you opt in, at most twice a month, and every message tells you how to stop. Anything that sounds like
a crisis stops reminders for that person permanently.</p>
<h2>AI processing</h2>
<p>Chat questions go to an AI language model provider to write the reply. We do not sell your data. You can ask us to delete your
data by writing to the contact address.</p>"""),
    "terms": ("Terms of use", "Terms for using Times Astro.", """
<h1>Terms of use</h1>
<ul><li>Times Astro offers astrological guidance for reflection. It is not medical, legal or financial advice.</li>
<li>Results depend on the birth details you enter. A wrong time or place gives a wrong chart.</li>
<li>Chat and call guidance is given by AI astrologers, not human astrologers.</li>
<li>You must be 18 or older to buy paid services.</li>
<li>We may change features and prices; the price shown before you pay is the price you pay.</li></ul>"""),
    "refund": ("Refund policy", "When Times Astro refunds a payment.", """
<h1>Refund policy</h1>
<ul><li>If a paid chat or call did not start because of a fault on our side, we refund the full amount.</li>
<li>If a report could not be generated, we refund it or regenerate it.</li>
<li>Used minutes are not refunded because an answer was not to your liking.</li>
<li>Refunds go back to the original payment method within 5 to 7 working days.</li></ul>
<p>Write to the contact address with your payment reference to request one.</p>"""),
}


def _mk(slug: str):
    def view() -> HTMLResponse:
        t, d, b = TRUST[slug]
        return page(t, b, d, "/" + slug)
    return view


for _s in TRUST:
    router.add_api_route("/" + _s, _mk(_s), methods=["GET"], response_class=HTMLResponse, include_in_schema=False)


# ---------------------------------------------------------------- daily horoscope
# Classical gochar rule: houses counted from the natal Moon sign where each transiting planet is favourable.
GOOD = {"Sun": {3, 6, 10, 11}, "Moon": {1, 3, 6, 7, 10, 11}, "Mars": {3, 6, 11}, "Mercury": {2, 4, 6, 8, 10, 11},
        "Jupiter": {2, 5, 7, 9, 11}, "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12}, "Saturn": {3, 6, 11}, "Rahu": {3, 6, 10, 11}}
AREAS = {"love": ["Venus", "Moon", "Jupiter"], "career": ["Sun", "Saturn", "Mercury", "Mars"],
         "health": ["Sun", "Mars", "Moon", "Saturn", "Rahu"], "money": ["Jupiter", "Venus", "Mercury", "Moon"]}
AREA_NAME = {"love": ("Love", "प्रेम"), "career": ("Career", "करियर"), "health": ("Health", "सेहत"), "money": ("Money", "धन")}
TEXT = {
    "love": {"hi": ["आज रिश्तों में थोड़ा धैर्य रखें; बड़ी बात कल पर छोड़ें।", "रिश्तों में सामान्य दिन; सुनना बोलने से ज़्यादा काम आएगा।", "आज साथी या अपनों से बात बनेगी; मन की बात कहने का अच्छा दिन।"],
             "en": ["Go slow in relationships today; leave big conversations for tomorrow.", "A steady day in relationships; listening will help more than speaking.", "Good day to open up to a partner or family; conversations go well."]},
    "career": {"hi": ["काम में रुकावट लग सकती है; नया जोखिम आज न लें।", "काम सामान्य चलेगा; पुराने अधूरे काम निपटाएँ।", "काम में पहचान और प्रगति के संकेत; फ़ैसले लेने का अच्छा दिन।"],
               "en": ["Work may feel stuck; avoid new risks today.", "Work runs normally; clear pending tasks.", "Signs of recognition and progress; a good day to decide."]},
    "health": {"hi": ["थकान संभव है; आराम और पानी का ध्यान रखें।", "सेहत ठीक रहेगी; दिनचर्या बनाए रखें।", "ऊर्जा अच्छी रहेगी; थोड़ी सैर या योग फ़ायदा देगा।"],
               "en": ["You may feel tired; rest and drink water.", "Health steady; keep your routine.", "Energy is good; a walk or yoga will help."]},
    "money": {"hi": ["खर्च पर नज़र रखें; आज बड़ा खर्च या उधार टालें।", "धन के मामले सामान्य; बजट पर टिके रहें।", "धन के लिए अनुकूल दिन; बातचीत या सौदे में फ़ायदा संभव।"],
              "en": ["Watch spending; avoid big purchases or loans today.", "Money matters are normal; stick to your budget.", "A supportive day for money; talks or deals may favour you."]},
}
WEEKDAY = [("Monday", "सोमवार", "White", "सफ़ेद"), ("Tuesday", "मंगलवार", "Red", "लाल"), ("Wednesday", "बुधवार", "Green", "हरा"),
           ("Thursday", "गुरुवार", "Yellow", "पीला"), ("Friday", "शुक्रवार", "Pink", "गुलाबी"), ("Saturday", "शनिवार", "Blue", "नीला"),
           ("Sunday", "रविवार", "Orange", "नारंगी")]
MOON_HOUSE = {1: ("मन अपने बारे में सोचेगा", "mind turns inward"), 2: ("परिवार और बोलचाल पर ध्यान", "focus on family and speech"),
              3: ("हिम्मत और पहल का दिन", "a day for courage and initiative"), 4: ("घर और मन की शांति ज़रूरी", "home and peace of mind matter"),
              5: ("रचनात्मकता और बच्चों से जुड़ाव", "creativity and bonds with children"), 6: ("मेहनत और प्रतिस्पर्धा में बढ़त", "an edge in effort and competition"),
              7: ("साझेदारी और मुलाक़ातें", "partnerships and meetings"), 8: ("अनिश्चितता; जल्दबाज़ी न करें", "some uncertainty; do not rush"),
              9: ("भाग्य और बड़ों का साथ", "luck and support from elders"), 10: ("कर्म और पहचान का दिन", "a day of work and recognition"),
              11: ("लाभ और दोस्तों का साथ", "gains and friends"), 12: ("खर्च और थकान; आराम करें", "expenses and fatigue; rest")}


@lru_cache(maxsize=8)
def sky(day: str) -> dict:
    """Sidereal signs of the grahas at noon IST on `day`, computed by the engine."""
    t = dt.datetime.fromisoformat(day + "T06:30:00+00:00")
    with ENGINE_LOCK:
        pos = positions_on(t, engine_config({}))
    return {n: int(p.sidereal_lon // 30) % 12 for n, p in pos.items()} | {"_moon_lon": pos["Moon"].sidereal_lon}


def reading(sign: int, day: str) -> dict:
    s = sky(day)
    out: dict = {"moon_house": (s["Moon"] - sign) % 12 + 1, "areas": {}}
    for area, planets in AREAS.items():
        pts = sum(1 for p in planets if ((s[p] - sign) % 12 + 1) in GOOD[p])
        out["areas"][area] = {"pct": round(35 + 60 * pts / len(planets)), "band": 0 if 35 + 60 * pts / len(planets) < 50 else (2 if 35 + 60 * pts / len(planets) >= 70 else 1)}
    nak = int(s["_moon_lon"] // (360 / 27)) + 1
    out["lucky_no"] = (nak + sign) % 9 + 1
    out["weekday"] = dt.date.fromisoformat(day).weekday()
    return out


def bars(r: dict, hi: bool) -> str:
    rows = ""
    for a, v in r["areas"].items():
        rows += (f'<div class="row"><b>{AREA_NAME[a][1 if hi else 0]}</b><div class="bar2"><i style="width:{v["pct"]}%"></i></div>'
                 f'<span class="muted">{v["pct"]}%</span></div><div class="muted" style="margin:-4px 0 6px 100px">{e(TEXT[a]["hi" if hi else "en"][v["band"]])}</div>')
    return rows


@router.get("/rashifal", response_class=HTMLResponse, include_in_schema=False)
def rashifal_index(lang: str = "en") -> HTMLResponse:
    hi = lang == "hi"
    day = dt.date.today().isoformat()
    cards = "".join(f'<a class="sign" href="/rashifal/{s}{"?lang=hi" if hi else ""}"><b>{h if hi else n}</b><span>{n if hi else h}</span></a>' for s, n, h in SIGNS)
    tog = f'<a href="/rashifal{"" if hi else "?lang=hi"}">{"English" if hi else "हिन्दी"}</a>'
    body = (f'<h1>{"आज का राशिफल" if hi else "Today’s Rashifal (Daily Horoscope)"}</h1>'
            f'<p class="muted">{day} · {"गोचर ग्रहों की आज की स्थिति से गणना" if hi else "Computed from today’s planetary transits (Moon-sign based, Lahiri)"} · {tog}</p>'
            f'<div class="grid">{cards}</div>')
    return page("Aaj ka Rashifal" if not hi else "आज का राशिफल", body, "Daily horoscope for all 12 rashis, computed from today's planetary positions.", "/rashifal", lang)


@router.get("/rashifal/{slug}", response_class=HTMLResponse, include_in_schema=False)
def rashifal_sign(slug: str, lang: str = "en") -> HTMLResponse:
    if slug not in SLUGS:
        raise HTTPException(404)
    hi = lang == "hi"
    i = SLUGS.index(slug)
    day = dt.date.today().isoformat()
    r = reading(i, day)
    wd = WEEKDAY[r["weekday"]]
    mh = MOON_HOUSE[r["moon_house"]][0 if hi else 1]
    name = SIGNS[i][2] if hi else SIGNS[i][1]
    other = f'/rashifal/{slug}{"" if hi else "?lang=hi"}'
    body = (f'<h1>{name} {"आज का राशिफल" if hi else "Horoscope Today"}</h1><p class="muted">{day} · {wd[1 if hi else 0]} · <a href="{other}">{"English" if hi else "हिन्दी"}</a></p>'
            f'<div class="card"><p>{"आज चंद्रमा आपकी राशि से" if hi else "The Moon is in your"} {r["moon_house"]}{" वें भाव में है" if hi else "th house from your sign"}: {e(mh)}.</p>'
            f'{bars(r, hi)}'
            f'<p>{"शुभ अंक" if hi else "Lucky number"}: <span class="pill">{r["lucky_no"]}</span> &nbsp; {"शुभ रंग" if hi else "Lucky colour"}: <span class="pill">{wd[3 if hi else 2]}</span></p></div>'
            f'<div class="cta"><b>{"अपनी कुंडली के हिसाब से जानें" if hi else "This is for everyone born under your Moon sign."}</b><p class="muted">'
            f'{"आपकी अपनी कुंडली अलग कहानी बताती है। शुरू में पहला जवाब मुफ़्त।" if hi else "Your own kundli tells a more personal story. First answer is free."}</p>'
            f'<a class="btn" href="/kundli">{"मुफ़्त कुंडली" if hi else "Get my free kundli"}</a> <a class="btn" href="/">{"Shreya से चैट" if hi else "Ask Shreya"}</a></div>'
            f'<h2>{"अन्य राशियाँ" if hi else "Other signs"}</h2><div class="grid">' +
            "".join(f'<a class="sign" href="/rashifal/{s}{"?lang=hi" if hi else ""}"><b>{h if hi else n}</b></a>' for s, n, h in SIGNS if s != slug) + "</div>"
            f'<p class="muted">{"गणना: गोचर ग्रह चंद्र राशि से शुभ/अशुभ भावों में हैं या नहीं (शास्त्रीय गोचर नियम)।" if hi else "Method: whether each transiting graha sits in a favourable house from your Moon sign (classical gochar rules). Percentages are a simple count, not a prediction."}</p>')
    return page(f"{SIGNS[i][1]} Horoscope Today ({SIGNS[i][2]})", body,
                f"{SIGNS[i][1]} daily horoscope: love, career, health and money, computed from today's planetary positions.", f"/rashifal/{slug}", lang)


# ---------------------------------------------------------------- free kundli
def _form(v: dict, err: str = "") -> str:
    g = lambda k: e(v.get(k, ""))
    er = f'<div class="err">{e(err)}</div>' if err else ""
    return f"""<h1>Free Kundli (Janam Kundli)</h1><p class="muted">Full chart, dasha, yogas and doshas in plain words. No login.</p>{er}
<form class="card" method="get" action="/kundli"><label>Name</label><input name="name" value="{g('name')}" maxlength="60">
<div class="two"><div><label>Date of birth</label><input type="date" name="date" value="{g('date')}" required></div>
<div><label>Time of birth (if known)</label><input type="time" name="time" value="{g('time')}"></div></div>
<label>Place of birth</label><input name="place" value="{g('place')}" required placeholder="e.g. Jaipur" maxlength="120">
<p class="muted">If you do not know the time, leave it empty; we use 12:00 and the Moon/dasha parts stay reliable, house placements may shift.</p>
<button type="submit">Show my kundli</button></form>"""


YOGA_PLAIN = "Yogas are planet combinations that colour a chart; presence is computed, interpretation is general."


@router.get("/kundli", response_class=HTMLResponse, include_in_schema=False)
def kundli_page(request: Request, name: str = "", date: str = "", time: str = "", place: str = "", style: str = "north") -> HTMLResponse:
    v = {"name": name, "date": date, "time": time, "place": place}
    if not (date and place):
        return page("Free Kundli", _form(v), "Free janam kundli online: chart, dasha, yogas, manglik and kaal sarp dosha.", "/kundli")
    from .app import Person, build
    try:
        kd, pl = build(Person(name=name, date=date, time=time or None, place=place))
    except HTTPException as ex:
        msg = {"place_not_found": "We could not find that place. Try the nearest big city.",
               "birth_date_in_future": "Date of birth cannot be in the future."}.get(str(ex.detail), "We could not build this chart. Check the details.")
        return page("Free Kundli", _form(v, msg), "", "/kundli")
    k = to_dict(kd)
    from kundli.render import north_indian, south_indian
    from kundli.render.common import view_for
    with ENGINE_LOCK:
        svg = (north_indian if style == "north" else south_indian).render(view_for(kd, "D1"))
    stack = current_dasha(kd, aware(dt.date.today().isoformat()), "vimshottari", 2)
    av = k["avakahada"]
    rows = "".join(f'<tr><td>{e(p["name"])}</td><td>{e(p["sign_name"])} {p["degree_in_sign"]:.1f}°{" (R)" if p.get("retrograde") else ""}</td>'
                   f'<td>{p["house"]}</td><td>{e(p["nakshatra_name"])} {p["pada"]}</td><td>{e(str(p.get("dignity", "")))}</td></tr>' for p in k["planets"])
    d = k["doshas"]
    man = d["manglik"]
    kal = d["kaal_sarpa"]
    ss = [x for x in d.get("sadhesati_events", []) if x["date"] >= dt.date.today().isoformat()][:1]
    m_txt = "Yes" if man["is_manglik"] else "No"
    m_int = " (intensity about %s%%)" % man["intensity_percent"] if man["is_manglik"] else ""
    k_txt = ("Present (%s)" % e(str(kal.get("type")))) if kal["present"] else "Not present"
    s_txt = ss[0]["date"] if ss else "none soon"
    dosha = ("<li><b>Manglik:</b> " + m_txt + m_int + ". Mars is in house " + str(man["mars_house"]) + ". Cancellations are checked by the engine.</li>"
             "<li><b>Kaal Sarp:</b> " + k_txt + ".</li><li><b>Sade Sati:</b> next phase change " + s_txt + ".</li>")
    yogas = [y for y in k["yogas"] if y.get("present") and y.get("effective")]
    ytxt = "".join(f'<li><b>{e(y["name"])}</b> <span class="muted">({e(", ".join(y["planets_involved"]))})</span></li>' for y in yogas[:12]) or "<li>No major yogas found.</li>"
    dtxt = ""
    if stack:
        dtxt = f'<p>Current Mahadasha: <b>{e(stack[0]["lord"])}</b> until {stack[0]["end_local"][:10]}' + \
               (f'; Antardasha: <b>{e(stack[1]["lord"])}</b> until {stack[1]["end_local"][:10]}' if len(stack) > 1 else "") + ".</p>"
    approx = '<div class="err">Birth time was not given, so we used 12:00. Lagna and houses may be off; Moon sign and nakshatra are usually safe.</div>' if not time else ""
    q = f"date={e(date)}&place={e(place)}&time={e(time)}&name={e(name)}"
    other = "south" if style == "north" else "north"
    body = (f'<h1>{e(name or "Your")} Kundli</h1><p class="muted">{e(date)} {e(time)} · {e(pl["name"])}</p>{approx}'
            f'<div class="card chart">{svg}<p class="muted"><a href="/kundli?{q}&style={other}">Show {other.title()} Indian style</a></p></div>'
            f'<div class="card"><h2 style="margin-top:0">Basics</h2><table><tr><td>Lagna (Ascendant)</td><td><b>{e(k["lagna"]["sign_name"])}</b></td></tr>'
            f'<tr><td>Moon sign (Rashi)</td><td><b>{e(av["sign"])}</b></td></tr><tr><td>Nakshatra</td><td><b>{e(av["nakshatra"])}</b> pada {av["charan"]}</td></tr>'
            f'<tr><td>Gana / Nadi / Yoni</td><td>{e(av["gana"])} / {e(av["nadi"])} / {e(av["yoni"])}</td></tr><tr><td>Name syllable</td><td>{e(av["name_syllable"])}</td></tr></table></div>'
            f'<div class="card"><h2 style="margin-top:0">Dasha now</h2>{dtxt}</div>'
            f'<div class="card"><h2 style="margin-top:0">Doshas</h2><ul>{dosha}</ul></div>'
            f'<div class="card"><h2 style="margin-top:0">Yogas</h2><ul>{ytxt}</ul><p class="muted">{YOGA_PLAIN}</p></div>'
            f'<div class="card"><h2 style="margin-top:0">Planet positions</h2><div style="overflow-x:auto"><table><tr><th>Planet</th><th>Sign</th><th>House</th><th>Nakshatra</th><th>Dignity</th></tr>{rows}</table></div></div>'
            f'<div class="cta"><b>Want to know what this means for your career, marriage or money?</b><p class="muted">First answer is free.</p>'
            f'<a class="btn" href="/">Ask Shreya</a> <a class="btn" href="/api/report.pdf?{q}">Download PDF</a></div>')
    return page("Your Kundli", body, "Free janam kundli.", "/kundli")


# ---------------------------------------------------------------- astrologers, tools, city panchang
@router.get("/astrologers", response_class=HTMLResponse, include_in_schema=False)
def astrologers() -> HTMLResponse:
    def card(n, role, price, langs, topics, cta):
        return (f'<div class="card"><h2 style="margin:0">{n} <span class="pill">AI astrologer</span></h2><p class="muted">{role}</p>'
                f'<p><b>{price}</b> · {langs}<br>{topics}</p><a class="btn" href="/">{cta}</a></div>')
    body = ("<h1>Our astrologers</h1><p class='muted'>Both are AI astrologers. They read your computed kundli and today’s transits. First answer is free.</p>"
            + card("Shreya", "Chat · career, marriage, money, relationships", "₹299 / 30 min", "Hindi, English, Hinglish", "Also: plans from ₹49", "Chat with Shreya")
            + card("Jyoti", "Call · talk it through in her voice", "₹299 / 15 min", "Hindi, English, Hinglish", "Best for a quick, focused question", "Call Jyoti"))
    return page("Astrologers", body, "Chat with Shreya or call Jyoti, AI astrologers on Times Astro.", "/astrologers")


@router.get("/tools/moon-sign", response_class=HTMLResponse, include_in_schema=False)
def moon_sign(date: str = "", time: str = "", place: str = "") -> HTMLResponse:
    form = f"""<h1>Moon Sign (Rashi) Calculator</h1><p class="muted">Vedic moon sign, nakshatra and sun sign from your birth details.</p>
<form class="card" method="get"><div class="two"><div><label>Date of birth</label><input type="date" name="date" value="{e(date)}" required></div>
<div><label>Time of birth</label><input type="time" name="time" value="{e(time)}"></div></div>
<label>Place of birth</label><input name="place" value="{e(place)}" required maxlength="120"><p></p><button>Find my rashi</button></form>"""
    if not (date and place):
        return page("Moon Sign Calculator", form, "Find your Vedic moon sign (rashi) and nakshatra.", "/tools/moon-sign")
    from .app import Person, build
    try:
        kd, pl = build(Person(date=date, time=time or None, place=place))
    except HTTPException:
        return page("Moon Sign Calculator", form + '<div class="err">Could not read those details. Check the date and place.</div>', "", "/tools/moon-sign")
    k = to_dict(kd)
    pm = {p["name"]: p for p in k["planets"]}
    note = "" if time else '<p class="muted">No time given, used 12:00. The Moon changes sign about every 2.5 days, so this is usually right but not on a sign-change day.</p>'
    res = (f'<div class="card"><h2 style="margin-top:0">Your Moon sign: {e(pm["Moon"]["sign_name"])}</h2><p>Nakshatra: <b>{e(pm["Moon"]["nakshatra_name"])}</b> pada {pm["Moon"]["pada"]}'
           f'<br>Vedic Sun sign: <b>{e(pm["Sun"]["sign_name"])}</b><br>Lagna: <b>{e(k["lagna"]["sign_name"])}</b></p>{note}'
           f'<a class="btn" href="/kundli?date={e(date)}&time={e(time)}&place={e(place)}">See full kundli</a></div>')
    return page("Moon Sign Calculator", form + res, "Your Vedic moon sign.", "/tools/moon-sign")


CITIES = ["delhi", "mumbai", "bengaluru", "kolkata", "chennai", "hyderabad", "pune", "jaipur", "lucknow", "ahmedabad", "chandigarh", "patna", "bhopal", "indore", "varanasi", "kanpur", "nagpur", "surat", "ranchi", "guwahati"]


@router.get("/panchang/{city}", response_class=HTMLResponse, include_in_schema=False)
async def city_panchang(city: str) -> HTMLResponse:
    if city not in CITIES:
        raise HTTPException(404)
    from .app import panchang
    d = await panchang(place=city.title())
    rows = [("Date", d["date"] + " · " + d["vara"]), ("Tithi", f'{d["tithi"]} (till {d["tithi_end"]})'), ("Nakshatra", f'{d["nakshatra"]} (till {d["nakshatra_end"]})'),
            ("Yoga", d["yoga"]), ("Karana", d["karana"]), ("Hindu month", d["month"]), ("Sunrise", d["sunrise"]), ("Sunset", d["sunset"]), ("Moonrise", d["moonrise"])]
    if d["festivals"]:
        rows.append(("Festival", ", ".join(d["festivals"])))
    t = "".join(f"<tr><td>{a}</td><td><b>{e(str(b))}</b></td></tr>" for a, b in rows if b and b != "None")
    links = " ".join(f'<a class="pill" href="/panchang/{c}">{c.title()}</a>' for c in CITIES)
    body = f'<h1>Aaj ka Panchang: {city.title()}</h1><div class="card"><table>{t}</table></div><p class="muted">Times are local for {city.title()}.</p><h2>Other cities</h2><p>{links}</p>'
    return page(f"Panchang today in {city.title()}", body, f"Today's panchang for {city.title()}: tithi, nakshatra, yoga, sunrise and sunset.", f"/panchang/{city}")
