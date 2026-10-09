# Sources

- Swiss Ephemeris / pyswisseph — https://www.astro.com/swisseph/ (AGPL / commercial dual license).
- Lahiri ayanamsa — Indian Calendar Reform Committee (1955): 23°15′00.658″ at 1956-03-21; used as a unit-test anchor.
- GeoNames `cities15000`, `countryInfo`, `admin1CodesASCII` — https://download.geonames.org/export/dump/ (CC-BY 4.0). Trimmed by `scripts/build_geo_data.py`.
- IANA tz database via the `tzdata` PyPI package.
- Nominatim (OpenStreetMap) — fallback geocoder; usage policy requires a User-Agent and caching (done).
