# Figure Catalog — Exploratory Analysis v0.2

All figures are generated from version-controlled CSV exports. PNG and SVG versions share the same source table and metadata.

| Figure | Research question / purpose | Metric | Interpretation warning |
| --- | --- | --- | --- |
| `visual_01a_anchor_layer_counts` | Raw candidate counts by anchor/layer. | Priority Candidate count | Inventory composition ≠ historical prevalence. |
| `visual_01b_anchor_layer_percentages` | Within-anchor candidate shares by layer. | Candidate share within anchor | Inventory composition ≠ historical prevalence. |
| `visual_02_anchor_voice_counts` | Candidate counts by anchor/voice. | Priority Candidate count | Source composition may shape apparent lexical change. |
| `visual_03a_anchor_family_counts` | Candidate count heatmap. | Priority Candidate count | Not corpus frequency. |
| `visual_03b_anchor_family_row_normalized` | Family-wise maximum-normalized display. | Count divided by family maximum | Within-family normalized display — not frequency. |
| `visual_04_voice_family_heatmap` | Candidate count heatmap. | Priority Candidate count | Source/speaker composition, not prevalence. |
| `visual_05_climate_framing_trajectories` | Raw annual Ngram series. | Normalized frequency × 1,000,000 | String frequency is not semantic evidence. |
| `visual_06a_modern_compounds_raw` | Raw annual Ngram series. | Normalized frequency × 1,000,000 | String occurrence is not validated target sense. |
| `visual_06b_modern_compounds_normalized` | Each trajectory scaled to its own peak. | Term value / term maximum | Normalized display is not corpus frequency. |
| `visual_07_ngram_vs_validated_attestation` | Raw string appearance versus project evidence. | Year | Project evidence is not first-ever attestation. |
| `visual_08_ngram_vs_search_discoverability` | Parallel measurement comparison. | Ngram peak per million; IA count log10 | Metrics answer different questions. |
| `visual_09_dictionary_status_by_anchor` | Candidate lexicographic treatment by anchor. | Priority Candidate count | Does not establish semantic evolution. |
| `visual_10_searchability_bias` | Bounded-search outcomes by anchor. | Candidate count | Retrieval ease is not lexical abundance. |
| `visual_11_candidate_missingness_heatmap` | Coverage across seven candidate dimensions. | Controlled status | Zero and missing states are not imputed. |
| `visual_12_structural_alluvial` | Metadata composition flow. | Candidate count | Not a historical process or causal flow. |

## Reproduction

Run `python3 scripts/fear-temperature/generate_eda_figures.py` from the repository root.

The alluvial diagram visualises metadata structure only. It does not assert a historical process, causal flow, or semantic-evolution pathway.
