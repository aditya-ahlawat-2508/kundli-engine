"""North Indian (diamond) chart: houses are fixed on the page, signs rotate with the lagna."""
from .common import ChartView, Mark

S = 400.0


def _pt(x: float, y: float) -> tuple[float, float]:
    return x * S, y * S


# House polygons in unit-square coordinates (A top-left, B top-right, C bottom-right, D bottom-left).
A, B, C, D = (0, 0), (1, 0), (1, 1), (0, 1)
MT, MR, MB, ML = (0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5)
O = (0.5, 0.5)
P1, P2, P3, P4 = (0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)
HOUSES: dict[int, list[tuple[float, float]]] = {
    1: [MT, P1, O, P2], 2: [A, MT, P1], 3: [A, P1, ML], 4: [ML, P1, O, P4], 5: [ML, P4, D], 6: [D, P4, MB],
    7: [MB, P4, O, P3], 8: [MB, P3, C], 9: [C, P3, MR], 10: [MR, P3, O, P2], 11: [MR, P2, B], 12: [B, P2, MT],
}


def _centroid(poly: list[tuple[float, float]]) -> tuple[float, float]:
    # Vertex average, nudged toward the outer edge for triangles so text clears the lines.
    x = sum(p[0] for p in poly) / len(poly)
    y = sum(p[1] for p in poly) / len(poly)
    return x, y


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;")


def render(view: ChartView, size: int = 400) -> str:
    if view.lagna_sign is None:
        raise ValueError("North Indian chart needs a lagna; use South Indian or the Chandra chart")
    by_house: dict[int, list[Mark]] = {}
    for sign, marks in view.by_sign.items():
        by_house.setdefault(view.house_of_sign(sign), []).extend(marks)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size + 28}" '
           f'viewBox="0 0 {S:.0f} {S + 28:.0f}" font-family="Helvetica, Arial, sans-serif">',
           f'<text x="{S / 2:.0f}" y="16" text-anchor="middle" font-size="14" font-weight="bold">{_esc(view.title)}</text>',
           '<g transform="translate(0,24)">',
           f'<rect x="0" y="0" width="{S:.0f}" height="{S:.0f}" fill="white" stroke="black" stroke-width="2"/>']
    for a, b in ((A, C), (B, D), (MT, MR), (MR, MB), (MB, ML), (ML, MT)):
        (x1, y1), (x2, y2) = _pt(*a), _pt(*b)
        out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="black" stroke-width="1.5"/>')
    for h in range(1, 13):
        cx, cy = _centroid(HOUSES[h])
        sign = (view.lagna_sign + h - 1) % 12
        x, y = cx * S, cy * S
        out.append(f'<text x="{x:.2f}" y="{y - (34 if h in (1, 4, 7, 10) else 20):.2f}" text-anchor="middle" '
                   f'font-size="11" fill="#555">{sign + 1}</text>')
        marks = by_house.get(h, [])
        if h == 1:
            marks_txt = [view.lagna_label] + [m.label() for m in marks]
        else:
            marks_txt = [m.label() for m in marks]
        for i, t in enumerate(marks_txt):
            yy = y - 4 + i * 13
            out.append(f'<text x="{x:.2f}" y="{yy:.2f}" text-anchor="middle" font-size="11">{_esc(t)}</text>')
    out.append("</g></svg>")
    return "\n".join(out)
