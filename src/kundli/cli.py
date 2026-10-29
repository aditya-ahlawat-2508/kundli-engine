"""Command line: `kundli generate | ask | dasha | places | serve`."""
import json
from pathlib import Path

import typer

from .chart import current_dasha, generate, to_json
from .config import EngineConfig
from .errors import AmbiguousLocalTime, AmbiguousPlace, NonexistentLocalTime, PlaceNotFound
from .geo import candidates
from .predict.llm import AnthropicClient, answer
from .render import north_indian, pdf_report, south_indian
from .render.common import view_for
from .service import aware, load_chart, make_birth

app = typer.Typer(add_completion=False, help="Deterministic Vedic astrology engine.")
oracle_app = typer.Typer(add_completion=False, help="Compare the engine with an external reference (oracle).")
app.add_typer(oracle_app, name="oracle")
content_app = typer.Typer(add_completion=False, help="Content blocks: status, lint, review (human) and freeze.")
app.add_typer(content_app, name="content")
shadow_app = typer.Typer(add_completion=False, help="Shadow-mode diff rates and cutover readiness.")
app.add_typer(shadow_app, name="shadow")
CHARTS = ["D1", "Chandra", "Surya", "Bhava", "D9", "D10", "D7", "D12"]


@app.command()
def places(query: str) -> None:
    """List place candidates for a query."""
    for i, p in enumerate(candidates(query)):
        typer.echo(f"[{i}] {p.name}, {p.admin1}, {p.country}  lat={p.lat:.4f} lon={p.lon:.4f} tz={p.tz}")


@app.command()
def generate_cmd(
    name: str = typer.Option(...), dob: str = typer.Option(..., help="YYYY-MM-DD"),
    time: str = typer.Option("unknown", help="HH:MM[:SS] or 'unknown'"), place: str = typer.Option(None),
    place_choice: int = typer.Option(None), fold: int = typer.Option(None, help="0/1 for a DST-overlap time"),
    lat: float = typer.Option(None), lon: float = typer.Option(None), tz: str = typer.Option(None),
    out: Path = typer.Option(Path("out")), ayanamsa: str = "lahiri", node_type: str = "true",
    house_system: str = "whole_sign", dasha_year_days: float = 365.25, language: str = "en",
    style: str = typer.Option("north", help="north | south"), pdf: bool = True,
) -> None:
    """Generate chart.json, SVG charts and a PDF report."""
    try:
        birth = make_birth(name, dob, time, place, place_choice, fold, lat, lon, tz)
        cfg = EngineConfig.model_validate({"ayanamsa": ayanamsa, "node_type": node_type, "house_system": house_system,
                                           "dasha_year_days": dasha_year_days, "language": language})
        k = generate(birth, cfg)
    except AmbiguousPlace as e:
        typer.echo("Several places match; re-run with --place-choice N:", err=True)
        for i, p in enumerate(e.candidates):
            typer.echo(f"  [{i}] {p.name}, {p.admin1}, {p.country} ({p.tz})", err=True)
        raise typer.Exit(2) from None
    except (AmbiguousLocalTime, NonexistentLocalTime, PlaceNotFound, ValueError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from None
    out.mkdir(parents=True, exist_ok=True)
    (out / "chart.json").write_text(to_json(k), encoding="utf-8")
    rend = north_indian if style == "north" else south_indian
    for c in CHARTS:
        try:
            (out / f"{c}.svg").write_text(rend.render(view_for(k, c)), encoding="utf-8")
        except ValueError:
            pass
    if pdf:
        (out / "report.pdf").write_bytes(pdf_report.build_pdf(k, style=style))
    typer.echo(f"wrote {out}/chart.json (run_id {k.header['run_id'][:12]})")


app.command("generate")(generate_cmd)


@app.command()
def ask(question: str, chart: Path = typer.Option(...), as_of: str = typer.Option(None, "--as-of"),
        from_: str = typer.Option(None, "--from"), to: str = typer.Option(None, "--to"),
        language: str = "en", llm: bool = typer.Option(False, help="Use Claude (needs ANTHROPIC_API_KEY)")) -> None:
    """Answer a question from the chart (rule-based by default; --llm for grounded Claude narration)."""
    k = load_chart(chart)
    ref = as_of or from_
    if not ref:
        typer.echo("error: pass --as-of or --from (the engine never reads the clock)", err=True)
        raise typer.Exit(2)
    r = answer(k, question, aware(ref), aware(from_) if from_ else None, aware(to) if to else None,
               AnthropicClient() if llm else None, language)
    typer.echo(json.dumps(r, indent=1, ensure_ascii=False))


@app.command()
def dasha(chart: Path = typer.Option(...), date: str = typer.Option(...), system: str = "vimshottari",
          levels: int = 4) -> None:
    """Running dasha stack on a given date."""
    typer.echo(json.dumps(current_dasha(load_chart(chart), aware(date), system, levels), indent=1))


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the API + web UI (local only by default)."""
    import uvicorn

    uvicorn.run("kundli.api:app", host=host, port=port, access_log=False)


@oracle_app.command("cases")
def oracle_cases(n: int = 120, seed: int = 20260101, out: Path = Path("tests/oracle/cases.json")) -> None:
    """Write the deterministic birth-input cases used for oracle fixtures."""
    from .oracle.cases import generate_cases

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(generate_cases(n, seed), indent=1), encoding="utf-8")
    typer.echo(f"wrote {n} cases to {out}")


@oracle_app.command("gap")
def oracle_gap(out: Path = Path("docs/gap_analysis.md")) -> None:
    """Regenerate docs/gap_analysis.md from the endpoint registry."""
    from .compat.registry import gap_markdown

    out.write_text(gap_markdown(), encoding="utf-8")
    typer.echo(f"wrote {out}")


@oracle_app.command("diff")
def oracle_diff(expected: Path, actual: Path, limit: int = 20) -> None:
    """Field-level diff of two JSON documents with per-field-type tolerances."""
    from .oracle.diff import diff, summarize

    r = diff(json.loads(expected.read_text(encoding="utf-8")), json.loads(actual.read_text(encoding="utf-8")))
    typer.echo(json.dumps(summarize(r), indent=1))
    for m in r.mismatches[:limit]:
        typer.echo(f"  {m.kind.value:9} {m.path}: expected {m.expected!r} got {m.actual!r}")
    for path in r.missing[:limit]:
        typer.echo(f"  missing   {path}")


@oracle_app.command("fingerprint")
def oracle_fingerprint(fixture: Path, top: int = 5) -> None:
    """Rank ayanamsa/node and dasha-year variants by agreement with an oracle fixture (tests/oracle/fixtures)."""
    from datetime import date, time

    from .models import BirthInput, Place
    from .oracle.fingerprint import fingerprint_dasha, fingerprint_positions

    f = json.loads(fixture.read_text(encoding="utf-8"))
    b = f["birth"]
    place = Place(name=b.get("place", "fixture"), lat=b["lat"], lon=b["lon"], tz=b["tz"], source="manual")
    birth = BirthInput(name="fixture", date=date.fromisoformat(b["date"]), time=time.fromisoformat(b["time"]), place=place)
    exp = f["expected"]
    if "sidereal_longitudes" in exp:
        typer.echo("positions (ayanamsa/node): max error deg, mean error deg")
        for fit in fingerprint_positions(birth, exp["sidereal_longitudes"])[:top]:
            typer.echo(f"  {fit.variant.name:22} {fit.max_error:9.5f} {fit.mean_error:9.5f}")
    if "vimshottari_maha_starts" in exp:
        typer.echo("dasha year length: max error days, mean error days")
        for fit in fingerprint_dasha(birth, [tuple(x) for x in exp["vimshottari_maha_starts"]]):
            typer.echo(f"  {fit.variant.name:22} {fit.max_error:9.3f} {fit.mean_error:9.3f}")


@oracle_app.command("collect")
def oracle_collect(endpoint: str, cases: Path = Path("tests/oracle/cases.json"), limit: int = 5,
                   tos_checked: bool = typer.Option(False, help="Confirm the provider's terms allow this")) -> None:
    """Save provider responses as fixtures (needs KUNDLI_ORACLE_URL / KUNDLI_ORACLE_AUTH)."""
    from .oracle.collect import collect, http_fetch_from_env

    chosen = json.loads(cases.read_text(encoding="utf-8"))[:limit]
    try:
        paths = collect(endpoint, chosen, http_fetch_from_env(), tos_checked=tos_checked)
    except (PermissionError, RuntimeError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from None
    typer.echo(f"saved {len(paths)} fixtures")


if __name__ == "__main__":
    app()


# ---- content layer (V2 phase 21) ---------------------------------------------------------------------------
@content_app.command("status")
def content_status() -> None:
    """Counts per language and status, locked blocks and coverage of the reachable key space."""
    from collections import Counter

    from .content import keys, schema
    from .content.store import ContentStore

    store = ContentStore()
    reachable = keys.all_keys()
    typer.echo(f"reachable keys: {len(reachable)}   content_version: {store.version}")
    for lang in schema.LANGS:
        blocks = [schema.read(p) for p in sorted(store.blocks_dir.glob(f"{lang}/*/*.md"))]
        counts = Counter(b.status for b in blocks)
        locked = len(store.lock()["blocks"].get(lang, {}))
        served = len(reachable & set(store.lock()["blocks"].get(lang, {})))
        typer.echo(f"{lang}: files={len(blocks)} draft={counts['draft']} reviewed={counts['reviewed']} frozen={counts['frozen']} "
                   f"locked={locked} served-coverage={served}/{len(reachable)}")


@content_app.command("lint")
def content_lint(langs: str = typer.Option("", help="comma-separated languages that must cover every reachable key")) -> None:
    """Lint all blocks and the lock; exit 1 on errors."""
    from .content.lint import errors, lint
    from .content.store import ContentStore

    issues = lint(ContentStore(), tuple(x for x in langs.split(",") if x))
    for i in issues:
        typer.echo(str(i))
    typer.echo(f"{len(errors(issues))} error(s), {len(issues) - len(errors(issues))} warning(s)")
    raise typer.Exit(1 if errors(issues) else 0)


@content_app.command("review")
def content_review(key: str = typer.Argument(None), lang: str = typer.Option("en"), reviewer: str = typer.Option(...),
                   topic: str = typer.Option(None, help="review every draft of this topic (requires --confirm-read)"),
                   confirm_read: bool = typer.Option(False, help="state that you have read every block you are promoting")) -> None:
    """HUMAN step: mark draft block(s) as reviewed by `reviewer`. Never run by the engine or the API."""
    from .content import schema
    from .content.freeze import review
    from .content.store import DEFAULT_DIR

    if topic:
        if not confirm_read:
            raise typer.BadParameter("--topic promotes many blocks at once: pass --confirm-read to confirm you read them")
        keys_ = [schema.read(p).key for p in sorted((DEFAULT_DIR / lang / topic).glob("*.md")) if schema.read(p).status == "draft"]
    elif key:
        keys_ = [key]
    else:
        raise typer.BadParameter("give a KEY or --topic")
    for k in keys_:
        review(DEFAULT_DIR, k, lang, reviewer)
    typer.echo(f"marked {len(keys_)} block(s) as reviewed by {reviewer}; run `kundli content freeze` to lock them")


@content_app.command("freeze")
def content_freeze() -> None:
    """Lint, then write content.lock from the reviewed blocks and mark them frozen. Exit 1 (nothing written) on lint errors."""
    from .content.freeze import freeze
    from .content.lint import errors
    from .content.store import DEFAULT_DIR, DEFAULT_LOCK

    lock, issues = freeze(DEFAULT_DIR, DEFAULT_LOCK)
    for i in issues:
        typer.echo(str(i))
    if errors(issues):
        raise typer.Exit(1)
    n = sum(len(v) for v in lock["blocks"].values())
    typer.echo(f"froze {n} block(s); content_version {lock['content_version']}")


# ---- shadow mode / cutover (V2 phase 23) -------------------------------------------------------------------
@shadow_app.command("report")
def shadow_report_cmd(log: Path = typer.Option(None, help="shadow log (default: $KUNDLI_SHADOW_LOG)"),
                      days: float = typer.Option(14.0, help="window in days")) -> None:
    """Per-endpoint diff rate over the window and whether the endpoint may cut over to the engine."""
    import os

    from . import ops

    if log:
        os.environ["KUNDLI_SHADOW_LOG"] = str(log)
    rep = ops.shadow_report(window_days=days)
    if not rep["log_configured"]:
        typer.echo("no shadow log configured (set KUNDLI_SHADOW_LOG or pass --log)")
        raise typer.Exit(1)
    for name, row in rep["endpoints"].items():
        rate = "n/a" if row["diff_rate"] is None else f"{row['diff_rate']:.2%}"
        verdict = "READY" if row["readiness"]["ready"] else "not ready: " + "; ".join(row["readiness"]["reasons"])
        typer.echo(f"{name:40s} {row['tier']:6s} mode={row['mode']:8s} n={row['requests']:5d} diff={rate:>7s}  {verdict}")

