# 06 批次政府语料范围、数量与覆盖率评估

生成时间：2026-09-21（Australia/Brisbane）  
冻结查询截止日：2026-09-21  
主时间字段：`first_published_at`（数据库 `documents.publication_timestamp`／其 UTC 日历日期）；`updated_at` 与获取时间仅作版本和获取证据，不替代首次发布日期。

## 结论摘要

本轮只对 9 个下载异常进行了受限处理，没有重新枚举来源、没有重下成功对象、没有对 21 个已下载提取异常做全量重处理。原地址的实际网络重试仍得到 8 个 HTTP 403 和 1 个 HTTP 200 错误页；经原发布页／机构官网核验同一文件后，9 个替代地址中恢复 5 个。最终下载成功 3,021/3,025，提取成功 3,000/3,025；剩余 4 个下载异常与 21 个已下载提取异常继续分开报告。

当前语料的准确范围是：

> 本次冻结查询中，GOV.UK 当前 DEFRA 机构标签下、符合 Search API `policy_paper` 条件的发布记录及其关联内容。

这不等于 DEFRA 所有类型发布、英国全部政府话语、英语国家政府话语、连续完整的 1988 年以来政策档案，也不等于已筛选出的气候或升温恐惧语料。

## 1. 异常重试与前后状态

| 项目 | 本轮前 | 本轮后 | 变化 |
|---|---|---|---|
| 发布记录 | 1,020 | 1,020 | 0 |
| 网页目标 | 1,020 | 1,020 | 0 |
| 唯一附件目标 | 2,005 | 2,005 | 0 |
| 内容对象目标／已尝试 | 3,025 / 3,025 | 3,025 / 3,025 | 0 |
| 下载成功 | 3,016 | 3,021 | +5 |
| 提取成功 | 2,995 | 3,000 | +5 |
| 下载异常 | 9 | 4 | -5 |
| 已下载但提取异常 | 21 | 21 | 0 |
| 提取片段（非自然段／非独立观察） | 2,853,343 | 2,865,202 | +11,859 |

原链接网络重试的远端结果与基线一致。执行审计中另保留了一次受限运行环境的 DNS 失败记录（未到达远端）以及一次在写回前中断、`attempted_count=0` 的实现故障记录；二者不计为对象的远端重试。最终状态已恢复为 3,025 个对象各一条当前状态，数据库核验通过。

| 对象 ID | 对象标题 | 最终状态 | 替代地址响应 | 提取状态 |
|---|---|---|---|---|
| cnt_299152ebeada5607089a | Climate adaption reporting third round: National Grid Gas plc | 已恢复 | 200 | success |
| cnt_48a6f19a6607e492dc7b | Climate adaption reporting third round: National Grid Electricity Transmission | 未解决，停止重试 | 403 | not_attempted_download_failed |
| cnt_531ef7729743e1c8bd31 | Climate adaptation reporting third round: Portsmouth Water | 未解决，停止重试 | 403 | not_attempted_download_failed |
| cnt_64382de7be6292e95543 | OECD report: biodiversity, natural capital and the economy: a policy guide for finance, economic and environment ministers | 已恢复 | 200 | success |
| cnt_7971dcf871bb3136e535 | Climate adaption reporting third round: Anglian Water | 未解决，停止重试 | 403 | not_attempted_download_failed |
| cnt_874c6030598f56b158bf | OECD report: towards G7 action to combat ghost fishing gear | 已恢复 | 200 | success |
| cnt_968313db5fb8a50f393d | Climate adaption reporting third round: Birmingham Airport | 未解决，停止重试 | DNS/连接失败 | not_attempted_download_failed |
| cnt_9fffa8707949d2e58a6e | Climate adaption reporting third round: Thames Water | 已恢复 | 200 | success |
| cnt_b7920fe7e4b7e2b7377c | Climate adaption reporting third round: Historic England and the English Heritage Trust  | 已恢复 | 200 | success |

已恢复 5 个对象：National Grid Gas、两份 OECD 报告、Thames Water、Historic England／English Heritage Trust。剩余 4 个对象为 National Grid Electricity Transmission、Portsmouth Water、Anglian Water、Birmingham Airport；前三者替代地址仍返回 403，Birmingham Airport 官方媒体域名在实际获取环境中无法解析。按任务边界停止继续重试，没有绕过访问限制。

成功获取后的 5 个对象均被识别为 PDF 并完成源文本提取，新增 11,859 个提取片段。片段是提取器的 PDF 行／块等技术单元，不是自然段数或独立观察数。

### 地址变更证据

- `cnt_299152ebeada5607089a`：原地址 <https://www.nationalgrid.com/gas-transmission/document/140476/download>；替代地址 <https://www.nationalgas.com/sites/default/files/documents/Third%20Round%20Climate%20Adaptation%20Report.pdf>；依据：PDF cover states 'Third Round Climate Change Adaptation Report', 'National Grid Gas plc', October 2021; this exactly matches the frozen GOV.UK attachment title and reporting round.
- `cnt_48a6f19a6607e492dc7b`：原地址 <https://www.nationalgrid.com/electricity-transmission/document/143211/download>；替代地址 <https://www.nationalgrid.com/document/343211/download>；依据：PDF cover and contents identify National Grid Electricity Transmission, July 2021, Climate Change Adaptation Report; the title, organisation, year and reporting round match the frozen attachment.
- `cnt_531ef7729743e1c8bd31`：原地址 <https://www.portsmouthwater.co.uk/policies-reports/>；替代地址 <https://www.portsmouthwater.co.uk/wp-content/uploads/2022/01/Portsmouth-Water_Climate-Change-Adaptation-Report_December-2021.pdf>；依据：PDF title is Portsmouth Water's Climate Change Adaptation Report 2021 and its introduction states that it is the third-round report to Defra.
- `cnt_64382de7be6292e95543`：原地址 <https://www.oecd-ilibrary.org/environment/biodiversity-natural-capital-and-the-economy_1a1ae114-en>；替代地址 <https://www.oecd.org/content/dam/oecd/en/publications/reports/2021/05/biodiversity-natural-capital-and-the-economy_940af1d4/1a1ae114-en.pdf>；依据：DOI suffix, full title, OECD authorship, 2021 G7 purpose and policy-paper number 26 match the frozen attachment.
- `cnt_7971dcf871bb3136e535`：原地址 <https://www.anglianwater.co.uk/environment/climate-change/adapting-to-climate-change/>；替代地址 <https://www.anglianwater.co.uk/siteassets/household/in-the-community/climate-change-adaptation-report-2020.pdf>；依据：The official PDF is Anglian Water's 2020 Climate Change Adaptation Report, identified by the organisation as its third-round submission.
- `cnt_874c6030598f56b158bf`：原地址 <https://www.oecd-ilibrary.org/environment/towards-g7-action-to-combat-ghost-fishing-gear_a4c86e42-en>；替代地址 <https://www.oecd.org/content/dam/oecd/en/publications/reports/2021/05/towards-g7-action-to-combat-ghost-fishing-gear_6288764d/a4c86e42-en.pdf>；依据：DOI suffix, full title, OECD authorship, 2021 UK G7 purpose and policy-paper number 25 match the frozen attachment.
- `cnt_968313db5fb8a50f393d`：原地址 <https://www.birminghamairport.co.uk/about-us/community-and-environment/sustainability-strategy/supporting-policies-plans/>；替代地址 <https://authoring.birminghamairport.co.uk/media/6746/birmingham-airport-climate-change-adaptation-progress-report-final.pdf>；依据：PDF title is Birmingham Airport Climate Change Adaptation Progress Report 2021 and the report content identifies the Defra adaptation reporting process.
- `cnt_9fffa8707949d2e58a6e`：原地址 <https://www.thameswater.co.uk/about-us/responsibility/climate-change>；替代地址 <https://www.thameswater.co.uk/media-library/pcjjeaop/climate-change-adaptability-report.pdf>；依据：The official PDF title and 2015-2020 reporting period match Thames Water's December 2021 third-round submission referenced by GOV.UK.
- `cnt_b7920fe7e4b7e2b7377c`：原地址 <https://historicengland.org.uk/research/results/reports/17-2022?searchType=research+report&search=17%2F2022>；替代地址 <https://historicengland.org.uk/research/results/reports/8614/ClimateChangeAdaptationReport>；依据：Report number 17/2022, title Climate Change Adaptation Report, authors, 44-page extent and joint Historic England/English Heritage Trust responsibility match the frozen attachment.

逐对象状态、哈希、保存路径和证据详见 [`retry_results.csv`](retry_results.csv)；审核过的映射见 [`retry_url_overrides.json`](retry_url_overrides.json)。

## 2. 时间分布

所有 1,020 条发布记录都有可核验的 `first_published_at`；缺失日期 0 条。逐年表固定列出 1988-2026，因此零返回年份不会从图表消失。最早观察年份为 1997；1988-1996 没有观察记录。查询零返回只表示本次来源集合未观察到记录，不表示该年不存在政府政策。

年度峰值为 2013 年 114 条。2026 年有 75 条，但只覆盖到 9 月 21 日。年代构成为：

| 年代组 | 发布记录 | 批次内部占比 | 边界 |
|---|---|---|---|
| 1988-1989 | 0 | 0.00% | partial_opening_decade |
| 1990-1999 | 3 | 0.29% | complete_calendar_decade |
| 2000-2009 | 52 | 5.10% | complete_calendar_decade |
| 2010-2019 | 488 | 47.84% | complete_calendar_decade |
| 2020-2026-09-21 | 477 | 46.76% | partial_closing_decade_to_cutoff |

一个共享附件 `cnt_7c040a51e7d7fb4cbe09` 同时关联 3 条父发布记录，父年份为 2019, 2024, 2025。年度和年代 CSV 的附件字符数／片段数采用“年份内去重对象、跨父年份可重复出现”的关联口径；跨年相加不能称为唯一附件总量。附件没有可核验独立发布日期时，没有把父文档日期写成附件自身发布日期。

图表：[`年度发布记录`](annual_publication_records.png) · [`年代构成`](decade_composition.png) · [`年×月热图`](year_month_heatmap.png)。源数值见 [`annual_distribution.csv`](annual_distribution.csv)、[`decade_distribution.csv`](decade_distribution.csv)、[`year_month_counts.csv`](year_month_counts.csv)。

## 3. 当前可以计算的覆盖率

| 指标 | 对象／记录口径 | 分子 / 分母 | 结果 |
|---|---|---|---|
| Frozen-list attempt completion | all objects | 3,025 / 3,025 | 100.00% |
| Download success | all objects | 3,021 / 3,025 | 99.87% |
| Download success | webpages | 1,020 / 1,020 | 100.00% |
| Download success | attachments | 2,001 / 2,005 | 99.80% |
| Extraction success among downloaded objects | all objects | 3,000 / 3,021 | 99.30% |
| Extraction success among downloaded objects | webpages | 1,020 / 1,020 | 100.00% |
| Extraction success among downloaded objects | attachments | 1,980 / 2,001 | 98.95% |
| Target-object text availability | all objects | 3,000 / 3,025 | 99.17% |
| Target-object text availability | webpages | 1,020 / 1,020 | 100.00% |
| Target-object text availability | attachments | 1,980 / 2,005 | 98.75% |
| All linked attachments extracted | publication records with attachments | 998 / 1,016 | 98.23% |
| Some but not all linked attachments extracted | publication records with attachments | 10 / 1,016 | 0.98% |
| No linked attachment extracted | publication records with attachments | 8 / 1,016 | 0.79% |

“至少提取到一个对象”只说明发布记录存在可用文本。由于 1,020 个网页都成功提取，该指标对发布记录为 100%，但不能称为政策全文完整率：网页可能只有摘要、说明和附件链接，正文主要价值可能位于附件。

有附件的发布记录共 1,016 条，其中附件全部提取成功 998 条、部分成功 10 条、全部未成功 8 条，三类互斥。配套可机读分子／分母见 [`coverage_metrics.csv`](coverage_metrics.csv)。

## 4. 当前不能计算的覆盖率

缺少独立、可靠总体分母，以下比例不计算：

- 英国政府整体覆盖率；
- DEFRA 历史政策完整率；
- proposal 所有目标国家政府语料覆盖率；
- 气候政策占比或恐惧表达占比。

年度记录占比仅是这个冻结批次内部的时间构成，不是某年政府话语覆盖率。当前 Search API 的查询类型与 Content API 当前类型也不完全一致：1,019 条当前类型为 `policy_paper`，1 条为 `guidance`（`Local nature recovery strategies`，对象 `doc_f369a1e56ff12dd91e81`）；该漂移被保留，没有静默改写。

## 5. 与 proposal 原计划的差距

| 原计划维度 | 当前证据 | 已满足部分 | 未覆盖部分 | 对后续工作的影响 |
|---|---|---|---|---|
| 国家与地区 | 核心优先英语文本，涉及美国、欧洲、澳大利亚、新西兰；更广地域待验证试点。 | 英国 GOV.UK 已有一个可审计的真实批次。 | 美国、欧洲其他国家、澳大利亚、新西兰政府层均未由本批覆盖。 | 不能把当前批次外推为英语国家政府话语；跨国比较尚不可做。 |
| 发布机构 | GOV.UK 为首要政策来源，要求按机构／类型／月份保留分母。 | 冻结清单按 GOV.UK 当前 DEFRA 机构标签形成。 | 不是 DEFRA 全部发布，也不是 GOV.UK 全部部门或英国政府整体。 | 机构职能造成的基准差异尚不能与其他机构合并。 |
| 文档类型 | 政策层需按文种分层，不能默认政策、议会、新闻稿、科学评估共享分母。 | Search API 查询类型固定为 policy_paper。 | 当前 Content API 类型为 policy_paper 1,019 条、guidance 1 条；议会、新闻稿等未覆盖。 | 保留类型漂移记录；不得把本批称为 DEFRA 全文种样本。 |
| 1988 起点及实际观察年份 | 目标从 1988-01 开始，但不保证连续分析覆盖。 | 逐年网格完整保留 1988-2026；最早观察记录为 1997。 | 1988-1996 为零返回，1997 前没有观察记录；这不是历史档案完整性证明。 | 1997-2010 仅作稀疏历史语境；不能据此识别 1988 前后变化。 |
| 月度／季度数量分布 | 政策来源可考虑季度，但共同 VAR/CCF 需其他来源同步聚合。 | 已提供年×月真实分布和年度／年代构成。 | 未验证稳定月度密度、季节性、结构突变或与其他角色的共同窗口。 | 本轮仅做构成描述；不提前宣称时间序列可行。 |
| 正文和附件可得性 | 政策正文、附件和长报告需保留父子关系与分母。 | 网页 1,020/1,020 提取成功；附件 1,980/2,005。 | 仍有 4 个下载异常和 21 个已下载提取异常；网页成功不等于附件政策全文到手。 | 后续文本处理需按网页摘要、附件正文和附件格式分别选择。 |
| 历史版本与更新时间 | 要求版本化、可追溯语料，并区分首次发布与更新。 | 保留 first_published_at、updated_at、retrieved_at；275 条的更新时间晚于首次发布。 | 最大首发—更新时间间隔为 4,952 天；只保存了本次获取时可见版本及少量错误页历史，不是完整版本档案。 | 日期分布仍按首次发布日期；当前正文可能不是首次发表时原文。 |
| 与新闻、公众层共同窗口 | 初始来源为 GOV.UK、Guardian、Reddit 申请路线；共同覆盖确认后再定窗口。 | 政府批次内部时间构成已明确。 | Guardian 与公众来源的可用月份、分母和权限仍未冻结。 | 保留共同窗口未定状态，不做跨角色领先／滞后分析。 |

特别需要注意版本解释：275 条记录的 `updated_at` 晚于 `first_published_at`，最长间隔 4,952 天。年度分布按首次发布日期保留，但本次下载的是截止日可见内容，可能包含后来替换或更新的正文／附件，不能自动视为首次发表时的原文。

## 6. 暂定政府层使用范围

- **可直接用于后续源文本处理：** 3,000 个当前提取成功对象，但必须保留网页／附件、格式、父发布记录与版本字段；网页可用于发布说明和摘要，不能单独代替附件全文。
- **需要先调整切分或聚合：** PDF 的行／块级单元、CSV／ODS 的行或单元格、长报告的高密度技术片段。后续应在父对象内重组，而不是把当前片段当自然段或独立观察。
- **保留但暂不纳入语言处理：** 4 个下载异常、14 个 `needs_ocr`、5 个不支持格式、2 个 `extraction_failed`。原 HTTP 200 错误页作为历史证据保留，不作为正文。

基于真实分布，建议把 **1997-2026 的全部观察记录保留为政府层来源档案**；把 1997-2010 的稀疏记录主要用于历史语境，把 2011-2025 的完整年份作为进一步评估月度／季度稳定性的候选区间，2026 单列为截止日部分年份。这是审查范围，不是“足以支持时间序列分析”的结论。新闻和公众层的可用月份、分母与权限尚未冻结，因此共同窗口继续保留为未定，不开展跨角色时序推断。

## 7. 图表契约与口径

核心结论：冻结批次的记录在 2010 年后集中，1988 起点不构成连续完整历史覆盖。结果问题是“该冻结查询在哪些年份和月份观察到多少发布记录”。图表采用单面板定量图、Python／Matplotlib、183 mm 宽；主证据是逐年和年×月数量，年代构成是汇总验证。无抽样误差条或显著性检验；`n` 是唯一 `document_id` 数。主要审稿风险是把零返回误读为政策不存在、把 2026 误读为完整年份，或把父年份关联的共享附件相加成唯一附件总量；图注和 CSV 已显式约束这些解释。
