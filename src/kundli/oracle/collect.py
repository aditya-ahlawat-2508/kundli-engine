"""Collect oracle responses as test fixtures. The provider's terms of service decide how much may be collected and
kept: bulk collection is refused unless the caller states it has checked them (`tos_checked=True`)."""
import json
import os
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

Fetch = Callable[[str, dict[str, Any]], dict[str, Any]]
FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "oracle"
MAX_UNCHECKED = 5


def http_fetch_from_env() -> Fetch:
    """POST JSON to $KUNDLI_ORACLE_URL/<endpoint>. Auth header name/value come from $KUNDLI_ORACLE_AUTH_HEADER
    (default 'Authorization') and $KUNDLI_ORACLE_AUTH; nothing is hard-coded about any provider."""
    base = os.environ.get("KUNDLI_ORACLE_URL")
    if not base:
        raise RuntimeError("set KUNDLI_ORACLE_URL (and KUNDLI_ORACLE_AUTH) to collect from a provider")
    header = os.environ.get("KUNDLI_ORACLE_AUTH_HEADER", "Authorization")
    auth = os.environ.get("KUNDLI_ORACLE_AUTH", "")

    def fetch(endpoint: str, request: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(f"{base.rstrip('/')}/{endpoint}", data=json.dumps(request).encode(),
                                     headers={"Content-Type": "application/json", header: auth}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    return fetch


def collect(endpoint: str, cases: list[dict[str, Any]], fetch: Fetch, *, out_dir: Path | None = None,
            tos_checked: bool = False) -> list[Path]:
    """Save {'endpoint','case','response'} per case under tests/oracle/<endpoint>/<case id>.json."""
    if len(cases) > MAX_UNCHECKED and not tos_checked:
        raise PermissionError(f"refusing to collect {len(cases)} responses: check the provider's terms of service "
                              f"first, then pass tos_checked=True (limit without it: {MAX_UNCHECKED})")
    base = (out_dir or FIXTURES) / endpoint.replace("/", "__").replace(":", "")
    base.mkdir(parents=True, exist_ok=True)
    written = []
    for case in cases:
        f = base / f"{case['id']}.json"
        f.write_text(json.dumps({"endpoint": endpoint, "case": case, "response": fetch(endpoint, case)},
                                indent=1, sort_keys=True), encoding="utf-8")
        written.append(f)
    return written
