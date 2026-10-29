"""Read-only content store. Serves a block only when (1) its file is `reviewed` or `frozen`, (2) `content.lock` lists its hash
and (3) the file's current hash equals the locked one. Drafts, unlocked and edited blocks are NEVER served; a missing key
gives a `content_missing` marker, never an LLM fallback. `version` is the lock's `content_version`, echoed in responses."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import schema

DEFAULT_DIR = Path(__file__).parent / "blocks"
DEFAULT_LOCK = Path(__file__).parent / "content.lock"
EMPTY_VERSION = "empty"


class ContentStore:
    def __init__(self, blocks_dir: Path = DEFAULT_DIR, lock_path: Path = DEFAULT_LOCK) -> None:
        self.blocks_dir, self.lock_path = Path(blocks_dir), Path(lock_path)
        self._lock: dict[str, Any] | None = None

    def lock(self) -> dict[str, Any]:
        if self._lock is None:
            self._lock = (json.loads(self.lock_path.read_text(encoding="utf-8")) if self.lock_path.exists()
                          else {"content_version": EMPTY_VERSION, "blocks": {}})
        return self._lock

    @property
    def version(self) -> str:
        return str(self.lock()["content_version"])

    def get(self, key: str, lang: str) -> schema.Block | None:
        want = self.lock()["blocks"].get(lang, {}).get(key)
        if want is None:
            return None
        path = schema.path_for(self.blocks_dir, key, lang)
        if not path.exists():
            return None
        b = schema.read(path)
        if b.status == "draft" or b.key != key or b.lang != lang or schema.block_hash(b) != want:
            return None
        return b

    def lookup(self, key: str, lang: str) -> dict[str, Any]:
        """Endpoint-facing result: the block, or a clear `content_missing` marker."""
        b = self.get(key, lang)
        if b is None:
            return {"key": key, "lang": lang, "status": "content_missing", "content_version": self.version}
        return {"key": key, "lang": lang, "status": "ok", "text": b.text, "sources": b.sources, "version": b.version,
                "content_version": self.version}


@lru_cache(maxsize=1)
def _default() -> ContentStore:
    return ContentStore()


_override: ContentStore | None = None


def default_store() -> ContentStore:
    return _override or _default()


def set_default_store(store: ContentStore | None) -> None:
    """Install (or with None remove) a store used by `lookup`; for tests and deployments with an external lock."""
    global _override
    _override = store


def lookup(key: str, lang: str = "en") -> dict[str, Any]:
    return default_store().lookup(key, lang)


def content_version() -> str:
    return default_store().version


__all__ = ["DEFAULT_DIR", "DEFAULT_LOCK", "EMPTY_VERSION", "ContentStore", "content_version", "default_store", "lookup",
           "set_default_store"]
