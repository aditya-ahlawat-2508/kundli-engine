# Performance targets and baseline (V2 phase 23)

## Targets
p95 latency per endpoint on the deploy target, measured in-process (no network), after the process warmed up (`ops.warm_up`
runs at server start). They are upper bounds with a large margin over the baseline below, so a deploy target several times slower
than a developer laptop still passes. `scripts/bench.py` prints a table and flags any endpoint over its target.

| Endpoint group | p95 target |
|---|---|
| Chart-derived endpoints (planets, panchang, dashas, KP, doshas, numerology, Lal Kitab, remedies, reports) | 1.5 s (2-3 s for panchang with festivals/day tables, daily prediction, Sade Sati life details, puja) |
| Varshaphal (second chart at the return moment) | 2.5 s |
| Match making (two charts) | 3 s |
| Muhurta scan, 14 days | 8 s (62 days at most per call) |
| Geo / time zone lookups | 0.2 s / 0.5 s |

Concurrency: compat handlers hold `ENGINE_LOCK` (swisseph keeps process-global state), so requests are serialised per process; scale
with processes, not threads. `tests/unit/test_phase23.py` checks that parallel requests with different ayanamsas return byte-identical
results to serial ones.

Memory: peak resident memory of a process that served every endpoint above was ~185 MB; a per-request leak check (40 requests, growth
under 150 MB) is part of the test suite.

## What was optimised, and what was not
* **Saturn ingress table.** Profiling showed 82% of `generate()` in `sadhesati_events`, which stepped Saturn day by day over 90 years
  for every chart. Saturn's sign changes 1900-2200 are now computed once per ephemeris setup (~1.1 s at startup) and sliced per chart;
  the slice is identical to the per-chart scan (tested to milliseconds). Chart endpoints went from ~0.37 s to ~0.022 s.
* **Yoga rule files** are parsed once per process (callers get copies).
* **Ephemeris cache** (`ephemeris._calc`, keyed on body, JD, flags, sidereal mode and ephemeris path, 64k entries): correct (tested not to
  mix sidereal modes) but a no-op for a single request; it helps only when the same instant is computed repeatedly (e.g. both partners
  born at the same moment, or repeated calls). The panchang/muhurta root-finding uses unique instants and is not cached.
* Not done: caching whole charts per request, a process pool, or an ahead-of-time Saturn table beyond 2200.

### Measured baseline

| Endpoint | p50 (s) | p95 (s) | p95 target (s) | within target |
|---|---|---|---|---|
| `planets` | 0.023 | 0.050 | 1.5 | yes |
| `basic_panchang` | 0.033 | 0.033 | 1.5 | yes |
| `advanced_panchang` | 0.033 | 0.033 | 2.0 | yes |
| `panchang_festival` | 0.025 | 0.025 | 2.0 | yes |
| `current_vdasha_all` | 0.022 | 0.022 | 1.5 | yes |
| `sub_vdasha/Venus` | 0.022 | 0.023 | 1.5 | yes |
| `kp_birth_chart` | 0.023 | 0.023 | 1.5 | yes |
| `manglik` | 0.022 | 0.023 | 1.5 | yes |
| `sadhesati_life_details` | 0.023 | 0.023 | 3.0 | yes |
| `varshaphal_year_chart` | 0.043 | 0.063 | 2.5 | yes |
| `varshaphal_mudda_dasha` | 0.044 | 0.045 | 2.5 | yes |
| `marriage` | 0.813 | 0.824 | 8.0 | yes |
| `numero_table` | 0.022 | 0.022 | 1.5 | yes |
| `lalkitab_horoscope` | 0.022 | 0.022 | 1.5 | yes |
| `daily_nakshatra_prediction` | 0.025 | 0.044 | 2.0 | yes |
| `puja_suggestion` | 0.022 | 0.023 | 2.5 | yes |
| `geo_details` | 0.002 | 0.003 | 0.2 | yes |
| `timezone_with_dst` | 0.002 | 0.002 | 0.5 | yes |
| `match_ashtakoot_points` | 0.043 | 0.043 | 3.0 | yes |

Ephemeris cache: first `planets` call after clearing 0.022 s, repeat 0.022 s.
Peak resident memory of this process after all calls: 183 MB.
