# Validation Report — Quantitative Baseline v0.1

Automated validation status: **PASS**

- PASS — controlled dimensions: 6 anchors, 4 layers, 5 voices, 5 modes, 14 families
- PASS — strict anchor windows contained by contextual windows
- PASS — seed ledger: 180 + 180 + 36 = 396, unique and provenance-labelled
- PASS — query inventory: 143 audited rules, 138 executable
- PASS — broad terms flagged BACKGROUND_AMBIGUOUS; standalone change not production-enabled
- PASS — retrieval outcomes preserved: 132 success, 6 zero, 5 incompatible, 0 failed
- PASS — 23,892 unique raw annual observations, 1842–2022, smoothing 0
- PASS — run metadata records provider, current English corpus, live probe, and warnings
- PASS — family summaries are member-wise and explicitly non-additive
- PASS — bounded-corpus search metrics scaffolded; no fabricated counts
- PASS — presentation artifacts present: 21 PNG figures

PostgreSQL runtime application is reported separately after the isolated-cluster test.
