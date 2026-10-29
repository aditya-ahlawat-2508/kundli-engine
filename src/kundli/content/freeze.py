"""Review and freeze. `review` is the HUMAN step that moves a draft to `reviewed` (names the reviewer); `freeze` hashes all
`reviewed`/`frozen` blocks into `content.lock` (after the linter passes) and marks them `frozen`. The lock is deterministic:
sorted keys, no timestamps; `content_version` = SHA-256 of the sorted (lang, key, hash) triples."""
import hashlib
import json
from pathlib import Path
from typing import Any

from . import schema
from .lint import Issue, errors, lint
from .store import ContentStore


def review(root: Path, key: str, lang: str, reviewer: str) -> schema.Block:
    """Mark a draft as reviewed by `reviewer` (a person). Never called by the engine or the API."""
    if not reviewer.strip():
        raise ValueError("a reviewer name is required")
    p = schema.path_for(root, key, lang)
    b = schema.read(p)
    b = b.model_copy(update={"status": "reviewed", "reviewer": reviewer.strip()})
    schema.write(root, b)
    return b


def freeze(root: Path, lock_path: Path) -> tuple[dict, list[Issue]]:
    """Write `lock_path` from the reviewed/frozen blocks under `root`. Returns (lock, issues); nothing is written when the
    linter reports errors (other than for the lock being rebuilt, which it is allowed to repair)."""
    entries: dict[str, dict[str, str]] = {}
    blocks: list[schema.Block] = []
    for path in sorted(root.glob("*/*/*.md")):
        b = schema.read(path)
        if b.status in ("reviewed", "frozen"):
            blocks.append(b)
            entries.setdefault(b.lang, {})[b.key] = schema.block_hash(b)
    ordered = {lang: dict(sorted(es.items())) for lang, es in sorted(entries.items())}
    triples = sorted((lang, k, h) for lang, es in ordered.items() for k, h in es.items())
    candidate: dict[str, Any] = {"blocks": ordered, "content_version": hashlib.sha256(
        json.dumps(triples, separators=(",", ":")).encode()).hexdigest()}
    tmp = lock_path.with_suffix(".lock.tmp")
    tmp.write_text(json.dumps(candidate, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    issues = lint(ContentStore(root, tmp))
    bad = errors(issues)
    if bad:
        tmp.unlink()
        return candidate, issues
    tmp.replace(lock_path)
    for b in blocks:
        if b.status != "frozen" or b.hash != entries[b.lang][b.key]:
            schema.write(root, b.model_copy(update={"status": "frozen", "hash": entries[b.lang][b.key]}))
    return candidate, issues


__all__ = ["freeze", "review"]
