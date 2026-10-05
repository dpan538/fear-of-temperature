# 政府收尾、独立分布审计与媒体转阶段

2026年10月5日。政府本轮有界补采、终态登记和独立分析已完成，可以进入媒体链路验证；政府全队列和各国原件覆盖尚未完成。固定发表区间为 **1988-01-01–2026-09-21**，2026年9月及末季度是部分区间。获取时间、正文版本时间、来源观察时间和本报告时间分别保留。

政府最终输入冻结于2026-10-04 19:57:43 UTC，manifest SHA256为 `4d60b7032ddbd200c7ee6cc6de8cb5c07e04830345a4b484c634cd4bf4b440c1`。UK分析复用2026-10-04 14:21 UTC已接受的有效元数据聚合；其他来源保持各自历史检查点。因此，本报告没有创造一个同步的国际独立文档总量，也没有刷新历史政府池化可读文本465/465个月的结论。

## 1. 补采的真实结果与停止边界

| 范围 | 本轮最终事实 | 保留缺口 |
|---|---|---|
| EU2015 | 冻结1,009 Works、979选定Item目标；原20复用，加27新保存，共47候选Item，22,231,574 bytes（约21.20 MiB），partial 0 | 1项当前HTTP406、931未尝试；另30 Works没有目标链接 |
| 原五项原件 | 首条Hansard官方HTML历史403；另外两条Hansard未尝试；AU首条landing本轮90秒读取超时，另一条landing未尝试，两份PDF均未请求 | 新原件0，原日期/版本/作者/出版者问题没有借CMS日期消除 |
| 新增检查 | 27份新PDF单次hash/签名/解析检查通过，257页有非空文本层，27个首页可视检查 | 没有逐页视觉阅读，也没有完整Work或组件覆盖认证 |
| 全部保存Item | 47身份、45不同raw SHA、392页面；18 COM/JOIN文件、29 OJ rendition | 7个首页多通知边界、10个选定Manifestation多Item、2组跨Work共享PDF；全部父长度资格为false |

两个CDM日与印刷日冲突均为2015-01-30与01-31，同月分配不变，日级证据冲突保留。所有新保存Item均在2015年1月，47/979约4.80%只表示候选Item暂存比例；不能解释为2015全年正文覆盖或完整Work完成率。22行当前缺口登记包含重叠问题，不能相加为独立错误数。详见[完整终态账本](01_gov_closeout/continuation/FINAL_B_STATUS_LEDGER.csv)、[原五项结果](01_gov_closeout/continuation/FINAL_A_DISPOSITIONS.csv)、[局部检查与限制](01_gov_closeout/continuation/HANDOFF_zh.md)。

旧失败Item的一次精确URI通配Accept请求返回200，随后另一Item返回406便停止。官方接口说明允许在精确URI已确定内容时使用通配Accept；这支持该修正的可审查性，但一次先后比较不能证明旧406的因果根源。旧失败、冷却和新停止均保留，没有展开sibling或自动续跑。[CELLAR接口说明，第21页](https://op.europa.eu/documents/10530/676542/ao10463_annex_17_cellar_dissemination_interface_en.pdf)、[Item与Work获取层次说明](https://op.europa.eu/documents/d/cellar/cellar_ml_dataset_guide)。原2 GiB政府raw上限、15 GiB floor和共享I/O锁保持；没有正式数据库导入。

## 2. 原算法可以用，但要修正统计单位和权重

| 原设计 | 本轮采用的修正 | 对研究的意义 |
|---|---|---|
| 季度覆盖率 | 在固定区间内使用完整155季度、465月份网格；区间日期不能强制分到某月；最后季度标partial | 有记录、已核实枚举零、覆盖未知、可读原文覆盖分别报告；不能以季度存在替代连续月份或完整覆盖 |
| 部门归一化熵 | Shannon熵除以声明且适用的类别数K的log，并同时给原熵/观测类别数；空期未定义、K=1归一化不可比 | 本轮缺部门沿革映射，计算的是来源路线构成，不能改叫部门均衡度，也不设“接近1才合格”的清洗目标 |
| 部门断层 | 重建完整历法网格，保存未观察/适用范围未知/明确零的状态，单列日期缺失及机构时代 | 直接unstack只补已出现年份会遗漏整年断层；首次/末次记录不能证明API适用边界 |
| 长度与Passage | 使用实际完整父正文和声明版本的实际tokenizer；限制单父贡献，记录重叠/特殊token预算 | 1000字符≈250 word pieces不能跨语言、类型通用；本轮Item长度只诊断文件边界，不估算Passage数 |
| 分层配额 | 稀疏层全保留且设计权重1；密集层若保留a个确定性长文，它们π=1，其余随机部分π=(Y−a)/(n−a)，权重为1/π | 原n/Y赋给全部样本会错误加权确定性选入的长文；稀疏层“补偿权重”不能制造未观测文档 |

最小配额只能登记缺额，不能补出不存在或未取得的文档。未来如做比较用平衡视图，应保留总体库和全部raw、明确目标总体与入选概率，并控制每父Passage贡献；本轮没有生产降采样。优先长文会改变长度、体裁和语义组成，需要单独说明，不能默认为更优训练数据。同一随机种子重复套每层也应改为稳定身份排序和可复现的分层随机流。

Coverage Index应是一组有分母的证据指标，不压成一个不透明总分。至少分开日历存在率、适用来源×月份的已核实覆盖率、可读父正文覆盖率及未知比例。本轮缺适用/完整枚举/可读父正文账本，相应指标为不可评估，不能把未知填0。

## 3. 分布结果与四张图

UK有效来源父身份 **248,319**（含镜像）；其中248,268可分配到单月，51为跨月区间；248,195有精确日元数据支持。官方路线239,871，声明K=5。镜像与共享回复的跨路线独立性未建立。

| UK元数据指标 | 结果 | 限制 |
|---|---:|---|
| 季度存在 | 155/155 | 不能代表连续可读正文覆盖 |
| 月份存在 | 434/465（93.33%） | 与历史跨来源可读文本465/465的输入和单位不同，不构成其反证 |
| 来源×月日历矩形存在 | 707/2,790（25.34%） | 含非适用/未知时代；不是有效来源覆盖率 |
| 官方路线归一化熵 | 0.61324 | 固定K=5；来源路线而非部门 |
| 官方路线HHI | 0.42199 | 描述保存来源父身份的构成 |
| 纳入镜像HHI | 0.39492 | 指标下降不能证明独立话语更多 |

季度官方路线HHI最低约0.34429，出现在2014Q3，只有34个保存父身份。接口交接和低样本量能造成极端变化；不能直接解释成部门垄断或气候事件。后续RQ1可报告来源×时代×体裁构成及低N敏感性，只有合适的测量和模型设计才能决定是否作为协变量，加入HHI并不自动消除混合偏差。

![UK来源与月份](/Users/jarlgiovanni/Desktop/fear_of_temperature/work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/01_gov_closeout/independent_review/figure_01_source_gap_map.png)

图1：修正后的UK来源元数据存在。浅灰表示观察跨度外未知，深灰表示跨度内未观察到父身份且覆盖仍未核实；两者都不是零表达。

![季度来源构成](/Users/jarlgiovanni/Desktop/fear_of_temperature/work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/01_gov_closeout/independent_review/figure_02_quarterly_concentration.png)

图2：官方路线与纳入镜像的季度HHI。镜像影响、接口时代切换、日期区间和末季度partial限制保留；没有推断检验或因果结论。

![政府原生计数与未知遮罩](/Users/jarlgiovanni/Desktop/fear_of_temperature/work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/01_gov_closeout/independent_review/figure_03_government_native_coverage.png)

图3：13个可视原生框架，完整465个月网格。蓝色是各自行的原生单位计数，灰色是覆盖未知或日期未核实，琥珀色是有保存证据的声明元数据/索引查询零；不可跨行把颜色当同一种独立正文数量。EU Work网格464个正值月加1个查询零月；IE171个索引月份为152正值、19查询零，不是部长回答正文。NZ仅2025年12个月的现有问题显示，用asked date和历史portfolio范围。AU821目录候选有819主表缺日期及2个旧日期未核实；7份旧原件是重叠子集，其中2份仅年份，不能把它们补成月分布。US元数据parent33,544与旧18,590 operational状态保留；未建立全部可读原件认证。来源检查点不同步，图不汇总国际独立总量。

![EU候选Item长度](/Users/jarlgiovanni/Desktop/fear_of_temperature/work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/01_gov_closeout/independent_review/figure_04_eu_item_lengths.png)

图4：47个保存Item的实际文本层codepoint长度，横向抖动只帮助显示。COM/JOIN文件18个、中位13,356.5；OJ rendition29个、中位8,175。空心圈保留跨Work共享raw的4个身份，黑线为Item中位数。封面、脚注、同页通知和组件限制存在；没有完整父长度小提琴、总体抽样声明、推断区间或Passage等价估计。

可复核表见[原生月份状态](01_gov_closeout/independent_review/government_native_month_cells.csv)、[覆盖分母与未知](01_gov_closeout/independent_review/government_native_coverage_summary.csv)、[季度构成](01_gov_closeout/independent_review/quarterly_concentration_official_routes.csv)、[Item形状记录](01_gov_closeout/independent_review/eu_item_shape_diagnostic.csv)。图同时提供PDF/SVG/320dpi PNG；18项封存评估器边界测试通过，四图最小PDF文字6pt、最终重叠错误0，并已逐图查看。[图形检查摘要](01_gov_closeout/independent_review/FIGURE_QA_SUMMARY.json)。

## 4. 媒体与报纸预采集：设计通过，真实正文待取得

同一现有媒体窗口完成V2整包；本协调者复核37项网络禁用测试及SQLite完整性/外键。稳定身份现在包含source、edition和有类型的native ID，防止同刊跨版次撞ID；纸报issue/page、正文版本、首发/更新/取得时间、OCR、转载/通讯社采用和许可字段分开。V1留存，真实记录与模拟夹具分开。见[schema](02_media_precollection/schema.sql)、[字段字典](02_media_precollection/FIELD_DICTIONARY.md)、[身份规则](02_media_precollection/IDENTITY_RULES_v2.md)、[链路](02_media_precollection/PIPELINE.mmd)。

| 互不重复的地理层 | 冻结候选来源 | 原定名额 | 新真实文章/正文 |
|---|---|---:|---:|
| EU/Europe，UK除外 | Irish Times（IE）、DW（DE） | 30 | 0 |
| UK | Guardian、BBC | 30 | 0 |
| AU | Sydney Morning Herald、ABC | 30 | 0 |
| US | New York Times、NPR | 30 | 0 |
| NZ | New Zealand Herald、RNZ | 30 | 0 |

每来源在1995-07、2015-12、2025-07各5篇，150名额尚未填充。EU是区域层，具体国家/编辑市场保留；这两国候选不代表全欧洲或各成员国。五层等额计划不等于各国具有相同可采量、已实现等额或全国代表性。

本轮仅保存一个212-byte HTTP200访问挑战，不是文章或可读目录。没有执行挑战或再次请求。旧Guardian396元数据/4篇正文诊断有历史范围，不能冒充本轮全话题150样本。真实正文抽取、OCR和转载识别仍未经过实际文章验证；模拟测试不能代替它们。

每个候选的最小待确认事实已合成[10来源访问就绪表](02_media_precollection/ACCESS_READINESS.csv)：具体title/year/edition是否可访问，元数据与全文允许用途，研究保留/导出范围，纸报issue/article/OCR边界。出版产品或图书馆目录存在不证明Dai/UQ已有相应权限。Guardian当前条款6(g)限制TDM，需匹配实际授权。[官方条款](https://www.theguardian.com/open-platform/terms-and-conditions)。1995的BBC网文框、报纸旧版和后期API分别记录时代缺口；缺额不转给其他地理层。

## 5. 下一轮只保留一个完整媒体任务

建议政府本轮关闭：保留可用输入、停止账本、47候选Item及未解决原件/组件问题；只在出现新可行访问证据或明确研究检查点需求时重开有界政府补采，不以填满979或抬高分布指标为目的。部门crosswalk和逐父长度可在确有用途时作一次限定存储字段导出，不阻止媒体推进。

下一轮沿用媒体现有窗口、GPT-6.1 Sol / Extra High，完成“现有访问证据核实 → 原150名额框枚举 → 实际article/issue/version登记 → 正文或OCR验证 → 日期、身份、转载与覆盖表 → 一次局部验收”这一整条链。冻结五层30名额，不转移缺额；只用已确认允许的路线，无法确认则提交真实缺口。保留128 MiB raw上限、15 GiB floor、共享锁、逐源间隔和持久停止。原型可运行不意味着本报告已放行新的访问受限来源请求。

相邻月份1995-08、2016-01、2025-08扩展暂缓；先验证原150名额。不要另拆接口/字段微任务，不自动采整卷报纸、不扩成大规模媒体库，也不按气候或恐惧挑文。真实样本到位后，再决定正式来源×时间框、可知入选概率及角色比较范围。

本轮证据层次：①来源/日期存在和有限可读Item证据已有；②气候/升温相关性与相似性未评估；③affect、risk、未来伤害或责任关联未验证；④fear特异解释未进行。后三层不作为当前采集或清洗的通过条件。RQ1/RQ2仍先于RQ3，覆盖与HHI不能建立情绪流或因果影响。

评估器在仓库外解封运行，既有V1保留，新增图形扩展在取得终态输入后形成，不能称为事前盲审注册。新版本以认证加密封存，保留输入/源码/输出校验及恢复、篡改拒绝记录，删除仅本轮创建的明文副本。凭据没有写进项目、采集消息、自动化或日志。共享OS账号下的加密防止无凭据直接读取，不构成操作系统权限隔离。采集窗口未取得审计源码或评分目标。
