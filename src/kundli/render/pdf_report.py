"""PDF report (reportlab). Deterministic: invariant mode, no timestamps."""
import io
from typing import Any

from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus.flowables import Flowable
from svglib.svglib import svg2rlg

from ..data.tables import SEVEN, SIGNS
from ..models import Kundli
from . import north_indian, south_indian
from .common import LEGEND, view_for

DEFAULT_CHARTS = ["D1", "Chandra", "Surya", "Bhava", "D9", "D10", "D7", "D12"]
STY = getSampleStyleSheet()
TS = TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                 ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")), ("VALIGN", (0, 0), (-1, -1), "TOP")])


class _Svg(Flowable):
    def __init__(self, svg: str, width: float):
        super().__init__()
        d = svg2rlg(io.StringIO(svg))
        assert d is not None
        self.d = d
        s = width / self.d.width
        self.d.scale(s, s)
        self.width, self.height = self.d.width * s, self.d.height * s

    def draw(self) -> None:
        renderPDF.draw(self.d, self.canv, 0, 0)


def dms(x: float) -> str:
    d = int(x)
    m = int((x - d) * 60)
    s = round(((x - d) * 60 - m) * 60)
    if s == 60:
        m, s = m + 1, 0
    if m == 60:
        d, m = d + 1, 0
    return f"{d}°{m:02d}'{s:02d}\""


def _table(rows: list[list[Any]], widths=None) -> Table:
    t = Table([[str(c) for c in r] for r in rows], colWidths=widths, repeatRows=1)
    t.setStyle(TS)
    return t


def _chart_pair(k: Kundli, names: list[str], style: str) -> list:
    rend = north_indian if style == "north" else south_indian
    out: list = []
    row: list = []
    for n in names:
        try:
            row.append(_Svg(rend.render(view_for(k, n)), 85 * mm))
        except ValueError:
            continue
        if len(row) == 2:
            out.append(Table([row]))
            row = []
    if row:
        out.append(Table([row]))
    return out


def build_pdf(k: Kundli, charts: list[str] | None = None, style: str = "north") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, invariant=1, title=f"Kundli - {k.birth['name']}", author="kundli-engine")
    h1, h2, body = STY["Title"], STY["Heading2"], STY["BodyText"]
    b, cfg = k.birth, k.header["config"]
    f: list = [Spacer(1, 40 * mm), Paragraph("Kundli (Janma Patrika)", h1), Spacer(1, 8 * mm),
               Paragraph(f"<b>{b['name']}</b>", STY["Heading1"]),
               Paragraph(f"Born {b['local']} (UTC offset {b['utc_offset_seconds'] / 3600:+.2f} h)", body),
               Paragraph(f"{b['place']['name']}, {b['place']['admin1']} {b['place']['country']} &nbsp; "
                         f"lat {b['place']['lat']:.4f}, lon {b['place']['lon']:.4f}, tz {b['place']['tz']}", body)]
    if b["time_unknown"]:
        f.append(Paragraph("<b>Birth time unknown - lagna-dependent sections omitted.</b>", body))
    f += [Spacer(1, 10 * mm), Paragraph("Calculation settings", h2),
          _table([["Setting", "Value"]] + [[kk, vv] for kk, vv in sorted(cfg.items())], [60 * mm, 60 * mm]),
          Spacer(1, 4 * mm), Paragraph(f"Engine {k.header['engine_version']} &nbsp; run id {k.header['run_id'][:16]}... "
                                       f"&nbsp; Swiss Ephemeris {k.header['swisseph_version']}", body),
          Spacer(1, 6 * mm),
          Paragraph("Astronomical positions and dasha dates are computed exactly. Interpretive statements follow "
                    "traditional Jyotish and are not scientific predictions.", body), PageBreak()]
    f += [Paragraph("Charts", h2)] + _chart_pair(k, charts or DEFAULT_CHARTS, style) + [Paragraph(LEGEND, body)]
    f += [PageBreak(), Paragraph("Planets", h2)]
    rows: list[list[str]] = [["Planet", "Longitude", "Sign", "Deg", "Nakshatra", "Pd", "Lord", "Sub", "House", "Dignity", "Flags"]]
    for pd in k.planets:
        flags = ",".join(x for x, c in (("R", pd.retrograde), ("comb", pd.combust), ("vargottama", pd.vargottama)) if c)
        rows.append([pd.name, dms(pd.sidereal_lon), pd.sign_name, dms(pd.degree_in_sign), pd.nakshatra_name,
                     str(pd.pada), pd.nakshatra_lord[:2], pd.sub_lord[:2], str(pd.rashi_house or "-"), pd.dignity, flags])
    f.append(_table(rows))
    if k.lagna:
        f.append(Paragraph(f"Lagna: {k.lagna['sign_name']} {dms(k.lagna['degree_in_sign'])}, "
                           f"{k.lagna['nakshatra']} pada {k.lagna['pada']}", body))
    if k.panchang:
        pc = k.panchang
        f += [Paragraph("Panchang", h2), _table([["Tithi", "Vara", "Nakshatra", "Yoga", "Karana", "Moon illum."],
                                                  [f"{pc['tithi']['name']} ({pc['tithi']['paksha']})",
                                                   pc["vara"]["name"], pc["nakshatra"]["name"], pc["yoga"]["name"],
                                                   pc["karana"]["name"], f"{pc['moon_illumination']:.0%}"]])]
        if pc.get("sun_events"):
            f.append(Paragraph(f"Sunrise {pc['sun_events']['sunrise_local']} &nbsp; Sunset "
                               f"{pc['sun_events']['sunset_local']}", body))
    f += [PageBreak(), Paragraph("Vimshottari dasha", h2)]
    vb = k.dashas["vimshottari"]["balance_at_birth"]
    f.append(Paragraph(f"Balance at birth: {vb['lord']} {vb['years']:.2f} years", body))
    drows = [["Maha", "Start (local)", "End (local)"]] + [[m["lord"], m["start_local"][:10], m["end_local"][:10]]
                                                         for m in k.dashas["vimshottari"]["mahadashas"]]
    f.append(_table(drows))
    f.append(Paragraph("Antardashas (first 3 mahadashas)", h2))
    arows = [["Maha", "Antar", "Start", "End"]]
    for m in k.dashas["vimshottari"]["mahadashas"][:3]:
        for a in m.get("children", []):
            arows.append([m["lord"], a["lord"], a["start_local"][:10], a["end_local"][:10]])
    f.append(_table(arows))
    if k.shadbala:
        f += [PageBreak(), Paragraph("Shadbala (virupas)", h2)]
        srows = [["Planet", "Sthana", "Dig", "Kala", "Cheshta", "Naisarg.", "Drik", "Total", "Rupas", "Req.", "Ratio"]]
        for p in SEVEN:
            s = k.shadbala["planets"][p]
            srows.append([p, f"{s['sthana']['total']:.1f}", f"{s['dig']:.1f}", f"{s['kala']['total']:.1f}",
                          f"{s['cheshta']:.1f}", f"{s['naisargika']:.1f}", f"{s['drik']:.1f}",
                          f"{s['total_virupas']:.1f}", f"{s['total_rupas']:.2f}", s["required_virupas"],
                          f"{s['ratio']:.2f}"])
        f.append(_table(srows))
    if k.ashtakavarga:
        av = k.ashtakavarga
        f += [Paragraph("Ashtakavarga", h2)]
        hdr = ["", *[SIGNS[i][:3] for i in range(12)], "Tot"]
        rows = [hdr] + [[p, *av["bav"][p], sum(av["bav"][p])] for p in SEVEN] + [["SAV", *av["sav"], av["sav_total"]]]
        f.append(_table(rows))
    f += [PageBreak(), Paragraph("Yogas and doshas present", h2)]
    yrows = [["Yoga", "Category", "Planets", "Strength", "Cancelled by", "Source"]]
    for y in k.yogas:
        if y["present"]:
            yrows.append([y["name"], y["category"], ",".join(y["planets_involved"]), f"{y['strength']:.2f}",
                          ",".join(y["cancelled_by"]) or "-", y["source"]])
    f.append(_table(yrows, [48 * mm, 18 * mm, 30 * mm, 14 * mm, 30 * mm, 40 * mm]))
    f += [PageBreak(), Paragraph("Appendix: calculation details", h2),
          Paragraph("Sidereal longitudes use the configured ayanamsa via Swiss Ephemeris (Moshier mode unless Swiss "
                    "files are configured). Houses: " + str(k.houses["system_used"] if k.houses else "n/a") +
                    ". Conventions, sources and unverified (VERIFY) items are listed in docs/conventions.md, "
                    "docs/sources.md and docs/open_questions.md.", body),
          Paragraph(f"Ayanamsa at birth: {dms(k.header.get('ayanamsa_degrees', 0.0))}", body)]
    for n in k.notes:
        f.append(Paragraph("Note: " + n, body))
    doc.build(f)
    return buf.getvalue()
