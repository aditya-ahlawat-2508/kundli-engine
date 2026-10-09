# kundli-engine

Deterministic Vedic (Jyotish) astrology engine. **All calculations are done by code; an LLM (Phase 9, optional) only narrates facts the engine computed.**
Same input + same config = identical output.

## Status
- Phase 1 (time, geo, ephemeris, ayanamsa): done.

## Licensing note
`pyswisseph` (Swiss Ephemeris) is AGPL. Check licensing before commercial use.

## Honest caveat
The astronomical part (positions, dashas, charts) is exact and verifiable. The predictive part is interpretive
tradition: different schools (Parashari, Jaimini, KP) give different readings, and there is no scientific evidence
that chart readings predict life events. The engine labels predictions accordingly and shows which chart facts a
statement is based on.

## Dev
    uv sync && uv run pytest && uv run ruff check . && uv run mypy
