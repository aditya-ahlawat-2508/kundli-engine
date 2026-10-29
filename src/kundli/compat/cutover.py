"""Per-endpoint cutover. Mode per endpoint: `engine` (our answer, the default), `shadow` (provider's answer returned, ours
compared and logged) or `provider` (provider only). Modes come from the JSON file in `KUNDLI_CUTOVER_FILE`
({"<endpoint>": "<mode>", "*": "<default mode>"}); the file is re-read on every request so a flag flips without a restart.

`readiness` implements the plan's rule for moving an endpoint to the engine:
* T1 (and Data): diff rate under 1% over the last 14 days with at least MIN_REQUESTS compared requests spanning the window;
* T2: every remaining differing field is classified as a convention (none unclassified, none bug/provider_error);
* T3: only after content review (`content_reviewed=True`, i.e. the endpoint's content keys are reviewed and frozen);
* mixed tiers (e.g. T1/T2, T1/T3) must satisfy every part."""
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

MODES = ("engine", "shadow", "provider")
WINDOW_DAYS = 14
MIN_REQUESTS = 100
MAX_DIFF_RATE = 0.01


def load_flags(path: str | None = None) -> dict[str, str]:
    p = path or os.environ.get("KUNDLI_CUTOVER_FILE")
    if not p or not Path(p).exists():
        return {}
    flags = json.loads(Path(p).read_text(encoding="utf-8"))
    bad = {k: v for k, v in flags.items() if v not in MODES}
    if bad:
        raise ValueError(f"unknown cutover modes: {bad}")
    return dict(flags)


def mode_for(endpoint: str, path: str | None = None) -> str:
    flags = load_flags(path)
    return flags.get(endpoint, flags.get("*", "engine"))


def readiness(tier: str, stats: dict[str, Any] | None, content_reviewed: bool = False, now: datetime | None = None) -> dict[str, Any]:
    """Can an endpoint of `tier` with shadow `stats` (one entry of `shadow.summary`) switch to the engine?"""
    now = now or datetime.now(UTC)
    parts = {"Data": "T1"}.get(tier, tier).split("/")
    reasons: list[str] = []
    if stats is None or not stats["requests"]:
        return {"ready": False, "reasons": ["no shadow data yet"], "tier": tier}
    for part in parts:
        if part == "T1":
            first = datetime.fromisoformat(stats["first"])
            if now - first < timedelta(days=WINDOW_DAYS):
                reasons.append(f"shadow data spans less than {WINDOW_DAYS} days")
            if stats["requests"] < MIN_REQUESTS:
                reasons.append(f"only {stats['requests']} compared requests (need {MIN_REQUESTS})")
            if stats["diff_rate"] is None or stats["diff_rate"] >= MAX_DIFF_RATE:
                reasons.append(f"diff rate {stats['diff_rate']} is not under {MAX_DIFF_RATE:.0%}")
        elif part == "T2":
            if stats["unclassified_fields"]:
                reasons.append(f"{stats['unclassified_fields']} differing fields are not classified")
            if stats["bug_fields"]:
                reasons.append(f"{stats['bug_fields']} differing fields are classified as bug or provider_error")
        elif part == "T3":
            if not content_reviewed:
                reasons.append("content is not reviewed and frozen")
        else:
            reasons.append(f"unknown tier part {part!r}")
    return {"ready": not reasons, "reasons": reasons, "tier": tier}


__all__ = ["MAX_DIFF_RATE", "MIN_REQUESTS", "MODES", "WINDOW_DAYS", "load_flags", "mode_for", "readiness"]
