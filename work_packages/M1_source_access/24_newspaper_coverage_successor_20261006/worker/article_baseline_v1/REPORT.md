# Local complete-article baseline reconciliation

The hard monthly lower bound is **two complete, distinct original publication articles**, with every additional qualified article retained. This local register confirms **142 articles** from the fixed selected evidence. **43/465 pooled months meet the article-count minimum**; 33 months have one and 389 have none confirmed in this bounded register. This does not establish full-period collection or absence of newspaper discourse in gaps.

| Ledger | 0 confirmed | 1: below minimum | 2+: meets minimum | Confirmed distinct article total |
| --- | ---: | ---: | ---: | ---: |
| pooled | 389 | 33 | 43 | 142 |
| EU/Europe excluding UK | 457 | 8 | 0 | 8 |
| UK | 458 | 7 | 0 | 7 |
| AU | 444 | 21 | 0 | 21 |
| US | 416 | 12 | 37 | 100 |
| NZ | 459 | 6 | 0 | 6 |

All six ledgers use January 1988–September 2026, publication cutoff **2026-09-21**. September is partial. Pooled passing months do not establish regional completeness. These counts measure the inspected evidence, not all articles already saved in the earlier corpus: only at most three previously selected candidate parents per each of 51 observed prior months were inspected, without refill. No new network, raw download or source discovery was performed.

## Unit correction and frozen evidence

The frozen tranche reported 45 readable HTML units and 3 mapped readable article spans (48 readable units), and 86 combined readable months. Those historical figures remain unchanged. Readable pages, tables, article spans and issue containers were not retrospectively renamed complete articles. This correction confirms 41 complete successor articles and 101 complete selected prior articles. Four additional successor rows preserve missing-content/out-of-interval context; they are not extra released acquisition candidates.

The register has 185 candidate rows: {'pending': 17, 'non_article': 26, 'confirmed_complete': 142}. `article_id` persists the observed publisher item identity; pending/non-article rows explicitly do not assert article status. Confirmed rows carry complete-body reference, title, source/edition, publication date, actual source link, and boundary/opening/ending evidence. Identity-map keys use canonical publication identities or accepted native print locators, never body hashes/retrieval times. Body `version_id`/hashes are separate. Actual PDF links have page/column sidecar locators; old invented fragment aliases are retained as history and never presented as publisher article permalinks.

The April 2008 Tech Table is a table-only component. Event schedules, fact/contact sidebars, empty activity content and unrelated notices cannot supply complete article counts. The August 2007 single roadworks brief and April 2007 single signed outage report qualify despite generic container headings; shortness/byline absence is not an exclusion. Multiple section headings in the 2008 pastry-debate report belong to one coherent article. The 2007 December multi-article News Briefs and 2025/2026 separately signed editorial collections remain pending item mapping and are not split to manufacture a second article. Incident-log unit interpretation also remains pending rather than being decided by genre alone.

## Corrected bodies and named limits

6 new whole-item derivatives and sidecars preserve the old bodies and scans. Three mapped PDF bodies have their generated `[CONTIGUOUS ARTICLE SEGMENT]` markers removed; printed page-turn/continuation cues and geometric offsets move to sidecars. The 1991 first-page missing department line is restored from the retained scan. Each named article has one derivative, not one article per column. Remaining noisy OCR and column-join fidelity are explicitly pending; removing markers does not certify a complete clean transcription. The 1988 accepted article-span record is preserved by reference with its severe transcription limits pending. No universal correctness claim is made.

Where the Mancunion's unique native standfirst was demonstrably absent from its selected body, it is restored before that same article's prose; standfirst text already inside the body is not duplicated. The selected July 2020 InDaily comment-submission footer is removed after the author biography in a new derivative. Source/body paths and hashes trace every correction.

The Barclay update explicitly says April 20, 2007 in its body but has an October 6 header/URL. Its cross-month publication/content-version conflict remains pending and cannot certify October coverage. Otago's frozen archive evidence has same-month day differences where recorded; supported monthly identity is retained while exact-day mapping remains unresolved. Current archive renditions do not prove historical body equivalence, and quotation does not assign an emotion to the newspaper or verify every quoted claim. Known exact saved-body/canonical relations are recorded separately; distinct publisher articles on the same event are not automatically duplicates. No impossible global proof of journalistic novelty is required.

## Delivery and frontier

- `ARTICLE_REGISTER.jsonl`: article/item identities, dispositions, source links and evidence; `ARTICLE_REGISTER.csv` provides a compact review view.
- `IDENTITY_MAP.json`: persisted identity map invariant under body correction and versions.
- `CORRECTIONS_MANIFEST.json`, `bodies/`, `sidecars/`: corrected whole-item bodies with provenance and geometry.
- `ledgers/`: pooled and five geographic 465-row ledgers; exact counts retain surplus and apply `count >= 2`.
- `PENDING_FRONTIER.csv`: 17 named unresolved candidates, including the out-of-interval reference; no inference that other unsampled saved articles are absent.
- `INSPECTION_RECEIPT.json`, `BODY_BOUNDARY_QA.json`, `VERIFICATION.json`, `RESOURCE_RECEIPT.json`: bounded-selection, source-paragraph presence, frozen-input and resource checks. Every confirmed HTML article has one inspected native content container and all its native narrative paragraphs present in the saved/corrected body, with the documented publisher-footer removal treated separately. This supports completeness within the observed source rendition, not universal historical equivalence.

Every 0/1 cell remains below the minimum. Further article acquisition, OCR restoration, native aggregate-item mapping or date adjudication needs a separately bounded successor release; this local correction does not reopen requests or acquire a second article. All frozen input checks pass. Formal databases, government/social corpora, sealed evaluators, shared logs and Git were untouched. No climate/fear labels or semantic/length exclusions were executed. The original deadline is 2026-10-06T09:25:49.479281+00:00 and remains unchanged.
