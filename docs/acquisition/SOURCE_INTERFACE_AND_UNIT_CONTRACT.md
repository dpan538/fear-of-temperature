# Public source interfaces and native content units

Recorded: 8 October 2026. This contract documents the continuing newspaper and newly authorized social acquisition streams. It preserves prior frozen inputs and does not revise the submitted proposal. It is an acquisition/source/schema specification, not a claim that candidate APIs have already returned qualified content.

Updated 9 October: the [coordinated collection review](../../work_packages/M1_source_access/27_newspaper_context_recovery_20261008/review_20261009/README.md) supplies actual API returns, current frame counts and the final manifests. Student titles are now a distinct campus-publication subframe on the social/public-expression side, excluded from newspaper coverage; their native article units and uncertain discourse roles remain. No physical store merge or historical snapshot rewrite occurs.

The subsequent 9 October continuation expands the shared cumulative allocation to **15 GB decimal**, with **2 GB cumulative for the separate social envelope inside it**, under the unchanged physical floor and recovery rules. Two fixed same-owner tasks end at 16:41:51 AEST. The earlier report remains a frozen snapshot; the continuation's implementation and actual returns are reported separately once delivered.

## Public access and source evidence

Use genuinely public, documented, source-verifiable read interfaces. Newspaper acquisition may also use accepted native publisher/archive pages. Private or undocumented interfaces, unknown-origin datasets, login bypass and unavailable approval-only routes are excluded. A documented API requiring an ordinary API key is not inherently a private API; this release nevertheless has no supplied keys/accounts and cannot claim such a route is available.

Record these dimensions independently:

| Dimension | Required evidence or state |
| --- | --- |
| Interface and owner | Primary owner, official documentation or native archive entry, actual requested route and observation time |
| Public accessibility | Anonymous read observed, public but credentials required, blocked, or untested; an advertised capability is not a successful response |
| Collection and retention | Source-specific permitted use, restrictions or exact unresolved condition; public visibility alone does not settle storage conditions |
| Content licensing | License/version and evidence covering the actual body, restricted reuse, no open grant established, or unresolved |
| Redistribution | Full text, metadata/links/aggregates only, conditional or unresolved; collection does not automatically authorize publication |
| Provenance | Native ID, source URL, source/frame, creation date, retrieval time, body/version hashes and identity/date/content mapping status |

An open API, open-source server software and open-content licensing are different properties. The [Open Definition](https://opendefinition.org/od/2.1/en/) requires rights to use, modify and share the work; public visibility alone is insufficient. Dai's operational priority is reachable and verifiable public sources, with rights recorded independently. Do not describe all retained newspaper or public-platform text as an openly licensed corpus. Keep raw/full text local when redistribution is unconfirmed or restricted. An absent open-content grant alone is not a private-source finding or generic collection veto. Preserve concrete collection/retention prohibitions, source-specific unresolved conditions and missing required approvals; assess the actual source condition rather than substitute a blanket licence gate.

## Stream and unit boundary

| Source subtype | Native retained unit | Boundary and limitation |
| --- | --- | --- |
| Newspaper publisher or eligible archive | Complete independently published article | A page, issue PDF, OCR component or model passage is not an article. Reconstruct continuation pages into one article with provenance. |
| Campus publication, including the four reassigned student titles | Complete independently published campus article | Separate social/public-expression-side subframe; not newspaper coverage and not a native forum/platform post. Editorial role and individual author role remain distinct. |
| Public discussion forum | Authored post or reply | A topic is a context container. Its snapshot is not an extra post; preserve root/reply relations and unresolved context. |
| Public question-and-answer community | Question, answer or comment, separately typed | Specialist participation and site/topic scope are explicit; it cannot represent the general population. |
| Public social platform | Native authored post or long-form post | Preserve quotation/repost/context relations. A repost wrapper is not a newly authored independent body. |
| Newspaper-hosted reader discussion | Authored reader comment/reply | Separate social subframe linked to the newspaper article; do not count the article twice. |
| Historical public discussion archive | Verified native message or post | A separate source-era frame; it cannot manufacture pre-foundation coverage for a modern platform. |

Editorial publication belongs to the newspaper/media stream when its title/edition classification supports it. Forums, Q&A and eligible public platform discussion belong to the social carrier frame. Carrier does not determine discourse role: official accounts retain institutional roles, editorial accounts retain media roles, ordinary participants may be public, and uncertain authorship stays unknown. Do not infer emotion-holder or author country from the platform, server, community title, language or a quoted claim.

## Identity, versions and structural governance

Newspapers retain persistent `article_id`, native/source identity, canonical `source_url`, alias URLs and separate known work-family/version relationships. Social records retain persistent `post_id`, `native_post_id`, `source_id`, native type, `source_url`, `thread_id` and `reply_to_post_id`, plus quotation/repost relations where available. Namespace IDs by source and native object type; API pages and body digests do not replace native identity. Body/OCR corrections create versions without changing identity.

Keep creation/publication time, native edit/version time, retrieval time and report/snapshot time separate. Preserve source date precision and conflicts. Store immutable original responses with digests and structurally cleaned bodies with their own digests and transformation notes. A later body is not automatically the historical body. Missing/hidden/deleted replies, truncated bodies, attachments and unresolved date/completeness mappings have explicit states. Do not replace them with invented text or dates.

An exact body overlap is evidence for a duplicate, version or syndication review relation; it is not by itself permission to delete an independently published record. Distinct native IDs are not proof of distinct works. Report native IDs, canonical URLs, known work families, versions and unresolved independence separately. Repeated pages/cursors must not create additional native identities. Use transactions, uniqueness constraints and idempotent restart with version-preserving updates, plus one check of actual changed pipeline behavior and one changed-tranche closeout.

## Calendar, distribution and observed source frame

### Noise-preserving social schema requirements for the continuation

Retain source-verified short, repetitive, quoted, link-only/media-only, multilingual and uncertain-role records where source conditions permit. Noise is an expected property of public expression, not a reason to shrink acquisition to clean, long or emotionally explicit prose. Native or structural flags are separate annotations; no spam/bot/topic/fear classifier governs retention.

Use stable typed native entities, separate immutable body versions and observations, and typed reply/root/quote/repost/crosspost relations with unresolved endpoints preserved. Record attachment metadata without treating missing attachment text as supplied text. A source-native extension object may preserve additional fields, but must not replace the identity/time/provenance core or the field dictionary.

Readable authored bodies, bodyless entities, repost wrappers, context containers, truncated previews, tombstones and date-unresolved evidence have distinct statuses and counts. Retaining all permitted noisy evidence does not authorize counting every returned object as an independent complete post or dated coverage. Exact overlaps are relationships, not automatic deletions. Missing/hidden/private content is not recovered through bypass routes. Migrations are additive and transactional, preserving prior typed native IDs and version history.

Both streams retain the fixed publication interval **1988-01-01 through 2026-09-21**. September 2026 is partial. The newspaper ledger has 465 months plus five disjoint EU/Europe excluding UK, UK, AU, US and NZ strata. Two complete independent articles per claimed month is the lower bound. Retain eligible surplus and continue released native inventories after a month reaches two. Future newspaper writing has no article-count ceiling by month/source/stratum; historical counters remain recorded. Resource/source/discovery/PDF limits and fixed execution releases remain. Flag high-count months against their preceding and following three publication months without blocking retention, requiring periodicity, smoothing or downsampling. Incomplete boundary context stays explicit; a flag does not establish an event or an extraction error.

Newspaper distribution reporting includes month, title/source, concrete country/edition, genre, native article ID, canonical URL, known work family, versions and pending dispositions. Distinguish a genuine high-volume source/period from pagination multiplication, duplicate URLs, mirrored works, attachment splitting or date errors using source/index evidence. Preserve legitimate concentration. A source-opportunity sample or a partially consumed inventory is not a census; unknown population counts do not yield invented sampling probabilities. Equal planned regional effort does not require equal observed counts or justify shifting blocked-stratum opportunities elsewhere.

Social reporting uses source/platform/community-specific existence and recoverable eras. Keep `structurally_inapplicable`, `observed_text`, `applicable_unobserved`, `access_blocked` and `historical_scope_unknown` distinct. Earliest recovered content is not platform founding or proof of a complete historical archive. Global specialist communities remain a separate frame when regional attribution is unsupported. Unknown author location stays unknown, even in a regional community. Modern platform adoption is not an automatic historical cutoff or sampling weight.

Coverage, density and source-frame completeness are separate findings. Neither stream uses climate/fear words, emotion labels, length preference, entropy/HHI targets or a uniformity score as a current inclusion/cleaning gate. Current ELT is Extract, coarse structural cleanup, immediate durable Load; later consolidated transformation and validated topic/affect analysis remain separate.

## Official API capability evidence and unresolved access

The following documentation was consulted on 8 October. It is not a substituted record of live content collection; the social task must publish its actual API-return evidence and saved/Loaded native records separately.

| Family | Documented capability or limitation | Acquisition implication |
| --- | --- | --- |
| Stack Exchange | [Questions](https://api.stackexchange.com/docs/questions) support dated pagination; [filters](https://api.stackexchange.com/docs/filters) select additional body fields; [throttles](https://api.stackexchange.com/docs/throttle) require quota/backoff handling. [Public contributions](https://stackoverflow.com/help/licensing) use CC BY-SA, with applicable versions tied to contribution/revision dates. | Feasible candidate for a specialist Q&A subframe; request and verify whole bodies, licensing and context. No general-public or regional-representativeness claim. |
| Discourse forums | [Official API documentation](https://docs.discourse.org/) describes the software interface; anonymous routes depend on each site's settings and rules. [Discourse Meta terms](https://meta.discourse.org/tos) prohibit non-browser automation except the named search-indexing exception. | Assess actual forums individually. Do not collect Meta merely because its software can return JSON. Software capability is not a site-level permission. |
| Mastodon | [Public timeline documentation](https://docs.joinmastodon.org/methods/timelines/) specifies public statuses, cursor parameters and instance-dependent authentication/visibility restrictions. | Verify permitted instances and actual responses. A timeline's visible history and an instance location are not whole-network or national coverage. |
| Bluesky | [Public HTTP API documentation](https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed) describes unauthenticated AppView GET routes. | Assess dated eligible records and native URI/CID/context fields. API accessibility does not prove historical completeness or an open license for every post. |
| Reddit | [Researchers programme](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program) requires institutional application/ethical-review evidence and restricts sharing. | No approved access exists here. Registry/access limitation only; do not substitute undocumented/private routes or an unknown-origin copy. |

## Durable operation and publication

### Approved incremental data-pool direction

The 9 October continuations are closed. Their [accepted result and next-round design](../../work_packages/M1_source_access/27_newspaper_context_recovery_20261008/review_20261009_closeout/README.md) specify raw objects, a recoverable ingestion journal, typed catalog and reproducible analytical snapshots. The proposed eight-hour round and expanded social envelope are planning only; Dai explicitly requests no collector-window instructions during review. No new source acquisition or database migration follows automatically from this contract.

On 9 October Dai approved a lightweight data-pool direction for social media and future personal-voice material, with the larger architecture/database upgrade deferred to the next stage. The current social owner should assess its real ingestion/schema needs and make necessary additive improvements within the existing release, without delaying continuous collection for another pilot, deploying a database server or copying the historical corpus. An adequate existing implementation can be retained unchanged with an evidenced assessment.

The intended separation is immutable source payloads, a transactional provenance/entity catalog, and reproducible derived analytical views. Each raw object needs a source/request locator, retrieval time, media type, checksum and storage reference; preserve publication/edit times and their precision where available, native identity when available, access/retention evidence, parser/schema version and processing state. Unknown fields and parse failures remain explicit rather than receiving invented values. Persist permitted raw evidence before dependent parsing, with recoverable catalog registration and idempotent retry; raw persistence does not establish a completed entity Load or qualified coverage. Original bytes remain recoverable independently of normalized JSON/text. Shared storage conventions do not merge source frames or native units.

SQLite remains the present per-stream transactional store. Assess any future PostgreSQL/MySQL catalog migration using observed writer contention, transaction/recovery behavior, remote-client requirements, metadata queries and operational maintenance needs. Do not infer an immediate migration requirement from raw-data volume alone. Source-native extension fields complement typed identity/time/relationship fields. Future catalog deployment must preserve stable IDs, versions and raw-object references, and demonstrate a recoverable cutover; raw-object storage and analytical tables have a separate lifecycle. Personal voice denotes a future research/source-frame requirement, not automatic author-role attribution or permission to acquire private records or audio.

Each stream has its own store, lifetime writer mutex, source frame and manifests. Social cannot write or inspect the newspaper store. Both serialize heavy operations under the existing shared lock and re-read active leases and cumulative capacity per operation. The current shared **15,000,000,000-byte** allocation includes both streams, previous media packages and operational metadata; the separate social envelope has **2,000,000,000 cumulative bytes within it**. This prospectively supersedes the prior 5 GB allowance without resetting accounting. Preserve the **15 GiB** physical floor, **48 MiB** recovery allowance and complete pending-operation footprint accounting; the initial 8 MiB reservation is overridden by a larger actual transfer/journal/body/export footprint. Actual free space determines usable headroom independently of the allocation.

The social directory is located within an already-accounted package envelope solely to preserve exact live budget accounting. Its identity, content and coverage remain independent. No duplicate store, full raw copy or simultaneous writer is introduced by the directory layout.

Publish acquisition implementation, source/schema documentation, finalized consolidated tables/manifests and English summaries on main. Keep raw bodies, stores, per-object runtime receipts, live queues, dispatch/lease controls, PLAN and HANDOFF files local. Required decisions accompany the English project log and collection summary. Preserve frozen originals and historical stops; do not rewrite or delete evidence to improve a score or suppress a Git/UI warning.
