"""Content linter. Errors fail CI (and `freeze`); warnings are informational.

Errors: unparsable block files; key/lang not matching the file path; empty or very short text; a key outside the reachable
key space (orphan); banned claims (guaranteed outcomes, death/disease predictions, medical or financial instructions,
price/urgency language); a block in the lock whose file is missing, a draft, or whose hash differs from the lock.
With `required_langs`, every reachable key must have a block in each language that is reviewed/frozen and locked.
Disclaimer sentences that NEGATE a banned claim ("no outcome is guaranteed", "not a medical remedy") are allowed."""
import re
from dataclasses import dataclass

from . import keys, schema
from .store import ContentStore

MIN_CHARS = 20
NEGATION = re.compile(r"\b(no|not|never|nor|cannot|can't|without)\b|n't\b|नहीं|नही", re.IGNORECASE)  # no \b for Devanagari
DEVANAGARI = re.compile("[\u0900-\u097F]")
SENTENCE = re.compile(r"(?<=[.!?।])\s+")
# (label, pattern). Matched per sentence; a sentence with a negation before the match is treated as a disclaimer.
BANNED = [
    ("guaranteed outcome", re.compile(r"\bguarantee[sd]?\b|\b100\s*%\s*(sure|certain|effective|result)|गारंटी", re.IGNORECASE)),
    ("death or fatality prediction", re.compile(r"\b(will die|you will die|death|dies|dying|fatal|fatality)\b|मृत्यु", re.IGNORECASE)),
    ("disease prediction or medical claim", re.compile(
        r"\b((?-i:cancer)|diabetes|heart attack|stroke|tumou?r|disease will|cure[sd]?|heals?|surgery|diagnos\w+)\b|बीमारी होगी|कैंसर", re.IGNORECASE)),
    ("medical instruction", re.compile(r"\b(stop (taking|treatment|medication)|skip (treatment|medication)|instead of (medicine|treatment))\b", re.IGNORECASE)),
    ("financial instruction", re.compile(r"\b(invest in|buy (stocks?|shares|crypto)|lottery|gamble|take a loan|sell your)\b", re.IGNORECASE)),
    ("price or sales language", re.compile(r"(₹|\brs\.?\s*\d|\$\s*\d|\bprice\b|\bdiscount\b|\bcheap\b|\bonly \d+ (rupees|dollars))", re.IGNORECASE)),
    ("urgency or compulsion", re.compile(r"\b(must (wear|buy|do)|buy now|act now|immediately|urgent(ly)?|limited time|before it is too late)\b", re.IGNORECASE)),
    ("fear language", re.compile(r"\b(curse[sd]?|doomed|disaster will|ruin(ed)? your|terrible fate)\b", re.IGNORECASE)),
]


@dataclass(frozen=True)
class Issue:
    severity: str  # error | warning
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity.upper()} {self.where}: {self.message}"


def banned_claims(text: str) -> list[str]:
    """Labels of banned claims in `text`, ignoring sentences that negate the claim."""
    found: list[str] = []
    for sentence in SENTENCE.split(text):
        for label, pat in BANNED:
            m = pat.search(sentence)
            if not m or label in found:
                continue
            # English negates before the claim ("no outcome is guaranteed"); Hindi negates after it ("गारंटी नहीं है")
            scope = sentence if DEVANAGARI.search(m.group(0)) else sentence[: m.start() + len(m.group(0))]
            if not NEGATION.search(scope):
                found.append(label)
    return found


def lint(store: ContentStore, required_langs: tuple[str, ...] = ()) -> list[Issue]:
    issues: list[Issue] = []
    reachable = keys.all_keys()
    seen: dict[tuple[str, str], schema.Block] = {}
    root = store.blocks_dir
    for path in sorted(root.glob("*/*/*.md")):
        where = str(path.relative_to(root))
        try:
            b = schema.read(path)
        except Exception as e:  # noqa: BLE001 - report any parse failure as a lint error
            issues.append(Issue("error", where, f"unparsable block: {e}"))
            continue
        if path != schema.path_for(root, b.key, b.lang):
            issues.append(Issue("error", where, f"path does not match key/lang ({b.key}, {b.lang})"))
        seen[(b.key, b.lang)] = b
        if len(b.text.strip()) < MIN_CHARS:
            issues.append(Issue("error", where, "empty or too short"))
        if b.key not in reachable:
            issues.append(Issue("error", where, "key is not reachable from any computed fact (orphan)"))
        for label in banned_claims(b.text):
            issues.append(Issue("error", where, f"banned claim: {label}"))
        if b.status != "draft" and not b.reviewer:
            issues.append(Issue("error", where, f"status {b.status} requires a reviewer"))
        if b.status != "draft" and not b.sources:
            issues.append(Issue("warning", where, "no sources listed"))
    for lang, entries in store.lock()["blocks"].items():
        for key, h in entries.items():
            locked = seen.get((key, lang))
            where = f"lock:{lang}/{key}"
            if locked is None:
                issues.append(Issue("error", where, "locked block has no file"))
            elif locked.status == "draft":
                issues.append(Issue("error", where, "locked block is still a draft"))
            elif schema.block_hash(locked) != h:
                issues.append(Issue("error", where, "block was edited after it was frozen (hash differs from the lock)"))
    for lang in required_langs:
        locked = store.lock()["blocks"].get(lang, {})
        missing = sorted(reachable - set(locked))
        if missing:
            issues.append(Issue("error", f"coverage:{lang}", f"{len(missing)} reachable keys have no reviewed, locked block "
                                f"(first: {', '.join(missing[:3])})"))
    return issues


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.severity == "error"]


__all__ = ["BANNED", "Issue", "banned_claims", "errors", "lint"]
