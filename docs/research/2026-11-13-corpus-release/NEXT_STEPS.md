# Post-Acquisition Research Plan

**Status at this release:** raw acquisition is complete. Independent bounded review and pre-chunk design have been recorded; a separate implementation workstream is preparing derived views and a bounded pilot. This publication does not claim that full-corpus preprocessing, gold annotation, frozen production splits, model training or empirical RQ analyses are complete.

## Preserve meaning while deriving model views

Remove demonstrated interface/navigation/form/recommendation noise using structural evidence and traceable spans. Retain paragraphs, quotation attribution, negation, pronouns, intensity, bodily expressions, temporal comparison, memory, metaphor, mixed affect and medical language. Generic stopword deletion or forced English-only filtering is not a safe default for these questions. Keep original/derived hashes and offset maps; changes belong in a derived layer.

Repeated text may matter for cultural circulation. Shared text caching and leakage groups must not replace each record's voice, publication date or context with the first occurrence. Unknown or conflicting dates remain visible. Preserve neutral and positive texts across time rather than selecting a desired trend.

## Separate records, groups and evaluation

Establish work, version, thread and verified shared/copy/context groups before splitting or chunking. Chunks inherit the parent group and partition. Merely mentioning the same event does not merge independent records in the main classifier experiment. Unknown authors must not all collapse into one synthetic author group.

Freeze experiment-specific parent manifests before fitting vocabulary, IDF, learned stoplists, scaling or model parameters. These transformations fit training only; validation selects settings and test remains held out. The current bounded implementation plan proposes approximately 90/5/5 train/validation/test targets with intact groups taking precedence. This supersedes the earlier 70/15/15 design suggestion; achieved splits and diagnostics must be reported separately when executed.

Time-transfer, source/author-held-out and unseen-event experiments answer different questions. A proposed pre-2023 versus 2023–2025 temporal evaluation must use its own training-fitted artifacts and does not establish historical as-of forecasting from later captures. Events require independently evidenced timing; draft event names or publication spikes are not verified treatments.

## Validate measurement before historical claims

Annotate the continuum rather than binary pure-Fear text. Separate temperature/climate relation, general-negative intensity, affect subtype, Fear probability/intensity, speaker, target, narrative time and uncertainty. Strong anger or ecological grief is not automatically Fear. Query labels and sampling families are not gold annotation.

Evaluate mild/somatic/indirect/metaphorical cases, mixed affect, negation, quotation, medical context and backlash alongside intense Fear. Use record-level probability samples and separate challenge sets, with known selection rules and clear denominators. Report source/year/genre/length errors and calibration; a small parser pilot cannot estimate whole-corpus emotion prevalence.

Keep full native-record views for classical ML. For deep models, verify the actual tokenizer and total input limit before choosing focus/context budgets. Use nonoverlapping focus spans with bounded attributed context, explicit coverage and no silent truncation. Do not broadcast a document label to every chunk or let long documents receive hundreds of independent votes.

## Connect validated outputs to the three questions

| Question | Required evidence |
|---|---|
| RQ1: longitudinal learning-compatible development | Validated record-level affect/Fear measurement, publication/narrative-time distinctions, learning/memory/transmission narratives, and source/capture/genre/version/length sensitivities |
| RQ2: classification and scoring | Group-disjoint evaluation, subtype/intensity separation, calibration, uncertainty, transparent baselines and robustness across the continuum |
| RQ3: event-centred change | Independently documented events and windows, overlapping-event handling, distinct activity versus affect denominators, and original-passage interpretation |

A monotonic curve, classifier accuracy or before/after association alone cannot establish learned cultural transmission. Results may support, qualify or fail to support the macro hypothesis. The code and synthetic demo already in this repository are infrastructure candidates, not the adopted final measurement system.
