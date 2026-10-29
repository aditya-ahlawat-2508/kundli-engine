"""FastAPI routes generated from the endpoint registry. Built endpoints return the engine-neutral body inside an
envelope with `conventions_used`; the rest return 501 naming their registry status and phase."""
import os
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .. import __version__
from ..chart import generate, to_dict
from ..config import EngineConfig
from ..content import content_version
from ..errors import AmbiguousLocalTime, AmbiguousPlace, KundliError, NonexistentLocalTime, PlaceNotFound
from . import cutover, provider, shadow
from .adapters.engine_neutral import ADAPTERS
from .adapters.geo import SIMPLE_ADAPTERS
from .adapters.match import MATCH_ADAPTERS
from .normalize import BirthRequest, MatchRequest, to_inputs, to_match_inputs
from .registry import Endpoint, load
from .shadow import ShadowLog

ENGINE_LOCK = threading.RLock()  # swisseph keeps process-global state (sidereal mode, ephemeris path)
router = APIRouter(prefix="/compat", tags=["compat"])


def conventions_used(cfg: EngineConfig) -> dict[str, Any]:
    import swisseph as swe

    config = cfg.model_dump()
    config["content_version"] = config["content_version"] or content_version()  # hash of the frozen content store
    return {"engine_version": __version__, "swisseph_version": swe.version, "config": config,
            "content_version": content_version(), "response_shape": "engine_neutral"}


def _error(code: int, error: str, **extra: Any) -> JSONResponse:
    return JSONResponse({"error": error, **extra}, status_code=code)


def _adapter_for(e: Endpoint):  # type: ignore[no-untyped-def]
    return ADAPTERS.get(e.path)


def _concrete(e: Endpoint, params: dict[str, Any]) -> str:
    """The endpoint name with `:param` segments replaced by the request's path values (what the provider is called with)."""
    return "/".join(str(params.get(p[1:], p)) if p.startswith(":") else p for p in e.name.split("/"))


def _make_built(e: Endpoint, adapter):  # type: ignore[no-untyped-def]
    def handler(req: BirthRequest, request: Request) -> JSONResponse:
        def run() -> tuple[EngineConfig, Any]:
            birth, cfg = to_inputs(req)
            with ENGINE_LOCK:
                k = generate(birth, cfg)
                return cfg, adapter(k, req, dict(request.path_params))
        return _respond(e, run, req.model_dump(exclude_none=True), dict(request.path_params))
    return handler


def _make_match(e: Endpoint, adapter):  # type: ignore[no-untyped-def]
    def handler(req: MatchRequest, request: Request) -> JSONResponse:
        def run() -> tuple[EngineConfig, Any]:
            boy, girl, cfg = to_match_inputs(req)
            with ENGINE_LOCK:
                return cfg, adapter(generate(boy, cfg), generate(girl, cfg), dict(request.path_params))
        return _respond(e, run, req.model_dump(exclude_none=True), dict(request.path_params))
    return handler


def _make_simple(e: Endpoint, model, fn):  # type: ignore[no-untyped-def]
    def handler(req: model, request: Request) -> JSONResponse:  # type: ignore[valid-type]
        def run() -> tuple[EngineConfig, Any]:
            return EngineConfig(), fn(req)
        return _respond(e, run, req.model_dump(exclude_none=True), dict(request.path_params))  # type: ignore[attr-defined]
    return handler


def _engine_response(e: Endpoint, run) -> JSONResponse:  # type: ignore[no-untyped-def]
    """Run an endpoint body and map engine errors to HTTP responses."""
    try:
        cfg, body = run()
        return JSONResponse({"endpoint": e.name, "conventions_used": conventions_used(cfg),
                             "data": _jsonable(body)})
    except AmbiguousPlace as ex:
        return _error(409, "ambiguous_place", candidates=[{"index": i, **p.model_dump()}
                                                          for i, p in enumerate(ex.candidates)])
    except (AmbiguousLocalTime, NonexistentLocalTime) as ex:
        return _error(409, "local_time", detail=str(ex))
    except PlaceNotFound:
        return _error(404, "place_not_found")
    except (KundliError, ValueError, ValidationError) as ex:
        return _error(422, "invalid_request", detail=str(ex))


def _shadow_log(e: Endpoint, payload: dict[str, Any], summary: dict[str, Any] | None, status: str) -> None:
    path = os.environ.get("KUNDLI_SHADOW_LOG")
    if path:  # only a keyed hash of the request and field paths are written (compat/shadow.py)
        ShadowLog(Path(path)).append(shadow.record(e.name, payload, summary, status))


def _respond(e: Endpoint, run, payload: dict[str, Any], params: dict[str, Any]) -> JSONResponse:  # type: ignore[no-untyped-def]
    """Dispatch on the endpoint's cutover mode: engine (default), shadow (provider answers, engine compared) or provider."""
    mode = cutover.mode_for(e.name)
    if mode == "engine":
        return _engine_response(e, run)
    try:
        theirs = provider.client().call(_concrete(e, params), payload)
    except Exception as ex:  # noqa: BLE001 - any provider failure must never break the app
        _shadow_log(e, payload, None, f"provider_error:{type(ex).__name__}")
        if mode == "provider":
            return _error(503, "provider_unavailable")
        return _engine_response(e, run)  # shadow: the provider is down, serve our own answer
    if mode == "provider":
        return JSONResponse(theirs)
    try:  # shadow: record a diff summary only, return the provider's answer
        _, body = run()
        _shadow_log(e, payload, shadow.summarize_diff(e.name, theirs, _jsonable(body)), "compared")
    except Exception as ex:  # noqa: BLE001
        _shadow_log(e, payload, None, f"engine_error:{type(ex).__name__}")
    return JSONResponse(theirs)


def _jsonable(x: Any) -> Any:
    """Round through the engine's serialiser so floats follow the single rounding policy."""
    import json

    from ..chart import _round

    return _round(json.loads(json.dumps(x, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o))),
                  "", 1)


def _make_stub(e: Endpoint):  # type: ignore[no-untyped-def]
    def handler() -> JSONResponse:
        return _error(501, "not_implemented", endpoint=e.name, status=e.status, phase=e.phase, note=e.note)
    return handler


for _e in load():
    _ad = _adapter_for(_e)
    if _e.path in SIMPLE_ADAPTERS:
        _built = _make_simple(_e, *SIMPLE_ADAPTERS[_e.path])
    elif _e.path in MATCH_ADAPTERS:
        _built = _make_match(_e, MATCH_ADAPTERS[_e.path])
    else:
        _built = _make_built(_e, _ad) if _ad else _make_stub(_e)
    router.add_api_route("/" + _e.path, _built, methods=["POST"],
                         name=_e.name, summary=f"{_e.group}: {_e.name} [{_e.status}]")
__all__ = ["ENGINE_LOCK", "conventions_used", "router", "to_dict"]
