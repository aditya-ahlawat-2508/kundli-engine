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
:root{--bg:#F7F6F2;--card:#fff;--fg:#1B1936;--muted:#5B5873;--line:#E4E2EC;--ink:#17143A;--ink2:#26225C;--gold:#F6A21A;--goldink:#8A4F00;--teal:#0B6B6A;--tealbg:#E3F3F1;--band:#EFEDF7;--bad:#B3261E;--onink:#F1F0FA;--mut2:#B9B6D6}
:root[data-theme=dark]{--bg:#0F0E24;--card:#1A1838;--fg:#F1F0FA;--muted:#AEABC8;--line:#2E2B57;--ink:#0A0918;--ink2:#1A1838;--goldink:#F6B94A;--teal:#6FD3CF;--tealbg:#12312F;--band:#16143A}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0F0E24;--card:#1A1838;--fg:#F1F0FA;--muted:#AEABC8;--line:#2E2B57;--ink:#0A0918;--ink2:#1A1838;--goldink:#F6B94A;--teal:#6FD3CF;--tealbg:#12312F;--band:#16143A}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 Mukta,"Noto Sans Devanagari",system-ui,sans-serif;padding-bottom:72px}
a{color:var(--goldink)}:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
header{background:var(--ink);color:var(--onink)}.w{max-width:1040px;margin:0 auto;padding:0 18px}
.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:60px}
.logo{font-weight:800;font-size:22px;letter-spacing:-.3px;text-decoration:none;color:#fff}.logo b{color:var(--gold)}
nav{display:flex;gap:18px;align-items:center;font-size:15px}nav a{color:var(--onink);text-decoration:none;opacity:.88}nav a:hover{opacity:1}
nav .dsk{display:none}@media(min-width:820px){nav .dsk{display:inline}body{padding-bottom:0}.tabs{display:none!important}}
.tg{background:transparent;border:1px solid #ffffff44;color:#fff;border-radius:10px;min-width:44px;height:40px;font:600 14px Mukta,sans-serif;cursor:pointer}
.btn,button.btn,button{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:48px;padding:0 22px;border:0;border-radius:12px;background:var(--gold);color:#1A1208;font:700 17px Mukta,sans-serif;text-decoration:none;cursor:pointer}
.btn.sec{background:transparent;color:var(--fg);border:1.5px solid var(--line)}.btn:active{transform:translateY(1px)}
main{padding:26px 0 40px}h1{font-size:clamp(28px,6.4vw,44px);line-height:1.15;margin:.1em 0 .3em;letter-spacing:-.5px;font-weight:800}
h2{font-size:clamp(21px,4.4vw,28px);line-height:1.25;margin:1.6em 0 .5em;font-weight:800}h3{margin:0 0 .2em;font-size:19px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin:12px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:10px}
.sign{display:block;text-align:center;text-decoration:none;color:var(--fg);padding:16px 8px;background:var(--card);border:1px solid var(--line);border-radius:12px;min-height:64px}
.sign:hover{border-color:var(--gold)}.sign b{display:block;font-size:19px}.sign span{color:var(--muted);font-size:14px}
.muted{color:var(--muted);font-size:15px}.bar2{height:10px;background:var(--line);border-radius:6px;overflow:hidden}.bar2 i{display:block;height:100%;background:linear-gradient(90deg,var(--gold),#E4572E)}
.row{display:grid;grid-template-columns:84px 1fr 44px;gap:10px;align-items:center;margin:8px 0}
label{display:block;font-size:15px;margin:12px 0 4px;color:var(--muted);font-weight:600}
input,select{width:100%;min-height:50px;padding:0 14px;border:1.5px solid var(--line);border-radius:12px;background:var(--bg);color:var(--fg);font:inherit}
input:focus,select:focus{border-color:var(--gold);outline:0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}table{width:100%;border-collapse:collapse;font-size:15px}td,th{padding:9px 6px;border-bottom:1px solid var(--line);text-align:left}
.pill{display:inline-block;padding:3px 12px;border-radius:99px;font-size:14px;background:var(--band);border:1px solid var(--line);color:var(--fg);text-decoration:none}
.ai{background:var(--tealbg);color:var(--teal);border-color:transparent;font-weight:700}
.cta{background:var(--band);border-radius:16px;padding:22px;margin:24px 0;text-align:center}
footer{background:var(--ink);color:var(--mut2);padding:28px 0;font-size:14px}footer a{color:var(--onink);margin-right:16px}
.chart svg{max-width:100%;height:auto}.err{background:#FCE9E7;color:var(--bad);padding:12px 14px;border-radius:12px;margin:12px 0}
.tabs{position:fixed;left:0;right:0;bottom:0;z-index:20;display:grid;grid-template-columns:repeat(5,1fr);background:var(--card);border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
.tabs a{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:60px;font-size:12.5px;font-weight:600;text-decoration:none;color:var(--muted)}
.tabs a svg{width:23px;height:23px}.tabs a.on{color:var(--goldink)}.tabs a.mid span.dot{background:var(--gold);color:#1A1208;width:46px;height:46px;border-radius:50%;display:grid;place-items:center;margin-top:-22px;box-shadow:0 4px 12px #0003}
/* home */
.hero{background:var(--ink);color:var(--onink);position:relative;overflow:hidden;padding:30px 0 40px}
.hero .w{position:relative;z-index:1;display:grid;gap:22px;grid-template-columns:1fr}@media(min-width:820px){.hero .w{grid-template-columns:1.1fr .9fr;align-items:center}}
.hero h1{color:#fff;font-size:clamp(32px,8vw,54px)}.hero p{color:var(--mut2);margin:.2em 0 0;max-width:34ch}
.hero .card{background:var(--ink2);border-color:#ffffff22;color:var(--onink)}.hero label{color:var(--mut2)}.hero input{background:#0E0C2A;border-color:#ffffff30;color:#fff}
.hero .chartbg{position:absolute;right:-60px;top:-40px;width:420px;opacity:.28;z-index:0}.hero .chartbg path{stroke-dasharray:1200;stroke-dashoffset:1200;animation:draw 2.4s ease-out forwards}
@keyframes draw{to{stroke-dashoffset:0}}@media(prefers-reduced-motion:reduce){.hero .chartbg path{animation:none;stroke-dashoffset:0}}
.today{display:flex;gap:10px 22px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin:-22px 0 0;position:relative;z-index:2;font-size:15px}
.today b{color:var(--fg)}.today span{color:var(--muted)}
.ast{display:grid;grid-template-columns:76px 1fr;gap:14px;align-items:center}.ast img{width:76px;height:76px;border-radius:50%;object-fit:cover;border:3px solid var(--gold)}
.price{font-weight:800;font-size:20px}.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px}
.tile{display:flex;align-items:center;gap:10px;min-height:56px;padding:0 14px;background:var(--card);border:1px solid var(--line);border-radius:12px;text-decoration:none;color:var(--fg);font-weight:700}
.tile:hover{border-color:var(--gold)}.prom{display:grid;gap:16px 28px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}.prom div{padding:2px 0}
@media(max-width:560px){.two{grid-template-columns:1fr 1fr}.row{grid-template-columns:70px 1fr 40px}}
"""

THEME_JS = """<script>(function(){try{var t=localStorage.getItem('ta-theme');if(t)document.documentElement.dataset.theme=t}catch(e){}})();
function tt(){var d=document.documentElement,n=(d.dataset.theme==='dark'||(!d.dataset.theme&&matchMedia('(prefers-color-scheme:dark)').matches))?'light':'dark';d.dataset.theme=n;try{localStorage.setItem('ta-theme',n)}catch(e){}}</script>"""


ICON = {
    "home": '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "kundli": '<path d="M12 2l10 10-10 10L2 12z"/><path d="M2 12h20M12 2v20"/>',
    "star": '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "wallet": '<rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 10h18M16 15h2"/>'}


def ic(n: str) -> str:
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[n]}</svg>'


def page(title: str, body: str, desc: str = "", path: str = "", lang: str = "en", wide: bool = False) -> HTMLResponse:
    hi = lang == "hi"
    nav = [("/rashifal" + ("?lang=hi" if hi else ""), "राशिफल" if hi else "Rashifal"), ("/kundli", "Free Kundli"), ("/tools/muhurat", "Muhurat"),
           ("/panchang/delhi", "Panchang"), ("/astrologers", "Astrologers")]
    links = "".join(f'<a class="dsk" href="{u}">{t}</a>' for u, t in nav)
    foot = " ".join(f'<a href="{u}">{t}</a>' for u, t in
                    [("/about", "About"), ("/contact", "Contact"), ("/privacy", "Privacy"), ("/terms", "Terms"), ("/refund", "Refund policy")])
    tabs = [("/", "Home", "home"), ("/kundli", "Kundli", "kundli"), ("/app", "Ask", "chat"), ("/rashifal", "Rashifal", "star"), ("/wallet", "Wallet", "wallet")]
    tb = "".join(f'<a href="{u}" class="{"on" if (path == u or (u != "/" and path.startswith(u))) else ""}{" mid" if k == "chat" else ""}">'
                 + (f'<span class="dot">{ic(k)}</span>' if k == "chat" else ic(k)) + f"<span>{t}</span></a>" for u, t, k in tabs)
    inner = body if wide else f'<div class="w">{body}</div>'
    return HTMLResponse(f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{e(title)} | Times Astro</title>
<meta name="description" content="{e(desc)}"><link rel="canonical" href="{BASE}{path}">
<meta name="theme-color" content="#17143A"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;600;700;800&display=swap">{THEME_JS}<style>{CSS}</style></head><body>
<header><div class="w bar"><a class="logo" href="/">Times<b>Astro</b></a><nav>{links}
<a href="/login" class="dsk">Login</a><button class="tg" onclick="tt()" aria-label="Switch day or night theme">☀/☾</button></nav></div></header>
<main{' style="padding:0"' if wide else ''}>{inner}</main>
<footer><div class="w"><p>{foot}</p><p>Shreya and Jyoti are AI astrologers. Astrology is guidance for reflection, not medical, legal or financial advice. Calculations use the Swiss Ephemeris (Lahiri ayanamsa).</p></div></footer>
<nav class="tabs" aria-label="Main">{tb}</nav></body></html>""")


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
    rows = [("Date", d["date"] + " · " + WEEKDAY[dt.date.fromisoformat(d["date"]).weekday()][0]), ("Tithi", f'{d["tithi"]} (till {d["tithi_end"]})'), ("Nakshatra", f'{d["nakshatra"]} (till {d["nakshatra_end"]})'),
            ("Yoga", d["yoga"]), ("Karana", d["karana"]), ("Hindu month", d["month"]), ("Sunrise", d["sunrise"]), ("Sunset", d["sunset"]), ("Moonrise", d["moonrise"])]
    if d["festivals"]:
        rows.append(("Festival", ", ".join(d["festivals"])))
    t = "".join(f"<tr><td>{a}</td><td><b>{e(str(b))}</b></td></tr>" for a, b in rows if b and b != "None")
    links = " ".join(f'<a class="pill" href="/panchang/{c}">{c.title()}</a>' for c in CITIES)
    body = f'<h1>Aaj ka Panchang: {city.title()}</h1><div class="card"><table>{t}</table></div><p class="muted">Times are local for {city.title()}.</p><h2>Other cities</h2><p>{links}</p>'
    return page(f"Panchang today in {city.title()}", body, f"Today's panchang for {city.title()}: tithi, nakshatra, yoga, sunrise and sunset.", f"/panchang/{city}")


# ---------------------------------------------------------------- muhurat finder (INDICATIVE: rules not astrologer-verified)
MUH = {
    "marriage": ("Marriage (Vivah)", {"Rohini", "Mrigashira", "Magha", "Uttara Phalguni", "Hasta", "Swati", "Anuradha", "Mula", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"}),
    "griha-pravesh": ("Griha Pravesh (house warming)", {"Rohini", "Mrigashira", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Anuradha", "Dhanishta", "Shatabhisha", "Revati"}),
    "vehicle": ("Vehicle purchase", {"Ashwini", "Rohini", "Punarvasu", "Pushya", "Hasta", "Anuradha", "Shravana", "Revati"}),
}
GOOD_DAYS = {"Monday", "Wednesday", "Thursday", "Friday", "Moon", "Mercury", "Jupiter", "Venus"}  # engine returns the weekday lord
RIKTA = ("Chaturthi", "Navami", "Chaturdashi", "Amavasya")
_pc: dict = {}


@router.get("/tools/muhurat", response_class=HTMLResponse, include_in_schema=False)
async def muhurat(kind: str = "marriage", city: str = "delhi") -> HTMLResponse:
    from .app import panchang
    if kind not in MUH:
        kind = "marriage"
    if city not in CITIES:
        city = "delhi"
    title, naks = MUH[kind]
    today = dt.date.today()
    found = []
    for n in range(45):
        d = (today + dt.timedelta(days=n)).isoformat()
        key = (d, city)
        if key not in _pc:
            _pc[key] = await panchang(date=d, place=city.title())
        p = _pc[key]
        if p["vara"] in GOOD_DAYS and p["nakshatra"] in naks and not any(t in p["tithi"] for t in RIKTA):
            found.append(p)
        if len(found) >= 10:
            break
    opts = "".join(f'<option value="{k}"{" selected" if k == kind else ""}>{v[0]}</option>' for k, v in MUH.items())
    copts = "".join(f'<option value="{c}"{" selected" if c == city else ""}>{c.title()}</option>' for c in CITIES)
    rows = "".join(f'<tr><td>{p["date"]}</td><td>{WEEKDAY[dt.date.fromisoformat(p["date"]).weekday()][0]}</td><td>{e(p["nakshatra"])}</td><td>{e(p["tithi"])}</td></tr>' for p in found) or "<tr><td colspan=4>No matching day in the next 45 days.</td></tr>"
    body = (f'<h1>Shubh Muhurat Finder</h1><div class="err" style="background:var(--band);color:var(--fg)"><b>Indicative only.</b> Days are picked by simple rules (good weekday, auspicious nakshatra, no Rikta tithi) and have not been verified by a pandit. '
            f'Check the exact time with your family astrologer before you fix a date.</div>'
            f'<form class="card" method="get"><div class="two"><div><label>For</label><select name="kind">{opts}</select></div><div><label>City</label><select name="city">{copts}</select></div></div><p></p><button>Find dates</button></form>'
            f'<div class="card"><h2 style="margin-top:0">{title}: next dates</h2><div style="overflow-x:auto"><table><tr><th>Date</th><th>Day</th><th>Nakshatra</th><th>Tithi</th></tr>{rows}</table></div>'
            f'<p class="muted">Nakshatra and tithi are taken at sunrise for {city.title()}. They can change during the day.</p></div>')
    return page(f"{title} Muhurat", body, f"Upcoming auspicious dates for {title.lower()}.", "/tools/muhurat")


# ---------------------------------------------------------------- new home page
HOME = {
    "hl": {"h1": "Aapki kundli. Free. Abhi.", "sub": "Janam ki details daaliye, 10 second mein poori kundli. Login nahi chahiye.",
           "dob": "Janam tithi", "tob": "Samay (pata ho to)", "pob": "Janam sthan (shehar)", "go": "Meri kundli dekhein", "fine": "Free · Private · Bina login",
           "ask": "Astrologer se poochiye", "ask_s": "Pehla jawab free. Uske baad kitna lagega, shuru karne se pehle dikhega.",
           "chat": "Shreya se chat", "call": "Jyoti se call", "free1": "Pehla jawab free", "permin": "per minute",
           "topics": "Aap kya jaanna chahte hain?", "ras": "Aaj ka rashifal", "ras_s": "Apni rashi chuniye. Aaj ke grahon se gina gaya hai.",
           "tools": "Aur free tools", "why": "Hamara vaada", "p1": "Keemat pehle", "p1d": "Chat ya call shuru karne se pehle aapko rate aur kul kharch dikhta hai. Koi chhupa charge nahi.",
           "p2": "AI hai, saaf likha hai", "p2d": "Shreya aur Jyoti AI astrologers hain. Yeh har jagah likha hota hai, paise dene se pehle bhi.",
           "p3": "Refund wahin, jahan se aaya", "p3d": "Hamari galti se chat ya call nahi hui to paisa original payment method mein wapas.",
           "p4": "Spam nahi", "p4d": "Reminder sirf tab, jab aap haan kahein. Mahine mein 2 se zyada nahi, aur STOP likhte hi band."},
    "en": {"h1": "Your kundli. Free. Right now.", "sub": "Enter your birth details and see your full kundli in 10 seconds. No login.",
           "dob": "Date of birth", "tob": "Time of birth (if known)", "pob": "Place of birth (city)", "go": "Show my kundli", "fine": "Free · Private · No login",
           "ask": "Ask an astrologer", "ask_s": "Your first answer is free. After that, you see the price before you start.",
           "chat": "Chat with Shreya", "call": "Call Jyoti", "free1": "First answer free", "permin": "per minute",
           "topics": "What do you want to know?", "ras": "Today’s rashifal", "ras_s": "Pick your sign. Calculated from today’s planets.",
           "tools": "More free tools", "why": "Our promises", "p1": "Price first", "p1d": "Before a chat or call starts, you see the rate and the total. No hidden charges.",
           "p2": "AI, clearly labelled", "p2d": "Shreya and Jyoti are AI astrologers. We say so everywhere, including before you pay.",
           "p3": "Refunds to where it came from", "p3d": "If a chat or call fails on our side, the money goes back to your original payment method.",
           "p4": "No spam", "p4d": "Reminders only if you say yes. At most 2 a month, and STOP ends them."}}
TOPICS = [("💼", "Career", "कैरियर", "/t/career"), ("💍", "Marriage", "शादी", "/t/marriage"), ("❤️", "Love", "प्यार", "/t/love"),
          ("💰", "Money", "पैसा", "/t/money"), ("✈️", "Videsh", "विदेश", "/t/foreign"), ("📅", "Muhurat", "मुहूर्त", "/tools/muhurat")]
CHART = ('<svg class="chartbg" viewBox="0 0 400 400" fill="none" stroke="#F6A21A" stroke-width="2" aria-hidden="true">'
         '<path d="M10 10H390V390H10Z M10 10L390 390 M390 10L10 390 M200 10L390 200L200 390L10 200Z"/></svg>')


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(lang: str = "hl") -> HTMLResponse:
    lang = lang if lang in HOME else "hl"
    t = HOME[lang]
    en = lang == "en"
    try:
        from .app import panchang
        d = await panchang(place="Delhi")
        today = (f'<div class="today"><span>{"Today, Delhi" if en else "Aaj, Delhi"}</span><b>{e(d["tithi"].title())}</b><span>Nakshatra <b>{e(d["nakshatra"])}</b></span>'
                 f'<span>{"Sunrise" if en else "Suryoday"} <b>{d["sunrise"]}</b></span><a href="/panchang/delhi">Panchang</a></div>')
    except Exception:  # noqa: BLE001 - home must render even if the engine is slow
        today = ""
    hero = (f'<section class="hero">{CHART}<div class="w"><div><h1>{t["h1"]}</h1><p>{t["sub"]}</p></div>'
            f'<form class="card" method="get" action="/kundli"><label for="d">{t["dob"]}</label><input id="d" type="date" name="date" required>'
            f'<label for="tm">{t["tob"]}</label><input id="tm" type="time" name="time">'
            f'<label for="pl">{t["pob"]}</label><input id="pl" name="place" required list="pls" autocomplete="off" placeholder="Jaipur">'
            f'<datalist id="pls"></datalist><p style="margin:14px 0 6px"><button class="btn" style="width:100%">{t["go"]}</button></p>'
            f'<div class="muted" style="color:var(--mut2);text-align:center">{t["fine"]}</div></form></div></section>')
    def ast(name, img, role, price, cta, href):
        return (f'<div class="card"><div class="ast"><img src="/static/{img}" alt="{name}" width="76" height="76"><div><h3>{name} <span class="pill ai">AI</span></h3>'
                f'<div class="muted">{role}</div></div></div><p style="margin:14px 0 4px"><span class="price">{price}</span> <span class="muted">· {t["free1"]}</span></p>'
                f'<a class="btn" style="width:100%" href="{href}">{cta}</a></div>')
    cards = ('<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">'
             + ast("Shreya", "shreya.webp", "Chat · career, shaadi, paisa" if not en else "Chat · career, marriage, money", "₹299 / 30 min", t["chat"], "/app?svc=chat")
             + ast("Jyoti", "jyoti.webp", "Call · seedhi baat" if not en else "Call · talk it through", "₹299 / 15 min", t["call"], "/app?svc=call") + "</div>")
    topics = '<div class="tiles">' + "".join(f'<a class="tile" href="{u}"><span aria-hidden="true">{i}</span>{n}</a>' for i, n, _h, u in TOPICS) + "</div>"
    signs = '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(104px,1fr))">' + "".join(
        f'<a class="sign" href="/rashifal/{s}"><b>{h}</b><span>{n}</span></a>' for s, n, h in SIGNS) + "</div>"
    tools = '<div class="tiles">' + "".join(f'<a class="tile" href="{u}">{n}</a>' for n, u in [
        ("Kundli Milan", "/app#milan"), ("Panchang", "/panchang/delhi"), ("Moon sign", "/tools/moon-sign"), ("Muhurat", "/tools/muhurat"), ("Astrologers", "/astrologers")]) + "</div>"
    prom = '<div class="prom">' + "".join(f"<div><h3>{t[k]}</h3><div class='muted'>{t[k + 'd']}</div></div>" for k in ("p1", "p2", "p3", "p4")) + "</div>"
    sw = f'<a class="pill" href="/?lang={"hl" if en else "en"}">{"Hinglish" if en else "English"}</a>'
    body = (hero + f'<div class="w">{today}<h2>{t["ask"]}</h2><p class="muted" style="margin-top:-6px">{t["ask_s"]}</p>{cards}'
            f'<h2>{t["topics"]}</h2>{topics}<h2>{t["ras"]}</h2><p class="muted" style="margin-top:-6px">{t["ras_s"]}</p>{signs}'
            f'<h2>{t["tools"]}</h2>{tools}<h2>{t["why"]}</h2><div class="card">{prom}</div><p>{sw}</p></div>'
            "<script>(function(){var p=document.getElementById('pl'),l=document.getElementById('pls'),tm;p.addEventListener('input',function(){clearTimeout(tm);var q=p.value;if(q.length<2)return;"
            "tm=setTimeout(function(){fetch('/api/places?q='+encodeURIComponent(q)).then(function(r){return r.json()}).then(function(a){l.innerHTML=(a.places||a||[]).slice(0,6).map(function(x){return '<option value=\"'+(x.label||x.name||x)+'\">'}).join('')}).catch(function(){})},250)})})();</script>")
    return page("Free Kundli, Rashifal, Panchang and AI Astrologers", body,
                "Free kundli in 10 seconds, daily rashifal, panchang, kundli milan. Chat with Shreya or call Jyoti, AI astrologers. Prices shown upfront.", "/", "en" if en else "hi", wide=True)
