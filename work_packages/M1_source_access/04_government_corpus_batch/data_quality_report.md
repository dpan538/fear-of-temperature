# 政府批次数据质量报告

**验收：PASS。** PASS 表示限定元数据枚举、追溯和离线重建满足本批次标准；正文与附件字节仍为 blocked。

## 自动检查

| 检查 | 观察值 | 期望 | 结果 |
|---|---|---|---|
| `partition_count` | 39 | 39 | PASS |
| `partition_status` | [] | [] | PASS |
| `api_total_matches_manifest` | {"api_total": 1020, "manifest": 1020} | "equal" | PASS |
| `unique_external_ids` | 1020 | 1020 | PASS |
| `metadata_record_status` | [] | [] | PASS |
| `date_boundaries` | [] | [] | PASS |
| `metadata_hashes` | [] | [] | PASS |
| `raw_file_index` | [] | [] | PASS |
| `webpage_parent_coverage` | 1020 | 1020 | PASS |
| `failure_pending_manifest_complete` | 3025 | 3025 | PASS |
| `fetch_outcome_exports_partition_manifest` | {"success": 0, "failed": 0, "skipped": 0, "pending": 3025} | {"classified_once": 3025} | PASS |
| `content_gate_enforced` | [] | [] | PASS |

## 数据库与计数检查

- manifest / 数据库唯一文档：1020 / 1020。
- 机构实体 / 关系：69 / 1473；多机构文档 206。
- 完整计数权重和 / 分数权重和：1473.0 / 1020.0。
- 网页内容对象 / 唯一附件对象 / 附件父关系：1020 / 2005 / 2007。
- 成功内容 / 真实段落 / 可向量化段落：0 / 0 / 0。
- 重复导入计数不变：PASS。
- 干净离线重建指纹一致：PASS。
- 跨运行逻辑指纹一致（验证时间变化后）：PASS；DuckDB 物理文件 SHA 按每次构建单独记录，不作为逻辑等价判断。

## 明确限制

- Search API 没有不可变快照；结论是记录查询时点的可见集合。
- 实际观察窗口为 2026-09-21 01:05:02+00:00 至 2026-09-21 01:10:54+00:00；日期过滤到 2026-09-21 不代表观察到当日 23:59:59。
- Search/API 类型复核出现 1 条漂移；manifest 同时保留查询类型与当前 Content API 类型。
- 早期零年份和当前最早记录不能证明来源历史起点或当年无政策。
- 伦理状态保持 pending；没有把 OGL、公开可访问或元数据成功误写成研究审批。
- 正文、附件下载、文本提取和向量化均未发生；它们是 blocked，不是空字符串或成功。
