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
