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
