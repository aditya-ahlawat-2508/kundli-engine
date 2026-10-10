# kundli-engine

Deterministic Vedic (Jyotish) astrology engine. **All calculations are done by code; the optional LLM only narrates facts the
engine computed.** Same input + same config = byte-identical JSON (`run_id` = SHA-256 of input, config, engine version).

Input: name, date, time (or unknown), place. Output: JSON kundli (planets, houses, bhava chalit, 20 vargas, Chandra/Surya charts,
panchang, special lagnas, upagrahas, Vimshottari + Yogini dashas, Shadbala, Bhava bala, Ashtakavarga, Vimshopaka, yogas/doshas,
Jaimini), North/South Indian SVG charts, a PDF report, transits/Sade Sati, a scored timeline and grounded Q&A.

## Quick start
    uv sync --all-extras
    uv run kundli generate --name "Aditya" --dob 2000-01-01 --time 12:00 --place "Agra, India" --out out/
    uv run kundli ask "When is a good time for a job change?" --chart out/chart.json --from 2026-10-10 --to 2028-12-31
    uv run kundli dasha --chart out/chart.json --date 2026-10-10
    uv run kundli serve            # API + web UI at http://127.0.0.1:8000

Ambiguous places (e.g. "Springfield") are never guessed: the CLI/API lists candidates; pass `--place-choice N`.
A DST-overlap local time needs `--fold 0|1`. Dates are always explicit (`--as-of`/`--from`); nothing reads the clock.

`--llm` uses Claude (`pip install kundli-engine[llm]`, set `ANTHROPIC_API_KEY`). Answers are validated: every claim must cite
real fact ids and every number must appear in the cited facts, otherwise the deterministic rule-based reading is returned.

API: `POST /kundli`, `GET /kundli/{id}`, `POST /kundli/{id}/ask`, `GET /kundli/{id}/charts/{varga}.svg`,
`GET /kundli/{id}/dasha?date=`, `GET /kundli/{id}/report.pdf`, `DELETE /kundli/{id}`, `GET /places?q=`.
Privacy: no logging of birth details, charts stored only under `~/.kundli/data` (`KUNDLI_DATA_DIR`), delete endpoint provided.

## Status and verification
See `docs/open_questions.md`. In short: positions match raw Swiss Ephemeris and published ingress dates; **not yet cross-checked
against JHora/Parashara's Light**; Shadbala and some tables are flagged `VERIFY`; Ashtottari/Chara/Kalachakra dashas and
Ashtakoota compatibility are not implemented.

## Licensing note
`pyswisseph` (Swiss Ephemeris) is AGPL; check licensing before commercial use. GeoNames data is CC-BY 4.0.

## Honest caveat
The astronomical part (positions, dashas, charts) is exact and verifiable. The predictive part is interpretive tradition:
different schools (Parashari, Jaimini, KP) give different readings, and there is no scientific evidence that chart readings
predict life events. The engine labels predictions accordingly and always shows which chart facts a statement is based on.

## Development
    uv run ruff check . && uv run mypy && uv run pytest -q
On macOS with the project under an iCloud-synced folder, keep the virtualenv outside it
(`UV_PROJECT_ENVIRONMENT=~/.venvs/kundli-engine`): the editable-install `.pth` can get a hidden flag and be ignored.
