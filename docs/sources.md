# Sources

- Swiss Ephemeris / pyswisseph — https://www.astro.com/swisseph/ (AGPL / commercial dual license).
- Lahiri ayanamsa — Indian Calendar Reform Committee (1955): 23°15′00.658″ at 1956-03-21; used as a unit-test anchor.
- GeoNames `cities15000`, `countryInfo`, `admin1CodesASCII` — https://download.geonames.org/export/dump/ (CC-BY 4.0). Trimmed by `scripts/build_geo_data.py`.
- IANA tz database via the `tzdata` PyPI package.
- Nominatim (OpenStreetMap) — fallback geocoder; usage policy requires a User-Agent and caching (done).
- BPHS (Brihat Parashara Hora Shastra): ch.3 (dignities, friendships, moolatrikona), ch.26 (graha drishti), ch.27 (Shadbala),
  ch.36/41/75 (yogas), ch.66-72 (Ashtakavarga), Vimshottari dasha chapters. Constants live in `src/kundli/data/tables.py`.
- Yogini dasha: standard 36-year scheme (start index = (nakshatra number + 3) mod 8).
- Published Lahiri ingress dates (Drik Panchang convention) used in `tests/unit/test_transits_timeline.py`.
- Ashtakavarga row totals (48/49/39/54/56/52/39 = 337) are asserted in tests; this verifies the transcribed contribution tables.

## Added in v0.2 (full-report sections) - status of each source
- **Lagna Ashtakavarga table** (`LAGNA_BAV_CONTRIB`): derived from, and checked against, an external sample report (total 49 = classical total). Source for the classical text still to be cited.
- **Avakahada, name syllables, paya, Kaal Sarp type names, gem table, functional-nature rules, Chara dasha rules**: entered from the standard traditional schemes from memory. Verified only against one external report (see `tests/reference/test_sample_report.py`). **No primary source line yet**: each is tagged `# VERIFY` in code and listed in `docs/open_questions.md`; they need a cited source and second-person review before any endpoint using them is marked `done`.
- **Sample report values** (`tests/oracle/fixtures/reference_1985.json`): numeric facts only, used as a test oracle. No vendor text, images or branding are copied; fixtures live under `tests/` and are not part of the shipped package.


## Added in V2 phase 12 (panchang)
- **Rahu Kaal / Yamaganda / Gulika part tables, Abhijit as the 8th of 15 muhurtas, night Choghadiya rule, festival rule list
  (`panchang/festivals/rules/major.yaml`), Tamil month names and sunset rule**: standard almanac practice entered from memory;
  no primary source line yet. Each is `# VERIFY` and listed in `docs/open_questions.md`. Published 2025 dates (Diwali Oct 20,
  Holika Dahan Mar 13, Holi Mar 14, Maha Shivaratri Feb 26, Rama Navami Apr 6, Ganesh Chaturthi Aug 27, Dussehra Oct 2,
  Makar Sankranti Jan 14) are used as sanity tests only, not as an oracle.
- Rise/set: Swiss Ephemeris `swe_rise_trans` (flags `BIT_DISC_CENTER`, `BIT_NO_REFRACTION`); documented in the Swiss Ephemeris manual.

## Added in V2 phase 13
- `panchang/rules/monthly_yogas.yaml`: each rule carries its own `source` and `verify` flag; Ravi Pushya and Guru Pushya
  (weekday + Pushya) are definitional. Dwi/Tripushkar nakshatra sets are verified against the 2/2 and 3/1 pada split.

## Added in V2 phase 16
- `match/tables.yaml`: standard Ashtakoota/Dashakoota schemes from memory (`verify: true`); no primary source line yet. Structural checks in tests:
  yoni matrix symmetric with exactly the seven enemy pairs, rajju and vedha lists cover all 27 nakshatras exactly once.

## Added in V2 phase 17
- `varshaphal/tables.py` (Hadda/Egyptian terms, deeptamsa, harsha houses, relation fractions) and `varshaphal/sahams.yaml`: standard Tajika scheme from memory (`# VERIFY`). The Hadda table is checked structurally in tests (each sign sums to 30; planet totals 79/82/76/66/57 = 360).

## Added in V2 phase 18
- `muhurta/tables.yaml` and `muhurta/rulesets/*.yaml`: standard nakshatra-class scheme (Dhruva/Chara/Kshipra/Mridu/Ugra/Tikshna/Misra; partition of the 27 checked in tests),
  Dishashoola (partition of the 7 weekdays checked), inauspicious yogas, Tarabala and Chandrabala; all from memory, `verify: true`, no primary source line yet.

## Added in V2 phase 19
- `numerology/data.yaml`: Vastu planet-direction lordship and navagraha beeja mantras from standard practice (from memory, `verify: true`). Pythagorean letter table is the standard A=1..I=9 cycle (checked in tests).

## Added in V2 phase 20
- `lalkitab/tables.py`, `lalkitab/debts.yaml`: from memory, `verify: true`, no cited edition. Exaltation/debilitation houses are derived from the sign exaltation table already sourced above.

## Added in V2 phase 21
- `scripts/content_data.py` vocabulary and the 558 drafted blocks are original text (no provider or vendor prose); they carry `sources: template:scripts/content_data.py (original vocabulary, unreviewed draft)` and must be reviewed before use. Tarabala nine-tara scheme: standard, from memory (`# VERIFY`).

## Added in V2 phase 22
- `remedies/rules.yaml`: selection rules from standard practice, from memory, `verify: true`; `GEMS` table as above. No remedy wording in code; drafts for gem/Sade Sati text come from the original vocabulary in `scripts/content_data.py`.

## Added in V2 phase 23
- Time zones: IANA tz database via `tzdata` (historical rules) and `timezonefinder` (zone boundaries, MIT). Places: the existing GeoNames extract. No new data tables.
