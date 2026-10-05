# Methodology

## Current research pipeline

Follow the [current project direction](../PROJECT_DIRECTION.md): international temporal
coverage and independently documented events guide collection; national completeness does
not gate the study. The publication endpoint stays at 21 September 2026. Current work audits
distribution and provenance quality and performs structural/numerical cleaning; climate
relevance validation begins in the later analysis stage. See the [4 October stage decision](../decisions/2026-10-04-fixed-cutoff-distribution-and-source-quality.md).

```text
Cross-regional event/checkpoint evidence + source/role/date provenance
        ↓
Fixed interval → distribution and provenance audit → structural cleaning / passage repair
        ↓
LATER ANALYSIS: lexical/TF-IDF and Sentence-Transformer climate relevance comparison
        ↓
Passage similarity → inspect affect/risk association and original evidence
        ↓
Validated attention/association measures → pooled role/time series if comparable
        ↓
CCF / conditional VAR / ITS + channel-transition diagnostics
        ↓
Evidence-linked macro interpretation; later RQ3 fear synthesis and attribution
```

Later quantitative analysis must preserve the semantic, documentary and source limitations established during research validation. Frequency, retrieval quantity, semantic classification and accepted historical evidence are related but non-equivalent outputs.

The first retrieval and role/time stages do not directly map fear. They establish climate-topic discourse and investigate how affective or risk language is associated with it. An explicit-fear label in a bounded pilot is diagnostic only; an anticipated-harm cue is not automatically fear. Original-passages review and construct validation precede any fear-specific measure. See the [staged construct decision](../decisions/2026-09-27-staged-climate-affect-and-fear-interpretation.md).

The executable architecture and implementation inventory are documented in [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Existing emotion/relation/topic candidates and S/E/B demo outputs are optional infrastructure, not new requirements for the similarity-led research path. The synthetic demo verifies software interfaces; real collection status is recorded in [`../PROJECT_LOG.md`](../PROJECT_LOG.md).
