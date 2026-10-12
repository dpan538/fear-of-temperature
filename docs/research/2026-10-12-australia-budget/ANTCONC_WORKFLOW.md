# AntConc before embeddings: Australian analysis preparation

Assessment date: 12 October 2026. Documentation review only; no installation, application execution, corpus export, model download, empirical annotation or external submission was performed.

AntConc is suitable for a small, traceable lexical exploration and close-reading stage before committing to passage and vector production. It does not settle Australian source eligibility, comparable time coverage, climate relevance or fear attribution. The project's [Australia amendment](../../decisions/2026-10-12-australia-analysis-scope.md) and [current direction](../../PROJECT_DIRECTION.md) govern the empirical frame; NLP/model analysis and the prototype remain planned.

## Verified current capabilities

The official download page lists **4.4.2 (2026)** for Windows, Apple Silicon macOS and Linux. UTF-8 is the default file encoding. [Official page](https://www.laurenceanthony.net/software/antconc/).

The current help documents:

| Area | Capability |
|---|---|
| Storage and inputs | SQLite corpora/results; TXT/SRT/SUB, CSV/TSV, HTML/XHTML/XML, DOC/DOCX, PDF and EPUB inputs. |
| Corpus Manager | Named database building, target/reference assignment, metadata tables joined by document keys, token settings and file/row units. |
| Concordance | KWIC sorting, regex, paging/random subsets and full-text File View. |
| Lexical patterns | Clusters, n-grams, collocates with adjustable left/right span, frequency/range and association statistics (e.g. Log-Likelihood, MI, LogDice). |
| Comparison | Word lists; target/reference keyword frequencies/ranges, normalized columns, likelihood/effect statistics (e.g. Chi-Squared, Log-Likelihood, LogRatio); configurable normalization multiplier. Negative keywords mean relative underrepresentation. |

[Official 4.4.2 help, pp. 3–20, 27–36](https://www.laurenceanthony.net/software/antconc/releases/AntConc442/docs/help.pdf).

The release history records metadata/subcorpus improvements, Full Regex, AI-assisted searches, ChatAI, local-model management and media/transcription features. These additions are optional; classic lexical inspection requires no embedding pipeline. [Official version history](https://www.laurenceanthony.net/software/antconc/releases/AntConc442/docs/version_history.pdf).

The license permits free non-commercial academic research with an individual authorized user; commercial use has separate terms. This software license does not license the corpus texts. [Official license](https://www.laurenceanthony.net/software/antconc/releases/AntConc442/docs/license.pdf).

## Proposed bounded workflow

This is a design recommendation, not an active corpus run or a new acquisition scope.

1. Select an actually observed Australian source/time window from finalized metadata. A manageable first diagnostic subset could contain **500–1,500 whole native texts**, across a few evidenced sources and one observed year or two comparable six-month periods. These are planning assumptions, not source quotas or a statistically representative sample. Keep newspaper articles, public/community bodies and government originals separate. Include routine and low-emotion material. Retain the fixed 1988-01-01–2026-09-21 outer interval and partial September boundary; do not promise a three-role comparison before government evidence supports it.
2. Derive UTF-8 text copies only after named structural checks. Prefer one original article/post/report per file, with stable original ID in its filename. Keep a sidecar manifest linking AntConc document keys to original ID, URL, publication date/precision, retrieval date, source/genre, version hash and source-selection reason. Check the import join on a few records. Keep metadata outside the text counted as vocabulary. Imported PDF/HTML conversion is not proof that extraction or dates are correct.
3. Inspect vocabulary and repeated strings for extraction artefacts, quotation blocks and version multiplication. Record proposed structural corrections in a derived view; preserve originals and legitimate volume peaks. This stage does not exclude records by topic or emotion.
4. At the later relevance stage, develop a transparent climate/warming query list and inspect retrieved **and non-retrieved** material. Lexical concordances can help refine ambiguous terms and supply traceable passages, but recall and precision need independent manual evaluation. Proposed first review: 100–200 concordance hits plus a separately drawn non-hit sample, expanding when ambiguity warrants it. This number is a workload assumption, not a validation standard.
5. Compare declared source/time subsets with identical tokenization and processing. Report raw counts, text counts, token denominators and source composition alongside rates. A proposed reporting unit is occurrences per million tokens: `count / eligible_tokens × 1,000,000`. Normalization cannot correct different genres, archive gaps, duplicate versions or source concentration. Use keyword and collocate results to nominate passages for reading; document span, minimum frequency/range, statistic, threshold and reference selection. A general-English reference answers a different question from an Australian within-source/time reference.
6. Preserve an evidence table and analysis recipe: original ID/date/URL, passage offsets, query, corpus/version manifest, settings and researcher judgement. Inspect speaker/holder, target, quotation, negation and future-harm horizon before fear interpretation. Broad negativity, risk language, lexical keyness and co-occurrence do not establish fear, emotional prevalence or causal influence. If a fear measure is unsupported, keep useful topic/association analysis available.

## Capacity and effort boundaries

The reviewed official documents provide **no tested RAM requirement or maximum corpus GB**. Full Regex bypasses the fast index path and is costly on very large corpora. A legacy database upgrade requires at least **1.5× its database size in additional free space** and retains a backup. [Official help, pp. 25, 31](https://www.laurenceanthony.net/software/antconc/releases/AntConc442/docs/help.pdf). That upgrade condition is not a general fresh-build capacity formula.

Treat **50 GB preferred / 100 GB alternative** as proposed total storage envelopes, not AntConc capacity claims or RAM allocations. Measure export copies, corpus databases/indexes, saved results, backups and operation peaks on the bounded subset before extrapolation. Preserve existing raw and frozen material; historical cumulative acquisition accounting and current physical occupancy are distinct. This note changes no acquisition allocation or retention rule.

For later embeddings, the [existing helper assessment](../2026-10-12-australia-scope/CCF_COMPUTING_REFERENCE.md) records an encoder returning an entire float32 matrix rather than streamed output. AntConc cannot remove that separate engineering requirement. Measure passage counts and token lengths by native form, then design resumable bounded input/output before a bulk vector run. Do not transfer a Canadian article-to-passage multiplier to Australian posts or reports.

The help documents cloud and local AI services. For this workflow, leave AI features unused; their presence is not authorization to send corpus text or KWIC passages to external services. Any later service choice needs a separate permitted data-flow decision. [Official help, pp. 23–24, 27](https://www.laurenceanthony.net/software/antconc/releases/AntConc442/docs/help.pdf).

**Planning assumption:** allow roughly **8–20 researcher hours over 2–4 working days** for the first subset's export/lineage checks, settings, query development, close reading and recorded recipe, assuming usable source/date metadata. This is not measured AntConc runtime, a delivery promise or the full annotation/embedding/analysis effort. A benchmark should separately record import time, query latency, peak memory and disk growth; increase scope only after those measurements and the scientific comparison design support it.
