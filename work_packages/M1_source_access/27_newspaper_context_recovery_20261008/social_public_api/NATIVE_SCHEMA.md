# Native social schema and field dictionary

`code/schema.sql` defines one local SQLite store. The publication manifest is one row per retained body version; distinct authored posts are counted by `posts.persistent_post_id`, never by manifest rows, API pages, topic containers, raw responses, aliases or revisions. Body text and native response objects stay local. `summaries/native_posts_manifest.csv` publishes identifiers, dates, rights, context states and digests only.

| Field/table | Meaning and constraints |
| --- | --- |
| `posts.persistent_post_id` | Stable source/native-namespace/native-ID identity. Early 50 legacy IDs remain valid via the explicit native mapping. A body or URL correction does not renumber a post. |
| `source_id`, `native_post_id`, `native_unit` | Acquisition parent, original source ID and native authored type. Stack Exchange questions/answers share `post`; comments have their independent `comment` namespace. Forum roots/replies share their native forum-post namespace. Mastodon uses `status`; Bluesky uses an AT URI. |
| `native_identities` | Unique `(source_id,native_namespace,native_post_id)` mapping to a stable post ID. Deprecated adapter aliases are preserved with an explicit basis and excluded from native-object counts. |
| `source_url`, `post_urls` | First canonical source URL plus subsequently observed canonical/alias evidence. API-returned links are preferred; the early comment's derived native-post anchor is preserved and the later returned URL recorded as an alias. |
| `thread_id` | Native root/thread container at first Load. A forum topic or question root is context, not another independent post. `unresolved` is explicit rather than an invented root. |
| `reply_to_post_id` | Native parent ID when returned/verified. A Discourse reply-to **post number** is converted to an ID only through a same-topic mapping. An unmapped number remains native sidecar evidence. |
| `parent_context.parent_namespace` | Distinguishes comment parents that are answers from those that are questions, and forum/status/AT-URI parents. |
| `parent_context.root_thread_id` | Derived current context root. An answer's `post_id` is never assumed to be a question ID. Resolution requires native `question_id` metadata or an explicit source root URI. |
| `context_status` | Partial thread, unmapped reply number, unresolved answer/question root or mapped parent with incomplete surrounding discussion. Mapping a parent does not establish complete replies. |
| `native_created_at` | Original source creation timestamp, UTC ISO format as returned or losslessly converted from native seconds. It controls fixed-interval eligibility. |
| `native_edited_at` | Source edit timestamp where supplied; Discourse's native `updated_at` is retained here with its source-field meaning. It is an update timestamp, not a universally certified content-edit time. Absence is not replaced with creation/retrieval time. |
| `native_revision` | Source revision/version number or Bluesky CID. A CID is a version identifier, not an edit timestamp. |
| `first_retrieved_at`, `observations.retrieved_at` | First version retrieval and subsequent saved-response observations. They do not certify that a body was unchanged since publication. |
| `author_id`, `author_role`, `author_country` | Original author identifier; public/institutional/editorial/unknown role vocabulary. Roles remain unknown except the explicitly official Bluesky account. Country remains NULL/unknown throughout. Community, host and language do not assign it. |
| `versions.body_version_id` | Hash of stable post identity, native-body hash, native update/edit timestamp and revision. Identical reruns are idempotent; changed body/revision retains the earlier version. |
| `body_original` | Complete returned native HTML/cooked body or platform plain text. It is a present-day source version; attachments/embedded media are not fetched. |
| `body_text` | Coarse HTML text extraction with block boundaries and entity decoding, or newline-normalized plain platform text. It does not remove topics, emotions, quotation passages or short neutral posts. |
| `body_sha256`, manifest `cleaned_body_sha256` | Separate original-native-body and derived-cleaned-text digests. The manifest records the cleaned digest without copying full text. |
| `native_fields_json` | Returned non-body metadata needed for attribution, revision, dates, quotation/embed indicators and context. Duplicate full body/raw fields are omitted here; the original response remains recoverable separately. |
| `content_license`, `license_basis` | Native returned exact CC BY-SA version, source-wide restricted grant or explicit unknown/no-open-grant state. Original creation year is not used to invent the current revision's licence. |
| `completeness`, `provenance` | Complete returned native text, with media/context limits; direct/original evidence of the recorded author's utterance. Provenance verification does not establish claim truth or an emotion-holder. |
| `responses`, `observations` | Saved-response identity/URL/retrieval/raw digests and post-version-to-response linkage. A response is transport/provenance, not an independent authored observation. |
| `raw_reference`, `raw_sha256`, `stored_sha256` | Local gzip object path, original transferred entity bytes and stored gzip-byte hashes. Some sources use an inner compressed HTTP entity; decoding preserves both levels. |

Thread snapshots can contain complete native posts and still omit later pages, hidden/deleted replies or older revisions. Discourse index `truncated` flags are structural limits: previews do not enter `posts`; full topic-returned bodies can. Reposts, nonpublic statuses and posts without readable native text are not substituted for new authored texts. Source-returned records beyond 21 September remain outside the qualified store, with the original response and exclusion receipt preserved.

The source-era ledger has 465 rows per candidate parent. Source inception, conservative platform start bounds, historical-scope uncertainty and access status are separate columns. Known pre-source/platform months are structurally inapplicable, not zero public expression. An applicable unobserved month is a collection gap, not an assertion that nobody posted. A platform-level start does not establish an instance's start or archive completeness. Source-family pooled counts do not establish a comparable three-role time series or fear prevalence.
