# M1.5 approved core content storage

This work package implements Dai Pan's 21 September 2026 approval of five logical
storage tables. It migrates the frozen M1.4 database into a new working database;
it does not modify the frozen DuckDB file, manifests, raw evidence, or reports.

The approval covers storage and provenance only. It does not approve attachment
weights, aggregation rules, genre denominators, body-use ethics, or republication.
Consequently the current migration creates no `content_versions` or
`text_segments`: every one of the 3,025 content objects remains blocked.

## Rebuild and verify

Run from the repository root with the existing environment:

```bash
.venv/bin/python -m fear_temperature.government_collection migrate-core \
  --config work_packages/M1_source_access/05_core_content_storage/config.yaml

.venv/bin/python -m fear_temperature.government_collection verify-core \
  --config work_packages/M1_source_access/05_core_content_storage/config.yaml
```

`migrate-core` checks the frozen database hash, builds two independent temporary
databases, repeats population in the first database, compares logical
fingerprints, and atomically installs the second database only after validation.
`verify-core` is read-only with respect to both DuckDB files and refreshes the
small JSON verification record.

The generated DuckDB database and CSV exports are local rebuildable artefacts and
are not committed. `migration_verification.json`, `verification.json`, the data
dictionary, and the reports in this directory are the tracked evidence.

## Content collection gate

No new live Search API enumeration is performed. The exact frozen
`enumeration_manifest.csv` remains the discovery set. If a documented UQ/content
use path later covers the intended operations, create a separate acquisition
configuration referencing that manifest, run a maximum three-publication smoke
fetch first, and keep the resulting fetches and versions in a new acquisition
batch. Do not edit the frozen M1.4 configuration or snapshot.
