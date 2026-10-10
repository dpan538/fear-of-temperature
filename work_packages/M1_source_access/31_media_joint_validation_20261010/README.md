# Media amount, parent dependence and distribution validation

The second implementation replaces the historical two-record success flag with
an explicit diagnostic vector. It links text amount to parent concentration
through dependence scenarios, then reports a bounded signed temporal contrast.
It does not decide whether a source, month or record should be retained.

Read the [method and formulas](../../../docs/acquisition/MEDIA_JOINT_DIAGNOSTICS.md),
[literature evidence](LITERATURE_EVIDENCE.csv) and [search scope](SEARCH_LOG.json).
The search verified nine paper records with explicit reading/access limits,
plus NIST formula documentation and the MeCCO project methodology. This is a
bounded methodological review, not an exhaustive systematic review.

## Current empirical finding

The closed social main-phase comparison demonstrates why these dimensions must
be read together. Dated bodies rose from 239,392 to 503,044 and observed months
from 201 to 294. The 2026 share fell from 58.10% to 29.60%. Contributing source
IDs rose from 14 to 17, while the order-2 effective **source-ID** count fell from
6.80 to 3.64. Python-list accounts for 48.43% of the later dated-body snapshot.
Historical recovery is substantial, but nominal source growth did not prevent
greater concentration. These IDs are not verified independent parent owners.

The newspaper nine-hour baseline has 16,138 dated complete article IDs across
401 observed months; 152 months still have exactly two. That latter flag remains
a historical diagnostic with no prospective stopping/evaluation weight. This
input predates the subsequent 2,103-article historical repair, whose final count
is 18,241 across 434 observed months. The later count is context from its closed
delivery and is deliberately not substituted into the pinned earlier table.

The social four-hour input is the **main closed phase only** at 14:41 AEST. It
excludes the later capacity-resume delta. Snapshot differences are acquisition
differences, not evidence of changes in public emotion or real-world activity.
No corpus database, raw response or body was opened by this validation run.

## Reproduce

From the repository root, in the existing project environment:

```sh
.venv/bin/python -m pytest tests/test_media_diagnostics.py -q
.venv/bin/python work_packages/M1_source_access/31_media_joint_validation_20261010/run_validation.py --output /tmp/media-joint-validation-new
```

The output directory must not exist. Inputs are exact named closed CSV files;
paths are in the driver. The social input remains local in its original closed
package, so external users must obtain that manifest-matched table before
reproducing it. Do not substitute an active database or silently use the latest
worker file. Source-month rows must be unique; confirmed alias/work mapping
must happen in an explicitly versioned upstream view. No collector or live
control file is an output target.

## Delivered validation

- [Monthly diagnostics](results_v2/monthly_joint_diagnostics.csv): 6,975 rows,
  three stream/snapshot combinations × 465 months × five ICC scenarios.
- [Snapshot comparison](results_v2/snapshot_summary.csv): dates, presence,
  2026 shares, source counts and concentration; publisher parents unknown.
- [Precision scenarios](results_v2/precision_scenarios.csv): 90 combinations of
  observed N, balanced-parent scenario, correlation and requested margin.
- [Variance simulations](results_v2/dependence_simulation.csv): 20 cases with
  30,000 replicates each, seed 20261010. Maximum relative error against the
  derived variance was **0.917%**, below the declared 5% numerical tolerance.
- [Validation status](results_v2/VALIDATION_REPORT.json) and
  [input/code/output hashes](results_v2/MANIFEST.json).

Forty-one focused tests cover an independent Statsmodels Wilson comparison,
reference-N calculations, two-record insufficiency, parent concentration and
mapping bounds, valid peaks, composition-only changes, negative contrasts,
unknown inventory denominators, incomplete boundary context, duplicate cells
and invalid inputs. Annual/source sensitivity checks verify mean-one weights, conserved total mass, separated year/group effects, missing-year preservation and explicit unknown-group retention. Ruff formatting/lint passed. Numerical and synthetic
checks are not evidence of calibrated real-world anomaly detection.

## Interpretation and next validation

Use [0,1] for enumerated inventory recovery, mapping coverage, collision
complement, amount scenarios and source-mixture JS. Use [-1,1] for signed
distribution and joint contrasts. Keep raw N/K, the chosen parent relation,
unknown mapping mass, selected-panel share, missing exposure and all components
visible. A low joint magnitude can hide sparse evidence; the raw deviation
must remain visible. No opaque overall quality score is supplied.

For a hypothetical independent binary estimand at nominal 95% confidence,
Wilson worst-case margins of ±10, ±7.5 and ±5 percentage points correspond to
93, 167 and 381 independent-N reference values. They are **planning examples,
not monthly collection targets**. At rho=.05, 1,000 texts from one parent give
an effective-N scenario of 19.63, compared with 168.07 across ten balanced
parents. Neither example estimates this corpus's true dependence.

The parallel 2026 review can supply independent, evidence-linked adjudication
cases. Before empirical score calibration, separate real peaks, source-entry
changes, date mistakes, duplicate/version candidates and unresolved cases;
freeze labels and hold out whole parents and later periods. There is presently
no sensitivity/specificity result, p-value, valid emotional scale, automatic
deletion criterion or validated corpus-wide representativeness measure.

The implementation preserves the previous identity/lakehouse and parent
monitor contracts. It remains a metadata consumer and has no effect on source
selection, task duration, quotas, resource budgets or acquisition termination.

## Annual weighting extension

The latest implementation adds [annual share scenarios](results_v2/annual_share_scenarios.csv), [source/year weights](results_v2/year_source_weights.csv), [weight diagnostics](results_v2/weight_sensitivity_summary.csv) and [fixed-source recent-year panels](results_v2/annual_fixed_source_panel.csv):36 comparison cases across the three snapshots and two calendar frames. Within January–August2016–2026, the closed social main snapshot places64.77% of bodies in2026. The common-source panel accounts for only0.87% of its2026 slice. A lower full-history share therefore does not establish a balanced recent decade.

Raw, gentle year, moderate year, moderate source, joint and equal-observed stress scenarios remain separate. Lower weighted2026 shares arise by construction, not because records were corrected. The optional group API can later consume verified parents, native thread/type or supplied automation markers. Those fields are not present in the selected source-month input, so this run does not label noise/bots or test emotional-feedback effects. No corpus records are removed, sampling probabilities estimated or acquisition thresholds created.

The preliminary results_v1 directory is retained locally as an intermediate; results_v2 and its exact hashes are the current delivery.
