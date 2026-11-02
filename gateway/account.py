"""Phone-OTP login, wallet and recharge. TEST MODE by default: OTP is returned in the response and recharge is simulated.
Set OTP_PROVIDER / PAY_PROVIDER env vars and implement send_otp / charge when a real vendor is chosen."""
from __future__ import annotations

import os
import random
import re
import secrets
import time

from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .extras import db
from .pages import page, e

router = APIRouter()
TEST = not os.environ.get("OTP_PROVIDER")
PAY_TEST = not os.environ.get("PAY_PROVIDER")
PACKS = [(49, 0), (99, 10), (199, 25), (499, 75), (999, 200)]  # (pay, bonus)


def init() -> None:
    with db() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS otps(phone TEXT PRIMARY KEY, code TEXT, exp REAL, tries INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, phone TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS wallet(id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, amount INTEGER, kind TEXT, ref TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS wa_outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, text TEXT, ts REAL, status TEXT);""")


def send_otp(phone: str, code: str) -> None:
    """Real SMS/WhatsApp provider goes here. Test mode: nothing is sent."""


def me(token: str | None) -> str | None:
    if not token:
        return None
    init()
    with db() as c:
        r = c.execute("SELECT phone FROM sessions WHERE token=?", (token,)).fetchone()
    return r["phone"] if r else None


def balance(phone: str) -> int:
    with db() as c:
        return c.execute("SELECT COALESCE(SUM(amount),0) FROM wallet WHERE phone=?", (phone,)).fetchone()[0]


class Phone(BaseModel):
    phone: str = Field(max_length=15)


class Verify(Phone):
    code: str = Field(max_length=6)


def norm(p: str) -> str:
    d = re.sub(r"\D", "", p)[-10:]
    if not re.fullmatch(r"[6-9]\d{9}", d):
        raise HTTPException(422, "invalid_phone")
    return d


@router.post("/api/auth/otp")
def otp(b: Phone) -> dict:
    init()
    ph = norm(b.phone)
    code = f"{random.randint(0, 999999):06d}"
    with db() as c:
        old = c.execute("SELECT exp FROM otps WHERE phone=?", (ph,)).fetchone()
        if old and old["exp"] - 300 > time.time() - 30:
            raise HTTPException(429, "wait_30_seconds")
        c.execute("REPLACE INTO otps(phone,code,exp,tries) VALUES(?,?,?,0)", (ph, code, time.time() + 300))
    send_otp(ph, code)
    return {"sent": True, "test_mode": TEST, **({"test_otp": code} if TEST else {})}


@router.post("/api/auth/verify")
def verify(b: Verify, resp: Response) -> dict:
    init()
    ph = norm(b.phone)
    with db() as c:
        r = c.execute("SELECT * FROM otps WHERE phone=?", (ph,)).fetchone()
        if not r or r["exp"] < time.time() or r["tries"] >= 5:
            raise HTTPException(400, "otp_expired")
        if r["code"] != b.code:
            c.execute("UPDATE otps SET tries=tries+1 WHERE phone=?", (ph,))
            raise HTTPException(400, "wrong_otp")
        c.execute("DELETE FROM otps WHERE phone=?", (ph,))
        tok = secrets.token_urlsafe(24)
        c.execute("INSERT INTO sessions VALUES(?,?,?)", (tok, ph, time.time()))
        if not c.execute("SELECT 1 FROM wallet WHERE phone=?", (ph,)).fetchone():
            c.execute("INSERT INTO wallet(phone,amount,kind,ref,ts) VALUES(?,?,?,?,?)", (ph, 0, "open", "signup", time.time()))
    resp.set_cookie("ta_session", tok, max_age=30 * 86400, httponly=True, samesite="lax")
    return {"ok": True, "phone": ph}


@router.get("/api/wallet")
def wallet(ta_session: str | None = Cookie(None)) -> dict:
    ph = me(ta_session)
    if not ph:
        raise HTTPException(401, "login_required")
    with db() as c:
        tx = [dict(x) for x in c.execute("SELECT amount,kind,ref,ts FROM wallet WHERE phone=? AND kind!='open' ORDER BY id DESC LIMIT 20", (ph,))]
    return {"phone": ph, "balance": balance(ph), "packs": PACKS, "payment_test_mode": PAY_TEST, "transactions": tx}


class Recharge(BaseModel):
    pay: int


@router.post("/api/wallet/recharge")
def recharge(b: Recharge, ta_session: str | None = Cookie(None)) -> dict:
    ph = me(ta_session)
    if not ph:
        raise HTTPException(401, "login_required")
    pack = next((p for p in PACKS if p[0] == b.pay), None)
    if not pack:
        raise HTTPException(422, "unknown_pack")
    if not PAY_TEST:
        raise HTTPException(501, "implement charge() for the chosen provider")
    with db() as c:
        c.execute("INSERT INTO wallet(phone,amount,kind,ref,ts) VALUES(?,?,?,?,?)", (ph, pack[0] + pack[1], "recharge_test", f"TEST-{secrets.token_hex(4)}", time.time()))
    return {"balance": balance(ph), "credited": pack[0] + pack[1], "test_mode": True}


@router.post("/api/wallet/spend")
def spend(b: Recharge, ta_session: str | None = Cookie(None)) -> dict:
    ph = me(ta_session)
    if not ph:
        raise HTTPException(401, "login_required")
    if b.pay <= 0 or balance(ph) < b.pay:
        raise HTTPException(402, "insufficient_balance")
    with db() as c:
        c.execute("INSERT INTO wallet(phone,amount,kind,ref,ts) VALUES(?,?,?,?,?)", (ph, -b.pay, "spend", "chat/call", time.time()))
    return {"balance": balance(ph)}


@router.post("/api/whatsapp/send")
def wa_send(ta_session: str | None = Cookie(None)) -> dict:
    """Mock WhatsApp: queues a message to the logged-in number. Replace body with a Cloud API / BSP call."""
    ph = me(ta_session)
    if not ph:
        raise HTTPException(401, "login_required")
    init()
    with db() as c:
        c.execute("INSERT INTO wa_outbox(phone,text,ts,status) VALUES(?,?,?,?)", (ph, "Your kundli PDF is ready (test message)", time.time(), "mock_not_sent"))
    return {"queued": True, "status": "mock_not_sent"}


LOGIN_JS = """
<div class="card" id="lg"><p class="muted">TEST MODE: no SMS is sent; the code appears below.</p>
<label>Mobile number</label><input id="ph" inputmode="numeric" maxlength="10" placeholder="10-digit number">
<p><button onclick="so()">Get OTP</button></p><div id="o" hidden><label>OTP</label><input id="cd" inputmode="numeric" maxlength="6">
<p><button onclick="vo()">Verify and continue</button></p></div><p id="m" class="muted"></p></div>
<script>
async function j(u,b){var r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return [r.ok,await r.json()]}
async function so(){var x=await j('/api/auth/otp',{phone:ph.value});m.textContent=x[0]?('OTP sent'+(x[1].test_otp?' (test OTP: '+x[1].test_otp+')':'')):('Error: '+(x[1].detail||''));if(x[0])o.hidden=false}
async function vo(){var x=await j('/api/auth/verify',{phone:ph.value,code:cd.value});if(x[0])location='/wallet';else m.textContent='Error: '+(x[1].detail||'')}
</script>"""


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page() -> HTMLResponse:
    return page("Login", "<h1>Login with mobile number</h1>" + LOGIN_JS, "Log in to Times Astro with your mobile number.", "/login")


@router.get("/wallet", response_class=HTMLResponse, include_in_schema=False)
def wallet_page(ta_session: str | None = Cookie(None)) -> HTMLResponse:
    ph = me(ta_session)
    if not ph:
        return page("Wallet", "<h1>Wallet</h1><p>Please <a href='/login'>log in</a> first.</p>", "", "/wallet")
    packs = "".join(f'<button style="margin:4px" onclick="rc({p})">Pay ₹{p}' + (f" + ₹{b} bonus" if b else "") + "</button>" for p, b in PACKS)
    body = (f'<h1>Wallet</h1><div class="card"><p class="muted">{e(ph)}</p><h2 id="bal" style="margin:0">₹{balance(ph)}</h2></div>'
            f'<div class="card"><h2 style="margin-top:0">Add money</h2><p class="muted">TEST MODE: UPI, GPay, PhonePe and Paytm are simulated. No real money moves.</p>{packs}'
            f'<p><span class="pill">UPI</span> <span class="pill">GPay</span> <span class="pill">PhonePe</span> <span class="pill">Paytm</span></p><p id="m" class="muted"></p></div>'
            "<script>async function rc(p){var r=await fetch('/api/wallet/recharge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pay:p})});"
            "var d=await r.json();if(r.ok){bal.textContent='₹'+d.balance;m.textContent='Added ₹'+d.credited+' (test)'}else m.textContent=d.detail}</script>")
    return page("Wallet", body, "", "/wallet")
