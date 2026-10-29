# Gap analysis: provider endpoints vs this engine

Generated from `src/kundli/compat/endpoints.yaml` (`kundli oracle gap`); do not edit by hand.

**131 endpoints, 20 groups.** exists: 67, partial: 62, missing: 2, done: 0.

`exists` = the engine computes it (response shape still engine-neutral); `partial` = some of it; `missing` = not built; `done` = oracle-verified and schema-matched (none yet).

| Group | Tier | Phase | exists | partial | missing |
|---|---|---|---|---|---|
| Basic Astro Details (10) | T1/T2 | V1+13 | 5 | 4 | 1 |
| Life Reports (4) | T3 | 21 | 0 | 4 | 0 |
| Horoscope Dosha (6) | T2 | 16 | 5 | 1 | 0 |
| Monthly Muhurta (18) | T2 | 18 | 0 | 18 | 0 |
| Lalkitab (5) | T2 | 20 | 0 | 5 | 0 |
| Suggestions and Remedies (4) | T2 | 22 | 0 | 4 | 0 |
| Daily Nakshatra Predictions (4) | T1/T3 | 21 | 0 | 4 | 0 |
| Varshaphal (10) | T1/T2 | 17 | 5 | 5 | 0 |
| Geo Details (2) | Data | 23 | 2 | 0 | 0 |
| Monthly Panchang Yoga (7) | T2 | 13 | 7 | 0 | 0 |
| Krishnamurti Paddhati (5) | T1/T2 | 15 | 5 | 0 | 0 |
| Biorhythm (2) | T1 | 19 | 1 | 0 | 1 |
| Horoscope Charts (2) | T1 | V1+11 | 2 | 0 | 0 |
| Ashtakvarga (2) | T2 | V1 | 2 | 0 | 0 |
| Numerology (8) | T2 | 19 | 3 | 5 | 0 |
| Panchang (15) | T1 | 12 | 15 | 0 | 0 |
| Match Making (11) | T2 | 16 | 3 | 8 | 0 |
| Vimshottari Dasha (8) | T1 | 14 | 8 | 0 | 0 |
| Char Dasha (4) | T2 | 14 | 0 | 4 | 0 |
| Yogini Dasha (4) | T1 | 14 | 4 | 0 | 0 |

## Basic Astro Details

Tier T1/T2; module: chart.generate, avakahada, friendship, functional, strength/; phase V1+13.

| Endpoint | Status | Note |
|---|---|---|
| `birth_details` | exists | chart.generate header/birth |
| `astro_details` | partial | lookups.astro_details; ghat_chakra and yunja missing (no verified table) |
| `planets` | exists | Kundli.planets |
| `planets/extended` | partial | outer planets via include_outer_planets only |
| `bhav_madhya` | exists | houses.madhyas/starts |
| `ghat_chakra` | missing | blocked: no authoritative table |
| `ayanamsha` | exists | header.ayanamsa_degrees |
| `planet_nature` | exists | friendship + functional |
| `bhavabala` | partial | simplified (no dig/occupant terms) |
| `shadbala` | partial | simplified; unverified vs reference |

## Life Reports

Tier T3; module: content/, panchang/tarabala; phase 21.

| Endpoint | Status | Note |
|---|---|---|
| `general_house_report/:planet_name` | partial | planet's whole-sign house -> content key house_report.<planet>.<house>; blocks are unreviewed drafts, so content_missing until reviewed + frozen |
| `general_rashi_report/:planet_name` | partial | planet's sign -> content key rashi_report.<planet>.<sign>; text pending review |
| `general_ascendant_report` | partial | lagna sign -> content key ascendant_report.<sign>; text pending review |
| `general_nakshatra_report` | partial | Moon nakshatra -> content key nakshatra_report.<nakshatra>; no vocabulary drafted yet |

## Horoscope Dosha

Tier T2; module: doshas, yogas/rules/doshas.yaml, transits; phase 16.

| Endpoint | Status | Note |
|---|---|---|
| `simple_manglik` | exists | Mars in 1/2/4/7/8/12 from lagna only |
| `manglik` | exists | references per config manglik_rules; cancellations standard_v1; intensity is our heuristic |
| `kalsarpa_details` | exists | full vs partial per config kalsarpa_variant; 12 type names # VERIFY |
| `sadhesati_current_status` | exists | phase at explicit as_of + containing period |
| `sadhesati_life_details` | exists | all Sade Sati/Dhaiya periods and phase-changing ingresses, second-level dates |
| `pitra_dosha_report` | partial | indicator rules only; school-dependent; text arrives with content store |

## Monthly Muhurta

Tier T2; module: muhurta/; phase 18.

| Endpoint | Status | Note |
|---|---|---|
| `griha_pravesh` | partial | muhurta.scan with muhurta/rulesets/griha_pravesh.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `bhumi_pujan` | partial | muhurta.scan with muhurta/rulesets/bhumi_pujan.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `property_purchase` | partial | muhurta.scan with muhurta/rulesets/property_purchase.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `vehicle_purchase` | partial | muhurta.scan with muhurta/rulesets/vehicle_purchase.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `gold_purchase` | partial | muhurta.scan with muhurta/rulesets/gold_purchase.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `loan_take` | partial | muhurta.scan with muhurta/rulesets/loan_take.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `loan_give` | partial | muhurta.scan with muhurta/rulesets/loan_give.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `account_opening` | partial | muhurta.scan with muhurta/rulesets/account_opening.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `business_start` | partial | muhurta.scan with muhurta/rulesets/business_start.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `job_joining` | partial | muhurta.scan with muhurta/rulesets/job_joining.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `agreement_signing` | partial | muhurta.scan with muhurta/rulesets/agreement_signing.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `travel` | partial | muhurta.scan with muhurta/rulesets/travel.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `mundan` | partial | muhurta.scan with muhurta/rulesets/mundan.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `namkaran` | partial | muhurta.scan with muhurta/rulesets/namkaran.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `annaprashan` | partial | muhurta.scan with muhurta/rulesets/annaprashan.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `vidyarambh` | partial | muhurta.scan with muhurta/rulesets/vidyarambh.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `upanayana` | partial | muhurta.scan with muhurta/rulesets/upanayana.yaml (v1, generic principles from memory, # VERIFY); explainable windows |
| `marriage` | partial | muhurta.scan with muhurta/rulesets/marriage.yaml (v1, generic principles from memory, # VERIFY); explainable windows |

## Lalkitab

Tier T2; module: lalkitab/; phase 20.

| Endpoint | Status | Note |
|---|---|---|
| `lalkitab_horoscope` | partial | chart layout per config lalkitab_edition (lagna_houses | fixed_aries); edition choice # VERIFY |
| `lalkitab_debts` | partial | 3 debt rules encoded (pitri, matri, stri); other classical debts not implemented |
| `lalkitab_remedies/:planet_name` | partial | selection facts + content-store key only; remedy text arrives in phase 21 |
| `lalkitab_houses` | partial | occupants, karakas from the pakka ghar table (# VERIFY) |
| `lalkitab_planets` | partial | house, pakka ghar (# VERIFY, low confidence), exaltation/debilitation houses (derived) |

## Suggestions and Remedies

Tier T2; module: remedies/, content/; phase 22.

| Endpoint | Status | Note |
|---|---|---|
| `puja_suggestion` | partial | rules in remedies/rules.yaml (weak benefic, afflicted malefic, dusthana lord weak, dosha pujas, Sade Sati when as_of given; # VERIFY); text via content keys remedy.puja.* |
| `basic_gem_suggestion` | partial | gems of the 1st/5th/9th lords + care flags (functional malefic, debilitated, combust, 6/8/12 lord); text via remedy.gem.* |
| `rudraksha_suggestion` | partial | mukhi linked to the gem-candidate grahas; the plan's blocked rule is unconfirmed (# VERIFY) |
| `sadhesati_remedies` | partial | phase at as_of + Saturn facts; text via remedy.sadhesati.<phase> |

## Daily Nakshatra Predictions

Tier T1/T3; module: content/, panchang/tarabala; phase 21.

| Endpoint | Status | Note |
|---|---|---|
| `daily_nakshatra_prediction` | partial | Tarabala (nine taras from the birth nakshatra) + Chandrabala at sunrise; key daily.tara.<tara>.nakshatra.<nak>; no daily text drafted yet |
| `daily_nakshatra_prediction/next` | partial | same, date + 1 |
| `daily_nakshatra_prediction/previous` | partial | same, date - 1 |
| `daily_nakshatra_consolidated` | partial | every nakshatra segment of the Vedic day with its tara and content block |

## Varshaphal

Tier T1/T2; module: varshaphal/; phase 17.

| Endpoint | Status | Note |
|---|---|---|
| `varshaphal_year_chart` | exists | chart at the solar return (config solar_return_zodiac), configured sidereal zodiac |
| `varshaphal_month_chart` | exists | month n = Sun advanced (n-1)*30 deg from natal; needs year+month |
| `varshaphal_details` | exists | return moment, lagna, muntha |
| `varshaphal_planets` | exists | planets of the year chart |
| `varshaphal_muntha` | exists | natal lagna + age; lord and house in the annual chart |
| `varshaphal_mudda_dasha` | partial | 1 dasha year = 3 days; basis per config mudda_dasha_basis (# VERIFY) |
| `varshaphal_panchavargeeya_bala` | partial | five divisions; hadda table sums verified, fractions from memory (# VERIFY) |
| `varshaphal_harsha_bala` | partial | four components; low confidence (# VERIFY) |
| `varshaphal_saham_points` | partial | 10 sahams from planets+lagna only; formulas from memory (# VERIFY) |
| `varshaphal_yoga` | partial | Ithasala and Ishrafa only; Nakta/Yamaya/Kambool etc. not implemented |

## Geo Details

Tier Data; module: geo.py, timeutil.py, tzinfo_lookup.py; phase 23.

| Endpoint | Status | Note |
|---|---|---|
| `geo_details` | exists | offline GeoNames candidates (no third-party call); own request model {place, limit} |
| `timezone_with_dst` | exists | IANA zone for lat/lon or place + offset, DST, abbreviation, nonexistent/ambiguous times and the year's transitions; historical rules |

## Monthly Panchang Yoga

Tier T2; module: panchang/yogas_monthly; phase 13.

| Endpoint | Status | Note |
|---|---|---|
| `sarvartha_siddhi` | exists | rules in panchang/rules/monthly_yogas.yaml (# VERIFY); windows from exact nakshatra/tithi boundaries |
| `amrit_siddhi` | exists | rules in panchang/rules/monthly_yogas.yaml (# VERIFY); windows from exact nakshatra/tithi boundaries |
| `ravi_yoga` | exists | rules in panchang/rules/monthly_yogas.yaml (# VERIFY); windows from exact nakshatra/tithi boundaries |
| `ravi_pushya` | exists | rules in panchang/rules/monthly_yogas.yaml (# VERIFY); windows from exact nakshatra/tithi boundaries |
| `guru_pushya` | exists | rules in panchang/rules/monthly_yogas.yaml (# VERIFY); windows from exact nakshatra/tithi boundaries |
| `dwipushkar` | exists | rules in panchang/rules/monthly_yogas.yaml (# VERIFY); windows from exact nakshatra/tithi boundaries |
| `tripushkar` | exists | rules in panchang/rules/monthly_yogas.yaml (# VERIFY); windows from exact nakshatra/tithi boundaries |

## Krishnamurti Paddhati

Tier T1/T2; module: kp; phase 15.

| Endpoint | Status | Note |
|---|---|---|
| `kp_planets` | exists | per planet: sign/star/sub/sub-sub lords + KP house (Placidus) |
| `kp_house_cusps` | exists | Placidus cusps with lord chains |
| `kp_birth_chart` | exists | planets + cusps + significators (kp.kp_chart) |
| `kp_house_significator` | exists | A-D ordering (kp/significators.py); Rahu/Ketu own no house # VERIFY |
| `kp_planet_significator` | exists | levels 1-4 ordering; Rahu/Ketu own no house # VERIFY |

## Biorhythm

Tier T1; module: biorhythm; phase 19.

| Endpoint | Status | Note |
|---|---|---|
| `biorhythm` | exists | 23/28/33-day sine cycles from days since birth; labelled entertainment |
| `moon_biorhythm` | missing | definition not confirmed; deliberately not implemented (plan: do not guess) |

## Horoscope Charts

Tier T1; module: render, vargas; phase V1+11.

| Endpoint | Status | Note |
|---|---|---|
| `horo_chart/:chart_id` | exists | Kundli.vargas / chandra / surya |
| `horo_chart_image/:chartId` | exists | render.north_indian/south_indian SVG |

## Ashtakvarga

Tier T2; module: strength/ashtakavarga; phase V1.

| Endpoint | Status | Note |
|---|---|---|
| `planet_ashtak/:planet_name` | exists | ashtakavarga.bav/prastara |
| `sarvashtak` | exists | ashtakavarga.sav |

## Numerology

Tier T2; module: numerology; phase 19.

| Endpoint | Status | Note |
|---|---|---|
| `numero_table` | exists | radical/destiny/name numbers; letter table per config numerology_system |
| `numero_report` | partial | facts computed; report text arrives in phase 21 |
| `numero_fav_time` | exists | weekday of the lord of the number (none for Rahu/Ketu numbers); radical and destiny |
| `numero_place_vastu` | partial | direction lordship of the ruling graha (# VERIFY, from memory) |
| `numero_fasts_report` | partial | weekday computed; text in phase 21 |
| `numero_fav_lord` | exists | friendly/neutral/inimical numbers from natural friendship; Rahu/Ketu not defined |
| `numero_fav_mantra` | partial | navagraha beeja mantras (# VERIFY, from memory); disclaimer in response |
| `numero_prediction/daily` | partial | daily number convention reduce(radical + date digits); text in phase 21 |

## Panchang

Tier T1; module: panchang/ (core, spans, sun_moon_times, hora, choghadiya, inauspicious, tamil, festivals); phase 12.

| Endpoint | Status | Note |
|---|---|---|
| `basic_panchang` | exists | engine-neutral; exact element spans (panchang/spans.py) |
| `basic_panchang/sunrise` | exists | engine-neutral; exact element spans (panchang/spans.py) |
| `advanced_panchang` | exists | engine-neutral; spans, hora, choghadiya, inauspicious, tamil, festivals |
| `advanced_panchang/sunrise` | exists | engine-neutral; spans, hora, choghadiya, inauspicious, tamil, festivals |
| `planet_panchang` | exists | basic panchang plus natal planets at the moment (not transits) |
| `planet_panchang/sunrise` | exists | basic panchang plus natal planets at the moment (not transits) |
| `chaughadiya_muhurta` | exists | day and night; night table is # VERIFY |
| `hora_muhurta` | exists | current hora of the moment |
| `hora_muhurta_dinman` | exists | 24 horas of the Vedic day |
| `panchang_chart` | exists | D1 chart + lagna at the moment |
| `panchang_chart/sunrise` | exists | D1 chart + lagna at the moment |
| `tamil_month_panchang` | exists | every civil day of the Tamil month; sunset rule is # VERIFY |
| `tamil_panchang` | exists | Tamil month and day; year name not implemented |
| `panchang_festival` | exists | rules in panchang/festivals/rules (single-anchor, # VERIFY) |
| `festival-by-date` | exists | festivals of the calendar month containing the date (semantics to confirm from provider docs) |

## Match Making

Tier T2; module: match/; phase 16.

| Endpoint | Status | Note |
|---|---|---|
| `match_birth_details` | exists | birth details of both partners |
| `match_ashtakoot_points` | partial | 8 kootas; tables from memory (# VERIFY, match/tables.yaml) |
| `match_ashtakoot_report` | partial | points + verdict; report text arrives in phase 21 |
| `match_obstructions` | partial | manglik match, nadi and bhakoot dosha with cancellations (# VERIFY) |
| `match_astro_details` | exists | avakahada of both |
| `match_planet_details` | exists | planets of both |
| `match_manglik_report` | partial | manglik match computed; text in phase 21 |
| `match_making_report` | partial | computed result; text in phase 21 |
| `match_making_detailed_report` | partial | computed result + astro details; text in phase 21 |
| `match_dashakoot_points` | partial | 9 of 10 poruthams; Rasi not implemented |
| `match_percentage` | partial | total/36*100 convention; provider formula to be discovered with the oracle |

## Vimshottari Dasha

Tier T1; module: dasha/vimshottari; phase 14.

| Endpoint | Status | Note |
|---|---|---|
| `current_vdasha_all` | exists | chart.current_dasha levels=5 |
| `major_vdasha` | exists |  |
| `current_vdasha` | exists |  |
| `current_vdasha_date` | exists | as_of explicit |
| `sub_vdasha/:md` | exists | antardashas of an MD (dasha.engine.descend) |
| `sub_sub_vdasha/:md/:ad` | exists | pratyantar list |
| `sub_sub_sub_vdasha/:md/:ad/:pd` | exists | sookshma list |
| `sub_sub_sub_sub_vdasha/:md/:ad/:pd/:sd` | exists | prana list |

## Char Dasha

Tier T2; module: dasha/chara; phase 14.

| Endpoint | Status | Note |
|---|---|---|
| `major_chardasha` | partial | maha dates verified against one reference; co-lord rule # VERIFY |
| `current_chardasha` | partial | as_of stack; sub-levels below maha # VERIFY |
| `sub_chardasha/:md` | partial | antars: one rule for all schools (# VERIFY) |
| `sub_sub_chardasha` | partial | pratyantars of the antar running at as_of; same # VERIFY rule |

## Yogini Dasha

Tier T1; module: dasha/yogini; phase 14.

| Endpoint | Status | Note |
|---|---|---|
| `major_yogini_dasha` | exists |  |
| `sub_yogini_dasha/:dashaCycle/:dashaName` | exists | cycle = n-th 36-year cycle; route semantics to confirm from provider docs |
| `sub_yogini_dasha` | exists | antars of the yogini MD running at as_of (cycle-aware) |
| `current_yogini_dasha` | exists | cycle-aware: repeats beyond the first 36 years |
