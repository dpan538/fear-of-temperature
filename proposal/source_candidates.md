# 社交与论坛语料候选清单

核查日期：2026-09-15。依据用户要求扩展 Facebook 以外的候选来源；以下为研究设计与官方文档初查，没有申请账户、调用平台数据接口、采集语料或验证实际覆盖。研究用途是设计建议，不能据此声称已发现足够的升温恐惧文本。

## 范围与选择原则

英语为主，覆盖美国、欧洲、澳大利亚和新西兰。平台清单是候选池，最终选择依据：相关文本数量、时间覆盖、地区证据、来源角色、访问成本与许可、能否保留上下文，以及开放发布条件。

“网页公开可读”“可通过 API／研究项目批量访问”“全文可再分发”是三个分别记录的属性。开放 API 不自动赋予帖子开放许可。广覆盖通过有依据的来源分层实现；不把英语用户自动归入某国，也不声称从平台样本测得全体国民情绪。

## 候选来源

| 来源 | 拟研究用途 | 已核查的访问情况 | 对开放语料与设计的影响 |
|---|---|---|---|
| **Facebook；Instagram 可作扩展** | 公开讨论与机构／媒体内容的公众回应，形成不同来源角色的比较 | Meta Content Library 提供 Facebook、Instagram 公开内容；需申请，API 在指定安全研究环境使用 | 保留优先候选。先核准资格、内容范围、可运行模型与导出条件，不能预定全部进入本地开放数据库 |
| **Reddit** | 主题社区中的长文本、回复链、气候担忧与政策态度 | 现行 Reddit for Researchers 项目通过 BigQuery Analytics Hub 提供数据；需机构支持与伦理审批／豁免等申请材料；官方当前说明为五年历史窗口、六个月延迟 | 有研究价值，但其项目明确禁止再分发数据；不作为可公开全文的默认来源，也不能承诺取得平台全部历史 |
| **YouTube 评论** | 围绕 IPCC、COP、热浪报道等视频的事件关联回应 | 官方 Data API 支持读取评论线程；线程返回未必包含全部回复，完整回复需额外读取 | 适合作为事件回应候选；须评估抽样、评论关闭／删除、API 配额、保存与再利用条件。视频所属国不等于评论者所在地 |
| **Bluesky** | 近期公共讨论、科学传播与事件响应 | 官方说明多数公开读取接口无需认证，可读取公开帖子与线程；也有实时数据流途径 | 适合先评估采集与分析流程；历史完整性和内容再分发许可另查，不承担 1988 起的连续历史覆盖 |
| **Mastodon** | 不同实例／社区中的公开讨论与事件反应 | 官方 public timeline API 可返回公开帖子；实例设置可能要求认证或关闭公开时间线访问 | 逐实例选择并记录规则、覆盖与可见性；单个实例不代表整个网络，软件开源不等于帖子获得开放许可 |
| **Stack Exchange：Sustainable Living、Earth Science** | 关于升温后果、理解与应对的提问／回答，作为独立的问答来源层 | 有官方 API；公开用户贡献有明确 CC BY-SA 许可，版本随贡献时间而异；已检查两站主题范围入口 | 在全文开放条件方面更明确，可先调查是否有足够相关情绪材料。保留署名、来源与适用许可；专业问答不能代替一般公众情绪样本 |
| **其他地区／主题公开论坛，包括采用 Discourse 的站点** | 地区热浪经验、生活影响、长篇叙述与讨论链 | Discourse 的公开帖子可能支持匿名 JSON 读取，取决于具体站点设置；尚未审定具体社区 | 下一步挑选实际论坛并逐站核查。软件能力不是某站点的采集／再分发授权，也未证明有长期连续记录 |

## 拟议调查顺序

1. **开放语料贡献**：先核查许可明确的问答／论坛内容是否具有足够研究价值，并逐项核查政策文本的开放条件。不能仅因易获取就把专业问答当成全体公众。
2. **近期分析先导**：评估 Bluesky、选定 Mastodon 实例，以及有适当访问与使用条件的论坛／YouTube 评论，检查三个必做模块是否能获得可验证的输入。
3. **主要平台扩展**：保留 Facebook 和 Reddit 的研究访问路线；依据学校支持、审批时间、时间覆盖与计算环境决定纳入方式。此处未提交任何申请。
4. **历时比较**：先记录来源 × 地区 × 年份覆盖，再确定实际共同观测期。1988 是主要历史采集的拟议锚点，不是所有社交来源必须具有的起始年份。

前三项是调查优先级建议，不是替用户最终拍板的平台组合。三个 NLP 模块与社会情绪主线保持不变。

## 官方依据与阅读范围

- [Meta Content Library / SOMAR](https://www.icpsr.umich.edu/sites/somar/meta-content-library)：阅读访问环境、平台覆盖、申请入口和删除要求。Threads 在该页被列为 UI 覆盖；未把它写成已确认的同等 API 候选。
- [Reddit for Researchers Program](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program)：2026-06-02 更新页；阅读资格、项目规则、BigQuery 路径与数据时间范围。较旧页面的“Research API”介绍不覆盖此处当前项目说明。
- [YouTube 评论线程 API](https://developers.google.com/youtube/v3/docs/commentThreads) 与 [评论读取说明](https://developers.google.com/youtube/v3/guides/implementation/comments)：阅读线程、顶层评论与回复关系；[开发者政策](https://developers.google.com/youtube/terms/developer-policies) 核查凭证和配额相关条款，具体研究保存、派生分析和发布方案尚待完整对照。
- [Bluesky API 文档](https://docs.bsky.app/docs/api/app-bsky-feed-get-feed)：阅读公开 AppView 与认证路由说明；未测试历史检索完整性，也未核准全文再发布许可。
- [Mastodon 时间线 API](https://docs.joinmastodon.org/methods/timelines/)：阅读 public timeline 的认证与实例配置说明；未抽样具体实例。
- [Stack Exchange API](https://api.stackexchange.com/docs)、[用户内容许可](https://stackoverflow.com/help/licensing)、[Sustainable Living 主题范围](https://sustainability.stackexchange.com/help/on-topic)、[Earth Science 主题范围](https://earthscience.stackexchange.com/help/on-topic)：核查接口入口、内容许可版本和社区主题；没有验证情绪样本量。
- [Discourse 官方社区的公开 JSON 读取说明](https://meta.discourse.org/t/what-scope-is-needed-for-acessing-localhost-posts-json/180358)：仅核查官方社区搜索返回的相关说明，未完成具体论坛接口与条款检查。
