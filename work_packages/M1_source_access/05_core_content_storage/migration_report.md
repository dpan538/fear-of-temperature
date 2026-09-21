# Core storage migration report

## Result

Migration status: **passed**. Content collection status: **blocked**.

The frozen `m1_government_batch_v2` database was migrated into a separate
`m1_government_content_storage_v3` working database. The frozen source SHA-256 was
`16690bc540f8194cc2bf8ec1cba3794fb9745d0986e0dae2643306d6cb48c396`
before and after migration. The new working database SHA-256 is
`5aa96f0f52fb499253853e62adecf0b307eee5f39b9d31e74141bae07fd0bf91`.

Two independent offline builds produced logical fingerprint
`a44dddcc2c85b2694d4360787c7abf1ca7e314a9f3d701913d3034b8b31b66d2`.
Repopulating the first build did not change any table count. A floating-point
nondeterminism in the derived institution fractional-count export was found during
validation and corrected by using fixed-precision decimal aggregation; underlying
stored weights and associations were not changed.

## Baseline preservation

| Measure | Frozen baseline | Migrated result |
| --- | ---: | ---: |
| Unique publication records | 1,020 | 1,020 |
| Webpage content objects | 1,020 | 1,020 |
| Unique attachment objects | 2,005 | 2,005 |
| Attachment-parent associations | 2,007 | 2,007 |
| Organisations | 69 | 69 |
| Document-organisation associations | 1,473 | 1,473 |
| Shared attachment objects | 1 | 1 |

All 3,025 content objects have a non-empty retained title and acquisition status
`blocked_pending_ethics_route`. The 3,027 document-content associations comprise
1,020 landing-page and 2,007 attachment edges.

## Version and paragraph behaviour

- Metadata `document_versions` remain separate from byte-level
  `content_versions`.
- Only a successful 2xx fetch with final URL, retrieval time, MIME type, saved
  raw path and verified SHA-256 can establish a content version.
- Failed, blocked, skipped and unattempted records retain fetch evidence but have
  `content_version_id = NULL`.
- The pair `(content_object_id, content_sha256)` is unique. Re-fetching identical
  bytes may add a fetch log while reusing the version; changed bytes receive a new
  stable version ID.
- `text_segments.content_version_id` and `extraction_run_id` are mandatory.
  `representation_kind` separates source extraction, cleaning and later derived
  text so none overwrites the other.

Because no content bytes were authorised or downloaded, both `content_versions`
and `text_segments` correctly contain zero rows.
