# GOV.UK / DEFRA 政府批次进度报告

## 实际完成

- 完成 GOV.UK、DEFRA 标签、`policy_paper`、1988-01-01..2026-09-21 的 39 个年度分区枚举；唯一文档 1020。
- 实际 Search API 观察窗口为 2026-09-21 01:05:02+00:00..2026-09-21 01:10:54+00:00（UTC）；未把日期过滤上界误写成全天快照。
- 保存必要 Search API 原始响应、1020 个不含正文的 Content API 元数据投影、哈希和 checkpoint。
- Content API 复核发现 1 条文档类型漂移；查询类型与当前类型均已保留，没有静默剔除。
- 枚举网页 1020、唯一附件 2005、附件父关系 2007；下载正文/附件 0。
- 入库文档 1020、机构 69、机构关系 1473；旧 9 条试点 evidence 未覆盖。
- 完成重复导入、离线干净重建、manifest/SQL/导出一致性和失败清单检查。

## 冻结交付状态

- 元数据枚举：`complete`（内部验证标签 `complete_as_visible`），仅限已记录 Search API 查询集合。
- 规范化入库与恢复验证：`passed`；规则版本 `govuk_metadata_v3`，两次离线重建逻辑指纹一致。
- schema review 材料：`prepared / awaiting Dai review`。
- 正文采集：`blocked`；依据与待确认问题见 `body_collection_gate_review.md`。
- 整体全文语料目标：`incomplete`；没有把元数据完成等同全文完成。
- 批次冻结：`true`；后续获准正文应另开恢复批次，不改写本冻结证据。

## 吞吐量与恢复

年度页与逐条元数据按原子文件 checkpoint；`enum --resume` 只补失败/缺失文件，结束仍复查 total。数据库可只用已保存 raw/manifest 和旧试点证据离线重建。
验证时间变化后两次独立重建的逻辑指纹一致；物理 DuckDB SHA 分别保存，不要求字节级布局相同。

## 下一步

1. Dai 按 `schema_decisions.csv` 回复 GOV-002..GOV-008 与 GOV-010。
2. 由适当 UQ 路线明确正文研究处理状态，并逐件处理附件例外；若允许，先运行最多 3 条 smoke fetch/extraction 验证。
3. 取得新闻小样本后，以实际异常记录设计跨来源 v3，不提前统一。
