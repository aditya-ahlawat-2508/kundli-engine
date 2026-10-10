"""Post-validation of answers against the facts they cite."""
import re
from typing import Any

from .facts import Fact

CITE = re.compile(r"\[?\bF\d{3}\b\]?")
NUM = re.compile(r"\d+(?:\.\d+)?")
SMALL_OK = set(range(13))  # house / sign counts


def _numbers(s: str) -> set[str]:
    return set(NUM.findall(CITE.sub(" ", s)))


def allowed_numbers(facts: list[Fact]) -> set[str]:
    out: set[str] = set()
    for f in facts:
        out |= _numbers(f.text)
        out |= {str(v) for v in f.data.values() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        for v in f.data.values():
            if isinstance(v, str):
                out |= _numbers(v)
    return out


def validate(resp: dict[str, Any], facts: list[Fact]) -> list[str]:
    """Return a list of problems (empty = valid): unknown fact ids, uncited claims, numbers not in facts."""
    ids = {f.id for f in facts}
    allowed = allowed_numbers(facts)
    probs: list[str] = []
    claims = resp.get("claims")
    if not isinstance(claims, list):
        return ["claims must be a list"]
    for i, c in enumerate(claims):
        fid = c.get("fact_ids") if isinstance(c, dict) else None
        if not fid or not isinstance(fid, list):
            probs.append(f"claim {i} has no fact_ids")
            continue
        for x in fid:
            if x not in ids:
                probs.append(f"claim {i} cites unknown fact {x}")
        cited_numbers = set()
        for f in facts:
            if f.id in fid:
                cited_numbers |= _numbers(f.text) | {str(v) for v in f.data.values() if isinstance(v, (int, float))}
        for n in _numbers(str(c.get("text", ""))):
            if n not in cited_numbers and not (n.isdigit() and int(n) in SMALL_OK):
                probs.append(f"claim {i} has number {n} not in its cited facts")
    for n in _numbers(str(resp.get("summary", ""))):
        if n not in allowed and not (n.isdigit() and int(n) in SMALL_OK):
            probs.append(f"summary has number {n} not in facts")
    if resp.get("confidence") not in ("low", "medium", "high"):
        probs.append("confidence must be low|medium|high")
    return probs
