"""Operations helpers (V2 phase 23): version/config identity, structured access logs WITHOUT request data, and the per-endpoint
shadow dashboard with the cutover readiness verdict.

Access logs record the route TEMPLATE (e.g. `/compat/sub_vdasha/{md}`), method, status and duration, never the query string,
request/response body, client address or path values. Health and version endpoints are public; the shadow dashboard needs
`KUNDLI_OPS_TOKEN` (disabled, 404, when unset)."""
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .compat import cutover, shadow
from .compat.registry import load
from .config import EngineConfig
from .content import keys
from .content.store import default_store

ACCESS_LOGGER = "kundli.access"
# registry endpoint name prefix -> content topic whose keys must all be reviewed and frozen before a T3 endpoint can cut over
ENDPOINT_TOPICS = {"general_house_report": "house_report", "general_rashi_report": "rashi_report",
                   "general_ascendant_report": "ascendant_report", "general_nakshatra_report": "nakshatra_report",
                   "daily_nakshatra": "daily", "numero_": "numerology", "match_": "match", "lalkitab_remedies": "lalkitab",
                   "puja_suggestion": "remedy", "basic_gem_suggestion": "remedy", "rudraksha_suggestion": "remedy",
                   "sadhesati_remedies": "remedy", "manglik": "dosha", "kalsarpa": "dosha", "sadhesati_current": "dosha",
                   "pitra_dosha": "dosha"}


def warm_up() -> None:
    """Pay the one-time costs at server start instead of on the first request: the Saturn ingress table (~1 s) and the
    yoga rule files."""
    from .transits import _saturn_table
    from .yogas.engine import load_rules

    cfg = EngineConfig()
    _saturn_table(cfg.ayanamsa, cfg.ephemeris, cfg.ephemeris_path)
    load_rules()


def config_hash() -> str:
    """SHA-256 of the default EngineConfig: identifies the default conventions of this build."""
    return hashlib.sha256(json.dumps(EngineConfig().model_dump(), sort_keys=True).encode()).hexdigest()


def version_info() -> dict[str, Any]:
    import swisseph as swe

    return {"engine_version": __version__, "swisseph_version": swe.version, "config_hash": config_hash(),
            "content_version": default_store().version}


def access_record(route: str, method: str, status: int, duration_ms: float) -> dict[str, Any]:
    return {"event": "request", "route": route, "method": method, "status": status, "duration_ms": round(duration_ms, 1)}


def log_access(route: str, method: str, status: int, duration_ms: float) -> None:
    logging.getLogger(ACCESS_LOGGER).info(json.dumps(access_record(route, method, status, duration_ms), sort_keys=True))


def configure_logging(level: int = logging.INFO) -> None:
    """One JSON line per request on stdout; call once at server start."""
    log = logging.getLogger(ACCESS_LOGGER)
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(h)
    log.setLevel(level)
    log.propagate = False


def content_reviewed(endpoint: str) -> bool:
    """True when every reachable content key of the endpoint's topic is reviewed, frozen and locked (default language)."""
    topic = next((t for prefix, t in ENDPOINT_TOPICS.items() if endpoint.startswith(prefix)), None)
    if topic is None:
        return False
    locked = default_store().lock()["blocks"].get("en", {})
    return all(k in locked for k in keys.reachable()[topic])


def shadow_report(now: datetime | None = None, window_days: float = cutover.WINDOW_DAYS) -> dict[str, Any]:
    """Per endpoint: shadow stats over the window and whether it may cut over, plus the current mode flags."""
    now = now or datetime.now(UTC)
    path = os.environ.get("KUNDLI_SHADOW_LOG")
    stats = shadow.summary(shadow.ShadowLog(Path(path)).records() if path else [], now, window_days)
    tiers = {e.name: e.tier for e in load()}
    rows = {name: {"tier": tiers.get(name), "mode": cutover.mode_for(name), **st,
                   "readiness": cutover.readiness(tiers.get(name, "T1"), st, content_reviewed(name), now)}
            for name, st in sorted(stats.items())}
    return {"window_days": window_days, "endpoints": rows, "log_configured": bool(path)}


__all__ = [
    "ACCESS_LOGGER",
    "access_record",
    "config_hash",
    "configure_logging",
    "content_reviewed",
    "log_access",
    "shadow_report",
    "version_info",
    "warm_up",
]
