# Fear of temperature - proposal 工作目录

从 2026-09-15 起，本目录是 proposal 后续讨论与写作的主目录。

## 当前草稿与阅读版本

- [draft_proposal.md](draft_proposal.md)：英文主稿，所有导出格式的共同内容来源。
- [draft_proposal.html](draft_proposal.html)：可浏览、带章节导航与引用链接的阅读版。
- [draft_proposal.pdf](draft_proposal.pdf)：A4 分页讨论稿，含模板原配 UQ 标志、目录与页码。
- [draft_proposal.txt](draft_proposal.txt)：UTF-8 纯文本版，包含可读正文引用与参考文献。
- [references.bib](references.bib)：主稿引用来源。

## 讨论与研究记录

- [discussion_log.md](discussion_log.md)：用户已确认的研究方向、决定、原话与待讨论项。
- [method_review.md](method_review.md)：方法审核、来源依据与实际阅读深度。
- [source_candidates.md](source_candidates.md)：社交平台／论坛候选及访问和再发布边界。
- [course_alignment_and_plan.md](course_alignment_and_plan.md)：学校材料与示例对照、20 页内容预算、图表规格、风险及里程碑讨论。
- [assessment_calendar_review.md](assessment_calendar_review.md)：本届 REIT7842 日期核查、公开评分表和日历冲突。
- [operationalization_review.md](operationalization_review.md)：最新五类指标审核、物理事件先导与反馈设计、数据库首要风险、两张图的规格及可用于英文稿的段落。
- [sampling_and_denominators.md](sampling_and_denominators.md)：三类分母原型、抽样与权重反例、时间粒度对齐、全部原型状态索引及剩余决定。
- `course_materials/`：本轮五份课程讲义／示例的原样副本与哈希清单。

## 状态

当前为完整英文讨论稿：21 页 PDF（含前置页与参考文献）、8 张原创矢量图、9 个表格面板、5 个编号公式、31 条正文对应参考文献。作者 Dai Pan、导师 Mashhuda Glencross，稿件日期暂定 16 September 2026。每周投入已更新为10–20小时，目标为2027年2月底完成所有分析与稳健性检查；3月之后聚焦写作与交付。450–590h总量及15%余量为暂定规划。时间图按用户最新纠正恢复为嵌入正文的紧凑复合图，图内整合里程碑卡片并与说明文字同页；正文 12 pt，表格约 9 pt。

课程 proposal 截止为 2026-09-17 15:00。最终 Thesis Report 日期存在公开大纲冲突，尚未解决；具体访问、共同分析窗口和模型由先导决定。此稿无实证结果。

用户最新决定：主线为政府／政策、新闻媒体与公众表达的领先和滞后；重点长期预期，统一采集后标注直接高温与预期威胁；采用两个归因轴；政策同时作为事件节点与研究文本；前后各六个月为初始分析窗口。

## 更新方式

编辑主稿与 BibTeX 后，运行 `build_exports.py`，同步生成 HTML、PDF、TXT。脚本使用 ReportLab 排版、Matplotlib 绘制全部九张图与矢量数学公式；后者与 PyMuPDF、pdfrw 安装在本目录 `.runtime/`，不修改系统 Python。使用当前机器的 Codex 运行时可执行：

```bash
/Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 proposal/build_exports.py
```

该命令从项目最外层运行。构建脚本也可从其他目录以绝对路径运行。`assets/UQ_Logo.png` 来自用户原始模板；`qa/` 存放导出一致性检查结果。

原 `docs/proposal/round2/` 保留为迁移前记录，不再作为当前版本同步维护。原始附件与旧研究数据没有改动。

## 完整稿新增记录

- [figure_design_contract.md](figure_design_contract.md)：用户视觉纠正、图形分工与 Nature Figure 审核契约。
- [reading_register_complete_draft.md](reading_register_complete_draft.md)：本版阅读范围、来源用途与仍需深入阅读的部分。
- `assets/schedule_source.csv`：暂定工作包时间与工时，不是研究观测数据。
- `assets/nature_qa/`：时间图源代码、字形、对齐、碰撞审核结果。
- `qa/`：最终 PDF 页面边界、格式一致性、HTML 视口检查和视觉检查记录。
- `versions/`：修改前12页稿及已被用户否定的整页时间图版本。

Nature Skills 仓库位于项目 `tools/nature-skills/`；安装 commit 为 `9ea7330a17813a15421fe843778a776c258b9001`。实际安装清单由更新脚本保存；20个技能目录均校验一致。依赖版本见 `figure_requirements.txt`。

最新解释性修订、术语约定及已确认图表：[revision_decisions_2026-09-15.md](revision_decisions_2026-09-15.md)。本轮没有增加新方法或实证结果。

## 最新视觉改版（2026-09-15）

采用 nature-figure 工作流重绘全部九张图。五种机制改为彩色节点与方向连线；RQ、分母和风险改为图形化表格；时间线整合阶段色带、工时范围、可选工作纹理与六个交付卡片。保留五个编号公式及必要的来源、标注、事件和效度表格。

- [visual_redesign_contract.md](visual_redesign_contract.md)：本轮视觉设计与证据边界。
- [visual_redesign.py](visual_redesign.py)：全部图的 Matplotlib 源码。
- `assets/visual_qa/`：九图的字形、对齐、碰撞与源代码检查。
- [qa/visual_review.md](qa/visual_review.md)：实际渲染检查、迭代修复和适用范围。
- `versions/before_visual_rebuild_2026-09-15/`：本次修改前的完整稿与构建代码。

图形只表达研究设计、示意关系与暂定工时，没有实证结果；未新增模型或方法。

## 最新：参照 coordinator 认可示例改写 3.8

3.8 改为“风险评估表 + 检查节点及范围调整”，参照语言学习示例 3.4/3.5 的信息组织，使用项目本身的风险与时间。时间图现为 Figure 8；风险表 Table 6；OHS 表 Table 7。用户要求暂不在 proposal 中呈现最终报告日期冲突，已从四种主稿格式及时间图中移除；内部记录保留明天核实事项。2.4 待讨论，未改动。
