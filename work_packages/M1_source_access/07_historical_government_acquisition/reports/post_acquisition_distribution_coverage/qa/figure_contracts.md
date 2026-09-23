# Figure contracts

## Figure 1 — annual distributions

Core conclusion: The three genres have different scales and temporal profiles and must remain analytically separate.
Results-level question: How many records are observed per year in each genre?
Figure archetype: quantitative small-multiple grid.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: a policy records; b written answers; c written statements.
Evidence hierarchy: annual record counts are primary; partial-year shading is a boundary cue.
Reviewer risk: independent axes could be misread, so each panel is explicitly labelled and the footer states the rule.

## Figure 2 — year × month heatmaps

Core conclusion: Monthly density varies by genre and observed zero months are not coverage claims.
Results-level question: Where are the dense and sparse months within each genre?
Figure archetype: aligned heatmap small multiples.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: a policy; b answers; c statements.
Evidence hierarchy: within-genre pattern is primary; independent scales prevent the answer series from erasing policy variation.
Reviewer risk: scale differences and zero semantics are stated in titles/footer.

## Figure 3 — collection coverage status

Core conclusion: Source support, incomplete enumeration, failed known targets, unrequested targets and confirmed zero records are categorically different states.
Results-level question: Which source-month partitions are complete, partial, unrequested, unsupported or confirmed zero?
Figure archetype: categorical status matrix.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: one source × month matrix.
Evidence hierarchy: categorical status is primary; volume-200 annotation is a boundary case.
Reviewer risk: unknown record counts must not be converted to numeric zero.

## Figure 4 — department composition

Core conclusion: Department mix changes with machinery of government and source regime.
Results-level question: Which departments constitute each genre in each year?
Figure archetype: normalized stacked small multiples.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: a policy; b answers; c statements.
Evidence hierarchy: annual fractional composition is primary; no topic or causal interpretation is made.
Reviewer risk: multi-organisation policy records use stored fractional weights, unlike one-department ministerial records.
