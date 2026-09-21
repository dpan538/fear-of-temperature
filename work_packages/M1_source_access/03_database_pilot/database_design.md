# M1 小规模数据库试点：设计与计数契约

## 存储选择

本试点沿用仓库已经验证的 **DuckDB + CSV 导出**。理由是：项目的现有 `corpus` 模块、README 和架构文档已经采用本地 DuckDB；9 条元数据不需要服务进程；DuckDB 能提供外键、唯一约束、可检查 SQL 和后续 Parquet/向量流程的接口。这里的数据库选择只解决存储与追溯，不解决跨角色、跨年代或研究测量的归一化。

## 当前数据流

`M1.1 保存的 Search/Content API 元数据 → 原始记录版本 → 规范化文档版本 → 当前文档`

同时保留：

- 来源 → 采集批次 → 覆盖/分母记录；
- 文档 ↔ 全部 GOV.UK 机构关联；
- 当前文档版本 → 原始记录 → 查询批次的完整追溯；
- 空的文本段落、声音归因和文档关系接口，供获得合法正文后扩展。

## 表及边界

| 表 | 本轮用途 | 关键边界 |
|---|---|---|
| `sources` | 来源角色、访问方式、实际覆盖、许可、伦理和文档链接 | `policy` 是发布功能；不等于引用者或被引用说话者 |
| `collection_batches` | 固定查询、首次发布日期窗、分页、数量和证据哈希 | 批次采集时间不等于发布日期 |
| `coverage_records` | 文档级分母及严格适用范围 | `9` 只属于同一 GOV.UK/DEFRA/type/month/filter/dedup 范围 |
| `raw_records` | 保存 Content API 元数据原貌及 SHA-256 | 不覆盖旧载荷；变化产生新记录 |
| `documents` | 稳定 ID、URL、标题、语言、三类日期、角色、正文状态 | 当前只含 9 个真实 `document`；无正文 |
| `document_versions` | 原始载荷或规范化规则改变时形成版本 | 同一文档恰有一个 `is_current=true` |
| `document_version_raw_links` | 文档版本回溯原始记录 | 再回溯到 collection batch 和 source |
| `organisations` / `document_organisations` | 完整保存多机构关联 | 多机构不增加文档总数；lead 状态为 `unknown` |
| `text_segments` | 父文档、顺序、定位、文本哈希和真实/合成边界 | 本轮为空；没有合法正文时不填造内容 |
| `voice_attributions` | quoted speaker / emotion holder 接口 | 与 `documents.publisher_role` 明确分离，本轮为空 |
| `document_relationships` | 重复、来源重叠、引用、回复、转发接口 | 没有正文或跨来源语料时保持为空/unknown |

完整逐字段字典见 `data_dictionary.csv`，它由实际 DuckDB schema 重建生成，避免文档与数据库字段漂移。

## 稳定 ID 与版本规则

- `source_id = hash(normalised publisher role, source name)`。
- `document_id = hash(source_id, GOV.UK content_id)`；重建后稳定。
- `batch_id = hash(source_id, query URL, accessed_at, metadata snapshot SHA-256)`。
- `raw_record_id = hash(batch_id, external_id, raw payload SHA-256)`。
- `document_version_id = hash(document_id, raw payload SHA-256, rule version, rule SHA-256)`。
- 同一批次重复导入采用主键/唯一约束与 upsert，不增加行。
- 原始载荷变化会新增原始记录和文档版本；规则变化必须使用新 `rule_version`，否则导入拒绝。

## 日期、角色与单位

- `publication_date`：保留来源时间戳中的英国日历日期，是本轮时间窗核验和未来时间分箱依据，不受运行机器时区影响。
- `publication_timestamp`：Content API `first_published_at` 的完整带时区时刻，用于精确追溯。
- `updated_timestamp`：Content API `public_updated_at`；不得代替首次发布日期。
- `collected_at` / `accessed_at`：证据获取时间。
- 当前来源角色是 `policy`，依据发布机构功能；未来 `media`、`public` 按相同字段契约进入。
- 当前计数单位是唯一文档；未来主帖和评论分别使用 `unit_type=post/comment`，回复/引用/转发使用父项和关系字段，不混作同一单位。
- 段落是后续切段/向量化单位，必须保留父文档 ID 和顺序；文档级统计不能按段落数膨胀。

## 多机构计数

9 个文档保持 9 个文档；14 条机构关系全部保存。每条关系同时记录：

- `full_count_weight=1`：按机构分别列示时每个关联机构完整计入；
- `fractional_count_weight=1/k`：跨机构合计时，一个含 `k` 个机构的文档总权重为 1。

这两个字段使规则显式可选，但本试点不据此发布机构注意力统计。Lead/emphasised organisation 没有在 M1.1 中核验，保持 `unknown`。

## 伦理、许可与正文门槛

已审阅材料明确写明没有伦理 clearance 声明，也没有逐件正文/附件权利审核。因此来源和文档的 `ethics_status` 均为 `pending`，`licence_status` 为 `pending_item_and_attachment_review`，真实 `text_segments` 为 0。只有在可核验的伦理路线及逐项权利条件建立后，正文才可进入切段接口。
