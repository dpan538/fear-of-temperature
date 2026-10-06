# Two-article minimum and persistent article identifiers

Date: 6 October 2026. Authority: Dai explicitly requires **two articles as the lower bound for every time period**, permits more, and requires a unique ID plus link for every article.

This supersedes the earlier quantity interpretation of one required article and two as a target. All complete-article, fixed-calendar, provenance, no-chunking and raw-preservation rules remain. Frozen collection/readable-unit reports and the earlier scope are retained as historical evidence rather than rewritten.

## Current coverage criterion

Use the existing 465 monthly bins from January 1988 to September 2026, with the fixed publication cutoff of **2026-09-21**. A claimed monthly newspaper point meets the baseline only when it has **at least two confirmed complete, distinct original publication articles**. Zero or one is below the minimum and remains an incomplete coverage cell. Two is a lower bound, not a cap: preserve and report every additional qualified article.

Maintain pooled and five disjoint geographic ledgers separately. A pooled passing month does not establish that each region passes. Known same-article copies, mirrors, body versions or fragments cannot supply the second article. Distinct articles may discuss the same event; no topic/emotion/length filter or equal observed-volume requirement is added.

## Mandatory article identity and links

Every article register row has at least:

- `article_id`: unique, persistent identity of the original publication article.
- `source_url`: actual traceable source link.
- `title`, `source_id`/edition and supported `publication_date`.
- Complete body reference, article boundary/completeness evidence and relevant duplicate/version/work-family relations.

Prefer the publisher's native article identifier with source/edition namespace; otherwise persist a mapping from the observed canonical publication identity. Article IDs do not change merely because retrieval time, OCR, corrected body text or content version changes. Keep `version_id` and body hashes separately. Do not generate identities solely from text hashes, or assign a new article identity for a corrected derivative.

Retain the publisher's real article-specific permalink where available, along with observed canonical URL and redirect aliases. For scanned articles without native article permalinks, record the real publisher/PDF URL, page/column/continuation locator and the uniquely identified restored article body. Do not invent a publisher permalink or use fabricated fragment strings to imply one. Shared issue containers are not evidence that several extracted spans are independent articles; their original boundaries and unique article identities must establish that relationship.

Check uniqueness of article IDs, nonempty valid source-link fields, traceability to saved source receipts, article-versus-version identity and known same-article relations. A field's existence alone does not prove complete article content. Counts must be computed from confirmed article identities, not raw URL, HTML, page, segment or version totals.

## Implementation boundary

Steer the already active local correction through `ARTICLE_BASELINE_SCOPE_v2.json`, preserving its original deadline, write root, existing allocation and zero-network limit. Its new ledger must report 0/1/2-or-more confirmed distinct articles and apply the hard `count >= 2` criterion. If the existing evidence supplies only one or none, report the deficit rather than relabel it as success or create a second article by splitting.

Future bounded acquisition frontiers prioritise the deficit to two confirmed articles in a source/time frame while retaining surplus and visible geographical gaps. This rule alone does not reopen stopped requests, enlarge the allocation or start a new collector. Main integration and new outer records remain English.
