# Article / issue identity rules — v2

Schema `media_schema_v2`, SQLite `PRAGMA user_version=2`; collector `media_route_pilot_v2_edition_scope_20261005`; parent rule `source_edition_native_v2`.

No provider-global native-ID scope has been established. Therefore identity uses a declared **source + edition + native identity key**. Source country/market anchors do not prove an item's edition; the current `edition:<source_id>` records remain provisional. `parse_article` parses metadata only and does not assign an edition. `parse_frame` requires an explicitly declared edition, and the builder checks it against the frozen source/edition mapping. A different verified edition requires a different parent identity, with a traceable old/new mapping if a provisional identity was ever used. Do not silently change the edition of an existing stable parent.

## Exact key and hash

`native_identity_key(url, native=None, issue_native=None)` produces compact UTF-8 JSON, `ensure_ascii=False`, separators `(',', ':')`:

| Evidence | native_id stored in article_parent | native_id_basis |
|---|---|---|
| Verified provider article ID, edition scope | `["native_article","<original ID>"]` | `provider_article_ID_with_declared_edition` |
| Article ID resets per paper issue | `["issue_article","<original issue ID>","<original article ID>"]` | `provider_issue_article_IDs_with_declared_edition` |
| Native ID unavailable | `["canonical_url","<canonical URL>"]` | `canonical_URL_fallback_with_declared_edition` |

The typed JSON keeps original native components inspectable and prevents issue keys from colliding with ordinary article IDs or URL fallback keys. Do not pass an already encoded native_id as the `native` argument; `parent_from_identity_key` consumes an already normalized key.

The parent hash input is compact JSON `["source_edition_native_v2", source_id, edition_id, native_id]`, encoded UTF-8. `parent_id = "article:v2:" + SHA256(input)[:32]`. No publication/updated/retrieved date or article text enters the ID. A native ID continues to identify the same edition-scoped article when its URL updates. Different editions with the same native ID remain distinct. With URL fallback, changed URL identity remains pending until independently mapped; text similarity is not an ID proof.

Database constraints are `UNIQUE(source_id, edition_id, native_id)` and a composite FK `(source_id, edition_id) -> edition(source_id, edition_id)`, backed by `UNIQUE(source_id, edition_id)` on edition. A same-edition duplicate is rejected; another edition may reuse the native ID; source/edition mismatches are rejected on insert/update. SQLite enforces consistency of supplied keys, not their real-world verification or the helper hash.

## Paper issue / article / page / OCR

`native_issue(source, edition, issue_native)` hashes compact JSON `["source_edition_issue_v2", source_id, edition_id, original_issue_ID]` with the same UTF-8/SHA256[:32] convention and prefix `issue:v2:`. An issue date alone is insufficient when morning/evening/market or multiple issue variants may exist; absent provider issue identity, retain an unresolved locator instead of inventing an issue.

For issue-local article IDs, retain both original issue and article IDs in the JSON native_id above. The parent ID is therefore scoped to source + edition + issue-native + article-native. `paper_issue` holds edition, issue ID/date/volume/number; `article_locator` joins that issue to the independent article parent and records page labels, OCR ID/bounding boxes, layout and boundary evidence. Its insert/update triggers reject an issue from a different edition; FK checks reject missing parents/issues. Parent and issue identity reassignment must use new identities and an explicit mapping, not direct edition updates.

A whole page, issue, OCR block, attachment or continuing page never automatically becomes another article parent. Verified continuation within the same article remains one parent with multiple locators/versions. Same-ID reuse across issues is distinct when IDs are issue-local; provider-global scope must be evidenced before treating it otherwise. Licensed XML article segmentation, print page layout and source article IDs require a boundary/mapping check under the actual rights frame. The original three pilot months and fixed endpoint remain unchanged.

## Version transition and limits

V1 schema/prototype/tests/validation and reports are copied byte-for-byte to `versions/v1/`; SNAPSHOT_RECEIPT.json maps their original logical paths and original acquisition evidence. V1 historical report links originally pointed at root paths, so use the snapshot path mapping when retrieving v1 derived files. The original raw/request/HTTP stop files remain once in their original root locations and are hash-checked against v1.

There are **zero real article parents/versions/issues/OCR locators**. No real parent migration, edition correspondence, OCR boundary or native-ID relation was validated by acquisition. Updated JSON examples and tests are synthetic and excluded from actual slots. The original 150 slots, unknown denominators/pi, all access stops, 212-byte raw and legacy Guardian396/4 scope remain unchanged. No new HTTP requests, account/contact/secret operations or editor sources are introduced.
