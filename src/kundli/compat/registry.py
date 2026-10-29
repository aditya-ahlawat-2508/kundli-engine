"""Endpoint registry: one row per provider endpoint (compat/endpoints.yaml), validated on load."""
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

REGISTRY_FILE = Path(__file__).parent / "endpoints.yaml"
Status = Literal["missing", "partial", "exists", "done"]
Oracle = Literal["none", "reference", "shadow"]
Tier = Literal["T1", "T2", "T3", "T1/T2", "T1/T3", "Data"]


class Endpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    group: str
    tier: Tier
    module: str
    phase: str
    status: Status
    oracle: Oracle = "none"
    note: str = ""

    @property
    def path(self) -> str:
        """Route path with the provider's `:param` segments turned into FastAPI `{param}`."""
        return "/".join("{" + p[1:] + "}" if p.startswith(":") else p for p in self.name.split("/"))


@lru_cache(maxsize=1)
def load(path: Path = REGISTRY_FILE) -> tuple[Endpoint, ...]:
    rows = [Endpoint(**r) for r in yaml.safe_load(path.read_text(encoding="utf-8"))]
    names = [r.name for r in rows]
    dup = sorted(n for n, c in Counter(names).items() if c > 1)
    if dup:
        raise ValueError(f"duplicate endpoint names: {dup}")
    return tuple(rows)


def by_name(name: str) -> Endpoint:
    for e in load():
        if e.name == name:
            return e
    raise KeyError(name)


def gap_markdown() -> str:
    """docs/gap_analysis.md body, generated from the registry so the document cannot drift from it."""
    rows = load()
    c = Counter(r.status for r in rows)
    out = ["# Gap analysis: provider endpoints vs this engine", "",
           "Generated from `src/kundli/compat/endpoints.yaml` (`kundli oracle gap`); do not edit by hand.", "",
           f"**{len(rows)} endpoints, {len({r.group for r in rows})} groups.** exists: {c['exists']}, "
           f"partial: {c['partial']}, missing: {c['missing']}, done: {c['done']}.", "",
           "`exists` = the engine computes it (response shape still engine-neutral); `partial` = some of it; "
           "`missing` = not built; `done` = oracle-verified and schema-matched (none yet).", ""]
    groups: dict[str, list[Endpoint]] = {}
    for r in rows:
        groups.setdefault(r.group, []).append(r)
    out += ["| Group | Tier | Phase | exists | partial | missing |", "|---|---|---|---|---|---|"]
    for gname, items in groups.items():
        cc = Counter(i.status for i in items)
        out.append(f"| {gname} ({len(items)}) | {items[0].tier} | {items[0].phase} | {cc['exists']} | {cc['partial']} | {cc['missing']} |")
    for gname, items in groups.items():
        out += ["", f"## {gname}", "", f"Tier {items[0].tier}; module: {items[0].module}; phase {items[0].phase}.", "",
                "| Endpoint | Status | Note |", "|---|---|---|"]
        out += [f"| `{i.name}` | {i.status} | {i.note} |" for i in items]
    return "\n".join(out) + "\n"
