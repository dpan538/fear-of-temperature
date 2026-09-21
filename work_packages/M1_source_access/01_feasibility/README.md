# M1.1 单一来源可行性先导

> 组会版结论：GOV.UK 可为一个严格限定的政策来源层提供可审计的**文档级分母**。本轮完整枚举了 2026-07-01 至 2026-07-31 首次发布、标记到 DEFRA、类型为 `policy_paper` 的 9 个 GOV.UK publication landing-page content items。9/9 条的 Search API、Content API 元数据与公开 HTML 均已实际访问验证。

**判定：状态 1（限定范围内完整列表及总量已核验），conditional go。** 这里的 `N_total=9` 不是“DEFRA 全部发文量”、不是“英国政府全部政策量”，也不是段落分母。

## 本轮做了什么

- 阅读 proposal 中关于来源分层、S 分母、时间对齐、数据治理和伦理前置的要求。
- 在 GOV.UK 同一官方接口内比较三个机构 strata；2026 年 7 月首次发布的 `policy_paper` 数量分别是 DEFRA 9、DESNZ 4、Cabinet Office 4。
- 选择 DEFRA，因为一个固定完整月恰好得到交接文件要求的 5–10 条；选择不是基于 climate/heat 关键词。
- 用 Search API 枚举、用 Content API 逐条核验首次发布日期/更新时间/文档类型/机构，用 canonical HTML 做可访问性检查。
- 实测分页（`start=0,count=5` 与 `start=5,count=5`）得到 5+4 条，合并集合与一次性返回的 9 条完全一致。
- 只持久化索引与内容元数据；没有保存、解析或分类正文，没有采集公众个人内容。

## 关键结果

| 检查 | 实测结果 |
|---|---:|
| Search API 报告总量 / 返回量 | 9 / 9 |
| Content API 元数据成功 | 9 / 9（HTTP 200） |
| canonical HTML 可访问 | 9 / 9（HTTP 200） |
| 关键字段缺失 | 0 |
| 重复 `content_id` / canonical URL | 0 / 0 |
| 多机构共同署名或共同标记 | 3 / 9 |
| 正文持久化 / 段落样例 | 0 / 0 |

访问时间：2026-09-16 01:44:09 UTC（11:44:09 AEST）。动态索引后续可能因补录、撤稿或更新而变化，因此保留了请求 URL、访问时间与证据文件 SHA-256。

## 文件导航

- [`meeting_brief.html`](meeting_brief.html)：今天可直接展示的中文单页材料，含 60–90 秒口头稿。
- [`meeting_brief.md`](meeting_brief.md)：同内容的 Markdown 版本。
- [`source_access_register.csv`](source_access_register.csv)：三个候选 strata、访问路线、总量、条件与权利状态。
- [`document_sample.csv`](document_sample.csv)：9 条真实可点击记录；本轮样本就是该限定查询的完整枚举结果。
- [`denominator_assessment.md`](denominator_assessment.md)：分母判定、证据、限制、风险与下一步。
- [`checks.json`](checks.json)：机器可读验收结果、请求 URL、HTTP 状态、缺失/重复/分页检查。
- [`evidence/search_index_snapshot.json`](evidence/search_index_snapshot.json)：Search API 结果的最小化证据快照。
- [`evidence/content_metadata_snapshot.json`](evidence/content_metadata_snapshot.json)：逐条 Content API 元数据快照，不含持久化正文。
- [`scripts/collect_and_check.py`](scripts/collect_and_check.py)：仅用 Python 标准库的独立复查脚本。

## 如何复查

先打开 `meeting_brief.html`。逐条检查时打开 `document_sample.csv` 中的 `canonical_url`。机器复查可在项目根目录运行：

```bash
/usr/bin/python3 work_packages/M1_source_access/01_feasibility/scripts/collect_and_check.py
```

脚本会访问公开官方端点并重写 CSV、JSON 与 evidence 快照；因为 GOV.UK 是动态索引，重跑时间不同可能得到不同快照。无需项目 `.venv`，本次实际运行使用系统 Python 3.9.6，不会干扰另一窗口的 NLP 环境。

选定查询（点击可复查）：[GOV.UK Search API：DEFRA / policy_paper / first_published_at 2026-07-01..2026-07-31](https://www.gov.uk/api/search.json?filter_organisations=department-for-environment-food-rural-affairs&filter_content_store_document_type=policy_paper&filter_first_published_at=from%3A2026-07-01%2Cto%3A2026-07-31&count=50&order=public_timestamp)。

## 日期与单位约定

- `published_at`：Content API 的 `first_published_at`，不是搜索响应中的 `public_timestamp`。
- `updated_at`：Content API 的 `public_updated_at`。
- `accessed_at`：本轮脚本访问时间。
- 分母单位：一个 GOV.UK publication landing-page content item（document）。附件和段落不另计；因此本轮没有段落级完整性主张。
- 机构规则：只要记录被 GOV.UK 标记到 DEFRA 就纳入，包含共同署名/共同标记记录；不是“DEFRA 独家作者”口径。

## 已确认的技术问题

1. Search API 接受 `first_published_at` 作为日期过滤字段，但本次响应没有返回已填充的该字段；把它用作 `order` 又返回 HTTP 422。因此脚本通过 Content API 逐条取回首次发布日期，再在本地排序。
2. 9 条中有 3 条关联多个机构。后续若计算机构注意力，需要预注册“全部计入、主机构计入或分数计权”规则。
3. GOV.UK 官方说明多数内容适用 OGL v3，但第三方材料、个人数据和另行声明内容存在例外；附件级权利尚未逐项审核。
4. 官方文档没有给出这个查询层的精确历史起点。短窗口枚举成功不证明 1988–2026 全历史完整。

## 官方依据

- [GOV.UK Search API 使用文档](https://docs.publishing.service.gov.uk/repos/search-api/using-the-search-api.html)：公开端点、严格参数校验、日期过滤、分页以及 `count` 最大值 1500。
- [GOV.UK Content API 文档](https://docs.publishing.service.gov.uk/repos/content-store/content-store-api.html)：按 GOV.UK 路径读取公开内容项 JSON。
- [GOV.UK Terms and conditions](https://www.gov.uk/help/terms-conditions)：多数 GOV.UK 内容按 OGL 发布，但有例外且内容可变更/移除。
- [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)：复用、署名与例外条件。

## 明确不做的解释

这 9 条没有被标注“恐惧”、没有计算 S/E、没有形成气候议题趋势、没有证明政策先行或社会情绪变化。它们只证明：在这个限定 stratum 中，来源访问和文档级分母有一条可复查的实现路线。

