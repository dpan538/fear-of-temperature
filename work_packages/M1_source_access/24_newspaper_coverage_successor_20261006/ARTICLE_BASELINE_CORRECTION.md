# Local article-baseline correction

The acquisition tranche is closed; its reports and receipts are frozen. Dai's latest clarification requires **at least two complete independent newspaper articles per monthly point**, with more retained. Every article has a unique persistent `article_id` and traceable `source_url`. See the [current governing decision](../../../docs/decisions/2026-10-06-two-article-minimum-and-stable-identifiers.md) and `control/ARTICLE_BASELINE_SCOPE_v2.json`; the earlier quantity interpretation and scope remain historical records.

The expressions "45 HTML units" and "3 mapped articles" describe different evidence:

- The 45 are readable webpage units. Their article identity/completeness must be established before article counting.
- The three PDF mappings identify three original titled articles, including continuations. Their several page/column spans must produce one body per original article. They are not arbitrary model chunks, and spans must never inflate article totals.

Named issues already observed:

1. `https://thetech.com/2008/04/01/ua-v128-n15` is titled `Table`, has one table and a 292-character body listing candidates. It cannot satisfy a full-article monthly baseline. Retain it as non-article/component evidence.
2. At least one mapped derivative includes `[CONTIGUOUS ARTICLE SEGMENT]` in the body. That generated marker belongs in technical metadata, not original article text. A new corrected derivative must preserve the old version and reference the original article/scan.
3. Mapped article body completeness and original-story independence have different meanings. Verify the article's original boundaries/continuation and known duplicate relations; do not hold all newspaper articles pending an impossible global proof of journalistic originality.

The existing owner receives a **30-minute local follow-through**, with no network allowance, new raw collection, changed frozen files or cumulative-budget increase. Write only `worker/article_baseline_v1/`. Use the accepted baseline references and current tranche metadata. Assess the 45 readable HTML candidates and three mappings, and select at most three earlier candidates per already observed baseline month from metadata to establish one or two complete articles where possible. Inspect only the selected named raw/body evidence; reuse unchanged hashes. If two complete articles cannot be established within those bounded checks, leave the target pending and record the frontier.

Deliver an English article register with mandatory unique persistent `article_id` and real `source_url`, complete/pending/non-article/duplicate dispositions, specific body/date/boundary evidence, canonical article/work-family IDs where supported, and pooled plus geographic 465-month ledgers with 0, 1 or 2-or-more confirmed distinct articles. Record uncertain/transcription-limited cases rather than relabelling readable units as complete articles. A month with zero or one confirmed complete article is below the minimum. Two or more meets this article-count criterion; it does not certify archive or geographic completeness.

Keep raw scans and original derivatives. Correct only named generated markers or demonstrated body-boundary errors, storing one restored body per original article and sidecar coordinates. No sentence/paragraph/model chunking and no joining unrelated source items. Reuse existing renders; avoid new large images or whole-corpus re-extraction. Use the existing shared lock and local-only staging boundary, current cumulative allocation and 15 GiB physical floor. No formal database, government, social, private evaluator, shared-log or Git access by the worker.
