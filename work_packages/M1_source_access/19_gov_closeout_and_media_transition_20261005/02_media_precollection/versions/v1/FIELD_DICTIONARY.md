# 媒体字段字典 v1

固定发表区间：1988-01-01–2026-09-21；2026-09部分。NULL表示未观测/未知，不是0。所有UTC字段保存ISO8601偏移；源日期按原精度保留。

本轮数据库是单独小型pilot。未实施新闻全文、OCR提取、转载自动判断或任何话题/情绪/恐惧标签；空的文章表是实际结果。原型的JSON-LD解析只做结构候选检查，不能保证全文边界。

## publisher

机构层，当前国家锚点与历史机构/作者所在地分开。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| publisher_id | TEXT / PK | 出版机构稳定键；当前机构不自动代表历史所有者。 |
| name | TEXT / NOT NULL | 出版机构记录名称。 |
| hq_country | TEXT / nullable | 机构总部国家候选锚点；须结合 hq_verification，不表示记者/读者所在地。 |
| hq_evidence_url | TEXT / nullable | 总部/机构身份核查凭据；不是授权证明。 |
| hq_verification | TEXT / NOT NULL | 总部事实的核实、候选或待核状态及适用年代。 |

## outlet

编辑来源层，本轮10个独立候选来源。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| source_id | TEXT / PK | 独立编辑来源键；同一来源跨月份不重新计为独立来源。 |
| publisher_id | TEXT / NOT NULL | 出版机构稳定键；当前机构不自动代表历史所有者。 |
| outlet_name | TEXT / NOT NULL | 媒体标题/产品名。 |
| outlet_type | TEXT / NOT NULL | newspaper/news_broadcaster 等载体分类，非部门或情绪分类。 |
| editorial_identity_evidence | TEXT / nullable | 编辑主体独立性依据；同一通讯社采用稿仍另存传播关系。 |
| official_home | TEXT / NOT NULL | 出版商官方站点，不表示访问成功。 |

## edition

五互斥配额层和具体编辑市场；逐文章历史版次仍未核。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| edition_id | TEXT / PK | 版次/市场键；当前候选锚点不冒充已核实历史版次。 |
| source_id | TEXT / NOT NULL | 独立编辑来源键；同一来源跨月份不重新计为独立来源。 |
| region_layer | TEXT / NOT NULL | 五个互斥配额层 EU_Europe/UK/AU/US/NZ；UK不重复进入Europe。 |
| edition_market | TEXT / NOT NULL | 目标编辑/发行市场与当前未核实事项，非作者国籍。 |
| edition_market_evidence | TEXT / nullable | 市场/版次核查证据。 |
| edition_verification | TEXT / NOT NULL | 逐项版次核实状态。 |
| region_assignment_basis | TEXT / NOT NULL | 来源分层依据；不能按报道地点或英语自动分配。 |

## source_era

30来源月单元；具体数字化、持权和所有者需要时期证据。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| era_id | TEXT / PK | 来源×版次×月份的时期登记键。 |
| edition_id | TEXT / NOT NULL | 版次/市场键；当前候选锚点不冒充已核实历史版次。 |
| month | TEXT / NOT NULL | YYYY-MM 发表框月份，不是抓取月份。 |
| medium | TEXT / NOT NULL | web/print/archive/OCR 等路线及载体；不同路线不可直接并为同一框。 |
| applicability | TEXT / NOT NULL | 该年代路线适用性，含未创办/未上线/未数字化/未知等。 |
| era_scope_note | TEXT / NOT NULL | 时期跨度、换版/所有者/索引缺口说明；不推定连续覆盖。 |
| route | TEXT / nullable | 当期官方/图书馆/许可路线；候选路线不表示获授权。 |
| rights_status | TEXT / NOT NULL | 许可/TDM核实状态；与实际访问成功和可公开分享分开。 |
| rights_evidence_url | TEXT / nullable | 许可判断所用官方条款/产品说明及其适用范围。 |
| access_status | TEXT / NOT NULL | 请求/授权/拦截/未尝试等访问状态。 |
| access_entitlement | TEXT / nullable | 当前账号/机构具体权利证据；本轮全部未建立，未查凭据。 |
| checked_at_utc | TEXT / nullable | 当前核查记录时刻，ISO8601带UTC偏移；非历史内容时刻。 |
| publisher_at_time | TEXT / nullable | 此发表时期的机构/所有者；NULL表示未知，不回填当前所有者。 |
| publisher_at_time_verification | TEXT / NOT NULL；default='unknown; current owner must not be backdated' | 历史所有者/机构证据状态与年代。 |

## frame

日期/文种全话题框；观察、完整枚举、确证零值和未知须分离。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| frame_id | TEXT / PK | 来源×月份全话题候选框键；未完整枚举仍保留。 |
| era_id | TEXT / NOT NULL | 来源×版次×月份的时期登记键。 |
| provider | TEXT / NOT NULL | 框提供者/官方系统标识。 |
| month | TEXT / NOT NULL | YYYY-MM 发表框月份，不是抓取月份。 |
| unit | TEXT / NOT NULL | article_publication_instance：媒体一次发表实例，非版面、版本或原创故事。 |
| date_filter_json | TEXT / NOT NULL | 明确日期边界、使用首发表/更新日期的规则及固定研究上限。 |
| type_filter_json | TEXT / NOT NULL | 来源特有文种映射；无话题过滤；未核文种需标记pending。 |
| topic_query | TEXT / nullable | 本轮必须NULL；不能在结构清理中筛气候/恐惧。 |
| enumeration_state | TEXT / NOT NULL | complete_month_frame、partial、unknown、stop、not_applicable 等；空页不等于零。 |
| visible_provider_count | INTEGER / nullable | 提供者页面显式计数；保留过滤条件，不能升级为月总体。 |
| observed_unique_links | INTEGER / nullable | 实际观察的独立文章链接数；导航日期链接不算文章。 |
| monthly_denominator | INTEGER / nullable | 仅明确、完整、适用月框的独立发表实例总数；否则NULL。 |
| denominator_unit | TEXT / nullable | 分母单位及排重范围，避免将issue/page/raw/版本当文章。 |
| count_evidence | TEXT / nullable | 计数/索引证据路径、URL或原始hash凭据。 |
| page_limit | INTEGER / NOT NULL | 冻结的索引页上限，达到上限并不表示枚举完成。 |
| visited_pages | INTEGER / NOT NULL；default=0 | 本地保存的实际框页数；web文档检查另列，不捏造本地请求。 |
| scope_detail | TEXT / NOT NULL | 提供者、日期、文种、已观察页、截断和缺口说明。 |
| retrieval_at_utc | TEXT / nullable | 框实际抓取时刻；无框请求则NULL。 |

## article_parent

独立发表实例；本轮实表为空，不能以导航链接造文章。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| parent_id | TEXT / PK | 稳定独立article parent键；跨来源传播各有parent。 |
| source_id | TEXT / NOT NULL | 独立编辑来源键；同一来源跨月份不重新计为独立来源。 |
| edition_id | TEXT / NOT NULL | 版次/市场键；当前候选锚点不冒充已核实历史版次。 |
| native_id | TEXT / NOT NULL | 提供者原生文章ID；缺失时保留canonical URL后备及其basis。 |
| native_id_basis | TEXT / NOT NULL | native ID/URL后备/待核的具体依据，不伪称原生ID已验证。 |
| canonical_url | TEXT / NOT NULL | 仅去已知追踪参数；保留可能决定身份的query参数。 |
| language | TEXT / nullable | 正文/元数据语言及其核实状态，未知不默认为英语。 |
| genre | TEXT / NOT NULL | 新闻、评论、社论、来信等文种；unknown保留，不能以低情绪剔除。 |
| publishing_role | TEXT / NOT NULL | 本轮出版主体media；来信作者、政府引述者另存attributed_voice。 |
| first_publication_value | TEXT / nullable | 源原样首发表时间；不得用更新或抓取时间替代。 |
| first_date_precision | TEXT / NOT NULL | timestamp_with_offset/day/unknown等；URL日期只能候选。 |
| first_timezone | TEXT / nullable | 明确偏移/时区证据；缺少则NULL，不自动按总部补区。 |
| first_date_min | TEXT / nullable | 未知/粗精度首发表的可证下界；NULL不表示1988年。 |
| first_date_max | TEXT / nullable | 首发表可证上界；与min共同保存不确定范围，不能冒充精确日。 |
| date_evidence | TEXT / nullable | 首发字段、官方索引/版面和冲突说明。 |
| byline | TEXT / nullable | 署名原值；不将被引述者作为署名。 |
| author_geography_json | TEXT / nullable | 作者可核身份/所在地及其证据；不能由媒体总部推断。 |
| reported_places_json | TEXT / nullable | 文章报道地点；与作者、市场、配额层分开。 |
| identity_state | TEXT / NOT NULL | 文章身份/parent映射核实或待核状态。 |

## paper_issue

纸报期号层；本轮未取得issue。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| issue_id | TEXT / PK | 纸报期号/发行实例键，不是文章parent。 |
| edition_id | TEXT / NOT NULL | 版次/市场键；当前候选锚点不冒充已核实历史版次。 |
| issue_date_value | TEXT / nullable | 期号印刷日期原值；未核不写作每篇首发时间。 |
| date_precision | TEXT / NOT NULL | 期号或定位日期精度，未知需保留。 |
| volume | TEXT / nullable | 纸报卷号原值。 |
| issue_number | TEXT / nullable | 纸报期号原值。 |
| issue_locator | TEXT / nullable | 出版商/图书馆期号定位标识。 |
| evidence_url | TEXT / nullable | 该期号/结构/来源关系官方证据定位。 |

## article_locator

文章页/栏/OCR边界；整页≠一篇，续页不自动新增parent。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| locator_id | TEXT / PK | article与纸报/OCR位置关系键。 |
| parent_id | TEXT / NOT NULL | 稳定独立article parent键；跨来源传播各有parent。 |
| issue_id | TEXT / nullable | 纸报期号/发行实例键，不是文章parent。 |
| page_start | TEXT / nullable | 起始页标签，可为非数值版面名。 |
| page_end | TEXT / nullable | 结束页标签；跨页续文属于同一parent时须核实。 |
| ocr_native_id | TEXT / nullable | 档案提供者OCR组件/文章ID，不能只按页面生成文章。 |
| ocr_bbox_json | TEXT / nullable | 页内边界框及坐标体系；跨栏/续页需单独核查。 |
| layout_status | TEXT / NOT NULL | 版面、栏、导航、版头/广告混入等结构检查状态。 |
| boundary_status | TEXT / NOT NULL | OCR文章边界核实状态，未核不认定整页为一篇。 |
| locator_evidence | TEXT / nullable | 页面/组件/边界定位证据，遵守访问和raw限制。 |

## raw_object

原响应/partial证据；本轮1个212-byte访问验证页。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| raw_id | TEXT / PK | 本地raw对象键；由路径与sha派生，允许相同内容的不同请求证据。 |
| path | TEXT / NOT NULL | 相对本交付目录路径；禁止raw符号链接。 |
| sha256 | TEXT / NOT NULL | 完整已保留对象的SHA256；partial hash仅代表已保留字节。 |
| byte_count | INTEGER / NOT NULL | 实际本地保存字节数；partial也计入128 MiB。 |
| mime_type | TEXT / nullable | 响应Content-Type原值；不能据此推定正文可读。 |
| object_kind | TEXT / NOT NULL | article_HTML/index/catalogue/PDF/OCR等对象种类；本轮仅challenge HTML。 |
| is_partial | INTEGER / NOT NULL | 0/1；中断和截断残件保留计费，不冒充完整对象。 |
| rights_status | TEXT / NOT NULL | 许可/TDM核实状态；与实际访问成功和可公开分享分开。 |
| redistribution_status | TEXT / NOT NULL | 可分享元数据/许可正文/限制证据等独立状态；TDM权利不等于公开再分发。 |
| request_id | TEXT / nullable | 稳定单次请求键；相同冻结路线不自动重复。 |
| retained_at_utc | TEXT / NOT NULL | 对象保留时刻；不是发表或历史版本时间。 |

## article_version

正文观察/更新版本；本轮实表为空。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| version_id | TEXT / PK | article内容观察版本键，与独立parent分开计数。 |
| parent_id | TEXT / NOT NULL | 稳定独立article parent键；跨来源传播各有parent。 |
| raw_id | TEXT / nullable | 本地raw对象键；由路径与sha派生，允许相同内容的不同请求证据。 |
| raw_publication_value | TEXT / nullable | 此响应中的源原始首发字段，可与规范parent日期对核。 |
| updated_value | TEXT / nullable | 源原始更新字段；不反推历史正文与当前正文一致。 |
| updated_precision | TEXT / NOT NULL | 更新字段精度/未知状态。 |
| content_version_time | TEXT / nullable | 可验证内容版本时刻；不得仅以抓取时刻填充。 |
| content_time_precision | TEXT / NOT NULL | 版本时刻精度/未知状态。 |
| retrieved_at_utc | TEXT / NOT NULL | 实际抓取内容的UTC时刻。 |
| retrieval_precision | TEXT / NOT NULL | 实际记录时刻的精度。 |
| body_storage_path | TEXT / nullable | 获准保留的正文派生路径；无正文或未获权限则NULL。 |
| body_sha256 | TEXT / nullable | 被保留正文hash；不等于页面raw hash。 |
| readability_status | TEXT / NOT NULL | preview/no_body/OCR_pending/body_boundary_pending/readable_verified等；HTTP200不充分。 |
| preview_status | TEXT / NOT NULL | paywall_or_preview/not_established等，避免把摘要当全文。 |
| ocr_quality_status | TEXT / NOT NULL | OCR可读、乱码、缺页和待核状态；不要代替文章边界。 |
| layout_status | TEXT / NOT NULL | 版面、栏、导航、版头/广告混入等结构检查状态。 |
| rights_status | TEXT / NOT NULL | 许可/TDM核实状态；与实际访问成功和可公开分享分开。 |
| access_status | TEXT / NOT NULL | 请求/授权/拦截/未尝试等访问状态。 |
| extractor_version | TEXT / NOT NULL | 确定的结构解析器版本，不是模型/情绪标签版本。 |
| version_evidence | TEXT / nullable | 来源版本、内容映射与差异核查依据。 |

## frame_membership

重复索引记录；重复URL不增加独立parent。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| frame_id | TEXT / PK | 来源×月份全话题候选框键；未完整枚举仍保留。 |
| parent_id | TEXT / PK | 稳定独立article parent键；跨来源传播各有parent。 |
| index_url | TEXT / PK | 实际索引出处；不是文章正文URL。 |
| index_occurrence_count | INTEGER / NOT NULL | 同索引的重复出现数；索引重复与传播/版本重复分开。 |
| identity_evidence | TEXT / nullable | 索引链接到native parent的核查证据。 |

## story_cluster

原始故事身份；语义去重须以后验证，本轮不自动判定。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| story_id | TEXT / PK | 通讯社原稿/转载/镜像候选故事簇键，不替代各媒体parent。 |
| cluster_kind | TEXT / NOT NULL | wire_story/syndication/mirror/unresolved_candidate。 |
| origin_provider | TEXT / nullable | 原稿通讯社/编辑机构，未知NULL。 |
| origin_native_id | TEXT / nullable | 原始story ID；没有证据不能靠文本相似度宣称已核实。 |
| origin_first_date | TEXT / nullable | 原稿首发表时间，区别于媒体采用发表时间。 |
| verification_state | TEXT / NOT NULL | 关系已核、待核、冲突等状态；不使用单一不透明置信分。 |
| evidence | TEXT / NOT NULL | 关系或原稿证据位置/原始ID依据。 |

## publication_relationship

采用/转载/镜像关系；保留每家发表实例及其日期。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| relation_id | TEXT / PK | 逐传播/版本/索引关系键。 |
| parent_id | TEXT / NOT NULL | 稳定独立article parent键；跨来源传播各有parent。 |
| related_parent_id | TEXT / nullable | 关系另一端媒体parent；未知可NULL，必须保留关系证据。 |
| story_id | TEXT / nullable | 通讯社原稿/转载/镜像候选故事簇键，不替代各媒体parent。 |
| relation_kind | TEXT / NOT NULL | wire_adoption/syndication/mirror/same_document_version/duplicate_index/unresolved_candidate。 |
| verification_state | TEXT / NOT NULL | 关系已核、待核、冲突等状态；不使用单一不透明置信分。 |
| evidence | TEXT / NOT NULL | 关系或原稿证据位置/原始ID依据。 |
| publication_instance_retained | INTEGER / NOT NULL | 强制1；传播关系不得把两家发表实例合并删除。 |

## attributed_voice

署名、引述者、来信作者角色；不把话语持有者等同媒体情绪。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| voice_id | TEXT / PK | 逐署名/引述/来信说话者键。 |
| version_id | TEXT / NOT NULL | article内容观察版本键，与独立parent分开计数。 |
| voice_kind | TEXT / NOT NULL | byline/quoted_speaker/reader_letter_author/editorial_voice/unknown。 |
| speaker_name | TEXT / nullable | 文本可证说话者名称，未知NULL。 |
| speaker_role | TEXT / nullable | government/media/civic等人物角色；不改变出版主体。 |
| speaker_geography_json | TEXT / nullable | 人物地理证据；未知保留，不从媒体所在地补值。 |
| quotation_locator | TEXT / nullable | 可追溯原文段落/页/字符位置；本轮不标情绪。 |
| attribution_state | TEXT / NOT NULL | 说话者归属的核实/待核/冲突状态。 |
| quotation_and_publishing_role_separate | INTEGER / NOT NULL | 强制1；新闻引述政府仍属media发表实例。 |

## provenance_assertion

来源质量多维登记；不验证原文全部事实，不排序官方高于公民。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| assertion_id | TEXT / PK | 逐来源质量核查断言键。 |
| parent_id | TEXT / NOT NULL | 稳定独立article parent键；跨来源传播各有parent。 |
| version_id | TEXT / nullable | article内容观察版本键，与独立parent分开计数。 |
| provenance_class | TEXT / NOT NULL | 相对于该次表达：direct_original/archival_reproduction/indirect_secondary/mixed/unresolved。 |
| identity_verification | TEXT / NOT NULL | 独立身份核查状态。 |
| date_mapping_verification | TEXT / NOT NULL | 独立发表日期映射核查状态。 |
| content_mapping_verification | TEXT / NOT NULL | 独立正文/版本/原件映射核查状态。 |
| conflict_note | TEXT / nullable | 有冲突时的两项证据和未解处，不能以总体评分掩盖。 |
| access_limit | TEXT / nullable | 访问限制及其使哪些事实无法验证。 |
| evidence_locator | TEXT / NOT NULL | 原始证据定位与hash/页/字段，可追溯。 |
| verified_at_utc | TEXT / nullable | 实际核实断言时间。 |
| truth_of_reported_claims_assessed | INTEGER / NOT NULL；default=0 | 本schema固定0；来源核实不验证文中所有事实为真。 |

## sample_slot

150冻结槽位；本轮均未填，pi均NULL，库存不下采样。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| slot_id | TEXT / PK | 冻结的地区×来源×月份×序号槽位键；未填也保留。 |
| frame_id | TEXT / NOT NULL | 来源×月份全话题候选框键；未完整枚举仍保留。 |
| slot_index | INTEGER / NOT NULL | 本来源月内1–5；不将失败配额转给别层/来源。 |
| parent_id | TEXT / nullable | 稳定独立article parent键；跨来源传播各有parent。 |
| status | TEXT / NOT NULL | 真实请求/槽位状态；filled_metadata_only不表示全文完成。 |
| unfilled_reason | TEXT / nullable | 具体时期/访问/许可/框缺口，非气候/恐惧原因。 |
| selection_design | TEXT / NOT NULL | 本轮first-five非概率先导；只有complete-frame概率设计可填写pi。 |
| pi | REAL / nullable | 单位入选概率，仅完整明确概率框才可知；本轮全NULL。 |
| pi_basis | TEXT / nullable | n/N、抽样方法/种子/框ID等可复核依据；非概率不得伪造。 |
| planned_region_weight | REAL / NOT NULL | 比较设计预设地区权重0.2；不是已观察人口权重。 |
| planned_source_within_region_weight | REAL / NOT NULL | 预设层内来源权重0.5；缺失不可静默重归一。 |
| observed_inventory_weight | REAL / NOT NULL；default=1 | 拟采用库存单位权重1；只对非NULL parent应用，本轮真实文章库存贡献为0；不按等额目标删库。 |

## request_attempt

仅本地HTTP真实尝试；WEB_ROUTE_CHECKS单独保留工具可见观察。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| request_id | TEXT / PK | 稳定单次请求键；相同冻结路线不自动重复。 |
| source_id | TEXT / NOT NULL | 独立编辑来源键；同一来源跨月份不重新计为独立来源。 |
| purpose | TEXT / NOT NULL | 冻结请求目的，catalogue/索引/原件须区分。 |
| request_url | TEXT / NOT NULL | 确切批准路线；不含认证token，不自动跟随重定向。 |
| requested_at_utc | TEXT / NOT NULL | 真实本地请求起始时刻，文档观察日志不能冒充它。 |
| finished_at_utc | TEXT / nullable | 请求结束时刻。 |
| http_status | INTEGER / nullable | 真实本地响应状态；web工具未知origin status必须NULL。 |
| status | TEXT / NOT NULL | 真实请求/槽位状态；filled_metadata_only不表示全文完成。 |
| final_url | TEXT / nullable | 不自动跳转时响应URL；未知不补写。 |
| response_headers_json | TEXT / nullable | Content-Type/Length/Date/ETag/Last-Modified/Retry-After等白名单；不保存Cookie或凭据。 |
| raw_id | TEXT / nullable | 本地raw对象键；由路径与sha派生，允许相同内容的不同请求证据。 |
| error | TEXT / nullable | 终止原因；网络异常细节省略以免暴露环境秘密。 |
| retry_not_before_utc | TEXT / nullable | Retry-After的最早可请求时刻；即使届时也不自动解除stop。 |
| transport | TEXT / NOT NULL | 实际使用的工具/requests路径及不自动重试规则。 |

## legacy_diagnostic

4个Guardian既有body检查收据，不是新实采全文或背景样本。

| 字段 | SQLite类型 / 必填或默认 | 定义 |
|---|---|---|
| diagnostic_id | TEXT / PK | 历史诊断收据键，不加入当前槽位。 |
| source_id | TEXT / NOT NULL | 独立编辑来源键；同一来源跨月份不重新计为独立来源。 |
| parent_url | TEXT / NOT NULL | 历史文章URL；非本轮新获取article parent。 |
| original_publication_value | TEXT / nullable | 原诊断记录的源首发表原值；保持历史scope。 |
| content_hash_receipt | TEXT / nullable | 历史正文/检查hash字段原收据；没有本地全文也可保留。 |
| evidence_path | TEXT / NOT NULL | 已有证据文件相对项目路径；仅读未改。 |
| evidence_sha256 | TEXT / NOT NULL | 已有证据文件hash；冻结报告和标签未改。 |
| original_scope | TEXT / NOT NULL | 原environment/标题选择框，不作为全话题背景样本。 |
| current_pilot_slot_eligible | INTEGER / NOT NULL | 强制0，防止396/4历史记录补填新配额。 |
| full_body_locally_retained | INTEGER / NOT NULL | 强制0，历史CSV有检查/摘录收据不表示本地保留全文。 |
| diagnostic_note | TEXT / NOT NULL | 历史诊断边界、未复抓/未重标及版本未知说明。 |

## 约束与统计口径

- FK完整性、独立native身份、槽位唯一性、article parent与版本/issue分离由schema保证。
- 月分母仅complete_month_frame允许非NULL；本轮所有分母NULL。真实publication zero需要适用完整框及证据，不能由空页推定。
- 本轮pi=NULL。未来只有明确定义总体和概率抽样设计，才在此框内记录pi；表约束与trigger阻止将非概率/partial frame写成已知概率。完整框标签仍必须人工审查证据，SQL不会证明提供者实际完整。
- equal quotas和0.2×0.5仅是固定比较设计，不能证明全国代表性。缺失不能自动重配额或重归一；传播库存全部保留。
- provenance按该次表达判断：原创媒体文章可为媒体表达的direct_original；引述政府人物的真实性和说话者情绪是另外的问题。
- web工具文档观察未提供原HTTP/字节/精确请求时刻时，保留未知；本地请求与212-byte raw有可校验hash。
