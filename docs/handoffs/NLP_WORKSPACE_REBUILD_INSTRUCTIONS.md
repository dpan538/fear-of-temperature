# 新窗口实施指令：重建可在 VS Code 使用的 Python/NLP 工作区

你接手的是一个已有研究资料、历史脚本、数据和完整 proposal 的本地仓库。请直接实施并验证以下任务，而不是只提交架构建议、目录空壳或安装说明。用户已授权本任务所需的项目内环境创建、依赖/合理大小的公开模型下载、kernel 注册和文档更新。

## 1. 项目位置与权威来源

在此现有工作目录实施：

`/Users/jarlgiovanni/Desktop/fear_of_temperature`

先检查工作树、适用的 AGENTS.md、现有目录、Python/CPU 架构、内存/磁盘、VS Code CLI 和已安装环境，再阅读：

1. `proposal/thesis_proposal.md`：最新研究内容的主要依据。
2. `proposal/README.md`、`proposal/discussion_log.md`：版本入口和用户已确认决定。
3. `proposal/compression_review.md`、`proposal/reference_scope_review.md`：最新方法补充及引用取舍。
4. `proposal/finalisation_review.md`：伦理与技术定位记录；开头已注明部分引用记录为历史状态。
5. 根 `README.md`、`requirements.txt`、`.gitignore`，以及现有 `scripts/`、`db/`、`data/`、`notebooks/`、`tests/`。

以当前用户要求和最新 proposal 为准。原始研究报告、历史 README、旧交接说明是背景材料，不自动成为新的实现要求。

## 2. 研究定位必须准确

当前标题：**Fear of temperature: Computational analysis of policy, media and public climate emotions**。

项目使用 CS/NLP 方法研究升温恐惧及社会情绪，属于 computational social science / climate communication。学位论文及研究发现是主要成果；可复现语料、代码、方法和潜在算法是支持性贡献，不声称已经有新架构或研究结果。

- 主要比较政府/政策、新闻媒体、公众表达的领先、滞后、同步和反馈。
- 英语为核心，覆盖美国、欧洲、澳大利亚、新西兰；中文与新增地区为扩展候选。
- 1988–2026 是目标收集范围；1938及更早材料只是可选历史context；实际统计只用有足够共同覆盖的窗口。
- 长期升温预期是重点，直接高温危险统一采集后分别标注；fear/worry、目标、持有者、时间范围、引用、否定必须区别。
- 三个必做NLP方向：事件/关系、方面与情绪、历时主题/语义；相关性检索是共同入口。
- 已有方法包括 lexical/TF-IDF baseline、Sentence-BERT候选、GoEmotions-derived候选、SRL/上下文关系、BERTopic、CCF、条件性小型VAR与segmented regression/ITS。不要擅自增加强制微调、LDA、联合多任务训练或新大模型架构。
- 3.6新增渠道转换诊断：复用ITS检查有独立记录的渠道/覆盖变化节点，比较固定来源子集。跳变是composition bias警示，不是因果证明；不连续平台不能直接拼成总体时间序列。
- 文化遗产只是背景，不预设或证明遗产地位；文本情绪不等于人口心理健康。

## 3. 保护已有工作，再重构

当前有大量未跟踪但重要的 `proposal/`、`docs/proposal/`、`tools/` 和图形文件；未跟踪绝不等于可删除。先写简明目录/迁移清单，保留原始数据、旧研究报告、数据库迁移、脚本、笔记、输出及Git历史。

重构以增量方式进行：旧lexical/Ngram流程标记为legacy/provisional baseline，保持其可追溯性。若确需移动，记录旧→新路径并修复引用/入口；能通过文档和包装入口归类的，不必大规模搬移。不可重建、清空或覆盖现有数据库。不执行git reset/clean，不自行push、不发布数据或远程改GitHub元数据。

`proposal/.runtime` 是文档生成专用依赖，不是新研究环境。保留proposal构建能力与已有symlink；本任务不重写研究设计或批量重导出proposal。

## 4. 环境要实际安装并能运行

建立一个明确、项目隔离、可复现的主要研究环境：

- 项目根 `.venv`；根据本机与NLP库兼容性选择受支持Python版本，固定并记录。不要依赖当前Codex临时runtime，也不污染系统Python。
- 用 `pyproject.toml` 管理包和依赖，并提供明确的锁定/重建机制。可使用uv管理；若选择其他方式，保持单一权威依赖来源，解释旧requirements.txt的兼容用途。
- 真正下载安装依赖，排查冲突；提供可重复执行的bootstrap脚本，不只是写配置文件。基础组、NLP/主题、开发、可选重型组件分组清晰，默认验收环境包含演示必需项。
- 数据能力：CSV/JSONL/Parquet读取、文本规范化、日期处理、验证、去重、可追溯关系存储与导出。支持实际检查后选定的本地无需外部服务的数据库演示；保留现有PostgreSQL路线，是否连接既有实例须避免破坏其状态。
- NLP能力：scikit-learn、PyTorch/Transformers/Sentence-Transformers、可用的实体/解析组件、BERTopic所需组件或经验证的对应依赖。包只是候选，版本须依据官方文档与本机兼容性核对，不盲装所有框架。
- 分析/绘图能力：适当的数值数据包、statsmodels、Matplotlib/Seaborn，以及按需交互可视化支持。
- JupyterLab、ipykernel、nbformat/nbconvert及必要开发检查工具实际可用。
- 提供项目 `.env.example`、本地未追踪 `.env`、统一配置加载和必要目录初始化。`.env`仅放非敏感本地默认项及空凭据，不能编造API key、覆盖已有私密配置或把密钥写进notebook/日志。
- 统一配置数据路径、输出路径、模型缓存、随机种子、device与可选数据库连接。数据/模型/缓存/环境/秘密默认不纳入Git；小型synthetic fixtures除外。
- 探测Apple Silicon/MPS（如本机适用），提供CPU回退。Mac不装CUDA专用构建。实际记录模型device与不支持算子的回退，不能只打印“GPU可用”就算通过。

请基于当前官方文档验证安装和模型调用。只从官方包/模型来源下载；模型ID、revision、许可证、缓存位置、资源开销应有记录。不默认启用远程自定义模型代码。合理的小型英文模型下载属于授权范围；多GB或不必要模型应先判断是否确有必要。

## 5. VS Code 与 kernel

用户要直接用 VS Code 打开项目根目录开展工作：

- 配置 `.vscode/settings.json`、`extensions.json`、合适的tasks/debug入口；路径尽量用workspace相对路径，不把个人机器绝对路径写进可移植配置。
- 默认解释器为根 `.venv`；配置notebook、代码格式化/lint、测试发现，以及大模型缓存/原始数据的搜索排除。
- 用该环境注册唯一且可识别的Jupyter kernel，例如内部名 `fear-of-temperature`、显示名 `Python (Fear of Temperature)`；验证kernelspec的argv和sys.executable指向该环境。避免覆盖别的项目kernel，给出更新/移除说明。
- Notebook metadata设置对应kernel。若本机VS Code CLI可用，检查并安装缺少的Python/Jupyter必要扩展；不要假称写extensions.json就完成安装。
- 提供常用任务：环境诊断、测试、demo pipeline、执行notebooks、生成图表。终端脚本及notebook共享同一套src代码，不依赖手动sys.path补丁。
- 如果首次打开仍需用户选择kernel或确认VS Code信任，说明实际需要的那一步，不宣称UI已经自动配置完成。

## 6. 目录与可执行代码

在现有仓库上实现一套一致布局。可采用以下结构，也可按现有内容合理调整，但不要形成两套重复环境/数据目录：

```text
src/fear_temperature/   可安装、可测试的研究代码包
  config / io / cleaning / corpus / embeddings / retrieval
  emotions / relations / topics / temporal / visualization
configs/               采样、标签、模型、运行设置
notebooks/             明确编号、可从头执行的研究notebooks
scripts/               bootstrap、doctor、demo与任务入口；保留旧脚本
tests/                关键数据约束与pipeline测试
data/                 原始/中间/处理后/导出，按现有树整合
outputs/              可再生成的运行结果、图表、日志与manifest
docs/                 环境、使用、架构、来源登记与迁移记录
.vscode/              编辑器配置
```

目录是建议而非要求照抄。保留 `proposal/` 作为提案权威入口。

提供真正可运行的英文synthetic示例（明确标记为测试数据，不冒充历史语料或人工gold labels），覆盖三角色、quoted speaker、时间信息和典型情绪边界。演示需包含：

1. 文件导入→规范化/去重→校验→来源和段落数据库/Parquet；保留raw到derived的ID和证据链。
2. TF-IDF与真实sentence encoder检索比较、模型缓存及向量持久化。
3. 至少一个可运行情绪候选、事件/关系候选和主题分析示例。NER/dependency parsing不能标成已实现SRL；GoEmotions nervousness不能自动当climate anxiety。基于规则/依存的关系输出可以作为明确标记的baseline，SRL模型若未能实际运行必须如实列为后续适配，不用空函数冒充完成。
4. 基于时间/来源角色的aggregation，分母与情绪条件比例分离，缺失与零分开，输出S/E/B与coverage信息。
5. CCF/ITS及条件允许的VAR演示。为接口验证使用足够长度、清楚标记的合成时序；不能用几十条示例文本伪装历史时间序列结果。包含渠道转换诊断入口。
6. 一套静态导出图（PNG及至少PDF/SVG之一）和必要的交互演示；代码、配置和随机种子可复现。

任务目标是可用研究基础设施与小规模演示，不是提前完成整篇论文、定型所有标签或收集全球语料。受限数据访问和人类评估仍按proposal的导师/伦理流程处理。

## 7. README 与相关文档

根README目前仍以早期digital humanities、1842–2022、A–D词层和V1–V5为主，不能继续作为最新研究范围。

根据proposal更新根README及受影响入口：

- 当前研究问题、英语地域范围、三角色与科学来源子类型；区分出版者/说话者/情绪持有者。
- CS方法支持社会情绪研究的定位；文化遗产不是核心结论。
- 真实已实现功能、规划中的研究功能和旧baseline分别说明，绝不把安装了某库写成已验证的方法或完成的结果。
- 一套从全新clone到VS Code/kernel/首个notebook/demo的明确quick start；命令须亲自运行验证。
- 环境重建、数据导入、模型首次下载/离线缓存、CPU/MPS选择、测试、图表导出、常见故障。
- 当前proposal链接、工程结构、数据不入Git规则、访问/发布边界，以及旧基线复现入口。
- 不自行给未授权数据或整个仓库套用开源许可证；区分代码许可与第三方语料许可。

把新的GitHub Description和可选topics写入文档供用户手动修改，不调用GitHub去改。建议Description：

Computational study of warming-related fear and anxiety across policy, news media and public discourse, using a reproducible NLP pipeline and temporal analysis.

## 8. 完成标准：必须实际验收

不要以“文件已生成”结束。至少验证并记录：

- 干净环境能按锁定依赖bootstrap；若测试完整重建，使用临时环境，不删除用户现有环境。
- 包可editable install；从项目外工作目录导入也正常，代码不依赖当前shell目录。
- `doctor`检查Python、关键库、device、数据/模型路径、kernel以及示例状态，失败清楚可诊断。
- 在注册的kernel中从头无交互执行所有交付demo notebooks；至少核实kernel进程的sys.executable。
- 小型synthetic数据端到端跑通真实清洗、存储、embedding检索、情绪/关系/主题演示、aggregation与可视化；不能以mock模型代替真实模型下载/推理成功声明。
- 关键测试覆盖去重/ID追溯、缺失与零、分母/单位一致性、时间顺序/泄漏、输出schema以及可复现性。测试要检查实际性质，不只是镜像实现。
- 至少一项现有legacy验证脚本仍可运行；不可写旧raw数据。若其外部环境不可用，记录具体原因及是否与本次变更相关。
- 明确哪些组件已实测、哪些受平台/权限/模型下载限制、哪些仅是后续接口；有阻塞就继续完成独立工作，不能宣称“开箱即用”而隐去缺项。

最终交付给用户：目录/迁移摘要、实际安装环境与版本、kernel名称、已跑通示例和检查结果、README入口、VS Code开始使用的最少步骤、仍需用户完成的真实外部前置项。过程中记录决定，避免结束时一次性补写虚假的成功日志。
