# Fear of temperature — thesis proposal

## 当前审阅版本

- [thesis_proposal.md](thesis_proposal.md)：唯一英文主稿。
- [thesis_proposal.pdf](thesis_proposal.pdf)：22页 A4 提案，含前置页和参考文献。
- [thesis_proposal.html](thesis_proposal.html)：可导航阅读版。
- [thesis_proposal.txt](thesis_proposal.txt)：纯文本版，含图形文字等价说明。
- [references.bib](references.bib)：34条已引用文献，导出为 APA 7 作者—年份体例。
- [finalisation_review.md](finalisation_review.md)：本轮取舍、UQ条例依据、引用核查深度及导师审阅前事项。

封面为 **Project proposal**，作者 Dai Pan，导师 Mashhuda Glencross，日期16 September 2026。当前状态为导师审阅版本，尚未提交或获得伦理批准。原 `draft_proposal.*` 是最新文件的兼容链接；旧稿留在 `versions/`。

## 研究与技术定位

**Fear of temperature: Computational analysis of policy, media and public climate emotions**。

Computational social science / climate communication；NLP pipeline、temporal analysis 和 reproducible corpus 用来研究升温恐惧及社会情绪。三个社会研究问题保持不变，技术基线、验证和可复现性更明确。包含8张原创矢量图、9个表格面板、5个编号公式。目标每周10–20小时，2027年2月底完成所有分析；计划450–590小时加15%余量。

## 过程与决策

- [discussion_log.md](discussion_log.md)：讨论与用户决定。
- [revision_decisions_2026-09-15.md](revision_decisions_2026-09-15.md)：历次修订。
- [finalisation_review.md](finalisation_review.md)：最新内容、CS定位、风险和伦理取舍。
- [method_review.md](method_review.md)、[operationalization_review.md](operationalization_review.md)、[sampling_and_denominators.md](sampling_and_denominators.md)：方法及分母审查。
- [source_candidates.md](source_candidates.md)：来源候选。
- [course_alignment_and_plan.md](course_alignment_and_plan.md)、[assessment_calendar_review.md](assessment_calendar_review.md)：课程依据与内部日期待确认项。
- [qa/visual_review.md](qa/visual_review.md)：最终渲染视觉审查及历史记录。
- `qa/finalisation_sources/`：本轮官方来源/元数据与获取日志。

## 构建

从项目最外层运行：

```bash
PYTHONPATH=proposal/.runtime /Users/jarlgiovanni/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 proposal/build_exports.py
```

主稿与 BibTeX 同源生成三种阅读格式；Python/Matplotlib 绘图，ReportLab 排版。`apa7.py` 负责已使用文献类型的引用渲染。默认重绘并审查八张图；仅调文字版面且图源未变时可设 `PROPOSAL_REUSE_FIGURES=1`。`qa/check_revision.py` 检查 PDF，`qa/check_html.cjs` 检查 HTML。

UQ 标志来自用户课程模板。`assets/schedule_source.csv` 为规划数据，不是研究结果。Nature Figure 的对齐/字形/碰撞审查保存在 `assets/visual_qa/`。原始准备包、课程样例与研究数据未改动。
