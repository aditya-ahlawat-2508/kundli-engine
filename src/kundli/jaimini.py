"""Jaimini: chara karakas, arudha padas, karakamsa, rashi drishti."""
from .aspects import rashi_drishti
from .core import Core
from .data.tables import SEVEN, SIGN_LORDS, SIGNS

KARAKA_NAMES = ["AK", "AmK", "BK", "MK", "PiK", "GK", "DK"]
KARAKA_FULL = {"AK": "Atmakaraka", "AmK": "Amatyakaraka", "BK": "Bhratrukaraka", "MK": "Matrukaraka",
               "PiK": "Putrakaraka", "GK": "Gnatikaraka", "DK": "Darakaraka"}


def chara_karakas(core: Core) -> dict[str, str]:
    """Seven-karaka scheme: Sun..Saturn ranked by degrees within sign, highest first (ties by name)."""
    ranked = sorted(SEVEN, key=lambda p: (-core.deg[p], p))
    return dict(zip(KARAKA_NAMES, ranked, strict=True))


def arudha_padas(core: Core) -> dict[str, int]:
    """Pada of house h: count from the house sign to its lord, then the same distance beyond the lord. If the
    result falls in the house itself or its 7th, take the 10th from it. A1=AL (Arudha Lagna), A12=UL (Upapada).
    Dual lordships use Mars (Scorpio) and Saturn (Aquarius)."""
    assert core.lagna_sign is not None
    out: dict[str, int] = {}
    for h in range(1, 13):
        hs = core.sign_of_house(h)
        lord = SIGN_LORDS[hs]
        d = (core.sign[lord] - hs) % 12
        a = (core.sign[lord] + d) % 12
        if a == hs or a == (hs + 6) % 12:
            a = (a + 9) % 12
        out[f"A{h}"] = a
    return out


def jaimini(core: Core) -> dict:
    if core.lagna_sign is None:
        raise ValueError("Jaimini analysis needs the lagna")
    ck = chara_karakas(core)
    pad = arudha_padas(core)
    ak = ck["AK"]
    karakamsa = core.varga["D9"][ak]
    return {
        "chara_karakas": {k: {"planet": p, "name": KARAKA_FULL[k], "degree_in_sign": core.deg[p]} for k, p in ck.items()},
        "arudha_padas": {k: {"sign": s, "sign_name": SIGNS[s], "house_from_lagna": (s - core.lagna_sign) % 12 + 1}
                         for k, s in pad.items()},
        "arudha_lagna": SIGNS[pad["A1"]], "upapada": SIGNS[pad["A12"]],
        "karakamsa": {"sign": karakamsa, "sign_name": SIGNS[karakamsa], "atmakaraka": ak},
        "rashi_drishti": {SIGNS[s]: [SIGNS[t] for t in rashi_drishti(s)] for s in range(12)},
    }
