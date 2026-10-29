"""Declarative yoga engine. Rule conditions are parsed with `ast` and evaluated by a whitelist interpreter:
no eval/exec, no attribute access, no imports. Only calls to the functions registered in `chart_functions`.
"""
import ast
import copy
import operator
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..aspects import aspects_sign
from ..core import Core, angdiff
from ..data.tables import BENEFICS, EXALTATION, PLANETS, SIGN_LORDS

RULES_DIR = Path(__file__).parent / "rules"
PLANET_NAMES = {p.lower(): p for p in PLANETS}
CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
       ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
BIN = {ast.Add: operator.add, ast.Sub: operator.sub}


class RuleError(Exception):
    pass


# ---- chart facts exposed to rules -------------------------------------------------------------------
def chart_functions(c: Core) -> dict[str, Callable[..., Any]]:
    def ref_sign(ref: str) -> int:
        if ref == "Lagna":
            assert c.lagna_sign is not None
            return c.lagna_sign
        return c.sign[ref]

    def house(p: str) -> int:
        h = c.rashi_house[p]
        assert h is not None, "needs lagna"
        return h

    def house_from(p: str, ref: str) -> int:
        return (c.sign[p] - ref_sign(ref)) % 12 + 1

    def lord(h: int) -> str:
        return c.lord_of_house(h)

    def conj(a: str, b: str) -> bool:
        return c.sign[a] == c.sign[b]

    def aspects(a: str, b: str) -> bool:
        return aspects_sign(a, c.sign[a], c.sign[b])

    def exchange(a: str, b: str) -> bool:
        return SIGN_LORDS[c.sign[a]] == b and SIGN_LORDS[c.sign[b]] == a and a != b

    def related(a: str, b: str) -> bool:
        return a != b and (conj(a, b) or aspects(a, b) or aspects(b, a) or exchange(a, b))

    def planets_in_house_from(ref: str, n: int, excl: list[str] | None = None) -> list[str]:
        skip = set(excl if excl is not None else ["Sun", "Moon", "Rahu", "Ketu"])
        s = (ref_sign(ref) + n - 1) % 12
        return [p for p in PLANETS if c.sign[p] == s and p not in skip]

    def planets_in_kendra_from(ref: str) -> list[str]:
        out: list[str] = []
        for n in (1, 4, 7, 10):
            out += planets_in_house_from(ref, n, ["Sun", "Rahu", "Ketu", "Moon"])
        return out

    def pure_benefic_in(ref: str, n: int) -> bool:
        occ = planets_in_house_from(ref, n, [])
        occ = [p for p in occ if not (ref in PLANETS and p == ref and n == 1)]
        return bool(occ) and all(p in BENEFICS for p in occ)

    def benefics_in(ref: str, houses: list[int]) -> list[str]:
        out: list[str] = []
        for n in houses:
            out += [p for p in planets_in_house_from(ref, n, []) if p in ("Mercury", "Jupiter", "Venus")]
        return out

    def kt_relations() -> list[list[str]]:
        kendra = {lord(h) for h in (1, 4, 7, 10)}
        trikona = {lord(h) for h in (1, 5, 9)}
        return [[a, b] for a in sorted(kendra) for b in sorted(trikona) if a != b and related(a, b)]

    def yogakarakas() -> list[str]:
        kendra = {lord(h) for h in (4, 7, 10)}
        trikona = {lord(h) for h in (5, 9)}
        return sorted(kendra & trikona)

    def related_lords(h1: int, h2: int) -> bool:
        return related(lord(h1), lord(h2))

    def exchange_pairs() -> list[list[str]]:
        sev = PLANETS[:7]
        return [[a, b] for i, a in enumerate(sev) for b in sev[i + 1:] if exchange(a, b)]

    def flatten(pairs: list[list[str]]) -> list[str]:
        return sorted({p for pr in pairs for p in pr})

    def exalted_in_sign_of(p: str) -> str | None:
        for q, (s, _) in EXALTATION.items():
            if s == c.sign[p] and q in PLANETS[:7]:
                return q
        return None

    def neecha_bhanga(p: str) -> list[str]:
        """Cancellation reasons for a debilitated planet (BPHS): dispositor or the planet exalted in that sign
        stands in a kendra from Lagna or Moon."""
        if c.dignity[p] != "debilitated":
            return []
        out = []
        for who, tag in ((SIGN_LORDS[c.sign[p]], "dispositor"), (exalted_in_sign_of(p), "exaltation_lord")):
            if who is None or who == p:
                continue
            if house(who) in (1, 4, 7, 10):
                out.append(f"{tag} {who} in kendra from Lagna")
            if house_from(who, "Moon") in (1, 4, 7, 10):
                out.append(f"{tag} {who} in kendra from Moon")
        return out

    def arc_contains(a: float, b: float, x: float) -> bool:
        return (x - a) % 360.0 <= (b - a) % 360.0

    def kaal_sarpa() -> bool:
        r, k = c.lon["Rahu"], c.lon["Ketu"]
        sev = PLANETS[:7]
        return all(arc_contains(r, k, c.lon[p]) for p in sev) or all(arc_contains(k, r, c.lon[p]) for p in sev)

    def dignity_of(p: str) -> str:
        return c.dignity[p]

    return {
        "house": house, "sign": lambda p: c.sign[p], "house_from": house_from, "dignity": dignity_of,
        "lord": lord, "conj": conj, "aspects": aspects, "exchange": exchange, "related": related,
        "related_lords": related_lords, "planets_in_house_from": planets_in_house_from,
        "planets_in_kendra_from": planets_in_kendra_from, "pure_benefic_in": pure_benefic_in,
        "benefics_in": benefics_in, "kt_relations": kt_relations, "yogakarakas": yogakarakas,
        "exchange_pairs": exchange_pairs, "flatten": flatten, "neecha_bhanga": neecha_bhanga,
        "kaal_sarpa": kaal_sarpa, "retro": lambda p: c.pos[p].retrograde, "combust": lambda p: c.combust[p],
        "houses_owned": lambda p: c.lords_of[p], "len": len,
        "angdiff": lambda a, b: angdiff(c.lon[a], c.lon[b]),
    }


# ---- safe evaluator ---------------------------------------------------------------------------------
def evaluate(expr: str, fns: dict[str, Callable[..., Any]]) -> Any:
    """Evaluate a whitelisted expression. Names resolve to planets (jupiter -> 'Jupiter') or 'lagna' -> 'Lagna'."""
    tree = ast.parse(expr.strip(), mode="eval")

    def ev(n: ast.AST) -> Any:
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float, str, bool, type(None))):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in PLANET_NAMES:
                return PLANET_NAMES[n.id]
            if n.id == "lagna":
                return "Lagna"
            raise RuleError(f"unknown name {n.id!r}")
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(e) for e in n.elts]
        if isinstance(n, ast.BoolOp):
            vals = (ev(v) for v in n.values)
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return not ev(n.operand)
        if isinstance(n, ast.BinOp) and type(n.op) in BIN:
            return BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, comp in zip(n.ops, n.comparators, strict=True):
                right = ev(comp)
                if type(op) not in CMP or not CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in fns and not n.keywords:
            return fns[n.func.id](*[ev(a) for a in n.args])
        raise RuleError(f"disallowed syntax: {ast.dump(n)[:60]}")

    return ev(tree)


# ---- rules ------------------------------------------------------------------------------------------
@lru_cache(maxsize=8)
def _load(directory: Path) -> tuple[dict, ...]:
    rules: list[dict] = []
    for f in sorted(directory.glob("*.yaml")):
        rules.extend(yaml.safe_load(f.read_text(encoding="utf-8")) or [])
    return tuple(rules)


def load_rules(directory: Path = RULES_DIR) -> list[dict]:
    """The rule dicts of every YAML file in `directory`. Parsed once per process; callers get their own deep copy."""
    return copy.deepcopy(list(_load(directory)))


def _expand(rule: dict) -> list[dict]:
    """Expand `foreach: [Mars, ...]` rules, substituting $p in strings with the lower-case planet name."""
    each = rule.get("foreach")
    if not each:
        return [rule]
    out = []
    for p in each:
        r = {k: v for k, v in rule.items() if k != "foreach"}
        r = yaml.safe_load(yaml.safe_dump(r).replace("$P", p).replace("$p", p.lower()))
        out.append(r)
    return out


def _static_planets(expr: str) -> list[str]:
    return sorted({PLANET_NAMES[n.id] for n in ast.walk(ast.parse(expr, mode="eval"))
                   if isinstance(n, ast.Name) and n.id in PLANET_NAMES})


def evaluate_yogas(core: Core, shadbala: dict | None = None) -> list[dict]:
    fns = chart_functions(core)
    results: list[dict] = []
    for raw in load_rules():
        for r in _expand(raw):
            base = {"id": r["id"], "name": r["name"], "category": r["category"], "source": r["source"],
                    "effects_key": r.get("effects_key", r["id"])}
            try:
                present = bool(evaluate(r["condition"], fns))
                detail = evaluate(r["detail"], fns) if present and r.get("detail") else None
                if present and r.get("planets"):
                    involved = sorted(evaluate(r["planets"], fns))
                else:
                    involved = _static_planets(r["condition"]) if present else []
                cancelled = []
                if present:
                    for cx in r.get("cancellations", []):
                        if evaluate(cx["condition"], fns):
                            cancelled.append(cx["id"])
                evaluated = True
            except (AssertionError, KeyError, TypeError):
                present, detail, involved, cancelled, evaluated = False, None, [], [], False
            strength = _strength(involved, shadbala)
            if present:
                for m in r.get("strength_modifiers", []):
                    if evaluate(m["if"], fns):
                        strength *= float(m["multiply"])
            results.append({**base, "present": present, "evaluated": evaluated, "effective": present and not cancelled,
                            "strength": round(strength, 4) if present else 0.0, "planets_involved": involved,
                            "cancelled_by": cancelled, "detail": detail})
    return sorted(results, key=lambda x: x["id"])


def _strength(planets: list[str], sb: dict | None) -> float:
    """Mean Shadbala ratio of the involved planets, capped at 1.5 and scaled to 0..1 (1.0 when unknown)."""
    ratios = [min(sb["planets"][p]["ratio"], 1.5) for p in planets if sb and p in sb["planets"]]
    return (sum(ratios) / len(ratios)) / 1.5 if ratios else 1.0
