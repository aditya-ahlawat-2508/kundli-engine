# Open questions / unverified items

## Not verified (read this first)
- **No JHora / Parashara's Light cross-check was done.** None were available. `tests/golden/*.json` are engine-generated
  regression snapshots, not external references. Replace `expected` with exports (note tool + settings) to validate the
  "within 1 arcminute / 1 day / SAV exact / Shadbala within 2%" acceptance claims. Verified instead: raw `swisseph`
  equality, Lahiri 1956 epoch, published Saturn/Jupiter ingress dates, SAV = 337, dasha contiguity and 120-year sums.
- **Shadbala totals are untested against any reference.** Simplifications: Yuddha bala = 0; Abda/Masa lords by solar
  sankranti; Cheshta uses true heliocentric longitude; Moon/benefic Paksha not doubled.
- **The LLM path was never run against the real API** (tested with fake clients only).
- Timeline weights are heuristic and only roughly calibrated; treat scores as an inspectable heuristic, not evidence.

## Values flagged `# VERIFY` in code
Node dignities/friendships/aspects; Moon moolatrikona 3-30; combustion orbs; D5, D8, D11, D60 rules; Indu lagna counting;
Gulika/Mandi position; Choghadiya start table; shodhya-pinda multipliers; ekadhipatya shodhana; yoga cancellation lists
(Mangal, Kaal Sarpa, Pitru, Adhi threshold).

## Still needed for the full report (blocked on an authoritative source)
- **Ghat Chakra** table (inauspicious tithi/day/nakshatra/yog/karana/prahar by month), **Yunja**, **Rudraksha** rule:
  no verified table available; needs an astrologer-supplied source. Month is computed (`panchang.hindu_month`).
- Chara dasha antardasha order: the reference's antardasha dates are internally inconsistent, only its first column
  matches ours. Name number alphabet (Chaldean here) differs from the reference.
- One external reference only (the sample report). Add JHora exports before trusting the VERIFY items.

## Second-person review list (tables entered from memory, one chart checked)
Avakahada (varna/vashya/yoni/gana/nadi/name syllables/paya), Kaal Sarp type names, gem table (`GEMS`), functional-nature
precedence rule, Chara dasha co-lord and antardasha rules, manglik `intensity_percent` weights. Each needs a cited source
and a reviewer before its compat endpoint can be marked `done`.

## Not implemented
Ashtottari, Chara and Kalachakra dashas (no reliably recalled tables); Ashtakoota compatibility (`compat.py`); Tajika yogas,
year lord and tithi pravesha (only solar return + Muntha); East Indian chart; Bhava-dig bala and occupant terms of Bhava bala;
night Choghadiya; 28-nakshatra mode is only a helper (`in_abhijit`); Hinglish output exists only in the LLM path (the
rule-based reading supports en/hi).

## Panchang (V2 phase 12)
- No provider oracle yet: sunrise definition, Vara/hora conventions and festival dates are unverified against a provider.
- Night Choghadiya start and step rule (`panchang/choghadiya.py`), Rahu/Yama/Gulika part tables, Abhijit definition: from memory.
- **Not implemented, no sourced table:** Dur Muhurta, Varjyam, Amrit Kaal, Brahma Muhurta, Tamil year names (60-year cycle),
  month-specific Ekadashi names, Sankashti names, regional Tamil sunset-rule variants (our rule puts Tula sankranti 2025 on Oct 17 as Aippasi 1;
  some Tamil calendars give Oct 18).
- Festival rules are single-anchor: two-day tithi tie-breaks (Smarta/Vaishnava, Raksha Bandhan bhadra, Karwa Chauth moonrise
  windows) are not applied. Verify every rule against Drik Panchang for a sample year per region before cutover.
- `festival-by-date` semantics are guessed (calendar-month list); confirm from the provider's schema.

## Monthly yogas (V2 phase 13)
- Sarvartha/Amrit Siddhi tables, Ravi Yoga offsets and Dwi/Tripushkar tithi+weekday rules are from memory (`verify: true` in the YAML).
  Published almanacs also cancel Siddhi yogas on certain tithis and handle windows that cross a day boundary differently.
- Ghat Chakra and Yunja are still not implemented (no verified table).

## Dasha endpoints (V2 phase 14)
- Chara sub-period rule below maha is one rule applied recursively; schools differ (see Chara notes above). Route semantics of
  `sub_sub_chardasha` (no path params) and `sub_yogini_dasha/:dashaCycle/:dashaName` are guessed until the provider's schema arrives.
- Vimshottari beyond 120 years and Chara beyond the 12 maha periods return an empty stack (Chara does not repeat in this implementation).

## KP (V2 phase 15)
- Rahu/Ketu as significators (agent rule) is not implemented: they own no house here and only act through their star/occupancy.
- Which ayanamsa the provider's KP endpoints use is unknown (`kp_ayanamsa` convention); fingerprint once oracle data exists.
- Ruling planets and the 249 table's use in horary (number 1..249) are not implemented.

## Doshas and match making (V2 phase 16)
- All match tables (vashya, gana matrices; Rajju groups; Vedha pairs; Varna ranks) and rules (Dashakoota thresholds, cancellations) are from memory
  and need a cited source and a second reviewer. The yoni matrix passes internal checks only (symmetric, 7 enemy pairs).
- Rasi porutham is not implemented (accepted sign-count rule unconfirmed). Schools differ on Gana and Vashya orientation (boy row / girl column here).
- The provider's percentage formula and verdict wording are unknown (`percentage` is a convention).
- Pitra dosha has no agreed rule set; only indicator matches are reported. Kaal Sarp partial-case handling and the 12 type names remain `# VERIFY`.

## Varshaphal (V2 phase 17)
- Year lord (Varshesha), Patyayani dasha, tithi pravesha, Tajika yogas other than Ithasala/Ishrafa (Nakta, Yamaya, Kambool, Gairi-kambool, Khallasara, Radda, Duhphali-kuttha, Tambira, Kuttha) are not implemented.
- Harsha bala components 2-4, the Panchavargeeya relation fractions, the saham formulas and day/night reversal, the deeptamsa orbs and the Mudda dasha basis are from memory.
- Retrograde handling in Ithasala/Ishrafa (applying/separating reverses) is not applied. The saham adjustment rule (+30 degrees outside a prescribed arc) is not applied.
- The month-chart definition (every 30 degrees of solar advance) may differ from the provider's.

## Muhurta (V2 phase 18)
- Every activity ruleset is a generic template (weekday + nakshatra class + common vetoes). Activity-specific classical rules are NOT yet encoded:
  lagna rules (no lagna scoring at all), Panchaka, month-by-month restrictions, tithi preferences per activity, Chaturmas boundaries
  (approximated by amanta months Shravana-Ashwin for marriage only), Jupiter/Venus asta periods beyond simple orb combustion, Pushya exceptions
  and Guru/Ravi Pushya for gold, Dur Muhurta/Varjyam (no sourced table), nakshatra padas for marriage, Kuja/Ravi dosha on the day, moon-in-8th.
- Marriage and upanayana, the plan's two most rule-heavy activities, have only the rules listed above.
- Veto vs weight choices (e.g. Yamaganda/Gulika as vetoes) are conventions to be reviewed by an astrologer.
- The score threshold (60) is arbitrary; the provider's "good date" definition is unknown.

## Numerology and biorhythm (V2 phase 19)
- `moon_biorhythm` is not implemented: the provider's definition must be confirmed from its docs and responses first.
- The daily numerology number, favourable-number rules and the choice of radical + destiny for the `numero_fav_*` endpoints are conventions.
- Direction lordship and beeja mantras are from memory; Ketu has no accepted direction here. Rahu/Ketu friendships are not defined.
- Fast and report texts are T3 content (phase 21).

## Lal Kitab (V2 phase 20)
- Edition: the house layout defaults to `fixed_aries` (the classic 1952 volume, chosen as the latest edition). `# VERIFY`: confirm against a cited source; the plan requires one. Pakka ghar and debts still need that same source. The pakka ghar table, in particular Saturn (8 vs 10) and Jupiter's secondary houses, differs between sources.
- Not implemented: sleeping planets (soya hua graha), Teva types (Andha, Nabalig, Dharmi...), Masnui (artificial) planets, planet aspects, Lal Kitab dasha/varshaphal, the other classical debts, and any remedy text.
- Remedy text must be written or licensed (not copied) and human-reviewed in the content store before the endpoints can be `done`.

## Content layer (V2 phase 21)
- **No content is reviewed or frozen.** The 558 shipped blocks are unreviewed drafts, so every text endpoint returns `content_missing`. The plan's acceptance
  ("every reachable key combination resolves to a reviewed block") needs astrologer review of 718 keys per language and drafts for the topics without vocabulary:
  nakshatra reports (27), daily (243), numerology daily/fast (18), match (41), lalkitab remedies (108), dosha pitra (2). Hinglish is supported but not drafted.
- Languages to support at launch (English, Hindi, Hinglish) is the owner's decision.
- Tarabala class labels, Chandrabala houses and the "primary nakshatra at sunrise" choice are conventions from memory.
- The banned-claims lint is a safety net, not a substitute for review; extend it from reviewer feedback.

## Remedies (V2 phase 22)
- All selection rules are from memory and school-dependent; there is no ground truth, so the oracle is a loose reference only (plan). Needs an astrologer's review before any endpoint is `done`.
- Rudraksha: no authoritative selection rule (the plan's blocker); the mapping and the choice of candidate grahas are placeholders. Rahu/Ketu pujas are selected only through dosha rules.
- Remedy and puja text (`remedy.*`) is drafted only for gems, gem roles and Sade Sati (36 blocks per language, all unreviewed); puja and rudraksha text still needs drafting and review.

## Geo, rollout and operations (V2 phase 23)
- **Shadow mode has never run against the real provider** (no provider name, credentials, schemas or terms were supplied). The framework, privacy guarantees and the cutover
  rule are tested with fakes; `map_request` is the identity and the diff compares our engine-neutral bodies with whatever the provider returns, so field names will not line up until
  the schemas land in `compat/schemas/`. No endpoint can be `done`, and none has been cut over.
- Acceptance "shadow mode runs on real traffic; at least the T1 endpoints cut over" is therefore NOT met: it needs the user's provider, traffic and two weeks of shadow data.
- `compat/classifications.yaml` is empty; it is filled as differences are explained (bug / convention / provider error).
- Authentication, rate limiting and CORS for the public API are still not implemented (only the ops dashboard is token-protected).
- A paid geocoder is still needed at scale (the offline GeoNames index covers cities over 15,000 people); Swiss Ephemeris AGPL/commercial licence is still undecided.
