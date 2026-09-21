# M1.3（工作包序号 04）GOV.UK / DEFRA 政府语料正式批次

本工作包沿用现有 `.venv`、DuckDB、稳定 ID、版本和 CSV 导出方式。它通过 Search API 完整枚举 1988-01-01 至 2026-09-21、带 DEFRA 机构标签、查询类型为 `policy_paper` 的返回集合，再用 Content API 逐条核验；不会把这个单一来源批次命名为“Content API 全量”或“全部政府语料”。

## 直接运行

从仓库根目录执行。先做 3 条 smoke run，再运行正式可恢复批次：

```bash
.venv/bin/python -m fear_temperature.government_collection enum \
  --config work_packages/M1_source_access/04_government_corpus_batch/config.yaml \
  --smoke --limit 3

.venv/bin/python -m fear_temperature.government_collection fetch \
  --config work_packages/M1_source_access/04_government_corpus_batch/config.yaml \
  --smoke --resume

.venv/bin/python -m fear_temperature.government_collection enum \
  --config work_packages/M1_source_access/04_government_corpus_batch/config.yaml \
  --resume

.venv/bin/python -m fear_temperature.government_collection fetch \
  --config work_packages/M1_source_access/04_government_corpus_batch/config.yaml \
  --resume

.venv/bin/python -m fear_temperature.government_collection verify \
  --config work_packages/M1_source_access/04_government_corpus_batch/config.yaml

.venv/bin/python -m fear_temperature.government_collection ingest \
  --config work_packages/M1_source_access/04_government_corpus_batch/config.yaml

.venv/bin/python -m fear_temperature.government_collection report \
  --config work_packages/M1_source_access/04_government_corpus_batch/config.yaml
```

`enum --resume` 以已经校验的年度页和逐条元数据投影为 checkpoint；成功文件不会重复下载，失败项可重试。Search API 是动态索引，正式运行结束仍会做一次小型 total 复查。`fetch --smoke` 由已限制为 3 个文档的 smoke manifest 驱动，并处理这 3 个文档的网页及全部附件。正式 `fetch` 必须由正式 `enumeration_manifest.csv` 驱动；启用内容采集后，每个内容对象会写入独立 fetch checkpoint，恢复时校验成功文件哈希后跳过。当前 `config.yaml` 明确关闭正文与附件字节下载，因此命令会生成完整的 blocked/pending 清单，而不会绕过项目伦理门槛。

离线重建不需要网络：保留 `raw/`、`enumeration_manifest.csv`、`query_partitions.csv`、`fetch_manifest.csv` 和旧试点证据后，重新执行 `verify`、`ingest`、`report`。

## 验证命令

```bash
.venv/bin/pytest tests/test_government_collection.py tests/test_database_pilot.py
.venv/bin/ruff check src/fear_temperature/government_collection.py tests/test_government_collection.py
.venv/bin/mypy src
```

## 状态语义

- `complete_as_visible`：限定查询在记录时点满足分页、total、二次日期核验和离线追溯标准；不代表官方不可变全量快照。
- `partial`：枚举可能完整，但内容对象仍有 blocked、failed、pending 或其他非 success 状态；不能称为完整全文批次。
- `blocked_pending_ethics_route`：内容对象已枚举，但正文/附件没有获准进入研究处理。
- `failed`：实际请求或校验失败，且重试后仍未恢复。
- `not_attempted`：尚未请求，区别于失败和受条件阻塞。

## 主要交付物

- `collection_scope.md`：边界、排除、历史覆盖和验收标准；
- `historical_coverage_gaps.md`：当前 DEFRA 标签与前身机构、旧档案的证据和未解决缺口；
- `rights_and_ethics_review.md`：OGL/公开访问与 UQ 伦理路径的分离判断；
- `body_collection_gate_review.md`：正文暂停依据、尚未核实的适用路径与明确提问；
- `schema_review_brief.md`：供 Dai 快速审阅的真实例子、推荐方案和研究影响；
- `batch_freeze.json`：最终状态、逻辑指纹及冻结输入/数据库哈希；
- `raw/search/`：必要的 Search API 原始响应包装（响应 JSON 原样嵌入）；
- `raw/content_metadata/`：不含正文的 Content API 元数据投影；
- `query_partitions.csv`、`enumeration_manifest.csv`、`content_file_index.csv`；
- `fetch_manifest.csv`、`success_records.csv`、`failed_records.csv`、`skipped_records.csv`、`pending_records.csv`、`failed_or_pending_records.csv`；
- 本地忽略的 `fear_temperature_government_batch.duckdb` 与 `exports/`；
- `verification.json`、`rebuild_manifest.json`、`cross_run_rebuild_check.json`、`data_dictionary.csv`、`data_quality_report.md`；
- `coverage_report.md`、`schema_review.md`、`schema_decisions.csv`、`progress_report.md`。
