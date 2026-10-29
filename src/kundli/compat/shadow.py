"""Shadow mode bookkeeping. For a shadowed endpoint the router calls both the provider and the engine, returns the provider's
answer and records ONLY a diff summary here. Privacy rules (plan): log the endpoint name, a keyed hash of the request (never
the request), field PATHS with their mismatch kind and numeric delta, counts and rates. No birth details, names, places,
coordinates or response values are ever written.

* `input_id`: HMAC-SHA256 of the canonical request JSON keyed by `KUNDLI_SHADOW_SALT` (a random per-process salt if unset, so ids
  are then only comparable within one process), truncated to 16 hex characters.
* `summarize_diff`: provider response (expected) vs engine response (actual) through `oracle.diff`, paths + kinds only.
* `ShadowLog`: append-only JSONL file; `summary()` aggregates per endpoint over a time window.
* `classify`: fnmatch patterns in `classifications.yaml` mark a field's difference as `convention`, `bug` or `provider_error`.
"""
import fnmatch
import hashlib
import hmac
import json
import os
import secrets
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..oracle.diff import diff

CLASSIFICATIONS = Path(__file__).with_name("classifications.yaml")
MAX_FIELDS = 50
_PROCESS_SALT = secrets.token_hex(16)


def _salt() -> bytes:
    return os.environ.get("KUNDLI_SHADOW_SALT", _PROCESS_SALT).encode()


def input_id(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hmac.new(_salt(), canonical.encode(), hashlib.sha256).hexdigest()[:16]


@lru_cache(maxsize=1)
def classifications() -> tuple[dict[str, Any], ...]:
    rows = yaml.safe_load(CLASSIFICATIONS.read_text(encoding="utf-8")) or []
    for r in rows:
        if r.get("class") not in ("convention", "bug", "provider_error") or not r.get("endpoint") or not r.get("path") or not r.get("note"):
            raise ValueError(f"malformed classification row {r!r}")
    return tuple(rows)


def classify(endpoint: str, path: str) -> str | None:
    for r in classifications():
        if fnmatch.fnmatch(endpoint, r["endpoint"]) and fnmatch.fnmatch(path, r["path"]):
            return str(r["class"])
    return None


def summarize_diff(endpoint: str, provider_body: Any, engine_body: Any) -> dict[str, Any]:
    res = diff(provider_body, engine_body)
    fields = [{"path": m.path, "kind": m.kind.value, "delta": None if m.delta is None else round(m.delta, 6),
               "class": classify(endpoint, m.path)} for m in res.mismatches]
    fields += [{"path": p, "kind": "missing", "delta": None, "class": classify(endpoint, p)} for p in res.missing]
    total = res.compared + len(res.missing)
    return {"compared": total, "mismatched": len(fields), "match_rate": res.match_rate, "fields": fields[:MAX_FIELDS],
            "fields_truncated": len(fields) > MAX_FIELDS}


def record(endpoint: str, payload: dict[str, Any], summary: dict[str, Any] | None, status: str, now: datetime | None = None) -> dict[str, Any]:
    """One log record: no request data, no response values."""
    return {"ts": (now or datetime.now(UTC)).replace(microsecond=0).isoformat(), "endpoint": endpoint, "input_id": input_id(payload),
            "status": status, **(summary or {})}


class ShadowLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, rec: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summary(records: list[dict[str, Any]], now: datetime | None = None, window_days: float | None = None) -> dict[str, dict[str, Any]]:
    """Per endpoint: requests, errors, requests with any diff, diff rate, field-level unclassified counts, first/last timestamp."""
    now = now or datetime.now(UTC)
    cutoff = None if window_days is None else now - timedelta(days=window_days)
    agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"requests": 0, "errors": 0, "with_diff": 0, "first": None, "last": None,
                                                           "unclassified_fields": 0, "bug_fields": 0, "convention_fields": 0})
    for r in records:
        ts = datetime.fromisoformat(r["ts"])
        if cutoff is not None and ts < cutoff:
            continue
        a = agg[r["endpoint"]]
        a["first"] = r["ts"] if a["first"] is None or r["ts"] < a["first"] else a["first"]
        a["last"] = r["ts"] if a["last"] is None or r["ts"] > a["last"] else a["last"]
        if r["status"] != "compared":
            a["errors"] += 1
            continue
        a["requests"] += 1
        if r["mismatched"]:
            a["with_diff"] += 1
        for f in r.get("fields", []):
            a["unclassified_fields" if f["class"] is None else "bug_fields" if f["class"] in ("bug", "provider_error") else "convention_fields"] += 1
    for a in agg.values():
        a["diff_rate"] = a["with_diff"] / a["requests"] if a["requests"] else None
    return dict(agg)


__all__ = ["ShadowLog", "classifications", "classify", "input_id", "record", "summarize_diff", "summary"]
