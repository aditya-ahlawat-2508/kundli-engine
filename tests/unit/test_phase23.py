"""V2 phase 23: geo/timezone endpoints, ephemeris cache, provider client, shadow mode, cutover, ops and concurrency."""
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from kundli import ephemeris, ops
from kundli.api import app
from kundli.compat import cutover, provider, shadow
from kundli.config import EngineConfig
from kundli.tzinfo_lookup import timezone_details, transitions, zone_at

SECRET = "Zyxwv Secretname"
BODY = {"name": SECRET, "date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}


@pytest.fixture(autouse=True)
def _isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path / "charts"))
    for var in ("KUNDLI_SHADOW_LOG", "KUNDLI_CUTOVER_FILE", "KUNDLI_OPS_TOKEN", "KUNDLI_SHADOW_SALT", "KUNDLI_PROVIDER_URL",
                "KUNDLI_PROVIDER_KEY", "KUNDLI_PROVIDER_TOS_CHECKED"):
        monkeypatch.delenv(var, raising=False)
    yield
    provider.set_client(None)


# ---- timezone ------------------------------------------------------------------------------------------------
def test_zone_lookup_and_transitions():
    assert zone_at(28.6139, 77.2090) == "Asia/Kolkata" and zone_at(51.5, -0.12) == "Europe/London"
    ny = transitions("America/New_York", 2024)
    assert [(t["utc"], t["offset_before_seconds"], t["offset_after_seconds"]) for t in ny] == [
        ("2024-03-10T07:00:00+00:00", -18000, -14400), ("2024-11-03T06:00:00+00:00", -14400, -18000)]
    assert transitions("Asia/Kolkata", 2025) == []
    assert len(transitions("Europe/London", 2024)) == 2 and len(transitions("Australia/Sydney", 2024)) == 2


def test_timezone_details_dst_states():
    summer = timezone_details("America/New_York", date(2024, 7, 1))
    winter = timezone_details("America/New_York", date(2024, 1, 1))
    assert (summer["utc_offset_seconds"], summer["is_dst"], summer["abbreviation"], summer["standard_offset_seconds"]) == (-14400, True, "EDT", -18000)
    assert (winter["utc_offset_seconds"], winter["is_dst"], winter["abbreviation"]) == (-18000, False, "EST")
    gap = timezone_details("America/New_York", date(2024, 3, 10), time(2, 30))
    assert gap["kind"] == "nonexistent"
    overlap = [timezone_details("America/New_York", date(2024, 11, 3), time(1, 30), f) for f in (0, 1)]
    assert [o["kind"] for o in overlap] == ["ambiguous", "ambiguous"] and overlap[0]["utc_offset_seconds"] != overlap[1]["utc_offset_seconds"]
    war = timezone_details("Asia/Kolkata", date(1943, 6, 1))  # India's wartime offset, from the historical rules
    assert war["utc_offset_seconds"] == 23400 and war["is_dst"] is True
    assert timezone_details("Asia/Kolkata", date(1900, 1, 1))["abbreviation"] in ("MMT", "HMT", "+0553", "LMT", "+0521")
    with pytest.raises(ValueError, match="unknown time zone"):
        timezone_details("Mars/Olympus", date(2024, 1, 1))


def test_geo_endpoints():
    c = TestClient(app)
    g = c.post("/compat/geo_details", json={"place": "Agra"}).json()
    assert g["data"]["count"] >= 1 and g["data"]["places"][0]["tz"] == "Asia/Kolkata" and g["conventions_used"]["engine_version"]
    assert c.post("/compat/geo_details", json={"place": "Zzzzqqq Nowhere"}).status_code == 404
    assert c.post("/compat/geo_details", json={"place": "A"}).status_code == 422
    assert len(c.post("/compat/geo_details", json={"place": "Springfield", "limit": 2}).json()["data"]["places"]) <= 2
    t = c.post("/compat/timezone_with_dst", json={"lat": 40.7128, "lon": -74.006, "date": "2024-07-01"}).json()["data"]
    assert t["timezone"] == "America/New_York" and t["is_dst"] is True and len(t["transitions_in_year"]) == 2
    by_place = c.post("/compat/timezone_with_dst", json={"place": "Agra", "date": "2025-01-01", "time": "08:00"}).json()["data"]
    assert by_place["timezone"] == "Asia/Kolkata" and by_place["utc_offset_seconds"] == 19800 and by_place["place"] == "Agra"
    for bad in ({"date": "2025-01-01"}, {"lat": 91, "lon": 0, "date": "2025-01-01"}, {"lat": 1, "lon": 1, "date": "nope"},
                {"lat": 1, "lon": 1, "date": "2025-01-01", "fold": 2}, {"place": "Zzzzqqq", "date": "2025-01-01"}):
        assert c.post("/compat/timezone_with_dst", json=bad).status_code in (404, 422), bad


# ---- ephemeris cache -----------------------------------------------------------------------------------------
def test_ephemeris_cache_is_transparent_and_keyed_by_mode():
    jd = 2460000.5
    ephemeris.clear_cache()
    cold = ephemeris.planet_positions(jd, EngineConfig())
    info = ephemeris.cache_info()
    assert info.misses > 0 and info.hits == 0
    warm = ephemeris.planet_positions(jd, EngineConfig())
    assert warm == cold and ephemeris.cache_info().hits >= info.misses  # every call served from the cache
    raman = ephemeris.planet_positions(jd, EngineConfig(ayanamsa="raman"))
    assert raman[0].sidereal_lon != cold[0].sidereal_lon and raman[0].tropical_lon == cold[0].tropical_lon
    ephemeris.clear_cache()
    assert ephemeris.planet_positions(jd, EngineConfig(ayanamsa="raman")) == raman  # cache never mixed sidereal modes
    assert ephemeris.planet_positions(jd, EngineConfig()) == cold


# ---- provider client -----------------------------------------------------------------------------------------
def test_provider_env_guards():
    with pytest.raises(provider.ProviderNotConfigured, match="KUNDLI_PROVIDER_URL"):
        provider.from_env({})
    with pytest.raises(provider.ProviderNotConfigured, match="terms of service"):
        provider.from_env({"KUNDLI_PROVIDER_URL": "http://x", "KUNDLI_PROVIDER_KEY": "k"})
    c = provider.from_env({"KUNDLI_PROVIDER_URL": "http://x/", "KUNDLI_PROVIDER_KEY": "k", "KUNDLI_PROVIDER_TOS_CHECKED": "1",
                           "KUNDLI_PROVIDER_TIMEOUT": "3"})
    assert (c.base_url, c.key, c.timeout) == ("http://x/", "k", 3.0)
    secret = provider.from_env({"KUNDLI_PROVIDER_URL": "http://x", "KUNDLI_PROVIDER_KEY": "super-secret-key", "KUNDLI_PROVIDER_TOS_CHECKED": "1"})
    assert "super-secret-key" not in repr(secret) and "super-secret-key" not in str(secret)  # the credential never leaks via repr


def test_http_provider_client_against_a_local_server():
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"], seen["auth"] = self.path, self.headers.get("Authorization")
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            data = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    c = provider.HttpProviderClient(f"http://127.0.0.1:{srv.server_port}/api", "secret-key", 5.0)
    assert c.call("planets", {"a": 1}) == {"ok": True}
    srv.server_close()
    assert seen == {"path": "/api/planets", "auth": "Bearer secret-key", "body": {"a": 1}}


# ---- shadow --------------------------------------------------------------------------------------------------
def test_input_id_is_keyed_and_deterministic(monkeypatch):
    monkeypatch.setenv("KUNDLI_SHADOW_SALT", "salt-one")
    a = shadow.input_id({"x": 1, "y": [2, 3]})
    assert a == shadow.input_id({"y": [2, 3], "x": 1}) and len(a) == 16 and a != shadow.input_id({"x": 2, "y": [2, 3]})
    monkeypatch.setenv("KUNDLI_SHADOW_SALT", "salt-two")
    assert shadow.input_id({"x": 1, "y": [2, 3]}) != a


def test_diff_summary_has_paths_and_deltas_but_no_values():
    mine = {"planets": [{"name": "Sun", "longitude": 100.0}, {"name": "Moon", "longitude": 200.0}], "tithi": 5, "extra": 1}
    theirs = {"planets": [{"name": "Sun", "longitude": 100.5}, {"name": "Moon", "longitude": 200.0}], "tithi": 6, "only_theirs": 1}
    s = shadow.summarize_diff("planets", theirs, mine)
    assert s["mismatched"] >= 2 and 0 <= s["match_rate"] < 1
    paths = {f["path"] for f in s["fields"]}
    assert any("longitude" in p for p in paths) and "tithi" in paths and "only_theirs" in paths
    text = json.dumps(s)
    assert "100.5" not in text and "200.0" not in text  # no response values, only paths/kinds/deltas
    lon = next(f for f in s["fields"] if "longitude" in f["path"])
    assert lon["kind"] == "longitude" and lon["delta"] == pytest.approx(0.5)


def test_record_contains_no_request_data(monkeypatch):
    monkeypatch.setenv("KUNDLI_SHADOW_SALT", "s")
    rec = shadow.record("planets", BODY, {"compared": 3, "mismatched": 0, "match_rate": 1.0, "fields": []}, "compared",
                        datetime(2026, 1, 1, 12, 0, 5, 999, tzinfo=UTC))
    text = json.dumps(rec)
    for secret in (SECRET, "Zyxwv", "28.6139", "77.209", "1990-05-05", "10:30", "Asia/Kolkata"):
        assert secret not in text, secret
    assert rec["ts"] == "2026-01-01T12:00:05+00:00" and rec["endpoint"] == "planets" and len(rec["input_id"]) == 16


def test_classification_rows(tmp_path, monkeypatch):
    rows = tmp_path / "c.yaml"
    rows.write_text("- {endpoint: 'basic_panchang*', path: 'sun*', class: convention, note: sunrise definition (docs/conventions.md)}\n"
                    "- {endpoint: '*', path: 'bug.*', class: bug, note: ours}\n")
    monkeypatch.setattr(shadow, "CLASSIFICATIONS", rows)
    shadow.classifications.cache_clear()
    assert shadow.classify("basic_panchang/sunrise", "sunrise") == "convention" and shadow.classify("planets", "sunrise") is None
    assert shadow.classify("anything", "bug.x") == "bug"
    bad = tmp_path / "bad.yaml"
    bad.write_text("- {endpoint: x, path: y, class: whatever, note: n}\n")
    monkeypatch.setattr(shadow, "CLASSIFICATIONS", bad)
    shadow.classifications.cache_clear()
    with pytest.raises(ValueError, match="malformed"):
        shadow.classifications()
    monkeypatch.undo()
    shadow.classifications.cache_clear()
    assert shadow.classifications() == ()


def mkrec(endpoint, ts, mismatched=0, status="compared", fields=None):
    return {"ts": ts.isoformat(), "endpoint": endpoint, "input_id": "x" * 16, "status": status, "compared": 10,
            "mismatched": mismatched, "match_rate": 1.0, "fields": fields or []}


def test_summary_rates_and_window(tmp_path):
    now = datetime(2026, 6, 30, tzinfo=UTC)
    recs = [mkrec("a", now - timedelta(days=20), 1), mkrec("a", now - timedelta(days=5), 0), mkrec("a", now - timedelta(days=4), 2,
            fields=[{"path": "p", "kind": "exact", "delta": None, "class": None}, {"path": "q", "kind": "exact", "delta": None, "class": "convention"},
                    {"path": "r", "kind": "exact", "delta": None, "class": "bug"}]),
            mkrec("a", now - timedelta(days=3), status="provider_error:URLError"), mkrec("b", now - timedelta(days=1))]
    full = shadow.summary(recs, now)
    assert full["a"]["requests"] == 3 and full["a"]["errors"] == 1 and full["a"]["with_diff"] == 2
    assert full["a"]["diff_rate"] == pytest.approx(2 / 3) and full["a"]["unclassified_fields"] == 1
    assert (full["a"]["convention_fields"], full["a"]["bug_fields"]) == (1, 1)
    windowed = shadow.summary(recs, now, 14)
    assert windowed["a"]["requests"] == 2 and windowed["a"]["with_diff"] == 1 and windowed["b"]["diff_rate"] == 0.0
    log = shadow.ShadowLog(tmp_path / "x" / "shadow.jsonl")
    assert log.records() == []
    for r in recs:
        log.append(r)
    assert log.records() == recs


# ---- cutover -------------------------------------------------------------------------------------------------
def test_cutover_flags_reload_per_call(tmp_path, monkeypatch):
    f = tmp_path / "flags.json"
    monkeypatch.setenv("KUNDLI_CUTOVER_FILE", str(f))
    assert cutover.mode_for("planets") == "engine"  # no file
    f.write_text(json.dumps({"planets": "shadow", "*": "provider"}))
    assert (cutover.mode_for("planets"), cutover.mode_for("other")) == ("shadow", "provider")
    f.write_text(json.dumps({"planets": "engine"}))
    assert (cutover.mode_for("planets"), cutover.mode_for("other")) == ("engine", "engine")
    f.write_text(json.dumps({"planets": "banana"}))
    with pytest.raises(ValueError, match="unknown cutover modes"):
        cutover.mode_for("planets")


def stats(**kw):
    base = {"requests": 500, "errors": 0, "with_diff": 2, "diff_rate": 0.004, "first": "2026-06-01T00:00:00+00:00", "last": "2026-06-20T00:00:00+00:00",
            "unclassified_fields": 0, "bug_fields": 0, "convention_fields": 0}
    return {**base, **kw}


NOW = datetime(2026, 6, 20, tzinfo=UTC)


def test_readiness_rules():
    assert cutover.readiness("T1", stats(), now=NOW)["ready"] is True
    assert "no shadow data" in cutover.readiness("T1", None, now=NOW)["reasons"][0]
    assert not cutover.readiness("T1", stats(diff_rate=0.01), now=NOW)["ready"]  # 1% is not under 1%
    assert any("spans less" in r for r in cutover.readiness("T1", stats(first="2026-06-10T00:00:00+00:00"), now=NOW)["reasons"])
    assert any("only 50" in r for r in cutover.readiness("T1", stats(requests=50), now=NOW)["reasons"])
    assert cutover.readiness("Data", stats(), now=NOW)["ready"] is True  # data tier follows T1
    t2 = cutover.readiness("T2", stats(requests=1, diff_rate=0.9, unclassified_fields=0, convention_fields=4), now=NOW)
    assert t2["ready"] is True  # T2: only classification matters, not the rate or the window
    assert not cutover.readiness("T2", stats(unclassified_fields=1), now=NOW)["ready"]
    assert not cutover.readiness("T2", stats(bug_fields=1), now=NOW)["ready"]
    assert not cutover.readiness("T3", stats(), now=NOW)["ready"] and cutover.readiness("T3", stats(), content_reviewed=True, now=NOW)["ready"]
    mixed = cutover.readiness("T1/T2", stats(diff_rate=0.5, unclassified_fields=2), now=NOW)
    assert not mixed["ready"] and len(mixed["reasons"]) >= 2  # every part must hold
    assert cutover.readiness("T1/T3", stats(), now=NOW)["ready"] is False and cutover.readiness("T1/T3", stats(), True, NOW)["ready"] is True


# ---- router modes with a fake provider ----------------------------------------------------------------------
class FakeProvider:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response or {"theirs": True}, error, []

    def call(self, endpoint, payload):
        self.calls.append((endpoint, payload))
        if self.error:
            raise self.error
        return self.response


def flags(tmp_path, monkeypatch, mapping, log=True):
    f = tmp_path / "flags.json"
    f.write_text(json.dumps(mapping))
    monkeypatch.setenv("KUNDLI_CUTOVER_FILE", str(f))
    if log:
        monkeypatch.setenv("KUNDLI_SHADOW_LOG", str(tmp_path / "shadow.jsonl"))
    monkeypatch.setenv("KUNDLI_SHADOW_SALT", "test-salt")
    return tmp_path / "shadow.jsonl"


def test_shadow_mode_returns_provider_and_logs_a_diff_summary(tmp_path, monkeypatch):
    log = flags(tmp_path, monkeypatch, {"planets": "shadow"})
    fake = FakeProvider({"planets": [{"name": "Sun", "longitude": 1.0}]})
    provider.set_client(fake)
    r = TestClient(app).post("/compat/planets", json=BODY)
    assert r.status_code == 200 and r.json() == {"planets": [{"name": "Sun", "longitude": 1.0}]}  # the provider's answer
    assert fake.calls[0][0] == "planets" and fake.calls[0][1]["date"] == "1990-05-05"
    rec = json.loads(log.read_text().splitlines()[0])
    assert rec["status"] == "compared" and rec["endpoint"] == "planets" and rec["mismatched"] >= 1
    text = log.read_text()
    for secret in (SECRET, "Zyxwv", "28.6139", "77.209", "1990-05-05", "10:30"):
        assert secret not in text, secret
    # engine default for other endpoints is untouched
    assert TestClient(app).post("/compat/bhav_madhya", json=BODY).json()["conventions_used"]["response_shape"] == "engine_neutral"


def test_shadow_mode_falls_back_to_the_engine_when_the_provider_fails(tmp_path, monkeypatch):
    log = flags(tmp_path, monkeypatch, {"planets": "shadow"})
    provider.set_client(FakeProvider(error=TimeoutError("boom")))
    r = TestClient(app).post("/compat/planets", json=BODY)
    assert r.status_code == 200 and r.json()["conventions_used"]["response_shape"] == "engine_neutral"
    rec = json.loads(log.read_text().splitlines()[0])
    assert rec["status"] == "provider_error:TimeoutError" and "boom" not in log.read_text()


def test_shadow_mode_survives_engine_errors(tmp_path, monkeypatch):
    log = flags(tmp_path, monkeypatch, {"planets": "shadow"})
    provider.set_client(FakeProvider({"planets": []}))
    r = TestClient(app).post("/compat/planets", json={**BODY, "date": "not-a-date"})
    assert r.status_code == 200 and r.json() == {"planets": []}
    assert json.loads(log.read_text().splitlines()[0])["status"] == "engine_error:ValueError"


def test_provider_mode_and_path_params(tmp_path, monkeypatch):
    flags(tmp_path, monkeypatch, {"*": "provider"}, log=False)
    fake = FakeProvider({"who": "provider"})
    provider.set_client(fake)
    c = TestClient(app)
    assert c.post("/compat/general_rashi_report/mars", json=BODY).json() == {"who": "provider"}
    assert fake.calls[0][0] == "general_rashi_report/mars"  # :planet_name replaced by the actual value
    assert c.post("/compat/geo_details", json={"place": "Agra"}).json() == {"who": "provider"}  # simple endpoints too
    provider.set_client(FakeProvider(error=OSError("down")))
    down = c.post("/compat/planets", json=BODY)
    assert down.status_code == 503 and down.json() == {"error": "provider_unavailable"}


def test_flags_flip_without_restart(tmp_path, monkeypatch):
    flags(tmp_path, monkeypatch, {"planets": "provider"}, log=False)
    provider.set_client(FakeProvider({"who": "provider"}))
    c = TestClient(app)
    assert c.post("/compat/planets", json=BODY).json() == {"who": "provider"}
    (tmp_path / "flags.json").write_text(json.dumps({"planets": "engine"}))
    assert c.post("/compat/planets", json=BODY).json()["endpoint"] == "planets"


# ---- ops -----------------------------------------------------------------------------------------------------
def test_health_version_and_shadow_dashboard(tmp_path, monkeypatch):
    c = TestClient(app)
    assert c.get("/health").json() == {"status": "ok"}
    v = c.get("/version").json()
    assert v["engine_version"] and len(v["config_hash"]) == 64 and v["content_version"] and v["config_hash"] == ops.config_hash()
    assert c.get("/ops/shadow").status_code == 404  # disabled without a token
    monkeypatch.setenv("KUNDLI_OPS_TOKEN", "tok")
    assert c.get("/ops/shadow").status_code == 401 and c.get("/ops/shadow", headers={"X-Ops-Token": "bad"}).status_code == 401
    empty = c.get("/ops/shadow", headers={"X-Ops-Token": "tok"}).json()
    assert empty["endpoints"] == {} and empty["log_configured"] is False
    log = shadow.ShadowLog(tmp_path / "shadow.jsonl")
    now = datetime.now(UTC)
    for i in range(120):
        log.append(mkrec("sarvashtak", now - timedelta(days=15) + timedelta(hours=3 * i)))
    monkeypatch.setenv("KUNDLI_SHADOW_LOG", str(log.path))
    rep = c.get("/ops/shadow", headers={"X-Ops-Token": "tok"}).json()
    row = rep["endpoints"]["sarvashtak"]
    assert row["tier"] == "T2" and row["mode"] == "engine" and row["requests"] > 0 and "readiness" in row
    assert ops.content_reviewed("general_house_report/mars") is False and ops.content_reviewed("planets") is False


def test_access_log_has_no_request_data(caplog):
    caplog.set_level(logging.INFO, logger=ops.ACCESS_LOGGER)
    c = TestClient(app)
    c.post("/compat/general_rashi_report/mars?secret=Zyxwv", json=BODY)
    c.post("/kundli", json={"name": SECRET, "date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"})
    c.get("/health")
    c.get("/no/such/route")
    lines = [r.getMessage() for r in caplog.records if r.name == ops.ACCESS_LOGGER]
    assert len(lines) == 4
    parsed = [json.loads(x) for x in lines]
    assert [p["route"] for p in parsed] == ["/compat/general_rashi_report/{planet_name}", "/kundli", "/health", "unmatched"]
    assert all(set(p) == {"event", "route", "method", "status", "duration_ms"} for p in parsed)
    blob = "\n".join(lines)
    for secret in (SECRET, "Zyxwv", "28.6139", "mars", "1990"):
        assert secret not in blob, secret


# ---- concurrency / memory -----------------------------------------------------------------------------------
def test_concurrent_requests_are_isolated_and_repeatable():
    c = TestClient(app)
    jobs = [("/compat/planets", {**BODY, "config": {"ayanamsa": a}}) for a in ("lahiri", "raman", "kp", "lahiri", "raman", "kp")]
    jobs += [("/compat/basic_panchang", BODY), ("/compat/sarvashtak", BODY)] * 3
    serial = [c.post(u, json=b).content for u, b in jobs]
    with ThreadPoolExecutor(max_workers=8) as ex:
        parallel = list(ex.map(lambda j: TestClient(app).post(j[0], json=j[1]).content, jobs * 2))
    assert parallel == serial * 2  # identical bytes under contention: no cross-request leakage of swisseph global state


def test_memory_does_not_grow_across_requests():
    import resource

    c = TestClient(app)
    for _ in range(3):
        c.post("/compat/planets", json=BODY)
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for _ in range(40):
        c.post("/compat/planets", json=BODY)
    grown = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before) / (1024 * 1024 if __import__("sys").platform == "darwin" else 1024)
    assert grown < 150  # MB; a loose bound that still catches a per-request leak


# ---- performance changes keep results identical -------------------------------------------------------------
def test_saturn_table_slice_equals_the_direct_scan():
    from kundli import transits

    cfg = EngineConfig()
    for y in (1943, 1990, 2026, 2060):  # inside the table
        s = datetime(y, 5, 5, 10, 30, tzinfo=UTC)
        e = s + timedelta(days=365.25 * 90)
        fast, slow = transits.ingresses("Saturn", s, e, cfg), transits._scan_ingresses("Saturn", s, e, cfg)
        assert [(x["utc"], x["to_sign"], x["direct"]) for x in fast] == [(x["utc"], x["to_sign"], x["direct"]) for x in slow]
        assert max(abs(a["jd_ut"] - b["jd_ut"]) for a, b in zip(fast, slow, strict=True)) * 86400 < 0.01  # milliseconds
    s = datetime(1850, 5, 5, tzinfo=UTC)  # outside the table: falls back to scanning
    assert transits.ingresses("Saturn", s, s + timedelta(days=3000), cfg) == transits._scan_ingresses("Saturn", s, s + timedelta(days=3000), cfg)
    other = EngineConfig(ayanamsa="raman")  # one table per ayanamsa
    a = transits.ingresses("Saturn", datetime(2000, 1, 1, tzinfo=UTC), datetime(2030, 1, 1, tzinfo=UTC), cfg)
    b = transits.ingresses("Saturn", datetime(2000, 1, 1, tzinfo=UTC), datetime(2030, 1, 1, tzinfo=UTC), other)
    assert [x["utc"] for x in a] != [x["utc"] for x in b] or [x["to_sign"] for x in a] == [x["to_sign"] for x in b]
    dir_b = transits._scan_ingresses("Saturn", datetime(2000, 1, 1, tzinfo=UTC), datetime(2030, 1, 1, tzinfo=UTC), other)
    assert [x["utc"] for x in b] == [x["utc"] for x in dir_b]


def test_yoga_rules_are_cached_but_callers_get_copies():
    from kundli.yogas import engine

    a = engine.load_rules()
    hits = engine._load.cache_info().hits
    a[0]["id"] = "mutated"
    a.append({"id": "extra"})
    b = engine.load_rules()
    assert engine._load.cache_info().hits == hits + 1 and b[0]["id"] != "mutated" and len(b) == len(a) - 1


def test_startup_warms_the_caches():
    from kundli import transits

    transits._saturn_table.cache_clear()
    with TestClient(app) as c:  # entering the context runs the lifespan
        assert transits._saturn_table.cache_info().currsize >= 1
        assert c.get("/health").status_code == 200
