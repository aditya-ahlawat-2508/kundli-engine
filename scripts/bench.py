"""Latency and memory baseline for the compat endpoints (V2 phase 23). Not part of the test suite (timings are machine-dependent).

    uv run python scripts/bench.py [--runs 7] [--write docs/performance.md]

Each endpoint is called `runs` times through an in-process TestClient (no network); the first call is a warm-up. Prints p50/p95
per endpoint, the cold-versus-warm ephemeris effect, and peak resident memory. Targets are in docs/performance.md."""
import argparse
import resource
import statistics
import sys
import time

from fastapi.testclient import TestClient

from kundli import ephemeris
from kundli.api import app

BIRTH = {"name": "Bench", "date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata",
         "as_of": "2026-10-10", "year": 2026, "month": 3, "end_date": "2026-10-24"}
GIRL = {"name": "G", "date": "1992-11-20", "time": "06:15", "lat": 19.076, "lon": 72.8777, "tz": "Asia/Kolkata"}
CASES = {  # endpoint -> (body, p95 target in seconds)
    "planets": (BIRTH, 1.5), "basic_panchang": (BIRTH, 1.5), "advanced_panchang": (BIRTH, 2.0), "panchang_festival": (BIRTH, 2.0),
    "current_vdasha_all": (BIRTH, 1.5), "sub_vdasha/Venus": (BIRTH, 1.5), "kp_birth_chart": (BIRTH, 1.5), "manglik": (BIRTH, 1.5),
    "sadhesati_life_details": (BIRTH, 3.0), "varshaphal_year_chart": (BIRTH, 2.5), "varshaphal_mudda_dasha": (BIRTH, 2.5),
    "marriage": ({**BIRTH, "date": "2026-10-10", "end_date": "2026-10-24"}, 8.0), "numero_table": (BIRTH, 1.5), "lalkitab_horoscope": (BIRTH, 1.5),
    "daily_nakshatra_prediction": (BIRTH, 2.0), "puja_suggestion": (BIRTH, 2.5), "geo_details": ({"place": "Agra"}, 0.2),
    "timezone_with_dst": ({"lat": 28.6, "lon": 77.2, "date": "2026-10-10"}, 0.5),
    "match_ashtakoot_points": ({"boy": BIRTH, "girl": GIRL}, 3.0),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=7)
    ap.add_argument("--write", help="write the markdown table to this file")
    a = ap.parse_args()
    c = TestClient(app)
    rows = []
    for ep, (body, target) in CASES.items():
        c.post(f"/compat/{ep}", json=body)  # warm-up
        times = []
        for _ in range(a.runs):
            t = time.perf_counter()
            r = c.post(f"/compat/{ep}", json=body)
            times.append(time.perf_counter() - t)
            if r.status_code != 200:
                print(f"{ep}: HTTP {r.status_code}", file=sys.stderr)
        times.sort()
        p95 = times[min(len(times) - 1, round(0.95 * (len(times) - 1)))]
        rows.append((ep, statistics.median(times), p95, target))
    ephemeris.clear_cache()
    t = time.perf_counter()
    c.post("/compat/planets", json=BIRTH)
    cold = time.perf_counter() - t
    t = time.perf_counter()
    c.post("/compat/planets", json=BIRTH)
    warm = time.perf_counter() - t
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    lines = ["| Endpoint | p50 (s) | p95 (s) | p95 target (s) | within target |", "|---|---|---|---|---|"]
    lines += [f"| `{ep}` | {p50:.3f} | {p95:.3f} | {tg} | {'yes' if p95 <= tg else 'NO'} |" for ep, p50, p95, tg in rows]
    lines += ["", f"Ephemeris cache: first `planets` call after clearing {cold:.3f} s, repeat {warm:.3f} s.",
              f"Peak resident memory of this process after all calls: {rss:.0f} MB."]
    out = "\n".join(lines)
    print(out)
    if a.write:
        with open(a.write, "a", encoding="utf-8") as f:
            f.write("\n### Measured baseline\n\n" + out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
