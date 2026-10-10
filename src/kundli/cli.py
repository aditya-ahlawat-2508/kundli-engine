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


if __name__ == "__main__":
    app()
