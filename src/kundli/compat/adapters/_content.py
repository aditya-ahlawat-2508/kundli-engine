"""Shared helpers: attach content-store blocks to endpoint bodies. Text is a lookup by key, never generated; a missing block
gives the store's `content_missing` marker."""
from typing import Any

from ...content import keys, lookup
from ...models import Kundli


def lang_of(k: Kundli) -> str:
    return str(k.header["config"].get("language", "en"))


def block(k: Kundli, key: str) -> dict[str, Any]:
    return lookup(key, lang_of(k))


def blocks(k: Kundli, **named: str) -> dict[str, dict[str, Any]]:
    return {name: block(k, key) for name, key in named.items()}


__all__ = ["block", "blocks", "keys", "lang_of"]
