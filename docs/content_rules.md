# Content rules (V2 phase 21)

Applies to every block under `src/kundli/content/blocks/` and to the vocabulary in `scripts/content_data.py`.

## Provenance
- All text is **original**. Never copy or paraphrase closely from the astrology API provider's responses, from another vendor's reports,
  or from copyrighted books. Classical texts may be cited in `sources`, not reproduced.
- Drafts may be produced offline by an LLM (`kundli.content.draft`) or by templates (`scripts/draft_content.py`). A draft has
  `status: draft`, is **never served**, and needs a named human reviewer before it can be frozen.
- Only `kundli content review` (a person) moves a block to `reviewed`; only `kundli content freeze` locks it. Editing a block after
  freezing changes its hash, so the store stops serving it until it is reviewed and frozen again.

## Tone
- Describe **tendencies**, not certainties: "tends to", "traditionally read as", "may". Balanced, non-fatalistic, practical.
- Frame interpretation as **traditional Jyotish**, not as science or advice.
- Plain language; short sentences; no jargon without a one-line explanation. Every block stands on its own (no "see above").

## Banned (the linter fails these)
- Guaranteed outcomes ("will definitely", "guaranteed"). A sentence that **negates** the word is allowed ("no outcome is guaranteed").
- Predictions of death, fatal illness or specific diseases; any medical claim or instruction (including "stop treatment").
- Financial instructions (invest, lottery, loans) and legal instructions.
- Price, discount, sales or urgency language ("must wear", "buy now", "immediately").
- Fear language (curses, doom, "ruin").

## Remedies (gems, puja, rudraksha, mantras, Lal Kitab)
- Always labelled **traditional belief / cultural practice**; every response carries a `disclaimer`.
- No price, no "must", no urgency, never a substitute for medical, legal or financial advice.

## Languages
- `en` and `hi` are drafted from the same vocabulary; `hinglish` is supported by the schema and store but not drafted yet.
- Hindi uses Devanagari; astrological terms use the usual Hindi names (शनि, मांगलिक, साढ़ेसाती).

## Keys
See `kundli.content.keys` (`reachable()` lists every key the engine can ask for). Key format: lowercase dotted parts of `[a-z0-9_]`.
