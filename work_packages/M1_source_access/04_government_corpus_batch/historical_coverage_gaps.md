# DEFRA 前身机构与旧档案覆盖调查

## 与正式枚举的边界

正式批次完成的是 GOV.UK Search API 在指定查询时点，对当前 DEFRA 机构标签、`policy_paper` 查询类型及 1988-01-01..2026-09-21 日期条件返回的集合。Content API 只核验每条命中，不承担历史全量发现。

本文件单独记录“当前标签之外可能存在什么”，不把候选旧档案静默混入本批次分母。

## 已核验事实

- 当前 DEFRA 机构 Content API 的 `links.superseded_organisations` 列出 Department of the Environment, Transport and the Regions（DETR，content ID `971eb79c-9236-47ff-9af1-b32c835a88fc`，状态 `split`）。这证明机构关系存在，不证明 DETR 文档已完整迁移或回填到 DEFRA 标签。
- DEFRA 2001–02 Resource Accounts 将 2001 年描述为部门组建时期，因此 1988–2000 不能被视为“当前 DEFRA 机构连续自产”的自然年度序列。
- 当前查询仍返回 1997、1999 和 2000 年记录，说明 GOV.UK 索引存在早期回填；最早命中为 1997-12-17。回填存在不等于回填完整。
- The National Archives 的现代政治史研究指南说明，相当一部分政府档案并未在线提供，并指向 UK Government Web Archive 等独立检索路径。因此 GOV.UK 当前 Search 索引不足以证明历史档案穷尽。

## 缺口清单

| gap_id | 候选范围 | 当前证据 | 本批次处理 | 状态 / 后续核验 |
|---|---|---|---|---|
| HIST-001 | DETR 及其拆分前的环境职能材料 | DEFRA Content API 明确给出 predecessor/superseded relation | 不并入当前分母 | unresolved；按 DETR 自身机构标签和同期类型独立枚举，检查与当前 1,020 条的 content ID 重叠 |
| HIST-002 | Ministry of Agriculture, Fisheries and Food 及农业/食品职能前身材料 | DEFRA 2001–02 accounts 表明部门组建涉及既有职能；当前批次未验证其 Search 标签迁移 | 不并入当前分母 | unresolved；先确认官方机构 slug/content ID，再做 1988–2001 独立枚举 |
| HIST-003 | GOV.UK 之外的旧部门网页与 UK Government Web Archive | National Archives 指出历史网页和未在线档案需通过其他路径检索 | 不并入当前分母 | unresolved；建立单独 source-era 与捕获日期口径，不能用当前 GOV.UK content ID 假定去重 |
| HIST-004 | 纸本或未数字化政策记录 | National Archives 说明部分记录不在线 | 不并入当前分母 | unresolved；只能报告 finding-aid/目录覆盖，不能将 Search 零结果解释为无政策 |
| HIST-005 | 被重新分类的 GOV.UK 记录 | 本批次发现 1 条 Search `policy_paper`、Content API 当前 `guidance` | 保留查询时点命中和当前类型 | awaiting_review；见 schema decision GOV-010 |

## 对 1988–2026 的解释

- 研究目标起点仍是 1988-01-01。
- 当前实际最早返回日期是 1997-12-17，只是“本次查询最早命中”。
- 1988–1996、1998、2001、2003 的 Search 分区已成功返回 total=0；对本接口条件可写“查询时点返回 0”，对历史政策活动只能写“来源覆盖未证实”。
- 在 HIST-001..004 解决前，不能把本批次称为 DEFRA 全历史、英国政府全历史或 1988 年以来连续政府语料。

## 核验来源

- GOV.UK Content API：`/api/content/government/organisations/department-for-environment-food-rural-affairs`（2026-09-21 查询）。
- DEFRA, *Department for Environment, Food and Rural Affairs Resource Accounts 2001–02*。
- The National Archives, *Modern political history* research guide。

