# M1.1 来源可行性：从 proposal 到一个可审计分母

**一句话结论：** GOV.UK 能为“2026 年 7 月、DEFRA 标签、`policy_paper`、文档级”提供完整可复查分母：`N_total=9`。判定为**状态 1 / conditional go**，但不能外推为 DEFRA 全部发文、英国政府全部政策或气候情绪结论。

## 本周第一步与实际核验

没有用 climate/heat 关键词挑好看的结果。先在同一官方 API 比较三个机构 strata：DEFRA 9、DESNZ 4、Cabinet Office 4；选择 DEFRA 是因为固定完整月恰好满足 5–10 条先导样本。

| 来源 | 访问路线 | 日期定义 | 实测 | 分母状态 |
|---|---|---|---:|---|
| GOV.UK / DEFRA / `policy_paper` | Search API 枚举 → Content API 核日期/类型 → canonical HTML | `first_published_at`，2026-07-01..31 | 总量 9；返回 9；分页 5+4；9/9 页面 HTTP 200 | **1：限定范围完整** |

访问于 2026-09-16 11:44 AEST。9 条关键元数据无缺失、`content_id`/URL 无重复；3 条关联多个机构。正文和附件本轮未持久化、未分析。

## 三条真实样本

1. **[Air Pollution Awareness Coalition (APAC)](https://www.gov.uk/government/publications/air-pollution-awareness-coalition-apac)**  
   首次发布 2026-07-03；更新 2026-08-21；DEFRA、DHSC、DfT 共同关联。说明“首次发布日”和“更新日”不能混用。

2. **[30by30 on land in England: Delivery plan](https://www.gov.uk/government/publications/30by30-on-land-in-england-delivery-plan)**  
   首次发布 2026-07-13；`policy_paper`；DEFRA 关联。

3. **[British Sign Language 5-year plan: DEFRA – 1-year update, July 2026](https://www.gov.uk/government/publications/british-sign-language-5-year-plan-department-for-environment-food-and-rural-affairs-1-year-update-july-2026)**  
   首次发布 2026-07-15；非气候条目，证明分母不是由气候关键词结果拼出来的。

完整 9 条见 [`document_sample.csv`](document_sample.csv)。

## 发现的问题、能做与不能做

- Search API 可按 `first_published_at` 过滤，但本次不返回其填充值，用它排序还返回 422；日期必须用 Content API 二次核验并本地排序。
- 3/9 为多机构关联。后续必须预注册“都计、只计 lead、或分数计权”的规则。
- GOV.UK 多数内容受 OGL v3 许可，但附件、第三方权利和个人数据有例外；本轮只保存元数据。
- 动态索引的短窗口完整，不证明 1988–2026 历史完整，也不证明段落分母完整。
- **尚不能得出：** S/E 趋势、恐惧程度、政策先行、情绪上升、全球或英国政府总体结论。

## 下一小步与导师问题

下一步只做 3 个时间窗口的历史稳定性抽查，并确认 3 个共同署名记录的 lead/emphasised organisation；不进入模型训练。

请导师确认：

1. 机构层 S 对共同发布应全部计入、只计 lead，还是分数计权？
2. 权利/伦理逐项记录后，是否批准提取 3 个公开文件的少量正文段落，只验证 provenance，不做情绪标签？

## 60–90 秒口头汇报稿

这周我先把 proposal 里的来源问题缩成一个可验证的小任务：政府政策来源到底能不能稳定给出日期、类型和分母。我没有用气候关键词搜样本，而是在 GOV.UK 官方 Search API 中固定 2026 年 7 月、DEFRA 标签和 `policy_paper` 类型。接口报告总量 9，也实际返回 9 条；拆成两页是 5 加 4，集合完全一致。随后我用 Content API 和公开页面逐条核验，9 条的首次发布日期、更新时间、类型和链接都有效，没有缺失或重复。因此，这个非常限定的文档层可以判为状态 1，分母是 9。但它不是 DEFRA 全部发文，也不是全政府或段落分母。技术上还发现两个问题：Search API 的公开时间不能直接当首次发布日期，而且 3 条是多机构共同关联。下一步我建议先抽查历史稳定性，并请导师确认共同发布的计数规则，以及是否允许在完成权利和伦理记录后，对 3 个文件做少量正文 provenance 验证。

