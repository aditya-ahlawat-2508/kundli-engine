"""South Indian (square) chart: signs are fixed on the page, the lagna is marked."""
from ..data.tables import SIGNS
from .common import ChartView

# sign index -> (col,row) on the 4x4 grid
GRID = {11: (0, 0), 0: (1, 0), 1: (2, 0), 2: (3, 0), 10: (0, 1), 3: (3, 1), 9: (0, 2), 4: (3, 2),
        8: (0, 3), 7: (1, 3), 6: (2, 3), 5: (3, 3)}
CELL = 100


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;")


def render(view: ChartView, size: int = 400) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size + 28}" '
           f'viewBox="0 0 400 428" font-family="Helvetica, Arial, sans-serif">',
           f'<text x="200" y="16" text-anchor="middle" font-size="14" font-weight="bold">{_esc(view.title)}</text>',
           '<g transform="translate(0,24)">']
    for sign, (c, r) in sorted(GRID.items()):
        x, y = c * CELL, r * CELL
        out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="white" stroke="black" stroke-width="1.5"/>')
        out.append(f'<text x="{x + 4}" y="{y + 12}" font-size="9" fill="#777">{SIGNS[sign][:3]}</text>')
        if view.lagna_sign == sign:
            out.append(f'<line x1="{x}" y1="{y}" x2="{x + 22}" y2="{y + 22}" stroke="black" stroke-width="2"/>')
            out.append(f'<text x="{x + CELL - 4}" y="{y + 12}" text-anchor="end" font-size="9" font-weight="bold">'
                       f'{_esc(view.lagna_label)}</text>')
        for i, m in enumerate(view.by_sign.get(sign, [])):
            out.append(f'<text x="{x + CELL / 2}" y="{y + 30 + i * 13}" text-anchor="middle" font-size="11">'
                       f'{_esc(m.label())}</text>')
    out.append('<rect x="100" y="100" width="200" height="200" fill="white" stroke="black" stroke-width="1.5"/>')
    out.append(f'<text x="200" y="200" text-anchor="middle" font-size="13" fill="#444">{_esc(view.title)}</text>')
    out.append("</g></svg>")
    return "\n".join(out)
