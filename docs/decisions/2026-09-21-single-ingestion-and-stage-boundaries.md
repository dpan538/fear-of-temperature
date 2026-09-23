# Decision: single logical ingestion, extraction repair and stage boundaries

- Date: 2026-09-21
- Decision owner: Dai Pan
- Status: approved in the project conversation; execution remains with the implementation task
- Scope: current frozen DEFRA/GOV.UK batch and its existing 06 working database
- Supersedes: the proposed 07 derived-passage sample and repeated sample-review gate in the earlier conversation and project log

## User instruction

> 应该一次性写入到数据库，关于提取片段只需要检查修理，不要多次给数据库引入同一批源。我们需要明确现在的抓取状态，预计的抓取数量以及抓取进度。最终进行检查。不要额外做向量验证要不要额外进行反复的确认。后续有专门做数据清洗的阶段，不要反复浪费时间。这个需要写入设计决策。

## 1. One authoritative working database and one logical ingestion

Continue using:

`work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb`

The sources are already ingested. Do not reintroduce the same batch as new documents, content objects, source registrations or content versions. Preserve existing stable IDs, source links, timestamps, shared-attachment relationships and original files. Leave the historical 04/05 snapshots unchanged.

“Single ingestion” means one authoritative stored representation of this source batch. It does not require holding all downloads in memory or postponing all writes until one giant transaction. Existing checkpoints and bounded transactional writes may be used for recovery; resuming must not duplicate successfully stored sources or text.

No new working-database copy, derived-text subsystem or mapping table is required merely to perform the current repair task. If temporary repair output is necessary, use staging and apply verified corrections to the existing working database. Do not leave competing current copies of the same extracted text.

## 2. Inspect and repair extraction; defer cleaning

Current work is limited to identifiable extraction defects: missing or garbled text, incorrect extraction order, broken locators, and accidental duplicate writes. Use already downloaded files; do not recrawl successful objects just to repair extraction.

Short lines alone are not evidence of corruption. General paragraph reconstruction, retrieval chunking, boilerplate removal, table/prose separation, linguistic normalisation and analytical deduplication belong to the later dedicated cleaning stage. Record these issues for that stage rather than repeatedly processing the whole corpus now.

Repairs must retain the content-version link and truthful source location. A changed extractor is a new processing run, not a new source or a new byte-level content version. Record affected IDs, repair reason, extractor/rule version, timestamp and before/after counts; preserve enough evidence to recover affected records. If existing references depend on segment IDs, maintain their integrity within the repair. Do not silently relabel an extraction line as a reconstructed paragraph.

The earlier request to create a separate 07 passage-preparation sample with a new Dai approval gate is withdrawn. No embeddings, vector validation, Jev, emotion classification or model evaluation are part of this task.

## 3. Fixed expected counts and explicit progress

The expected target is the frozen manifest, not an estimate of all government material:

| Measure | Target / denominator | Latest reported state |
|---|---:|---:|
| Publication records | 1,020 | 1,020 stored |
| Publication webpages | 1,020 | 1,020 downloaded |
| Unique attachments | 2,005 | 1,996 downloaded |
| Unique content objects | 3,025 | 3,025 attempted |
| Downloaded objects | 3,025 targets | 3,016 successful; 9 unavailable/error pages |
| Text extraction | 3,016 downloaded objects | 2,995 successful; 21 exceptions |

Extraction exceptions: 14 need OCR, 5 have unsupported formats, and 2 failed extraction. The 9 download exceptions comprise 8 HTTP 403 responses and 1 HTTP 200 error page. Thus 3,025 = 3,016 + 9 and 3,016 = 2,995 + 14 + 5 + 2.

These counts are the execution report baseline, not new measurements made by this decision. Current 2,853,343 extraction segments are not a target number of research paragraphs. Repair may change segment counts without changing source counts.

Progress reports must distinguish expected, attempted, downloaded, extracted, failed/deferred and unattempted. The acquisition pass is complete (3,025/3,025 attempted); complete text availability has not been achieved. Final access/format exceptions do not mandate endless retries or prevent closing the bounded acquisition task with documented exceptions.

Keep repair progress separate: affected objects identified, repaired, deferred with reasons and remaining. Never reset acquisition progress when a text repair begins. If a legitimate count changes, record the cause and updated totals.

## 4. One consolidated final acceptance

After necessary extraction repairs, run a focused final acceptance covering:

- manifest totals and mutually exclusive object statuses;
- no duplicate source/object ingestion or competing current extraction sets;
- saved-file/content-version consistency and valid segment source references;
- repaired text and locators checked against actual affected files;
- unchanged source identities and historical snapshots;
- explicit final exceptions and items deferred to cleaning.

Reuse existing successful verification evidence for unchanged components. Rerun only checks affected by a repair or a real failure. Do not add unrelated tests, vector validation, repeated full rebuilds or repeated approval checkpoints. Proceed within this approved scope and report the consolidated result to Dai. A genuinely new scope decision is recorded separately, not invented as a routine gate.

## 5. Logging and handoff

Update acquisition status and the project log with actual progress, repair actions, final checks and the cleaning-stage backlog. Do not modify the proposal. This decision does not itself execute database repairs, download files or commit/push changes.

Evidence: [06 README](../../work_packages/M1_source_access/06_government_content_acquisition/README.md), [text-quality review](../../work_packages/M1_source_access/06_government_content_acquisition/text_quality_review/text_quality_report_for_dai.md), [project log](../PROJECT_LOG.md).

中文执行摘要：同一批来源只入库一次，沿用 06 工作数据库；已有提取只检查并修理真实错误，不提前反复开展清洗、段落重建或向量验证。明确目标 3,025、已尝试 3,025、已下载 3,016、已提取 2,995，并分别记录失败与后续处理事项。完成必要修理后统一验收一次，不再设置小样本反复确认门槛。
