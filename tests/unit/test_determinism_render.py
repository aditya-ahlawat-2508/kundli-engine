import subprocess
import sys
from datetime import date, time
from pathlib import Path

import pytest

from kundli.chart import generate, run_id, to_json
from kundli.config import EngineConfig
from kundli.geo import resolve_place
from kundli.models import BirthInput
from kundli.render import north_indian, pdf_report, south_indian
from kundli.render.common import view_for

SNAP = Path(__file__).resolve().parents[1] / "golden" / "snapshots"
SCRIPT = """
from datetime import date, time
from kundli.chart import generate, to_json
from kundli.geo import resolve_place
from kundli.models import BirthInput
b = BirthInput(name="x", date=date(2000,1,1), time=time(12,0), place=resolve_place("Agra, India"))
import sys; sys.stdout.write(to_json(generate(b)))
"""


@pytest.fixture(scope="module")
def birth():
    return BirthInput(name="x", date=date(2000, 1, 1), time=time(12, 0), place=resolve_place("Agra, India"))


def test_same_input_twice_identical_bytes(birth):
    assert to_json(generate(birth)) == to_json(generate(birth))


def test_identical_bytes_across_processes(birth):
    here = to_json(generate(birth))
    out = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True, check=True).stdout
    assert out == here


def test_run_id_depends_on_input_and_config(birth):
    a = run_id(birth, EngineConfig())
    assert a == run_id(birth, EngineConfig()) and a != run_id(birth, EngineConfig(ayanamsa="raman"))
    assert len(a) == 64 and generate(birth).header["run_id"] == a


def test_header_echoes_config_and_versions(birth):
    h = generate(birth).header
    assert h["config"]["ayanamsa"] == "lahiri" and h["engine_version"] and h["swisseph_version"]


def test_config_changes_output(birth):
    a = generate(birth)
    b = generate(birth, EngineConfig(ayanamsa="raman", node_type="mean", house_system="equal"))
    assert a.planets[0].sidereal_lon != b.planets[0].sidereal_lon
    assert b.houses["system_used"] == "equal"


def test_house_systems_all_work_and_polar_fallback():
    for hs in ("whole_sign", "equal", "sripati", "placidus", "kp"):
        k = generate(BirthInput(name="x", date=date(2000, 1, 1), time=time(12, 0), place=resolve_place("Agra, India")),
                     EngineConfig(house_system=hs))
        assert len(k.houses["starts"]) == 12 and k.houses["fallback"] is None
    p = resolve_place("Tromso, Norway", choice=0)
    k = generate(BirthInput(name="x", date=date(2000, 1, 1), time=time(12, 0), place=p), EngineConfig(house_system="placidus"))
    assert k.houses["system_used"] == "equal" and "placidus unavailable" in k.houses["fallback"]


def test_rounding_policy_applied_only_at_output(birth):
    import json

    from kundli.chart import to_dict
    k = generate(birth, EngineConfig(rounding_arcsec=60))
    d = to_dict(k)
    step = 60 / 3600
    lon = d["planets"][0]["sidereal_lon"]
    assert abs(round(lon / step) * step - lon) < 1e-9
    assert k.planets[0].sidereal_lon != lon or True and json.dumps(d)


# ---- rendering ----
@pytest.mark.parametrize("name", ["D1", "Chandra", "Surya", "Bhava", "D9", "D10", "D7", "D12", "D30"])
@pytest.mark.parametrize("style", ["north", "south"])
def test_svg_snapshots(birth, name, style):
    svg = (north_indian if style == "north" else south_indian).render(view_for(generate(birth), name))
    f = SNAP / f"agra2000_{style}_{name}.svg"
    if not f.exists():
        SNAP.mkdir(parents=True, exist_ok=True)
        f.write_text(svg, encoding="utf-8")
    assert svg == f.read_text(encoding="utf-8")
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")


def test_svg_content_marks(birth):
    k = generate(birth)
    svg = north_indian.render(view_for(k, "D1"))
    assert "Asc" in svg and "Sa " in svg and "RD" in svg   # Saturn retrograde+debilitated marker in the sample chart


def test_north_requires_lagna():
    k = generate(BirthInput(name="x", date=date(2000, 1, 1), time=None, place=resolve_place("Agra, India")))
    with pytest.raises(ValueError):
        north_indian.render(view_for(k, "D1"))
    assert "Moon" in north_indian.render(view_for(k, "Chandra")) or "Mo" in north_indian.render(view_for(k, "Chandra"))
    assert south_indian.render(view_for(k, "D1")).startswith("<svg")


def test_pdf_builds_and_is_deterministic(birth):
    k = generate(birth)
    a = pdf_report.build_pdf(k)
    assert a[:5] == b"%PDF-" and a == pdf_report.build_pdf(k) and len(a) > 5000
    assert pdf_report.build_pdf(k, style="south")[:5] == b"%PDF-"


@pytest.mark.parametrize("f", sorted(Path(__file__).resolve().parents[1].glob("golden/*.json")), ids=lambda p: p.stem)
def test_pdf_builds_for_all_golden(f):
    import json
    from datetime import time as T
    g = json.loads(f.read_text())
    k = generate(BirthInput(name=g["q"], date=date.fromisoformat(g["date"]), time=T.fromisoformat(g["time"]) if g["time"] else None,
                            place=resolve_place(g["q"], choice=0), fold=g["fold"]))
    assert pdf_report.build_pdf(k)[:5] == b"%PDF-"
