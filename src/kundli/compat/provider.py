"""The third-party provider the app uses today, behind a tiny interface. Only shadow mode and `provider` cutover mode ever
call it; it is configured from the environment and refuses to run unless the provider's terms of service were checked:

    KUNDLI_PROVIDER_URL        base URL (endpoint names are appended)
    KUNDLI_PROVIDER_KEY        credential (sent as a bearer token; never logged)
    KUNDLI_PROVIDER_TOS_CHECKED=1   explicit acknowledgement (plan: check the ToS before any collection or shadowing)
    KUNDLI_PROVIDER_TIMEOUT    seconds (default 10)

Mapping our request fields to the provider's schema is `map_request` (identity until the schemas arrive in compat/schemas/)."""
import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderClient(Protocol):
    def call(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class ProviderNotConfigured(RuntimeError):
    pass


def map_request(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Our request body -> the provider's request body. Identity until the provider's schemas are supplied."""
    return payload


@dataclass(frozen=True)
class HttpProviderClient:
    base_url: str
    key: str = field(repr=False)  # a credential: never shown in reprs, logs or tracebacks
    timeout: float = 10.0

    def call(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url.rstrip('/')}/{endpoint}", data=json.dumps(map_request(endpoint, payload)).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return dict(json.load(r))


def from_env(env: dict[str, str] | None = None) -> HttpProviderClient:
    e = env if env is not None else dict(os.environ)
    if not e.get("KUNDLI_PROVIDER_URL") or not e.get("KUNDLI_PROVIDER_KEY"):
        raise ProviderNotConfigured("set KUNDLI_PROVIDER_URL and KUNDLI_PROVIDER_KEY")
    if e.get("KUNDLI_PROVIDER_TOS_CHECKED") != "1":
        raise ProviderNotConfigured("check the provider's terms of service, then set KUNDLI_PROVIDER_TOS_CHECKED=1")
    return HttpProviderClient(e["KUNDLI_PROVIDER_URL"], e["KUNDLI_PROVIDER_KEY"], float(e.get("KUNDLI_PROVIDER_TIMEOUT", "10")))


_override: ProviderClient | None = None


def set_client(client: ProviderClient | None) -> None:
    """Install a client (tests, or a deployment that builds its own); None restores the environment-based default."""
    global _override
    _override = client


def client() -> ProviderClient:
    return _override or from_env()


__all__ = ["HttpProviderClient", "ProviderClient", "ProviderNotConfigured", "client", "from_env", "map_request", "set_client"]
