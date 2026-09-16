# Methodology

## Current pipeline

```text
Preserved lexical/Ngram baseline (legacy/provisional)
        ↓
Source-role/date assignment + provenance-preserving ingestion
        ↓
Lexical/TF-IDF and Sentence-Transformer relevance comparison
        ↓
Event/relation + aspect/emotion + temporal topic candidates
        ↓
Validated S/E/B aggregation with coverage and denominators
        ↓
CCF / conditional VAR / ITS + channel-transition diagnostics
        ↓
Evidence-linked interpretation and source/period validation
```

Later quantitative analysis must preserve the semantic, documentary and source limitations established during research validation. Frequency, retrieval quantity, semantic classification and accepted historical evidence are related but non-equivalent outputs.

The executable architecture and current implementation boundary are documented in [`../ARCHITECTURE.md`](../ARCHITECTURE.md). The synthetic demo verifies software interfaces; it does not report historical results. Production source access, labels, model validation and temporal estimates remain pilot work under the current proposal.
