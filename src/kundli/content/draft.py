"""OFFLINE drafting tool: asks an LLM to draft content blocks from computed-fact descriptions (and optional classical-text
excerpts you supply). It is NEVER imported by the API, the engine or the compat layer (enforced by a test); run it by hand:

    python -m kundli.content.draft --topic house_report --lang en --limit 10 [--excerpts excerpts.json] [--model ...]

Every block it writes is `status: draft` with a `sources` entry naming the model, and is never served until a human reviews it
and `freeze` locks it (docs/content_rules.md)."""
import argparse
import json
import sys
from pathlib import Path
from typing import Protocol

from . import keys, schema
from .store import DEFAULT_DIR

DEFAULT_MODEL = "claude-sonnet-5-5"
LANG_NAMES = {"en": "English", "hi": "Hindi (Devanagari)", "hinglish": "Hinglish (Hindi in Roman script)"}
SYSTEM = """You draft short astrology report paragraphs for a Jyotish (Vedic astrology) product.
Rules: write original text; describe tendencies, never certainties; frame everything as traditional interpretation;
no medical, legal or financial claims or instructions; no death or disease predictions; no fear language; no price,
sales or urgency language; remedies are traditional belief and never guaranteed. 60-120 words, plain language, one paragraph.
Return only the paragraph text."""


class LLMClient(Protocol):
    def complete(self, system: str, user: str, temperature: float = 0.0) -> str: ...


def describe(key: str) -> str:
    """A plain-language description of the computed fact behind `key` (what the paragraph must explain)."""
    p = key.split(".")
    ordinal = lambda n: f"{n}{'th' if 10 <= int(n) % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(int(n) % 10, 'th')}"
    match p:
        case ["house_report", planet, house]:
            return f"{planet.title()} is placed in the {ordinal(house)} house of the birth chart."
        case ["rashi_report", planet, sign]:
            return f"{planet.title()} is placed in the sign {sign.title()} in the birth chart."
        case ["ascendant_report", sign]:
            return f"The ascendant (lagna) is {sign.title()}."
        case ["nakshatra_report", nak]:
            return f"The Moon is in the nakshatra {nak.replace('_', ' ').title()} at birth."
        case ["daily", "tara", tara, "nakshatra", nak]:
            return (f"Today's Moon is in {nak.replace('_', ' ').title()}, which is the {tara.replace('_', ' ')} tara "
                    "counted from the person's birth nakshatra (Tarabala).")
        case ["numerology", kind, n]:
            return f"The person's {kind} number is {n}."
        case ["lalkitab", "remedy", planet, house]:
            return f"In the Lal Kitab chart {planet.title()} stands in house {house}."
    return key.replace(".", " ").replace("_", " ")


def build_user(key: str, lang: str, excerpts: list[str]) -> str:
    parts = [f"Language: {LANG_NAMES[lang]}", f"Fact: {describe(key)}"]
    if excerpts:
        parts.append("Classical-text excerpts to ground the paragraph (summarise in your own words, do not copy):\n- "
                     + "\n- ".join(excerpts))
    return "\n".join(parts)


def draft_blocks(keys_: list[str], lang: str, client: LLMClient, model: str, root: Path = DEFAULT_DIR,
                 excerpts: dict[str, list[str]] | None = None, overwrite: bool = False) -> list[schema.Block]:
    out: list[schema.Block] = []
    for key in keys_:
        path = schema.path_for(root, key, lang)
        if path.exists() and not overwrite:
            continue
        ex = (excerpts or {}).get(key, [])
        text = client.complete(SYSTEM, build_user(key, lang, ex)).strip()
        b = schema.Block(key=key, lang=lang, text=text, status="draft",  # type: ignore[arg-type]
                         sources=[f"llm-draft:{model}", *[f"excerpt:{i}" for i in range(len(ex))]])
        schema.write(root, b)
        out.append(b)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else "")
    ap.add_argument("--topic", required=True, choices=sorted(keys.reachable()))
    ap.add_argument("--lang", default="en", choices=schema.LANGS)
    ap.add_argument("--limit", type=int, default=10, help="draft at most this many missing blocks")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--excerpts", type=Path, help='JSON {"<key>": ["excerpt", ...]}')
    ap.add_argument("--out", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args(argv)
    from ..predict.llm import AnthropicClient  # the project's single Anthropic wrapper (optional dependency)

    todo = [k for k in keys.reachable()[a.topic] if a.overwrite or not schema.path_for(a.out, k, a.lang).exists()][: a.limit]
    excerpts = json.loads(a.excerpts.read_text(encoding="utf-8")) if a.excerpts else None
    written = draft_blocks(todo, a.lang, AnthropicClient(model=a.model, max_tokens=600), a.model, a.out, excerpts, a.overwrite)
    print(f"drafted {len(written)} block(s) as status=draft under {a.out} (never served until reviewed and frozen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
