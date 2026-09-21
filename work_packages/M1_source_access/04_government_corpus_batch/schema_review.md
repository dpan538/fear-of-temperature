# Dai Pan schema review：基于正式政府批次的审阅材料

## 当前数据流

`Search API 年度分区 → 原始分页响应 → Content API 元数据投影 → enumeration_manifest → 网页/附件内容对象与 fetch 状态 → 原始记录/文档版本 → DuckDB → CSV/覆盖报告`。

文档是来源发布分母；机构和内容对象都是多对多关系。正文提取属于内容版本下游，当前因 gate blocked，没有伪造 `text_segments`。旧 9 条试点作为独立 batch/raw evidence 保留，正式批次新增版本而非覆盖旧证据。

## 核心字段为什么存在

| 对象 / 字段 | 需要它的原因 | 本批次证据 |
|---|---|---|
| `batch_id` / `query_partition_id` | 把动态索引观察固定到范围、时点和页 | 39 个年度分区；结束 total 复查 |
| `external_id` (`content_id`) | 跨路径/版本的稳定身份 | manifest 内唯一；URL 单独保存 |
| 首次发表 / 更新 / 获取时间 | 避免把更新移成新发布 | 275 条更新时间晚于首次发表 |
| 文档—机构关系 | 不把共同发布膨胀成新文档 | 206 个多机构文档、1473 条关系 |
| content object / parent relation | 网页、多个附件和共享附件需分别追溯 | 2005 个附件对象、2007 条关系 |
| body/rights/ethics 状态 | 公开、可抓、可研究、可再发布不是同一状态 | 当前所有正文对象明确 blocked/pending |
| raw/version/hash | 动态来源可更新；必须恢复旧观察 | 旧试点与正式批次 raw records 均保留 |

## 真实常见与异常记录

- 最早可见记录：`5e0f8f09-7631-11e4-a3cb-005056011aef`，1997-12-17，SCCPs in leather processing。它只说明当前索引最早命中，不是 DEFRA 历史起点。
- 机构最多记录：`01c9950c-52d7-457d-a462-54beb761f51f`，10 个机构，Defra group equality, diversity and inclusion strategy 2020 to 2024。
- 附件最多记录：`3182edb0-9a7e-473c-8f0c-6983347e7d6c`，48 个附件，Air quality plan for nitrogen dioxide (NO2) in UK (2017): air quality directions。
- 275 条的更新时间晚于首次发表；两种时间不能互相代填。
- 唯一附件与父关系相差 2；共享附件对象 1，说明附件身份和父关系必须分表。
- 类型漂移记录：`e22c3c5a-c49c-418c-b54a-681e1c044095`，Local nature recovery strategies；Search 类型 `policy_paper`，当前 Content API 类型 `guidance`。
- 0 条有撤稿标记；撤稿状态不能用 404 或空正文代替。

## 已由数据支持的设计

- `content_id` 去重、URL 单独保留；文档和机构多对多；首次发表与更新时间分离。
- 年度分区、原始响应索引和查询时点是必要 provenance，而不是运行日志装饰。
- 网页/附件作为内容对象、文档作为来源分母；blocked/failed/not_attempted/success 必须分开。
- 元数据版本和内容版本不能合并：本批次只有前者，不能据此声称全文版本已保存。

## Dai 需要决定

简版真实例子、推荐方案与研究影响见 `schema_review_brief.md`；完整迁移影响见 `schema_decisions.csv`。优先审阅 GOV-002 至 GOV-008 及 GOV-010。普通的 ID、哈希、checkpoint、HTTP 重试和 CSV 导出已经实现，不推给研究判断。

## 新闻小样本后的调整边界

先用与本批次共同窗口相交的少量 Guardian/其他获准新闻记录验证：publication/update 日期、article/body 关系、byline、quoted speaker、修订/更正、转载和许可状态。然后只把已被两类真实数据支持的 source/document/content-object/version/provenance 字段提升为共同 v3；新闻出版角色保持 media，被引部长仍是 attribution，而不是 publisher role。
