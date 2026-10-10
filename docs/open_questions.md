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

## Not implemented
Ashtottari, Chara and Kalachakra dashas (no reliably recalled tables); Ashtakoota compatibility (`compat.py`); Tajika yogas,
year lord and tithi pravesha (only solar return + Muntha); East Indian chart; Bhava-dig bala and occupant terms of Bhava bala;
night Choghadiya; 28-nakshatra mode is only a helper (`in_abhijit`); Hinglish output exists only in the LLM path (the
rule-based reading supports en/hi).
