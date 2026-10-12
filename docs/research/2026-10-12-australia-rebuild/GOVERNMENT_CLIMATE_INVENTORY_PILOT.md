# Government climate-attention inventory: bounded pilot

Recorded 12 October 2026, following Dai's latest request to map dated government climate explanations, warnings and related discussion before deciding minimum analytical coverage. This request authorizes the bounded exploratory inventory below; it does not turn climate keywords into a corpus-inclusion, structural-cleaning or acquisition-stop rule. All original material, neutral texts and lexical negatives remain retained.

**The downloaded samples contain climate-related passages, but they cannot define a full-period minimum analytical window.** The pilot finds 1,335 House paragraph candidates, 1,701 Senate paragraph candidates and one PM HTML-paragraph candidate, retaining their different units. Context review checks five passages across four months; one has an explicit prime-minister holder. The parliamentary examples remain separate institutional discourse with unresolved government/opposition/office roles. No prevalence, fear, comparable monthly attention series or sufficient-density claim is made.

The long-run objective is pooled source-frame coverage and distribution throughout **January 1988–September 2026**, ending **21 September**. Report the three roles' gaps separately. It does not require all roles in every month or a positive climate/fear hit in every month. The [full-period source bridge](GOVERNMENT_FULL_PERIOD_COVERAGE.md) remains necessary; the earlier recent-period overlap is a verification subset.

## Inputs and source-aware retrieval

Only already downloaded material is inspected: RAPID-CDL Parquet blocks 22 and 52, and four named official PM XML returns. No additional HTTP request, full paragraph-file scan, embedding/classifier run, raw deletion or semantic exclusion is performed. The preserved direct-request total remains **24,160,712 bytes** under **26,214,400 bytes**.

The case-insensitive body-only patterns are climate change, global warming, greenhouse and standalone climate. Strong phrases remain provisional; standalone climate can describe a political/business climate, while greenhouse can concern horticulture. Dates, titles and subject metadata do not replace readable-body matching. Source material is dated by native release or nominal sitting date; deposit/retrieval dates are not publication dates.

Risk/warning, negation-word and quotation-punctuation matches are separate review cues. They do not establish fear, affect prevalence, denial or quoted-holder attribution. Full expressions and neighbouring procedural context must resolve their scope. One reviewed PM quotation-punctuation flag is an apostrophe false positive, illustrating that even these cues need review.

| Sample frame | Inspected native units | Inspected months | Lexical candidates | Months with candidates | Strong-phrase candidates | Risk/warning cue among candidates |
|---|---:|---:|---:|---:|---:|---:|
| House block 22 |122,880 paragraphs|48|1,335|48|897|176|
| Senate block 52 |122,880 paragraphs|54|1,701|53|905|246|
| Four named PM releases |98 returned HTML paragraphs|4|1|1|1|0|

Parliament paragraph counts and PM HTML-paragraph counts are different units. Across these frames **81 months have some inspected material and 78 have lexical candidates**. These are nonrandom convenience blocks and named releases. Their IDs are not chronological; they span only selected source/month/procedural portions, and block edges may truncate complete units. Neither 78 nor 81 is a full-period coverage denominator or a proposed analytical window. The uninspected months and sampled lexical negatives are retained in the [1,395-cell source/month CSV](government_climate_inventory_pilot.csv).

## Five contextual checks

These are preliminary **Codex context reviews**, not independent human annotation or a classifier evaluation. The [pilot JSON](government_climate_inventory_pilot.json) records exact native IDs, dates, sitting/debate/procedural/speaker keys, source links, hashes, brief unchanged phrases and review states. Full texts and neighbouring paragraphs remain local.

| Locator and date | Context result | Holder/negation/quotation limit |
|---|---|---|
| House paragraph 2707054; 2011-11-02; Melissa Parke |Climate explanation connects ocean ecosystems, carbon capture and emissions.|Negation stresses importance rather than denying climate change. Harm refers to runoff. Governing/opposition and ministerial-office fields remain null.|
| Senate paragraph 6393642; 2025-11-24; Peter Whish-Wilson |Climate-action argument includes a future-generation risk cue.|The opening reports a Cornell finding; its scientific truth is not verified here. Risk language is not a fear label. Government-role fields remain null.|
| Senate paragraph 6393747; 2025-11-24; Penelope Wong |Climate/COP explanation discusses Pacific representation and negotiations.|Negation concerns agreement to a bid. Party and a recorded answer do not establish dated office; government-role fields remain null.|
| House paragraph 2811367; 2015-10-20; recorded speaker Melissa Parke |Climate-related quotation about capital and a low-carbon economy.|Immediately preceding paragraph 2811366 in the same unit identifies the quoted holder as Christiana Figuerres, preserving the source spelling. Do not assign that holder's claim or emotion to Parke.|
| PM 47643, HTML paragraph 0; 2026-09-21 |An explicitly labelled prime-minister turn discusses the climate challenge and Pacific neighbours.|Current official XML confirms Anthony Albanese's literal Prime Minister label. The climate clause is an own-turn statement; no fear inference or historical-body equality claim.|

The five reviewed passages establish four dated **sample context points**: November 2011, October 2015, November 2025 and September 2026. Only the September 2026 point has an explicitly evidenced executive holder in this pilot. Original ParlInfo content/date mapping and dated government roles remain pending for the parliamentary records. These checks cannot be extrapolated into retrieval accuracy, fear prevalence or sufficient monthly sample density.

## Coverage states and next analytical decision

Keep source presence and validated climate attention in different fields:

- **Uninspected:** no evidence about absence. CSV counts are blank, not zero.
- **Unavailable:** expected source/native text cannot be obtained or mapped; record the access/date problem.
- **Inspected partial sample with no lexical match:** a retrieval result for those units; no claim of zero climate discussion in that month.
- **Candidate or context-reviewed climate discussion:** traceable positive evidence at the recorded native unit. Attribution and measurement may remain pending.
- **True zero within a declared frame:** requires an applicable, complete/readable source inventory and validated retrieval/negative-context checks. None is established here.
- **Not applicable:** requires independent evidence that the particular source event/unit did not occur, such as a chamber not sitting. It does not imply absence of executive or other government expression.

Before choosing an RQ1/RQ2 window, freeze its source, genre, native unit, dated-role rules and applicable calendar. Retain a **contiguous baseline and its no-hit months**; do not select only the 78 positive sample months or choose before/after durations after inspecting outcome magnitudes. Event anchors require independent dated evidence. Role-unknown measurements stay null. Temporal associations remain descriptive unless their own causal identification requirements are met; no prediction-model objective is introduced.

The next concrete step is source-calendar/ID preparation for the missing historical government material, together with a declared chronological sample and reviewed lexical negatives. Determine minimum analytical coverage from that traced evidence and the intended comparison's validation requirements, rather than from a document quota, a forced positive monthly climate signal or the convenience-block hit rate. Supported climate-topic work can continue even when a fear-specific measure is unavailable.
