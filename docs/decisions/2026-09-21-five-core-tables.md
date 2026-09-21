# Approved: five core tables for first-stage corpus storage

- Decision date: 21 September 2026
- Reviewer: Dai Pan
- Design status: approved by the user in the project conversation
- Implementation status: pending a subsequent implementation task
- Scope: storage, provenance and engineering validation; no research analysis

## Decision

Use five core logical tables, reusing existing equivalent structures where possible.
These are not the only permitted tables: retain source, organisation, batch,
coverage, raw-record and access-governance tables already required by the project.

| Table | One row represents | Required responsibility |
| --- | --- | --- |
| `documents` | A source publication record, not necessarily an independent policy | Stable source identity, title, links, role, genre, language and publication/update observations |
| `content_objects` | A logical webpage or attachment | Object identity, kind, source URL, attachment title and acquisition state |
| `document_content_objects` | A document-to-content association | Many-to-many relationships, relation type and source order |
| `content_versions` | A specific saved version of a content object | Retrieval evidence, original file location, content hash, resolved URL and MIME type |
| `text_segments` | A paragraph from a specific content version | Text, sequence, optional heading, original locator and extraction-run reference |

A shared attachment must remain one content object with multiple associations.
Publication, update and retrieval timestamps are distinct and retain timezone
information where supplied. Unknown timestamps must not be filled by substituting
another timestamp. Metadata versions are distinct from saved body/file versions.
Failed or blocked requests do not establish a successful content version.

The segment table may remain empty until substantive text processing is permitted
and performed. Paragraphs must resolve to their exact source-content version.
Future search chunks may be derived without overwriting preserved source text.

## Approved boundaries

The first stage collects and stores records with recoverable provenance. Stable-ID
checks, hashes, duplicate detection, counts, foreign-key checks and rebuild tests
are necessary engineering validation, not research analysis.

Do not create model scores, embeddings, emotion labels, clusters, trees or temporal
analysis outputs in this stage. Do not split further merely to increase the table
count. Reuse existing implementation and add only missing relationships or version
boundaries.

## Relation to the frozen government batch

The frozen batch retains schema `m1_government_batch_v2` and normalisation rules
`govuk_metadata_v3`. This decision does not claim those artefacts have been migrated.
Before implementation, map each approved logical table to the actual existing
schema. Preserve frozen files and stable identities; use a versioned migration or
new working database for necessary structural changes.

This decision approves the storage component of GOV-002. Its analytical questions
remain open: attachment selection, aggregation weights, treatment of duplicate
passages and the final research unit. It does not approve all GOV-002 through
GOV-010 decisions and does not resolve content-use ethics or licensing.

The frozen `schema_decisions.csv` is retained as historical evidence. This dated
record is the subsequent approval; the implementation task should reference it
when preparing a new decision-register version rather than rewriting the snapshot.

## User approval evidence

Dai explicitly agreed to the five-table proposal and asked for English commits
with optional Chinese notes. Dai then clarified that the completed work should be
committed first, before the next task implements the tables. The current request
also authorises including this design record and pushing directly to `main`.

中文摘要：Dai 已批准五张核心表的存储设计；本提交记录决定，不代表迁移已完成。
第一阶段仅采集、保存、追溯和工程校验。附件分析规则及伦理路径仍单独处理。
