# CCF reference for Australian analysis workload

The supervisor-recommended [Canadian Climate Framing deposit](https://zenodo.org/records/22019204) supports planning for text splitting and vector storage. Its empirical coverage is Canada. The Australian thesis uses it as an external methods and engineering reference, preserving the source boundary confirmed by Dai.

## Published scale

The supplied version 2.0.2 describes 283,964 climate articles from 22 Canadian news outlets, 9,908,776 two-sentence analytical units, and 10,192,740 BGE-M3 embeddings. The database archive is 43.2 GB. Full article text is not redistributed. The record links a newer version 2.1.0 whose release notes retain the same corpus counts and change documentation. Keep the supplied DOI in the recommendation record rather than silently replacing it. [Supplied deposit](https://zenodo.org/records/22019204), [newer version](https://zenodo.org/records/22019287).

The [authors' repository](https://github.com/ccf-organization/CCF-canadian-climate-framing) describes two-sentence sliding windows, 1024-dimensional float16 vectors and title embeddings alongside analytical-unit embeddings. It reports sentence-embedding ingestion as the dominant cost on its Mac Studio setup. Its data release contains metadata, annotations and vectors; its current README states CC-BY 4.0 for the deposit. The paper remains under revision. These descriptions are a resource reference, not an Australian validation or a compute-time benchmark on Dai's hardware.

## Storage arithmetic

The published counts imply approximately **34.9 analytical units per article**. Adding one title vector per article reconciles the embedding total: 9,908,776 + 283,964 = 10,192,740. This demonstrates that source-record counts can substantially understate processing units.

For a dense vector array, payload bytes equal vector count × dimensions × bytes per value. One million 1024-dimensional vectors require 4.096 GB as float32 or 2.048 GB as float16. At the reported CCF vector count, float16 values alone occupy approximately 20.87 GB. These are decimal payload sizes, excluding IDs, offsets, row/array headers, metadata, index structures, model memory, temporary outputs and backups. Archive size does not establish restored storage or peak memory. The reproducible arithmetic is in [CCF_SCALING_ARITHMETIC.json](CCF_SCALING_ARITHMETIC.json).

The 34.9 multiplier must not be transferred to the Australian corpus as an expected average. Articles, short posts and government reports have different length distributions. The Australian candidate counts are not all climate-related; the CCF corpus is already topic-selected. No processing duration or final Australian passage count follows from this comparison.

## Preparation for the Australian computation stage

First select the source/time frame required for RQ1 and RQ2 and resolve its named structural issues. At the analysis stage, test retrieval and passage construction on a bounded, source-aware sample. Measure tokens, windows per document, length percentiles, runtime, peak memory and written bytes by native text form. Include complete long documents in the benchmark so unusually long originals remain visible. Preserve article/post identity, original passage offsets, date and version mappings.

Choose window size and overlap according to context preservation and validated interpretation, then measure their cost. Test a candidate embedding model against the research task before choosing its dimensions or precision. Use source-specific workload estimates and state both typical and long-text cases; retain uncertainty rather than multiplying record counts by a foreign corpus average.

Process input incrementally and save resumable shards with a manifest. Bind each saved result to the original text/version hash, passage parameters and model revision so unchanged work can be reused. Batch size controls inference batches; bounded input iteration and incremental output are separate requirements. Create a search index only when the planned queries require it, and evaluate its storage independently.

The existing [encoder helper](../../../src/fear_temperature/embeddings.py) accepts a sequence, materialises a list and returns one float32 matrix; its persistence helper writes that matrix and an ID list together. The [retrieval helper](../../../src/fear_temperature/retrieval.py) scores a supplied matrix against a query. These are existing infrastructure, not evidence of a completed thesis-stage corpus run or a validated streaming pipeline. A future scale implementation needs bounded input/output and restart semantics before bulk use.

CCF's annotations and filtering thresholds require their own transfer evaluation. Do not impose its newspaper length rules on short Australian posts, equate a broad negative tone with fear, or treat a quoted official inside a news article as an independent government source corpus. Preserve the project's structural-cleaning and later relevance/affect/fear stage boundaries.

No database archive, model or corpus was downloaded or executed for this assessment. The exposed deposit and authors' README support this reference; the PDF and individual script endpoints could not be fetched, so no line-level review of those remote scripts is claimed.
