# Conventions

Every choice below has a rejected alternative. Defaults live in `EngineConfig`.

| Area | Chosen | Rejected / alternative | Notes |
|---|---|---|---|
| Zodiac | Sidereal | Tropical | Tropical longitudes are also stored. |
| Ayanamsa | Lahiri (`SIDM_LAHIRI`) | Raman, KP, True Chitra, Fagan-Bradley… | Configurable. Value includes nutation (swe_get_ayanamsa_ex_ut). |
| Nodes | True node | Mean node | Configurable. Ketu = Rahu + 180° exactly. |
| Ephemeris | Moshier (built-in, ~1″ planets) | Swiss `.se1` files | `ephemeris="swiss_files"` + `ephemeris_path`. |
| Delta-T | swisseph (`swe_utc_to_jd`) | Own table | UT1/UTC handled by swisseph. |
| Retrograde | Sidereal longitudinal speed < 0 | – | Nodes: from node speed. |
| Time zones | IANA via `zoneinfo` + `tzdata` package (pinned) | System tz data | Deterministic across machines; includes historical rules. |
| DST overlap | Raise `AmbiguousLocalTime` unless `fold` given | Silently pick fold=0 | Never guess. |
| DST gap | Always raise `NonexistentLocalTime` | Shift forward | |
| Unknown birth time | Local noon, `time_unknown=True`; lagna outputs skipped | Sunrise | |
| Place ambiguity | Raise `AmbiguousPlace` with candidates | Pick most populous | Candidate order: population desc, then country/admin/name. |
| Place DB | GeoNames cities15000 (offline, CC-BY) → Nominatim fallback (disk-cached) | Online only | Nominatim results have no population; ordering is the API's. |
| swisseph global state | Sidereal mode set right before each dependent call | Set once at import | swisseph keeps it in process-global state. |

## Calculation conventions added in phases 2-10

| Area | Chosen | Rejected / alternative |
|---|---|---|
| Rashi-chart house | Whole-sign house always stored as `rashi_house`; `house` follows `house_system` | Single house field |
| Bhava chalit | Sripati: Porphyry cusps = bhava madhya, boundaries at midpoints | Placidus cusps as madhya |
| Placidus/KP at polar latitudes | Fall back to Equal houses with a flag + note | Fail |
| Combustion orbs | Moon 12, Mars 17, Mercury 14 (12 retro), Jupiter 11, Venus 10 (8 retro), Saturn 15 | Other schools' orbs (VERIFY) |
| Graha yuddha | Within 1 degree of longitude; more northern latitude wins | Lower longitude wins |
| Node aspects | 5th/7th/9th | 7th only (VERIFY) |
| Vara | Day starts at sunrise (upper limb, refraction) | Civil midnight |
| Hora / Choghadiya | 12 day + 12 night horas; daytime choghadiya only | Night choghadiya (not implemented) |
| Gulika / Mandi | Ascendant at start / midpoint of Saturn's portion | Both at start; end of portion (VERIFY) |
| Hora/Ghati/Bhava lagna | Sun + 12/30/6 degrees per ghati since sunrise | JHora variants |
| Indu lagna | 9th-lord kalas (from Lagna and Moon), mod 12, counted from Moon | Counted from Lagna (VERIFY) |
| D2 | Parashari (Sun/Moon hora) | Jagannatha/Kashinatha |
| D3 | Same sign, 5th, 9th | Parashara-alt orders |
| D30 | BPHS unequal parts | Equal 1 degree parts |
| D5, D8, D11, D60 | See `vargas.py` docstrings, flagged `VERIFY` | Other schools |
| Dasha year | 365.25 days | 360 (config) |
| Dasha storage | Maha/antar/pratyantar stored; deeper levels computed on demand by `current_dasha` | Full 5-level tree in JSON |
| Shadbala | BPHS formulas as in `strength/shadbala.py`; Cheshta uses true heliocentric longitude as mean-planet stand-in; Yuddha bala = 0; Abda/Masa via solar sankranti | Full ahargana method |
| Ashtakavarga | BPHS contributions; trikona shodhana; simplified ekadhipatya | Textual variants (VERIFY) |
| Timeline weights | `data/timeline_weights_v1.yaml`; `center`/`tanh_scale` calibrated on a sample chart only | Learned weights |
| LLM call | No `temperature` sent (current Claude API does not take it); stability from validation + deterministic fallback | temperature 0 |

## Full-report sections (v0.2)
Checked against an external report (`tests/reference/test_sample_report.py`). "Ref" = matched exactly or within tolerance.

| Area | Chosen | Status |
|---|---|---|
| Node for the report | Mean node (`node_type="mean"`); engine default stays true node | Ref: Rahu 28:41:42 only matches mean node |
| Friendship tables | Permanent, temporal, five-fold from `dignity.py` | Ref: all three 7x7 matrices identical |
| Avakahada | Varna/vashya/yoni/gana/nadi by rashi or nakshatra, paya by Moon house, tatva, name syllable | Ref: all fields. Shravana syllables vary by school (VERIFY). Yunja not implemented |
| Hindu month | Amanta; named by the Sun's sidereal sign at the preceding new moon; Adhika if no sankranti | Ref: Phalguna |
| Functional nature | Yogakaraka > trikona lord > 3/6/11 malefic > 2/8/12 neutral > sole kendra lord (natural benefic malefic, malefic neutral) | Ref: 7/7 for one lagna; rule set v1, VERIFY |
| KP | Nakshatra/sub/sub-sub by Vimshottari proportions; cusps Placidus in the sidereal zodiac | Ref: planets exact; cusps within 2' after adding ayanamsa (the reference prints tropical cusps) |
| Lagna ashtakavarga | Lagna as target, 8 contributors, total 49 | Ref: exact |
| Chara dasha | Direction by lagna group; years by lord distance (12 if 0); Scorpio/Aquarius co-lord = the one with greater degrees (nodes not reversed) | Ref: all 12 maha dates. Antardasha order and co-lord rule are VERIFY |
| Kaal Sarp | Full = all 7 grahas on one side; type by Rahu house; direction ascending if on the Ketu-to-Rahu arc | Ref: Shankhpal / ascending |
| Manglik | Mars from Lagna/Moon/Venus in 1,2,4,7,8,12 + other malefics + Mars aspects; `intensity_percent` is our own heuristic | Not comparable with the reference percentage |
| Sade Sati table | Saturn ingresses typed relative to the natal Moon, incl. retrograde re-entries | Ref: all 24 events within 1 day |
| Gemstones | Lords of 1st/5th/9th -> traditional navagraha gem table (`GEMS`) | Ref: life/benefic/lucky stones, day, finger |
| Numerology | Radical, destiny (digital root), name number (Chaldean) | Ref: radical and destiny; the reference's name number (4) uses another letter table |

## Oracle fingerprint results (`kundli oracle fingerprint tests/oracle/fixtures/reference_1985.json`)
| Oracle | Best variant | Max error | Notes |
|---|---|---|---|
| Sample horoscope report (1985, Malkapur) | `lahiri/mean` | 0.0002 deg | `lahiri/true` is off by 1.10 deg (Rahu/Ketu only); `kp/mean` 0.097 deg; true_chitra 0.012 deg |
| Same report, Vimshottari maha starts | `year=365.25` | 0.97 day | `year=360` is off by up to 231 days |

`EngineConfig` convention fields added in V2 Phase 11 each have a single value until their phase implements another.

## Panchang (V2 phase 12) - conventions in `src/kundli/panchang/`
Not yet compared with a provider oracle (none supplied); the only external check is published 2025 festival dates and one
tithi end time (Delhi, 2025-10-20: Chaturdashi ends 15:44-15:46 IST).

| Area | Chosen | Alternative / status |
|---|---|---|
| Rise/set definition | `sunrise_definition`: `upper_limb_refracted` (default, swisseph standard atmosphere) or `center_no_refraction`. Delhi 2025-10-20: sunrise 06:24:48 vs 06:28:54, sunset 17:46:42 vs 17:42:36 | Which one a provider uses is decided by the oracle (`kundli oracle fingerprint`), never by editing tolerances |
| Observer altitude | `observer_altitude_m` is passed to swisseph, which uses it only to estimate refraction (no horizon dip); effect is under a minute | Horizon dip would need our own correction |
| Element end times | Hourly scan + bisection (1e-8 day) on the exact angle: tithi 12 deg, karana 6 deg, nakshatra and yoga 13deg20' | Verified: angle at the boundary is a multiple of the unit within 1e-5 deg |
| Vara | Civil weekday of the sunrise that starts the Vedic day | Civil midnight day (not offered) |
| Hora | 12 day + 12 night horas, equal length, Chaldean order from the weekday lord | Fixed 60-minute horas (not offered) |
| Choghadiya | Day: start table `CHOGHADIYA_START`. Night: start = day-start of weekday+4, then -2 places per part | `# VERIFY` both; matches the common Sunday-night table only |
| Rahu Kaal / Yamaganda / Gulika | Eighth-of-daytime part by weekday tables | `# VERIFY` tables (classical, from memory) |
| Abhijit Muhurta | 8th of 15 equal daytime muhurtas | Fixed 24-minute window around noon (not offered) |
| Dur Muhurta, Varjyam, Amrit Kaal | Not implemented | No sourced tables (open_questions.md) |
| Tamil calendar | Month = Sun's sidereal sign; day 1 = civil day of the ingress if it occurs at or before sunset, else next day (`sankranti_before_sunset`) | Regional sunset rules differ; Tamil year name not implemented |
| Festivals | Amanta months; single-anchor rules (sunrise, madhyahna, aparahna 0.7 of day, pradosha = sunset + 2 ghati, nishita = midpoint of the following night, moonrise); Adhika months never match; `festival_tradition=drik_purnimanta` only relabels krishna-paksha months | Classical two-day tie-breaks not applied, e.g. Janmashtami 2025 falls on Aug 15 here |

## Monthly panchang yogas (V2 phase 13) - `panchang/yogas_monthly.py`, rules in `panchang/rules/monthly_yogas.yaml`
| Area | Chosen | Status |
|---|---|---|
| Window computation | Each Vedic day (sunrise to next sunrise) is cut at exact nakshatra and tithi boundaries; qualifying pieces are merged. Windows are not merged across days | Guru Pushya 2024-10-24 (Thu, Pushya) found; no provider oracle yet |
| Sarvartha / Amrit Siddhi | Weekday x nakshatra tables; tithi-based cancellations NOT applied | `# VERIFY` (from memory) |
| Ravi Yoga | Moon in the 4/6/9/10/13/20th nakshatra from the Sun's | `# VERIFY` |
| Dwi/Tripushkar | Sun/Tue/Sat + Bhadra tithis (2,7,12 of either paksha) + nakshatra class; the nakshatra sets are checked in tests against zodiac geometry (2/2 vs 3/1 pada split) | tithi and weekday part `# VERIFY` |
| Ghat Chakra, Yunja | Not implemented (no verified table) | `ghat_chakra` stays 501 |

## Dasha endpoints (V2 phase 14)
| Area | Chosen | Status |
|---|---|---|
| Nested lookup | `dasha.engine.descend(path)`: each lord occurs once per level inside its parent, so a path of lord names identifies one period; Vimshottari lords, Yogini names or lords, Chara sign names | Sub-periods equal the stored tree (tested) |
| Yogini cycles | 36-year cycle repeats for life; `current`/stack picks the cycle running at `as_of`; `/sub_yogini_dasha/:dashaCycle/:name` takes the cycle number | Fixed: the stack was empty after the first 36 years |
| Chara sub-levels | Maha as before; antar and every lower level = 12 equal parts, direction of the parent sign, starting from the next sign and ending with the sign itself | `# VERIFY`; only maha dates cross-checked |
| Year length | `dasha_year_days` 365.25 (matches the reference within 1 day) or 360 | fingerprint result above |

## KP (V2 phase 15) - `src/kundli/kp/`
| Area | Chosen | Status |
|---|---|---|
| Sub-lord table | Generated from Vimshottari proportions (27 x 9 pieces, cut at sign boundaries); count asserted = 249 | Exact arithmetic, no typed table |
| Cusps / houses | Placidus cusps in the chart's sidereal zodiac; planet house = Placidus house; owner of a house = sign lord of its cusp | Reference: cusps within 2' |
| `kp_ayanamsa` | `chart` (default: the chart's own ayanamsa, as the reference used) or `kp` (Krishnamurti, regenerates the chart) | Convention; provider default unknown |
| House significators | A planets in the star of occupants, B occupants, C planets in the star of the owner, D owner | Standard ordering |
| Planet significators | 1 houses occupied by star lord, 2 own house, 3 houses owned by star lord, 4 houses owned | Standard ordering |
| Rahu/Ketu | Own no house | `# VERIFY` (schools give them their sign lord's / conjunct planets' results) |

## Doshas and match making (V2 phase 16) - `src/kundli/doshas/`, `src/kundli/match/`
Not compared with a provider oracle. All match tables are in `match/tables.yaml` with `verify: true`.

| Area | Chosen | Status |
|---|---|---|
| Manglik references | `manglik_rules`: `lagna_only`, `lagna_moon`, `lagna_moon_venus` (default); intensity normalised to the references in use | Convention; variants nest (tested) |
| Kaal Sarp | `kalsarpa_variant`: `full_only` or `include_partial` | as before |
| Sade Sati / Dhaiya | Saturn's sign relative to the natal Moon: 12/1/2 = Sade Sati, 4 = Kantaka, 8 = Ashtama; periods with second-level ingress dates; retrograde re-entries are separate periods; cycles = runs separated by under 2 years | Dates equal the Saturn ingress finder (Pisces 2025-03-29 matches published dates) |
| Pitra dosha | Matched indicator rules only (Sun with a node; a node in the 9th or with the 9th lord) | School-dependent, `# VERIFY` |
| Ashtakoota | Varna rank, vashya matrix, Tara (counts inclusive, mod 9; always 1.5 or 3), yoni 14x14 matrix, Graha Maitri (natural friendship), gana matrix, Bhakoot (2/12, 5/9, 6/8 = 0), Nadi; boy = row, girl = column | Yoni matrix symmetric with exactly the 7 enemy pairs (tested); other matrices from memory |
| Dashakoota | Dina, Gana, Mahendra, Stree Deergha, Yoni (>=2), Rasyadhipati, Vasya (>=1), Rajju, Vedha; 9 of 10 | Rasi not implemented |
| Obstruction cancellations | Nadi: same sign + different nakshatra, or same nakshatra + different pada. Bhakoot: same or mutually friendly sign lords | `# VERIFY` |
| Percentage and verdict | total/36*100; verdict bands 33/25/18 | Convention, provider formula unknown |

## Varshaphal (V2 phase 17) - `src/kundli/varshaphal/`
Not compared with a provider oracle.

| Area | Chosen | Status |
|---|---|---|
| Solar return | Root-find (50 bisections, ~1 ms) of the Sun's return; `solar_return_zodiac`: `sidereal` (default) or `tropical` natal Sun longitude (tropical return ~20.4 min/year earlier); chart always in the configured sidereal zodiac | Sun at return equals natal Sun within 1e-7 deg (tested) |
| Month chart n | Sun at natal + (n-1) x 30 deg after the year chart | Convention; month 1 = year chart |
| Muntha | Natal lagna sign + completed years; lord, house and occupants in the annual chart; 6/8/12 flagged | Standard |
| Panchavargeeya | Kshetra 30, Uccha 20 (arc from debilitation / 9), Hadda 15, Drekkana 10, Navamsa 5; relation fractions 1, 3/4, 1/2, 1/4, 1/8, 1/16 by panchadha maitri; bala = sum / 4 | Hadda table: every sign sums to 30, each of five planets once per sign, totals 79/82/76/66/57 (tested); fractions `# VERIFY` |
| Harsha | Sthana (glad house), stri-purusha, uccha-adi, dina-ratri; 5 each | Low confidence, `# VERIFY` |
| Sahams | Planet+lagna formulas in `sahams.yaml`; reversed at night; no classical +30 adjustment | `# VERIFY` |
| Tajika yogas | Ithasala/Ishrafa by sign-based Tajika aspects and half-sum deeptamsa orbs; retrograde reported not applied | Others not implemented |
| Mudda dasha | Vimshottari compressed to 3 days per dasha year; `mudda_dasha_basis`: `annual_moon` (default) or `natal_vimshottari` | `# VERIFY` the basis |

## Muhurta (V2 phase 18) - `src/kundli/muhurta/`
Engine in `engine.py`; every activity is data in `rulesets/<activity>.yaml` (18 files) on top of `rulesets/_common.yaml`; tables in `tables.yaml`.
Not compared with a provider oracle: the plan's acceptance (>= 90% of "good" dates matching the oracle, every mismatch traced to a rule) cannot be run without oracle data.

| Area | Chosen | Status |
|---|---|---|
| Slots | Each Vedic day is cut at every tithi/nakshatra/yoga/karana boundary and at Rahu Kaal/Yamaganda/Gulika/Abhijit edges; neighbours with the same verdict merge | Exact boundaries (spans), month taken at sunrise |
| Scoring | Share of soft-rule weight passed (0-100); a failed veto rule vetoes the window (score null). `good_dates` = best window >= 60 | Convention; thresholds are not tuned |
| Common vetoes | Rahu Kaal, Yamaganda, Gulika, Riktha tithis (+Amavasya), nine inauspicious yogas, Vishti karana, Adhika month | `# VERIFY` (generic principles) |
| Activity rules | Weekday set (weight 3) and nakshatra class set (weight 4: Dhruva/Chara/Kshipra/Mridu...) plus a few activity-specific rules (Kharmas, Venus/Jupiter combustion, months, Dishashoola for travel, the 11 marriage nakshatras) | Generic, from memory; every ruleset is `verify: true` |
| Personal checks | Tarabala (count from natal nakshatra mod 9 not in 3/5/7) and Chandrabala (Moon in 1/3/6/7/10/11 from the natal Moon); `not_evaluated` without a birth chart | Standard |
| Range | At most 62 days per scan | Protects the API |

## Numerology and biorhythm (V2 phase 19) - `src/kundli/numerology/`, `src/kundli/biorhythm.py`
| Area | Chosen | Status |
|---|---|---|
| Letter table | `numerology_system`: `chaldean` (1-8, default) or `pythagorean` (A=1..I=9 repeating) | Convention; the reference report used another table for the name number |
| Radical / destiny | Digital root of the birth day / of all date digits | Exact |
| Favourable lord / numbers | Natural friendship of the ruling grahas (Rahu 4 and Ketu 7 have no row: `not_defined`) | Derived from the friendship table |
| Favourable day | Weekday of the ruling graha; none for Rahu/Ketu | Derived |
| Direction, mantra | `numerology/data.yaml` (Vastu graha-direction lordship, navagraha beeja mantras) | `verify: true`, from memory |
| Daily number | reduce(radical + digital root of the date digits); relation to birth number by friendship | Convention (provider definition unknown) |
| Biorhythm | sin(2 pi t / P), P = 23/28/33, t = whole days from the birth date; critical day = zero crossing; labelled entertainment | Exact arithmetic |
| Moon biorhythm | NOT implemented | Definition unconfirmed |

## Lal Kitab (V2 phase 20) - `src/kundli/lalkitab/`
Highest-ambiguity area: the source books are inconsistent between editions and no edition is cited yet. Everything below is `# VERIFY`.

| Area | Chosen | Status |
|---|---|---|
| Layout | `lalkitab_edition`: `fixed_aries` (default; house n = sign n from Aries, the Kaal Purush layout, as in the classic 1952 volume; works without a birth time) or `lagna_houses` (whole-sign houses from the lagna, needs a birth time). Default chosen as the latest classic edition `# VERIFY` against a cited source | Convention; which edition the provider follows is unknown |
| Exaltation/debilitation houses | Derived from the sign table (house = sign number): Sun 1/7, Moon 2/8, Mars 10/4, Mercury 6/12, Jupiter 4/10, Venus 12/6, Saturn 7/1; nodes none | Derived, tested |
| Pakka ghar | Sun 1; Moon 4; Mars 3,8; Mercury 7; Jupiter 2,5,9,12; Venus 7; Saturn 8,10; Rahu 12; Ketu 6 | From memory, low confidence |
| Debts (rin) | `debts.yaml`: Pitri (Venus/Mercury/Rahu in 2,5,9,12), Matri (Ketu in 4), Stri (Sun/Moon/Rahu in 2,7) | From memory; other debts not implemented |
| Remedies | Selection facts and a content-store key `lalkitab.remedy.<planet>.<house>`; no remedy text is written in code | Text in phase 21 |

## Content layer (V2 phase 21) - `src/kundli/content/`, `docs/content_rules.md`
| Area | Chosen | Status |
|---|---|---|
| Block | One file `blocks/<lang>/<topic>/<key>.md`: YAML front matter (key, lang, sources, status, reviewer, version, hash) + text | Schema-validated |
| Lifecycle | `draft` -> `reviewed` (a named person, `kundli content review`) -> `frozen` (`kundli content freeze` writes `content.lock`). Hash = SHA-256 of key, lang, text, sources, version | Editing a frozen block changes its hash, so it stops being served |
| Serving | The store serves a block only if its status is not draft AND `content.lock` lists its hash AND the file still hashes to it. Missing -> `{"status": "content_missing"}`; there is NO LLM fallback and no cross-language fallback | Tested |
| Determinism | Lookups only; `content_version` (hash of the lock, `empty` without one) is echoed in `conventions_used` | Byte-identical output |
| Key space | `kundli.content.keys.reachable()`: 718 keys per language (house 108, rashi 108, ascendant 12, nakshatra 27, daily 243, numerology 45, dosha 26, match 41, lalkitab 108) | Every key an endpoint emits is in the space (tested) |
| Lint | Missing/short/orphan/banned-claim blocks, reviewer required, lock hash checks, optional language coverage; negated disclaimers ("no outcome is guaranteed", Hindi "गारंटी नहीं") are allowed | `kundli content lint` |
| Offline drafting | `kundli.content.draft` (LLM, run by hand) and `scripts/draft_content.py` (templates from `scripts/content_data.py`); never imported by the API (static + runtime test) | 558 template drafts in the repo (en+hi), all `status: draft` |
| Tarabala | Count (inclusive) from the birth nakshatra to the transit Moon's nakshatra, mod 9 (0 -> 9): janma, sampat, vipat, kshema, pratyari, sadhaka, vadha, mitra, ati-mitra; vipat/pratyari/vadha inauspicious, janma mixed | `# VERIFY` classification |
| Daily nakshatra | The Vedic day (sunrise to sunrise) is cut at the Moon's nakshatra boundaries; `primary` = nakshatra at sunrise; Chandrabala houses 1/3/6/7/10/11 favourable | Convention |

## Remedies (V2 phase 22) - `src/kundli/remedies/`
Selection is data (`rules.yaml`, every rule `verify: true`); wording is a content block (`remedy.*` keys, 37 per language). Every response carries a `disclaimer`
("Traditional belief and cultural practice; not medical, legal or financial advice. No outcome is guaranteed.") and `tables_verified: false`; the engine's own output contains no
price, urgency or "must wear" language (tested with the content linter's banned-claims check).

| Area | Chosen | Status |
|---|---|---|
| Facts read | Functional nature for the lagna, dignity, combustion, retrograde, Shadbala ratio (below 1.0 = below the minimum), whole-sign house, lordships | Existing engine outputs |
| Graha-shanti pujas | `weak_benefic` (functional benefic/yogakaraka weak, debilitated or combust), `afflicted_malefic` (functional malefic in 1/4/7/8/10/12), `dusthana_lord_weak` (lord of 6/8/12 weak or debilitated); seven grahas, Rahu/Ketu have no rule | `# VERIFY`; schools differ a lot |
| Dosha pujas | Kaal Sarp, Manglik (effective), Pitra indicators present; Sade Sati/Dhaiya adds Saturn when `as_of` is given | `# VERIFY` |
| Gems | Gems of the lords of the 1st/5th/9th (existing `GEMS` table) with `examine_with_care` flags and `weak` | Table `# VERIFY` |
| Rudraksha | Mukhi 1-9 linked to Sun..Ketu; candidates = the gem grahas | Mapping from memory; the plan marks the selection rule blocked |
| Sade Sati remedies | Phase at `as_of` (rising/peak/setting/dhaiya/none) + Saturn facts; text `remedy.sadhesati.<phase>` | Facts exact |

## Geo, rollout and operations (V2 phase 23)
| Area | Chosen | Status |
|---|---|---|
| Geo lookup | Offline GeoNames index only (deterministic, no third-party call); ambiguous names return all candidates, never a guess | Exact |
| Time zone | `timezonefinder` zone for coordinates; offset/DST/abbreviation from the historical IANA rules; times in a DST gap are `nonexistent`, repeated times `ambiguous` (`fold` chooses); the year's transitions found to the second | Tested (New York 2024, India 1943 war time) |
| Cutover modes | Per endpoint, from the JSON file in `KUNDLI_CUTOVER_FILE` (`engine` default, `shadow`, `provider`; `"*"` = default), re-read on every request so flags flip without a restart | Tested |
| Shadow mode | Provider answers, engine runs, only a diff summary is logged (JSONL, `KUNDLI_SHADOW_LOG`): endpoint, UTC timestamp, a keyed HMAC of the request (`KUNDLI_SHADOW_SALT`), counts, rates, field PATHS with kind/delta/class. No names, dates, places, coordinates or response values; provider errors log only the exception class | Privacy tested |
| Provider client | `KUNDLI_PROVIDER_URL/KEY`, refuses to run unless `KUNDLI_PROVIDER_TOS_CHECKED=1`; the key is excluded from reprs; a provider failure never breaks the app (shadow falls back to the engine, provider mode returns 503) | Tested against a local server |
| Cutover rule | T1/Data: diff rate < 1% over 14 days, >= 100 compared requests spanning the window. T2: every differing field classified `convention` (`compat/classifications.yaml`). T3: content reviewed and frozen. Mixed tiers need every part | `kundli shadow report`, `GET /ops/shadow` |
| Ops | `GET /health`, `GET /version` (engine, swisseph, config hash, content version), `GET /ops/shadow` (needs `KUNDLI_OPS_TOKEN`, 404 otherwise), JSON access log of route template/method/status/duration only | Tested (no request data in logs) |
| Performance | See docs/performance.md: Saturn ingress table, rule-file cache, ephemeris cache; ~0.02 s per chart endpoint | Measured |
