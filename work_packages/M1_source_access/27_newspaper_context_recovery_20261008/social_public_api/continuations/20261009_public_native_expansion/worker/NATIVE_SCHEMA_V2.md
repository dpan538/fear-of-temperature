# Native social schema, prospective continuation

This schema extends the independent social SQLite store with additive tables. The first-wave 1,566 persistent IDs and body versions, including the first 50 legacy Q&A IDs, remain unchanged. An inherited body is referenced by its existing version ID rather than copied. Raw bodies and the database remain local.

The fixed publication interval is **1988-01-01 through 2026-09-21**. Creation/publication, native edit/update, retrieval and report times are distinct. A current API response does not establish that a body matches its historical version. Missing or conflicting time evidence is retained; it cannot establish dated coverage. September 2026 remains partial.

| Table | Unit and purpose |
|---|---|
| `acquisition_sources` | Source identity, jurisdiction/frame opportunity and separate access, local-retention, licensing and redistribution evidence |
| `acquisition_interfaces` | Documented endpoint family and adapter; API availability is separate from post licensing |
| `acquisition_frames` | Source-native index, local timeline or actor/community graph frame and its selection rule |
| `native_entities` | Stable typed native identity, source URL, native unit, native creation-time precision and nullable author identity/role/location |
| `entity_versions` | Immutable observed body/metadata/state version; references a core body version when applicable |
| `entity_observations` | Raw-response and acquisition-frame observation of a version |
| `native_edges` | Typed root, reply, quote, repost/reblog, crosspost, link and exact-body-overlap relations; unresolved endpoints stay explicit |
| `native_attachments` | Source-native attachment metadata, URL and availability; binary media is not downloaded |
| `structural_corrections` | Explicit previous and derived values for evidenced structural repairs |
| Existing `posts`, `versions`, `responses`, `observations`, `native_identities` | Stable complete-text core and original raw/body provenance retained from the accepted chain |

`source_id + native_namespace + native_id` identifies an entity. Q&A questions/answers share `post`; comments use `comment`. Discourse posts use `forum_post`, with topic containers using `topic`. Mastodon uses source-instance `status`; Bluesky uses the full `at_uri`, with returned repost events represented separately. Topic snapshots and threads are context containers, not additional authored posts. A preview remains a native post/reply whose **content state** is truncated; it does not acquire a different identity when the full body is returned.

A complete body stores original native HTML or text and a structurally derived text value. The original body hash does not hash a model interpretation. Body IDs preserve the existing source identity/body/edit/revision formula. The extended entity-version digest also distinguishes metadata and structural-state observations. A native update timestamp is not universally an actual textual edit; a Bluesky CID is a version identifier, not a publication date. API `indexedAt` is not substituted for creation time.

Native extensions live in namespaced `native_fields_json`. Source-specific fields retain their original meaning: Discourse topic/post numbers, truncation, hidden/deletion flags and version counter; Q&A content licence, migration/owner/context metadata; Mastodon visibility, language, content warnings, account and status metadata; Bluesky record reply URIs, CID, labels, embeds and native record metadata. Actor country remains unknown without explicit evidence. Public accessibility does not assign an author's discourse role.

The acquisition retains short, repetitive, multilingual, quoted and otherwise noisy native returns without semantic, fear, topic, spam/bot or length classifiers. Media-only/link-only, wrapper, tombstone, hidden, missing-date and index-preview evidence is preserved in entity/version/raw tables. These states do not fabricate complete independent authored text or dated coverage. No unavailable private/deleted body is fetched through a bypass route.

Report separately: HTTP returns, distinct returned native objects, persisted typed entities, body-readable native units, complete independently authored bodies, body/entity versions, distinct authors and context containers. Exact body overlap does not prove common authorship or the same published work; known versions and overlaps remain retained. A source frame or native cursor snapshot is not a representative public sample, population denominator or comparable emotion time series.

The first-wave API/native checks are reused. The new changed-chain check covers identity preservation, typed numeric collisions, idempotent transactions and non-readable states; one terminal check concerns the changed tranche. New operational receipts, controls, frontiers, queues and raw data remain local. Code, source/schema documentation, finalized non-body manifests and the English collection summary can be packaged together by the coordinator.


## Closed source-native extensions and derived date view

Lemmy uses distinct `post` and `comment` namespaces. `lemmy.post`, `lemmy.comment`, `lemmy.creator`, `lemmy.community` and `lemmy.counts` retain their source meaning; a returned comment root uses the post's creator ID. A post name/title with no native body is `native_title_only_text`, retained as original title evidence rather than a complete article/post body. Native local/deleted/removed/bot/language flags are provenance, not semantic exclusion scores.

`post_type` is scoped by native namespace: Stack Exchange's comment parent-type string is distinct from Discourse's numeric regular/action/moderation event enum. The named repair preserves prior versions and logs derived values. `native_aliases` resolves Discourse topic/post-number endpoints. `publication_memberships` uses native original URIs where returned, otherwise typed source identity; exact text equality alone does not merge works. A Bluesky repost view without its native record URI uses an explicit derived event fingerprint, which may change with mutable returned profile metadata; it is not a guaranteed native persistent repost ID and never inflates authored-body coverage.

`entity_quality_annotations` records directness, independent-body evidence and temporal limits without a confidence ranking. `native_date_mapping_limits.csv` records nine named source-era conflicts. `source_month_calendar.csv` separates retained core text by reported native time, title-only evidence, unresolved date counts and usable independent-body dating. The underlying raw/body/creation fields are preserved. Current API dating and later body retrieval remain narrower evidence than a historically verified publication snapshot.

The minimal raw catalog records source, endpoint, retrieval/format, raw and stored hashes/bytes, and mapped or pending state. Unknown source fields remain in original raw responses; normalized extension JSON need not pretend to be a byte-exact payload. Raw-object storage, the transactional catalog and derived analytical views are separate layers. SQLite remains the current collector; the PostgreSQL-versus-SQLite next-stage assessment is included with the closed collection report.
