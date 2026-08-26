# Methodology Notes — Quantitative Baseline v0.1

## Scope

This baseline measures annual Google Books Ngram string frequency from 1842 through the latest year supported by the current public English interface. It is descriptive lexical evidence, not a causal analysis, reception study, or direct measure of emotion.

## Corpus verification and retrieval

- Provider endpoint: `https://books.google.com/ngrams/json`
- Corpus shorthand: `eng`
- Interface release documented by the provider: July 2024 dataset
- Verified supported end year: 2022, inferred from a bounded live probe requesting 2019–2026 and receiving 2019–2022
- Retrieval smoothing: `0`
- Case setting: case-insensitive, with the returned `(All)` series retained
- Query length compatibility: up to seven ordinary words under the current interface documentation

Every compatible rule was executed independently. Responses were cached with SHA-256 checksums; retries and exponential backoff prevent a single failed request from aborting the run. Zero-result, failed, and incompatible rules remain in the audit trail.

The public `eng` shorthand points to the current English corpus and is mutable. The public corpus table does not expose a persistent numeric identifier for that current shorthand, so the metadata records the interface release, retrieval date, parameters, raw payload, and checksum rather than pretending a stable corpus ID was available.

## Descriptive statistics

Per-query summaries calculate:

- first non-zero and number of non-zero years within 1842–2022;
- interval peak year and normalized frequency;
- latest-year value;
- raw values at 1842, 1938, 1988, 2006, 2007, 2015, and 2022;
- an explicitly labelled 2006–2007 two-year mean;
- contextual-window mean, median, and maximum;
- five-year pre- and post-anchor means where the interval permits;
- zero/sparse and trajectory-availability flags.

These statistics are descriptive. They do not identify causal changes at the anchors.

## Interpretation safeguards

1. A raw hit is a candidate occurrence, not accepted evidence.
2. Generic strings such as `fear`, `risk`, `heat`, or `concern` remain `BACKGROUND_AMBIGUOUS`; their curves measure all corpus uses.
3. Threat is not fear, risk is not emotion, and a legal formula is not a personal feeling.
4. Media-prescribed worry, survey-elicited response, researcher-coded affect, and participant self-description remain separate.
5. `depressing effect` in the 1842 material is not coded as modern clinical depression.
6. Standalone `change` is not a production query.
7. First corpus-observed year is not historical coinage; isolated early values require source-level inspection.
8. Family members are never summed into a composite frequency or “fear index.” Nested phrases and divergent senses make such totals invalid.

Chart lines use radius-3 smoothing only for legibility. Raw annual values remain unchanged in the canonical time-series export. The row-normalized anchor heatmap is a display transformation; its source remains the raw anchor matrix and its cells are not corpus frequencies.

## Provisional reconstruction

Original later-stage structured artifacts were unavailable. Recoverable report tables were reconstructed deterministically into 396 seed-stage records and a new 143-rule project inventory. Reconstructed rows receive new stable IDs and explicit `RECONSTRUCTED_FROM_REPORT` provenance. Visible original IDs are retained only where they are genuinely present in the reports.

One identity discrepancy remains explicit: the latest report states 36 exact surface matches, while deterministic anchor-local reconstruction yields 37. No arbitrary reconciliation was imposed. This does not block the provisional quantitative baseline, but it prevents claiming a final immutable production freeze.

## Passage-pilot quality metrics

The schema defines, but does not yet claim, accepted-match precision, false-positive rate, wrong-sense rate, wrong-voice rate, insufficient-context rate, duplicate rate, provenance-completeness rate, unresolved rate, reviewer agreement, and family-specific ambiguity rate. Values require real reviewed passages.
