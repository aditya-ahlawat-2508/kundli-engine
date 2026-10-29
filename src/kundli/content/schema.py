"""Content block schema and file format.

A block is one file `blocks/<lang>/<topic>/<key>.md`: YAML front matter (key, lang, sources, status, reviewer, version,
hash) followed by the text. `status` moves draft -> reviewed -> frozen; only a human reviewer sets `reviewed`
(`freeze.review`), `freeze.freeze` records the hash in `content.lock`, and the store serves only blocks whose hash matches
the lock. Drafts are never served.
"""
import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

Lang = Literal["en", "hi", "hinglish"]
Status = Literal["draft", "reviewed", "frozen"]
LANGS: tuple[str, ...] = ("en", "hi", "hinglish")
SEPARATOR = "---"


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    lang: Lang
    text: str
    sources: list[str] = []
    status: Status = "draft"
    reviewer: str | None = None
    version: int = 1
    hash: str | None = None

    @field_validator("key")
    @classmethod
    def _key(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) < 2 or any(not p or not all(c.islower() or c.isdigit() or c == "_" for c in p) for p in parts):
            raise ValueError(f"bad content key {v!r}: lowercase dotted parts of [a-z0-9_]")
        return v

    @property
    def topic(self) -> str:
        return self.key.split(".")[0]

    @property
    def filename(self) -> str:
        return f"{self.key}.md"


def block_hash(b: Block) -> str:
    """SHA-256 of the canonical content (key, lang, text, sources, version): status/reviewer do not change it."""
    payload = json.dumps({"key": b.key, "lang": b.lang, "text": b.text.strip(), "sources": b.sources, "version": b.version},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def path_for(root: Path, key: str, lang: str) -> Path:
    return root / lang / key.split(".")[0] / f"{key}.md"


def dumps(b: Block) -> str:
    meta = b.model_dump(exclude={"text"})
    return f"{SEPARATOR}\n{yaml.safe_dump(meta, allow_unicode=True, sort_keys=True).strip()}\n{SEPARATOR}\n{b.text.strip()}\n"


def loads(raw: str) -> Block:
    if not raw.startswith(SEPARATOR + "\n"):
        raise ValueError("block file must start with a '---' front-matter line")
    head, sep, body = raw[len(SEPARATOR) + 1:].partition(f"\n{SEPARATOR}\n")
    if not sep:
        raise ValueError("block file has no closing '---' line")
    return Block(**yaml.safe_load(head), text=body.strip())


def read(path: Path) -> Block:
    return loads(path.read_text(encoding="utf-8"))


def write(root: Path, b: Block) -> Path:
    p = path_for(root, b.key, b.lang)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps(b), encoding="utf-8")
    return p


__all__ = ["LANGS", "Block", "Lang", "Status", "block_hash", "dumps", "loads", "path_for", "read", "write"]
