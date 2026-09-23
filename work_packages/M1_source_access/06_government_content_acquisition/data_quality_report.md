# Government content acquisition quality report

Generated: 2026-09-21T09:29:34Z

## Scope and authorization boundary

This work package attempts the frozen 1,020 publication webpages and 2,005 unique
attachments (3,025 content objects). It does not re-enumerate sources and does not
claim coverage of all UK government policy.

Dai explicitly authorized internal project downloading, storage and source-text
extraction. The statement that the supervisor has given a green light is recorded
as Dai's report. No UQ HREC approval, exemption or not-applicable determination is
asserted. Raw full text is not cleared for public redistribution.

## Results

- Attempted: 3025 / 3025.
- Webpages downloaded: 1020 / 1020.
- Attachments downloaded: 2001 / 2005.
- Download failures: 4.
- Objects with successful text extraction: 3000.
- Source text segments/blocks: 2865202.
- `needs_ocr`: 14; `unsupported_format`: 5.
- Recovery audit attempted only 12 non-final objects;
  completed objects were skipped from network retrieval.

### Download states

| State | Objects |
|---|---:|
| `access_denied` | 3 |
| `failed_http` | 1 |
| `success` | 3021 |

### Extraction states

| State | Objects |
|---|---:|
| `extraction_failed` | 2 |
| `needs_ocr` | 14 |
| `not_attempted_download_failed` | 4 |
| `success` | 3000 |
| `unsupported_format` | 5 |

## Verification

Overall: **PASS**.

- PASS — `all_frozen_objects_attempted`
- PASS — `one_current_status_per_object_in_acquisition_batch`
- PASS — `current_statuses_link_fetch_history`
- PASS — `successful_files_exist_and_hash_match`
- PASS — `successful_fetches_link_content_versions`
- PASS — `saved_statuses_link_content_versions`
- PASS — `historical_content_versions_link_objects`
- PASS — `segments_trace_to_version_and_extraction_run`
- PASS — `segment_count_matches_status_sum`
- PASS — `document_content_relations_preserved`
- PASS — `shared_attachment_relations_preserved`
- PASS — `04_database_unchanged`
- PASS — `04_manifest_unchanged`
- PASS — `05_database_unchanged`
- PASS — `resume_skipped_completed_objects`

PDF locators identify page and extracted text block; blocks are not asserted to be natural paragraphs.
