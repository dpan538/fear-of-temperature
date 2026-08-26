# Fear of Temperature

Fear of Temperature is a reproducible digital humanities research project investigating how rising temperature has been measured, experienced, causally explained, framed as risk or threat, communicated, and expressed affectively across different historical documentary contexts.

The thesis does not assume a simple linear history from “no fear” to “fear.” Instead, it examines relationships among:

- temperature measurement;
- lived heat experience;
- climatic causation;
- institutional risk and threat;
- mediated public warning;
- civic mobilisation;
- public appraisal;
- named affect.

## Historical framework

| Anchor | Research role |
| --- | --- |
| 1842 | Meteorological/environmental and embodied-heat baseline |
| 1938 | CO₂–temperature causal-science bridge |
| 1988 | Institutional climate-risk and mediated-warning anchor |
| 2006–2007 | Public-communication and threat-framing bridge |
| 2015 | Temperature-threshold governance anchor |
| 2022 | Contemporary heat/risk/affect endpoint |

These anchors are analytical historical positions, not assumed stages of a single stable emotion.

## Lexical framework

The current lexical layers are:

- **A — Temperature / Physical Phenomenon**
- **B — Climate / Atmospheric / Causal**
- **C — Affect**
- **D — Threat / Risk / Harm**

The current voice categories are:

- **V1 — Scientific / Research**
- **V2 — Institutional / Governance**
- **V3 — Mediated Public**
- **V4 — Organised Civic / Advocacy**
- **V5 — Direct Public / Lay**

Voice and source genre are separate analytical dimensions. A scientist quoted by a newspaper remains a scientific voice; a survey participant represented in an academic paper remains a public/lay voice.

## Research Data Principles

1. Raw evidence is never silently overwritten.
2. Derived, normalised, candidate, canonical and reviewed states remain distinguishable.
3. Historical source, later reproduction and scholarly interpretation must remain traceable.
4. Researcher terminology, survey instrument wording and participant wording must not be conflated.
5. A keyword hit is not automatically accepted research evidence.
6. Negative and rejected evidence remains auditable.
7. Historical source gaps must not be filled artificially for symmetry.
8. All later collection and review operations should be versioned.

## Repository structure

```text
docs/           research reports, methodology and decision records
data/raw/       immutable or minimally transformed collected data
data/interim/   intermediate processing outputs
data/processed/ validated research datasets
data/exports/   presentation and research exports
db/             PostgreSQL migrations and seed data
scripts/        reproducible collectors and analysis scripts
notebooks/      exploratory analysis only
figures/        generated research figures
tests/          validation and regression tests
```

Raw source data should not be manually edited after capture.

## Repository metadata

Suggested GitHub description:

> A reproducible digital humanities research project tracing how temperature, climate risk, threat, and affect are represented across historical scientific, institutional, media, civic, and public discourse.

Suggested topics: `digital-humanities`, `climate-change`, `climate-history`, `historical-linguistics`, `corpus-linguistics`, `semantic-analysis`, `history-of-emotions`, `climate-communication`, `postgresql`, `research-data`, `data-provenance`, and `nlp`.

## Current status

This initial repository establishes research scope, structure, provenance expectations and development hygiene. It intentionally contains no collectors, database implementation, quantitative baseline, analysis dependencies or licence. Licensing for source code, research data and restricted third-party sources will be decided separately.
