# 分母可行性判定

## 结论

**状态 1：短窗口内、明确机构标签/文档类型的完整列表及总量已核验。**

**工程决策：conditional go。** 可以进入下一小步的元数据历史稳定性与少量正文提取验证；在共同署名口径、历史覆盖和附件权利确认前，不应直接扩展到全历史 S 指标。

### 被核验的分母

集合定义：

> GOV.UK Search API 中，`organisations=department-for-environment-food-rural-affairs`、`content_store_document_type=policy_paper`，且 `first_published_at` 位于 2026-07-01 00:00 至 2026-07-31 23:59（API 文档说明日期区间为 inclusive）的 publication landing-page content items。

- 单位：document（GOV.UK publication landing page content item）。
- `N_total = 9`。
- 机构语义：被标记到 DEFRA；不等于由 DEFRA 单独发布。
- 时间语义：首次发布日期，不是最后更新时间或抓取日。
- 本轮样本量：9；由于完整枚举成功，本轮样本与这个限定集合相同。

若未来在此 stratum 计算注意力比例，可写为 `S = N_relevant / 9`；但 `N_relevant` 的主题判定规则尚未预注册或实施，本轮不计算 S。

## 支持状态 1 的实际证据

| 证据 | 结果 |
|---|---|
| 官方 Search API bounded query | HTTP 200，`total=9`，返回 9 条 |
| 分页复核 | `start=0,count=5` 得 5 条；`start=5,count=5` 得 4 条；并集 9 条，与完整返回集合一致 |
| 内容项核验 | 9/9 Content API HTTP 200 |
| 公开页面核验 | 9/9 canonical HTML HTTP 200 |
| 日期 | 9/9 有 Content API `first_published_at`，且均落在窗口内 |
| 类型 | 9/9 `document_type=policy_paper` |
| 机构 | 9/9 机构链接含 DEFRA |
| 去重 | `content_id` 重复 0；canonical URL 重复 0 |
| 关键元数据缺失 | 0 |

完整 URL、访问时间、HTTP 状态和检查布尔值见 [`checks.json`](checks.json)。最小化响应证据与 SHA-256 见 [`evidence/`](evidence/)。

## 为什么不是更大的分母

这个 `N_total=9` **只能**支持“2026 年 7 月 GOV.UK 上首次发布、被标记到 DEFRA、类型为 `policy_paper` 的文档量”。它不能代表：

- DEFRA 在该月的全部发布物；新闻、guidance、consultation、speech、statistics 等未纳入。
- 英国政府全部政策注意力；其他部门和非 GOV.UK 系统未纳入。
- 全部气候政策文本；查询没有按 climate 关键词过滤，且政策类型边界不同。
- 段落或词元分母；landing page 完整不等于附件、HTML 正文和 PDF 段落都完整。
- 1988–2026 历史分母；官方文档没有给出本筛选层的精确历史起点，本轮只核验一个月。

## 已发现的问题与风险

### 1. 日期字段必须二次核验

Search API 的 `public_timestamp` 可能对应公开更新，而非首次发布。例如 APAC 的首次发布日期为 2026-07-03，但公开更新时间为 2026-08-21。把 `public_timestamp` 直接当发布日期会把它错误移到 8 月。

本次 Search API 接受 `first_published_at` 过滤，但响应没有返回填充值；使用 `order=first_published_at` 返回 HTTP 422。解决方案是用 Content API 逐条取得 `first_published_at` 和 `public_updated_at`，再本地排序。

### 2. 机构标记不等于独家归属

9 条中有 3 条链接多个机构。当前规则是“含 DEFRA 标签即纳入，每个 landing page 计一次”。在跨机构 S 指标中必须先决定：

- 每个关联机构都计 1；
- 只计 emphasised/lead organisation；或
- 对共同发布做分数计权。

未预注册前，不应用同一文档在多个机构层重复计算后再汇总成“全政府总量”。

### 3. 当前索引是动态快照

GOV.UK 说明内容可随时更新或移除。回填发布日期、重分类、合并或撤稿会改变历史查询结果。本轮保留了 `accessed_at` 和快照哈希，但尚未测试周际重跑一致性。

### 4. 权利状态是“多数适用”，不是逐件无条件

GOV.UK Terms 说明多数内容按 OGL v3 发布；OGL 仍排除个人数据、部分第三方权利等内容。当前只保存最小元数据，不保存正文或附件。正式正文采集前仍要：

1. 完成导师/伦理前置确认；
2. 检查 landing page 与附件是否有另行版权声明；
3. 保存来源、许可、访问时间和署名信息；
4. 明确共享的是 URL/元数据、derived features，还是可再发布的原文。

### 5. 历史覆盖仍 unknown

Content Store 文档只称包含“almost all published content on GOV.UK”，没有证明所需研究年代和所有 document types 完整。短窗口成功不能外推到 1988–2026。

## Go 条件与停止条件

下一步只有在以下条件满足时才扩展：

- 同一查询在另一个时间点重跑，明确新增/删除/更新差异；
- 共同发布计数规则经导师确认并预注册；
- 选定 landing page 与附件的分析单位；
- 正文与附件的许可/伦理处理方式确认；
- 对更早月份/年份做 coverage audit，而不是直接声称全历史完整。

如果历史抽查显示大量缺失、日期回填不可追踪、类型字段跨期不可比，或机构归属无法稳定定义，则该路线应降为状态 2 或 3，而不是继续生成不可解释的 S。

## 下一项最小任务

不扩展语料库，先做一次 **3 个时间点/窗口的历史稳定性抽查**：同一机构、同一类型，检查一个近期月、一个中期月和一个较早月的枚举/日期/重定向；同时对本轮 3 个共同署名记录确认 lead/emphasised organisation 字段是否稳定。然后由导师决定共同发布计数规则和是否批准 3 个公开文件的正文/附件提取验证。

## 需要导师确认

1. 机构层 S 的归属规则应使用“含 DEFRA 标签即计入”、只计 lead organisation，还是共同发布分数计权？
2. 在 OGL/附件例外逐项记录且伦理前置完成后，是否批准下一轮只提取 3 个公开文档的正文段落，用于验证 paragraph provenance，而不做情绪分类？

