# Companion annotation schema

`findings.csv` contains actionable `conflict`, `needs_review` and field-missing `uncheckable` results. Aggregate `supported` and `not_applicable` counts are in `execution_coverage.csv`; no millions of redundant pass rows are materialised. Rerunning the same source checkpoint/rule replaces its output file deterministically.

| Column | Meaning |
|---|---|
| finding_id | SHA-256 of frame ID, unit ID, rule ID, rule version and source snapshot key; deterministic upsert key. |
| frame_id, unit_type, unit_id, source_id | Source-specific target, never a cross-source numerical ID. |
| source_version, input_snapshot | Saved content version/Item if known and input checkpoint identifier. |
| rule_id, rule_version, dimension | Independent structural rule and review dimension. |
| observed, expected | Original recorded value(s) and explicit contract; JSON strings where needed. Original data are not edited. |
| outcome, severity | Supported conflict, review or uncheckable classification; severity is triage, not credibility score. |
| evidence_path, evidence_locator | Saved file/table and precise parent/Work/row locator; no uncited model judgment. |
| reason, proposed_action | Why classified and bounded next action. |
| checked_at_utc | Actual validator run time. |

`source_quality_summary.csv` keeps original-utterance route, archival reproduction, secondary/mixed/unknown route and saved content-link evidence separate. Issuer/host outcomes are in `execution_coverage.csv` and named `findings.csv` rows. The summary's `substantive_claim_truth` value is `unassessed`; consumers must not infer truth from provenance.

Suggested later SQL (proposal only):

```sql
CREATE TABLE derived_provenance_findings (
  finding_id TEXT PRIMARY KEY, frame_id TEXT, unit_type TEXT, unit_id TEXT,
  source_id TEXT, source_version TEXT, input_snapshot TEXT,
  rule_id TEXT, rule_version TEXT, dimension TEXT,
  observed TEXT, expected TEXT, outcome TEXT, severity TEXT,
  evidence_path TEXT, evidence_locator TEXT, reason TEXT,
  proposed_action TEXT, checked_at_utc TEXT
);
-- Load a reviewed CSV to a staging table, then INSERT ... ON CONFLICT(finding_id)
-- DO UPDATE for the same input snapshot. Preserve findings from older snapshots.
```

This file proposes a derived review table only; the validator writes no formal database table.
