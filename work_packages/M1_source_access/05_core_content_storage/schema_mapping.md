# Approved five-table mapping

Decision authority: `docs/decisions/2026-09-21-five-core-tables.md`.

| Approved logical table | Frozen implementation | M1.5 implementation |
| --- | --- | --- |
| `documents` | Present with stable GOV.UK `content_id`-derived identity, publication/update observations and governance states | Reused unchanged; metadata `document_versions` remain distinct from saved content versions |
| `content_objects` | Present for 1,020 webpages and 2,005 unique attachments | Reused and extended with `title`, current `acquisition_status`, and provenance-preserving identity metadata |
| `document_content_objects` | Present as a document-to-webpage/attachment many-to-many table | Reused unchanged; the shared attachment keeps one object and two parent associations |
| `content_versions` | Missing; successful fetch evidence was stored only on `content_fetches` | Added. Only a successful 2xx fetch with saved bytes and verified SHA-256 can create a row; identical bytes for the same object map to one version |
| `text_segments` | Empty interface linked to `document_id`, not an immutable body version | Replaced in the new database by an empty interface requiring `content_version_id` and `extraction_run_id`; representation kind prevents source extraction and cleaning outputs from overwriting one another |

Supporting source, organisation, batch, query partition, raw record, metadata
version, fetch log, extraction run, relationship and governance tables remain.
The approved five-table design is a logical core, not a five-table-only database.

The document metadata normalisation rule remains `govuk_metadata_v3`. The new
`govuk_content_object_v2` rule records only the content-object title/identity and
successful-version gate added by this migration.
