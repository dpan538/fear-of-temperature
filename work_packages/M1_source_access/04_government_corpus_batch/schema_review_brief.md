# Dai Pan schema review 简版

状态：`prepared / awaiting Dai review`。以下只列需要研究判断的问题；实现细节已在 v2 schema / v3 normalisation 中完成。

| ID | 真实例子 | 推荐方案 | 研究影响 |
|---|---|---|---|
| GOV-002 分析单位 | `Air quality plan... (2017)` 有 48 个附件；另有 1 个附件被多个页面复用 | 文档作为发布分母；landing page 和每个附件作为独立 content object，分析后再汇总到文档 | 避免把附件数膨胀为政策数，也避免合并后丢失版本、许可和父子关系 |
| GOV-003 genre 分层 | 本批次查询 `policy_paper`，但并未枚举 news、speech、parliamentary material | genre 分层建分母；只有覆盖可比时才合并 | 防止不同发布机制的频率差异被误读为 attention 变化 |
| GOV-004 时间字段 | 275/1,020 文档的 `updated_at` 晚于 `first_published_at` | 发布 attention 用 `first_published_at`；更新作为版本事件 | 避免将修订日期当作新政策发布时间，时间序列可解释 |
| GOV-005 前身机构 | 当前 DEFRA 查询最早命中 1997；机构 API 只明确列出 DETR 前身关系 | DEFRA、DETR、MAFF/旧档案先作为 source-era strata，核验重叠后再映射 | 保留机构改组造成的渠道断裂，不把回填记录当作连续历史 |
| GOV-006 缺失正文 | 3,025 个内容对象全部 blocked，正文/提取文本为 0 | 枚举文档仍进入发布分母；正文分析另报可用覆盖并做缺失敏感性 | 不把获取成功率误当政策发布率；当前不能做正文语义结论 |
| GOV-007 attention 分母 | Search 条件集为 1,020 个唯一文档，未用气候关键词 | 当前只能称 DEFRA-tagged `policy_paper` 查询集合分母；气候相关性后续另标 | 可估计来源内主题占比，但不能外推到全部 DEFRA 或英国政府政策 |
| GOV-008 多机构计数 | 206 个多机构文档，最多 10 个机构；关系数 1,473 | 总体唯一文档计一次；分机构同时给 full 和 fractional counts | full 便于看参与面，fractional 保持跨机构总和等于 1,020 |
| GOV-010 类型漂移 | `Local nature recovery strategies`：Search 命中 `policy_paper`，当前 Content API 为 `guidance` | 同时保留 query-time 与 verified-current type；genre 分析做包含/排除敏感性 | 不丢失查询 provenance，也不把当前分类静默改写成历史分类 |
| GOV-009 新闻衔接 | 当前没有新闻实样本 | 新闻小样本后仅共享 source/document/content/version/date/provenance 核心；byline、quoted speaker、correction 保持媒体字段 | 防止在真实新闻例外出现前过早统一 schema |

请在 `schema_decisions.csv` 对对应 ID 填写 `user_decision`、理由、review date 和状态；不要把 `Dai Pan (planned)` 视为已批准。

