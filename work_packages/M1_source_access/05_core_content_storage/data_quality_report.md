# Data quality and recovery verification

Status: **passed** on 21 September 2026.

The following checks passed against the migrated working database:

- Frozen source SHA matched `batch_freeze.json` and was unchanged by migration.
- Two clean offline builds had the same logical fingerprint.
- Repeating population did not increase table counts.
- All document-content, content-version, fetch-version, segment-version and
  segment-extraction references resolved.
- Baseline document, webpage, attachment, attachment-parent, organisation and
  document-organisation counts were preserved.
- The shared attachment remained one object with multiple parent associations.
- Non-success fetches generated no content version.
- A success record without complete saved-byte evidence is rejected by code.
- Identical hashes for one content object map to the same version identity;
  changed hashes map to different versions.
- The paragraph interface requires a concrete content version and has no legacy
  `document_id`-only path.
- Zero content versions and zero text segments are consistent with the active
  body gate; no empty or synthetic body rows were inserted.

The test suite covers the new gate and version identity rules alongside existing
pagination, metadata projection, shared attachment, retry and download-validation
tests. Machine-readable results are in `migration_verification.json` and
`verification.json`.

Known limitation: the new database is recoverable from the local frozen DuckDB
and manifest/raw evidence. As documented by M1.4, the complete raw-response archive
and DuckDB files are intentionally local and not reconstructible from Git alone.
