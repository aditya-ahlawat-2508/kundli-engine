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
