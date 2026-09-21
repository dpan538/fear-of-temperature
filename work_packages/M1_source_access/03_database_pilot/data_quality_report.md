# 数据质量与重建检查

**总状态：PASS。** 该状态只覆盖 9 条已保存 GOV.UK/DEFRA 元数据的数据库试点，不评价正文、历史覆盖、主题相关性或伦理许可。

## 关键边界

- N=9 applies only when reproducing this exact source, organisation tag, content type, first-publication date field, inclusive window, document unit, and deduplication rule; it is not all DEFRA output, all UK policy, climate attention, or a passage denominator.
- 真实正文段落为 0；`text_segments` 和 `embedding_ready_segments` 只是接口。
- 来源与 9 条文档的伦理状态均为 `pending`；未发现可核验的 approved/exempt 记录。
- 多机构发布不增加文档总数；完整机构关联权重和分数权重均保存，但尚未选择机构统计口径。

## 数据检查

| 检查 | 观察值 | 期望值 | 结果 |
|---|---:|---:|---|
| `unique_research_documents` | 9 | 9 | PASS |
| `distinct_document_ids` | 9 | 9 | PASS |
| `raw_records` | 9 | 9 | PASS |
| `current_document_versions` | 9 | 9 | PASS |
| `traceable_documents` | 9 | 9 | PASS |
| `multi_organisation_documents` | 3 | 3 | PASS |
| `document_organisation_links` | 14 | 14 | PASS |
| `full_count_weight_sum` | 14.0 | 14.0 | PASS |
| `fractional_weight_sum` | 9.0 | 9.0 | PASS |
| `missing_first_publication_dates` | 0 | 0 | PASS |
| `wrong_date_basis` | 0 | 0 | PASS |
| `dates_outside_window` | 0 | 0 | PASS |
| `null_titles_or_urls` | 0 | 0 | PASS |
| `duplicate_external_ids` | 0 | 0 | PASS |
| `duplicate_urls` | 0 | 0 | PASS |
| `coverage_denominator` | 9 | 9 | PASS |
| `real_text_segments` | 0 | 0 | PASS |
| `all_text_segments` | 0 | 0 | PASS |
| `embedding_ready_segments` | 0 | 0 | PASS |
| `non_pending_source_ethics` | 0 | 0 | PASS |
| `non_pending_document_ethics` | 0 | 0 | PASS |
| `foreign_key_orphans` | 0 | 0 | PASS |

## 可重复性与版本检查

- 同一批次重复导入行数不变：PASS。
- 删除式干净重建的逻辑指纹一致：PASS。
- 原始记录变化产生 1 个新文档版本（内存测试）：1。
- 规则版本变化为 9 条文档各产生新版本（内存测试）：9。
- 版本测试后仍恰有 9 个 current versions：9。

## 未解决阻塞点

1. 尚无已记录的 UQ ethics approval 或 exemption；不能把 `pending` 改成 `approved`。
2. 正文和附件尚未做逐项许可/第三方权利审核，因此没有采集或切段真实正文。
3. Lead/emphasised organisation 尚未核验，机构归属统计口径尚未批准。
4. 单月快照不能证明 1988–2026 历史覆盖、渠道连续性或跨年代可比性。
5. 尚未检查跨来源重复或内容重叠；没有正文时也不能做内容级重复判定。
