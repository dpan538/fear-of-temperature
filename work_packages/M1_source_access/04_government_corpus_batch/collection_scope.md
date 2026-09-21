# GOV.UK / DEFRA 政府语料正式批次边界

## 批次标识与观察时点

- 批次 ID：`govuk_defra_policy_paper_1988_20260921_v1`。
- 发现接口：GOV.UK Search API，负责条件查询、分页与本批次枚举。
- 单条核验接口：公开 Content API，负责对每个 Search 命中核验稳定 ID、日期、当前类型、机构与附件；不用于声称“Content API 全量”。
- 查询日期上界：2026-09-21（UTC 日历日，Search API 日期过滤上界 inclusive）。
- 实际观察窗口：2026-09-21 01:05:02–01:10:54 UTC（Australia/Brisbane 当地时间 11:05:02–11:10:54，AEST, UTC+10）。因此不能把本批次解释为覆盖到 UTC 当日 23:59:59；它是截至 01:10:54 UTC 的动态索引观察。
- 实际请求开始、结束和复查时间由 `query_partitions.csv` 与原始响应逐项记录；接口没有不可变快照功能，因此本批次只声称“在所记录查询时点可见的集合”。

## 纳入规则

- Search API 机构筛选：`department-for-environment-food-rural-affairs`。含 DEFRA 标签即纳入，不要求 DEFRA 为唯一或主发布机构。
- 文档类型：`content_store_document_type=policy_paper`。
- Search API 查询类型与 Content API 当前类型分开保存；若单条记录后来重分类，仍保留在查询时点 manifest，并标记类型漂移。
- 日期筛选字段：Search API `first_published_at`；Content API 同名字段逐条二次核验。
- 日期过滤范围：1988-01-01 至 2026-09-21，年度分区互不重叠，API 日期边界两端 inclusive；实际集合仍受上述 01:10:54 UTC 观察截止时刻约束。
- 查询不含 climate、warming、fear、anxiety 或其他主题词，因此保留范围内非气候材料作为来源内分母。
- 文档身份：GOV.UK `content_id` 为主键；原始路径与规范化 URL 均保留；多机构关系不增加唯一文档数。

## 本批次包含与排除

包含：

- 39 个年度查询分区及其必要 Search API 原始 JSON 响应；
- 所有枚举记录的最小 Content API 元数据投影，用于核验 `content_id`、首次发表时间、更新时间、机构、强调机构、撤稿标记及附件清单；
- 网页和附件内容对象身份、父文档关系、声明 MIME/大小/页数及抓取状态；
- 旧 9 条试点记录、正式批次记录、版本和哈希的可追溯 DuckDB 重建。

排除：

- 其他英国机构、其他 GOV.UK 文档类型、非 GOV.UK 旧档案及其他国家；它们只列为后续扩展候选；
- 新闻、公众平台、模型推理、向量化、情绪分类、相似度结构和时间序列；
- 未经已记录伦理路线与逐件权利判断的网页正文、PDF/附件字节和正文提取。本批次将这些内容对象标记为 `blocked_pending_ethics_route`，不会把空值冒充成功正文。

## 元数据、网页与附件的口径

- 元数据：允许枚举和研究数据治理核验；Content API 响应只保存明确列出的元数据投影，不持久化 `details.body`、渲染后的 `details.documents` 或其他正文 HTML。
- 网页正文：建立 landing-page 内容对象和待处理状态，但当前不下载。
- 附件：枚举 Content API 声明的每个附件及其父文档关系；共享 URL 只建立一个内容对象并保留多条父关系；当前不下载文件、不做 OCR。
- 可公开访问、可采集、可用于研究处理和可重新发布是四个独立状态。OGL 的一般说明不替代 UQ 路线或附件例外审核。

## 完整性验收

枚举可判 `complete_as_visible` 仅当：

1. 39 个年度分区均有成功响应；
2. 每个分区的分页并集等于接口 `total`，且没有达到单次 1,500 条上限；
3. 结束时的 `count=0` 增量复查与初始 `total` 一致；
4. Content API 关键元数据核验无未解决失败；
5. 跨分区 `content_id` 无重复，日期均位于分区和总边界内；
6. manifest、原始响应索引和数据库记录数一致，并能离线重建。

正文/附件获取覆盖单独判定，不因枚举完整而视为完成。当前配置预期为 `blocked`，理由是尚无可核验的 UQ approval/exemption 且附件级例外未审核。

## 尚未证实的历史覆盖

- GOV.UK Content Store 的官方说明是包含 “almost all” GOV.UK published content，并未证明 1988–2026 所有 DEFRA/前身机构政策已迁移或连续索引。
- 当前 DEFRA 机构 Content API 列出 Department of the Environment, Transport and the Regions 为前身关系；本批次不据此把该机构的全部记录自动并入 DEFRA 分母。
- 早期零分区只能表示本次查询返回 0，不能解释为当年没有政策。
- 撤稿、重定向、回填日期、重分类和历史迁移可能在未来改变可见集合；原始响应、查询时间和复查结果用于记录这种动态性。
- 详细的前身机构与旧档案缺口见 `historical_coverage_gaps.md`。

## 扩展候选（未混入本批次）

- DEFRA 前身机构和 National Archives / legacy departmental archives；
- DESNZ、Cabinet Office、其他英国政府机构；
- `news_story`、`speech`、`consultation`、`guidance`、议会材料和统计发布；
- 美国、欧盟、澳大利亚、新西兰政府来源。
