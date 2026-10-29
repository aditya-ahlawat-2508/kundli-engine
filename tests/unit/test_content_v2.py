"""V2 phase 21: content schema/store/freeze/lint, key space, offline drafter isolation, Tarabala and the content-backed endpoints."""
import ast
import json
import subprocess
import sys
from datetime import date, time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.content import ContentStore, keys, schema, set_default_store
from kundli.content.draft import SYSTEM, build_user, describe, draft_blocks
from kundli.content.freeze import freeze, review
from kundli.content.lint import banned_claims, errors, lint
from kundli.content.store import DEFAULT_DIR, DEFAULT_LOCK
from kundli.models import BirthInput, Place
from kundli.panchang.tarabala import TARAS, daily_facts, tara_class, tara_of

PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=28.6139, lon=77.2090, tz="Asia/Kolkata", source="manual")
SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "kundli"
GOOD = "Mars tends to give energy and drive in this placement; traditionally it asks for patience. No outcome is guaranteed."


@pytest.fixture(autouse=True)
def _isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path / "charts"))
    yield
    set_default_store(None)


def mk(root: Path, key: str, lang: str = "en", text: str = GOOD, status: str = "draft", reviewer: str | None = None) -> schema.Block:
    b = schema.Block(key=key, lang=lang, text=text, status=status, reviewer=reviewer, sources=["test"])  # type: ignore[arg-type]
    schema.write(root, b)
    return b


def frozen_store(tmp_path, items: dict[str, str], lang: str = "en") -> ContentStore:
    root, lock = tmp_path / "blocks", tmp_path / "content.lock"
    for key, text in items.items():
        mk(root, key, lang, text)
        review(root, key, lang, "Reviewer One")
    _, issues = freeze(root, lock)
    assert not errors(issues), issues
    return ContentStore(root, lock)


# ---- schema -------------------------------------------------------------------------------------------------
def test_key_validation_and_paths(tmp_path):
    assert schema.Block(key="house_report.mars.7", lang="en", text="x" * 30).topic == "house_report"
    for bad in ("single", "Has.Upper", "a..b", "a.b-c", "a. b"):
        with pytest.raises(ValueError):
            schema.Block(key=bad, lang="en", text="x")
    assert schema.path_for(tmp_path, "house_report.mars.7", "hi") == tmp_path / "hi" / "house_report" / "house_report.mars.7.md"


def test_hash_covers_content_not_status():
    a = schema.Block(key="a.b", lang="en", text="hello", sources=["s"])
    assert schema.block_hash(a) == schema.block_hash(a.model_copy(update={"status": "reviewed", "reviewer": "R", "hash": "x"}))
    assert schema.block_hash(a) != schema.block_hash(a.model_copy(update={"text": "hello!"}))
    assert schema.block_hash(a) != schema.block_hash(a.model_copy(update={"lang": "hi"}))
    assert schema.block_hash(a) != schema.block_hash(a.model_copy(update={"sources": ["t"]}))
    assert schema.block_hash(a) == schema.block_hash(a.model_copy(update={"text": "  hello \n"}))  # surrounding whitespace ignored


def test_roundtrip_with_unicode_and_errors(tmp_path):
    b = schema.Block(key="ascendant_report.aries", lang="hi", text="मेष लग्न: साहसी और ऊर्जावान।", sources=["स्रोत"])
    assert schema.loads(schema.dumps(b)) == b
    p = schema.write(tmp_path, b)
    assert schema.read(p) == b
    with pytest.raises(ValueError, match="front-matter"):
        schema.loads("no front matter")
    with pytest.raises(ValueError, match="closing"):
        schema.loads("---\nkey: a.b\n")


# ---- keys ---------------------------------------------------------------------------------------------------
def test_reachable_key_space():
    r = keys.reachable()
    assert {t: len(v) for t, v in r.items()} == {"house_report": 108, "rashi_report": 108, "ascendant_report": 12,
                                                  "nakshatra_report": 27, "daily": 243, "numerology": 45, "dosha": 26,
                                                  "match": 41, "lalkitab": 108, "remedy": 37}
    allk = [k for v in r.values() for k in v]
    assert len(allk) == len(set(allk)) == 755
    for k in allk:
        schema.Block(key=k, lang="en", text="x")  # every key is a valid block key
    assert keys.house_report("Mars", 7) == "house_report.mars.7" and keys.rashi_report("Sun", 0) == "rashi_report.sun.aries"
    assert keys.daily("vipat", "Purva Phalguni") == "daily.tara.vipat.nakshatra.purva_phalguni"
    assert keys.num(0.5) == "0_5" and keys.num(3.0) == "3" and keys.num(1.5) == "1_5" and keys.num(7) == "7"
    assert keys.reachable()["daily"][0] == "daily.tara.janma.nakshatra.ashwini"


# ---- store --------------------------------------------------------------------------------------------------
def test_store_serves_only_locked_unchanged_reviewed_blocks(tmp_path):
    root, lock = tmp_path / "blocks", tmp_path / "content.lock"
    mk(root, "house_report.mars.7")
    mk(root, "house_report.sun.1")
    review(root, "house_report.mars.7", "en", "R")
    review(root, "house_report.sun.1", "en", "R")
    mk(root, "house_report.moon.4")  # stays a draft
    store = ContentStore(root, lock)
    assert store.version == "empty" and store.get("house_report.mars.7", "en") is None  # reviewed but not locked yet
    freeze(root, lock)
    store = ContentStore(root, lock)
    assert store.get("house_report.mars.7", "en").status == "frozen"
    assert store.get("house_report.moon.4", "en") is None  # draft
    assert store.get("house_report.mars.7", "hi") is None and store.get("house_report.venus.1", "en") is None
    ok = store.lookup("house_report.sun.1", "en")
    assert ok["status"] == "ok" and ok["text"] == GOOD and ok["content_version"] == store.version != "empty"
    assert store.lookup("house_report.moon.4", "en")["status"] == "content_missing"
    # editing after the freeze stops serving the block
    b = schema.read(schema.path_for(root, "house_report.sun.1", "en"))
    schema.write(root, b.model_copy(update={"text": GOOD + " Edited."}))
    assert ContentStore(root, lock).get("house_report.sun.1", "en") is None
    # reverting to a draft stops serving it too
    schema.write(root, b.model_copy(update={"status": "draft"}))
    assert ContentStore(root, lock).get("house_report.sun.1", "en") is None


def test_default_store_override_and_empty_repo_lock():
    from kundli.content import lookup
    set_default_store(None)
    served = [p for p in DEFAULT_DIR.glob("*/*/*.md") if ContentStore().get(schema.read(p).key, schema.read(p).lang)]
    assert all(schema.read(p).status != "draft" for p in served)  # a draft is never served
    assert lookup("house_report.mars.7", "en")["status"] in ("ok", "content_missing")
    assert DEFAULT_LOCK.name == "content.lock"


# ---- freeze -------------------------------------------------------------------------------------------------
def test_review_requires_a_person(tmp_path):
    mk(tmp_path, "house_report.mars.7")
    with pytest.raises(ValueError, match="reviewer"):
        review(tmp_path, "house_report.mars.7", "en", "  ")
    b = review(tmp_path, "house_report.mars.7", "en", " Asha ")
    assert b.status == "reviewed" and b.reviewer == "Asha"


def test_freeze_is_deterministic_and_marks_blocks(tmp_path):
    s1 = frozen_store(tmp_path / "a", {"house_report.mars.7": GOOD, "house_report.sun.1": GOOD + " More."})
    s2 = frozen_store(tmp_path / "b", {"house_report.sun.1": GOOD + " More.", "house_report.mars.7": GOOD})
    assert s1.lock_path.read_bytes() == s2.lock_path.read_bytes()  # order-independent, no timestamps
    lock = json.loads(s1.lock_path.read_text())
    assert list(lock["blocks"]["en"]) == sorted(lock["blocks"]["en"]) and len(lock["content_version"]) == 64
    b = schema.read(schema.path_for(s1.blocks_dir, "house_report.mars.7", "en"))
    assert b.status == "frozen" and b.hash == lock["blocks"]["en"]["house_report.mars.7"]
    s3 = frozen_store(tmp_path / "c", {"house_report.mars.7": GOOD + " Changed.", "house_report.sun.1": GOOD + " More."})
    assert s3.version != s1.version
    again, _ = freeze(s1.blocks_dir, s1.lock_path)  # re-freezing changes nothing
    assert again["content_version"] == s1.version


def test_freeze_refuses_banned_claims_and_writes_nothing(tmp_path):
    root, lock = tmp_path / "blocks", tmp_path / "content.lock"
    mk(root, "house_report.mars.7", text="This ring is guaranteed to cure you. Buy now for only 500 rupees.")
    review(root, "house_report.mars.7", "en", "R")
    _, issues = freeze(root, lock)
    assert errors(issues) and not lock.exists() and not lock.with_suffix(".lock.tmp").exists()
    assert schema.read(schema.path_for(root, "house_report.mars.7", "en")).status == "reviewed"  # not marked frozen


# ---- lint ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,labels", [
    ("No outcome is guaranteed.", []), ("Results are guaranteed.", ["guaranteed outcome"]),
    ("किसी परिणाम की गारंटी नहीं है।", []), ("परिणाम की गारंटी है।", ["guaranteed outcome"]),
    ("The sign Cancer is nurturing.", []), ("This will cure cancer.", ["disease prediction or medical claim"]),
    ("You will die young.", ["death or fatality prediction"]), ("उसकी मृत्यु होगी।", ["death or fatality prediction"]),
    ("It is not a medical remedy.", []), ("Stop taking your medication and wear this.", ["medical instruction"]),
    ("Invest in this now.", ["financial instruction"]), ("Only 500 rupees today.", ["price or sales language"]),
    ("You must wear it immediately.", ["urgency or compulsion"]), ("A curse is upon you.", ["fear language"]),
    ("Mars tends to give energy; traditionally it asks for patience.", [])])
def test_banned_claims(text, labels):
    assert banned_claims(text) == labels


def test_lint_checks(tmp_path):
    root, lock = tmp_path / "blocks", tmp_path / "content.lock"
    mk(root, "house_report.mars.7", text="short")
    mk(root, "orphan.key.here", text=GOOD)
    mk(root, "house_report.sun.1", text=GOOD, status="reviewed", reviewer=None)
    wrong = mk(root, "house_report.moon.4")
    schema.path_for(root, "house_report.moon.4", "en").rename(root / "en" / "house_report" / "house_report.venus.4.md")
    (root / "en" / "house_report" / "broken.md").write_text("garbage")
    msgs = [str(i) for i in lint(ContentStore(root, lock))]
    joined = "\n".join(msgs)
    assert "empty or too short" in joined and "orphan" in joined and "requires a reviewer" in joined
    assert "does not match key/lang" in joined and "unparsable block" in joined
    assert wrong.key == "house_report.moon.4"


def test_lint_lock_and_coverage(tmp_path):
    store = frozen_store(tmp_path, {"house_report.mars.7": GOOD})
    assert not errors(lint(store))
    cov = errors(lint(store, ("en", "hi")))
    assert any("coverage:en" in i.where for i in cov) and any("coverage:hi" in i.where for i in cov)
    b = schema.read(schema.path_for(store.blocks_dir, "house_report.mars.7", "en"))
    schema.write(store.blocks_dir, b.model_copy(update={"text": GOOD + " Edited."}))
    assert any("hash differs" in str(i) for i in lint(ContentStore(store.blocks_dir, store.lock_path)))
    schema.path_for(store.blocks_dir, "house_report.mars.7", "en").unlink()
    assert any("no file" in str(i) for i in lint(ContentStore(store.blocks_dir, store.lock_path)))


def test_shipped_blocks_lint_clean_and_are_drafts_or_reviewed():
    store = ContentStore()
    issues = lint(store)
    assert not errors(issues), [str(i) for i in errors(issues)][:5]
    statuses = {schema.read(p).status for p in DEFAULT_DIR.glob("*/*/*.md")}
    assert statuses <= {"draft", "reviewed", "frozen"}


# ---- offline drafter ----------------------------------------------------------------------------------------
class FakeClient:
    def __init__(self):
        self.calls = []

    def complete(self, system, user, temperature=0.0):
        self.calls.append((system, user))
        return "  A balanced, traditional paragraph about this placement.  "


def test_drafter_writes_only_drafts_and_never_overwrites(tmp_path):
    c = FakeClient()
    ks = ["house_report.mars.7", "rashi_report.sun.aries"]
    out = draft_blocks(ks, "en", c, "fake-model", tmp_path, {"house_report.mars.7": ["classical excerpt"]})
    assert [b.status for b in out] == ["draft", "draft"] and len(c.calls) == 2
    assert out[0].sources == ["llm-draft:fake-model", "excerpt:0"] and out[0].text == "A balanced, traditional paragraph about this placement."
    assert "classical excerpt" in c.calls[0][1] and "classical excerpt" not in c.calls[1][1]
    assert draft_blocks(ks, "en", c, "fake-model", tmp_path) == [] and len(c.calls) == 2  # nothing overwritten
    assert len(draft_blocks(ks, "en", c, "fake-model", tmp_path, overwrite=True)) == 2
    assert "no medical" in SYSTEM and "never guaranteed" in SYSTEM


def test_describe_keys():
    assert describe("house_report.mars.7") == "Mars is placed in the 7th house of the birth chart."
    assert describe("house_report.mars.11").endswith("11th house of the birth chart.")
    assert describe("rashi_report.sun.aries") == "Sun is placed in the sign Aries in the birth chart."
    assert "Hasta" in describe("daily.tara.vipat.nakshatra.hasta") and "vipat tara" in describe("daily.tara.vipat.nakshatra.hasta")
    assert "Hindi" in build_user("ascendant_report.leo", "hi", [])


def test_draft_tool_is_not_importable_from_the_api():
    """Static: no module imports content.draft; runtime: importing the API never loads it."""
    offenders = []
    for path in SRC_ROOT.rglob("*.py"):
        if path.name == "draft.py" and path.parent.name == "content":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or "", *[(node.module or "") + "." + a.name for a in node.names]]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            if any(n.endswith(("content.draft", ".draft")) or n == "draft" for n in names):
                offenders.append(str(path))
    assert not offenders, offenders
    code = "import sys, kundli.api, kundli.compat.router, kundli.content; assert 'kundli.content.draft' not in sys.modules"
    assert subprocess.run([sys.executable, "-I", "-c", code], check=False, capture_output=True, text=True).returncode == 0


# ---- tarabala -----------------------------------------------------------------------------------------------
def test_tara_names_and_classes():
    assert tara_of(5, 5) == (1, "janma") and tara_of(5, 6) == (2, "sampat") and tara_of(5, 7) == (3, "vipat")
    assert tara_of(5, 13) == (9, "ati_mitra") and tara_of(5, 14) == (10, "janma") and tara_of(5, 4) == (27, "ati_mitra")
    assert [tara_of(0, n)[1] for n in range(9)] == TARAS
    assert {t: tara_class(t) for t in TARAS} == {
        "janma": "mixed", "sampat": "auspicious", "vipat": "inauspicious", "kshema": "auspicious", "pratyari": "inauspicious",
        "sadhaka": "auspicious", "vadha": "inauspicious", "mitra": "auspicious", "ati_mitra": "auspicious"}
    assert all(tara_of(a, b)[0] == (b - a) % 27 + 1 for a in range(27) for b in range(27))


@pytest.fixture(scope="module")
def natal():
    return generate(BirthInput(name="T", date=date(1990, 5, 5), time=time(10, 30), place=PLACE), EngineConfig())


def test_daily_facts(natal):
    f = daily_facts(natal, date(2026, 10, 10), PLACE.lat, PLACE.lon, PLACE.tz, EngineConfig())
    segs = f["segments"]
    assert segs and f["primary"] == segs[0] and 1 <= len(segs) <= 3
    assert all(abs(a["end_jd"] - b["start_jd"]) < 1e-5 for a, b in zip(segs, segs[1:], strict=False))
    nak0 = next(p for p in natal.planets if p.name == "Moon").nakshatra
    for s in segs:
        assert s["tara"] == TARAS[(s["count_from_birth_nakshatra"] % 9 or 9) - 1] and s["chandrabala"] in ("favourable", "unfavourable")
        assert 1 <= s["count_from_birth_nakshatra"] <= 27 and 0 <= nak0 < 27
    assert 0.99 < segs[-1]["end_jd"] - segs[0]["start_jd"] < 1.01
    assert f["tables_verified"] is False


# ---- endpoints with a frozen test store ---------------------------------------------------------------------
BODY = {"date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata", "as_of": "2026-10-10"}


def test_life_reports_with_and_without_content(tmp_path, natal):
    c = TestClient(app)
    moon = next(p for p in natal.planets if p.name == "Moon")
    mars = next(p for p in natal.planets if p.name == "Mars")
    items = {keys.house_report("Mars", mars.rashi_house): "Mars here tends to give drive. No outcome is guaranteed.",
             keys.rashi_report("Mars", mars.sign): "Mars in this sign tends to act directly and quickly.",
             keys.ascendant_report(natal.lagna["sign"]): "This ascendant tends to be steady and practical.",
             keys.nakshatra_report(moon.nakshatra_name): "This nakshatra tends to bring a gentle, observant nature."}
    set_default_store(frozen_store(tmp_path, items))
    h = c.post("/compat/general_house_report/mars", json=BODY).json()
    assert h["data"]["content"]["status"] == "ok" and h["data"]["content"]["text"].startswith("Mars here")
    assert h["data"]["facts"] == {"planet": "Mars", "house": mars.rashi_house, "sign": mars.sign_name}
    assert h["conventions_used"]["content_version"] == h["data"]["content"]["content_version"] != "empty"
    assert h["conventions_used"]["config"]["content_version"] == h["conventions_used"]["content_version"]
    for ep in ("general_rashi_report/mars", "general_ascendant_report", "general_nakshatra_report"):
        assert c.post("/compat/" + ep, json=BODY).json()["data"]["content"]["status"] == "ok", ep
    miss = c.post("/compat/general_house_report/sun", json=BODY).json()["data"]
    assert miss["content"]["status"] == "content_missing" and "text" not in miss["content"] and miss["facts"]["planet"] == "Sun"
    assert c.post("/compat/general_house_report/pluto", json=BODY).status_code == 422
    assert c.post("/compat/general_house_report/mars", json={**BODY, "time": None}).status_code == 422
    assert c.post("/compat/general_ascendant_report", json={**BODY, "time": None}).status_code == 422
    assert c.post("/compat/general_rashi_report/mars", json={**BODY, "time": None}).status_code == 200


def test_language_follows_config_and_output_is_deterministic(tmp_path, natal):
    mars = next(p for p in natal.planets if p.name == "Mars")
    key = keys.rashi_report("Mars", mars.sign)
    store = frozen_store(tmp_path, {key: "मंगल इस राशि में सीधे और तेज़ी से काम करता है।"}, lang="hi")
    set_default_store(store)
    c = TestClient(app)
    hi = c.post("/compat/general_rashi_report/mars", json={**BODY, "config": {"language": "hi"}})
    en = c.post("/compat/general_rashi_report/mars", json=BODY)
    assert hi.json()["data"]["content"]["status"] == "ok" and hi.json()["data"]["content"]["lang"] == "hi"
    assert en.json()["data"]["content"]["status"] == "content_missing"  # no English block exists: no fallback
    assert hi.content == c.post("/compat/general_rashi_report/mars", json={**BODY, "config": {"language": "hi"}}).content


def test_daily_endpoints(tmp_path, natal):
    c = TestClient(app)
    today = c.post("/compat/daily_nakshatra_prediction", json=BODY).json()["data"]
    nxt = c.post("/compat/daily_nakshatra_prediction/next", json=BODY).json()["data"]
    prev = c.post("/compat/daily_nakshatra_prediction/previous", json=BODY).json()["data"]
    assert (prev["facts"]["date"], today["facts"]["date"], nxt["facts"]["date"]) == ("2026-10-09", "2026-10-10", "2026-10-11")
    p = today["facts"]["primary"]
    key = keys.daily(p["tara"], p["nakshatra"])
    assert today["content"]["key"] == key and today["content"]["status"] == "content_missing"
    set_default_store(frozen_store(tmp_path, {key: "Today's Moon tends to support steady, practical work."}))
    assert c.post("/compat/daily_nakshatra_prediction", json=BODY).json()["data"]["content"]["status"] == "ok"
    cons = c.post("/compat/daily_nakshatra_consolidated", json=BODY).json()["data"]
    assert len(cons["segments"]) >= 1 and all("content" in s for s in cons["segments"])
    assert cons["segments"][0]["content"]["status"] == "ok"
    assert c.post("/compat/daily_nakshatra_prediction", json={**BODY, "as_of": None}).status_code == 422


def test_other_endpoints_use_the_store(tmp_path, natal):
    c = TestClient(app)
    n = natal.numerology
    items = {f"numerology.radical.{n['radical']}": "This number tends to bring a particular temperament.",
             f"numerology.daily.{c.post('/compat/numero_prediction/daily', json=BODY).json()['data']['daily_number']}":
                 "Today's number tends to favour quiet, steady effort.",
             "dosha.pitra.absent": "No pitra indicators were found; this is traditional reading only.",
             "dosha.pitra.present": "Some pitra indicators were found; this is traditional reading only."}
    set_default_store(frozen_store(tmp_path, items))
    rep = c.post("/compat/numero_report", json=BODY).json()["data"]["content"]
    assert rep["radical"]["status"] == "ok" and rep["destiny"]["status"] in ("ok", "content_missing")
    assert c.post("/compat/numero_prediction/daily", json=BODY).json()["data"]["content"]["status"] == "ok"
    assert c.post("/compat/pitra_dosha_report", json=BODY).json()["data"]["content"]["status"] == "ok"
    for ep in ("manglik", "kalsarpa_details", "sadhesati_current_status", "numero_fasts_report", "lalkitab_remedies/saturn"):
        assert c.post("/compat/" + ep, json=BODY).status_code == 200, ep
    g = {"name": "G", "date": "1992-11-20", "time": "06:15", "lat": 19.076, "lon": 72.8777, "tz": "Asia/Kolkata"}
    m = c.post("/compat/match_making_report", json={"boy": BODY, "girl": g}).json()["data"]
    assert set(m["content"]) >= {"kootas", "verdict", "nadi_dosha", "bhakoot_dosha"} and set(m["content"]["kootas"]) == set(keys.KOOTA_POINTS)
    assert all(v["key"].startswith("match.koota.") for v in m["content"]["kootas"].values())
    mm = c.post("/compat/match_manglik_report", json={"boy": BODY, "girl": g}).json()["data"]
    assert mm["content"]["key"].startswith("match.manglik.")


def test_every_content_key_built_by_endpoints_is_reachable(natal):
    """Keys the adapters can emit must all be in the reachable space (the linter's coverage universe)."""
    allk = keys.all_keys()
    c = TestClient(app)
    g = {"name": "G", "date": "1992-11-20", "time": "06:15", "lat": 19.076, "lon": 72.8777, "tz": "Asia/Kolkata"}

    def walk(x):
        if isinstance(x, dict):
            if "key" in x and "status" in x and "lang" in x:
                yield x["key"]
            for v in x.values():
                yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)

    seen = set()
    for ep in ("general_house_report/mars", "general_rashi_report/sun", "general_ascendant_report", "general_nakshatra_report",
               "daily_nakshatra_prediction", "daily_nakshatra_consolidated", "numero_report", "numero_prediction/daily",
               "numero_fasts_report", "manglik", "kalsarpa_details", "sadhesati_current_status", "pitra_dosha_report",
               "lalkitab_remedies/saturn"):
        seen |= set(walk(c.post("/compat/" + ep, json=BODY).json()["data"]))
    for ep in ("match_ashtakoot_report", "match_manglik_report", "match_making_report", "match_making_detailed_report"):
        seen |= set(walk(c.post("/compat/" + ep, json={"boy": BODY, "girl": g}).json()["data"]))
    assert len(seen) > 20 and seen <= allk, sorted(seen - allk)
