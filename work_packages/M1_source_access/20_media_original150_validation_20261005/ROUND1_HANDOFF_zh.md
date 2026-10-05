# 第一回合集中交付

当前真实正文/框请求0；只进行了4份新robots/许可文档请求，新增201722字节，加旧212字节合计201934字节，partial0。代码修复完成，19个针对性检查及1个全socket禁用整链场景通过；模拟5篇全部在临时目录，与真实采集分开。19九项冻结输入hash未变，政府数据库和密封审计访问0。

只提交一次候选修订EDJNet：欧洲英语数据新闻网络，由意大利OBC协调，不能代表所有成员出版者。2017年前两月份不适用，2025-07最多5篇；原DW15槽位保留，新文章只能在candidate_mapping/sample中标scope_changed，不算DW或原来源成功。其余9原来源不重新请求；openDemocracy等调查止于已保存事实/访问限制，不扩充候选轮次。

待一次集中验收的精确对象是CODE_DIGESTS.json、ROUTE_PLAN.json、control/SCOPE.json及READY_FOR_ACCEPTANCE.json。候选搜索按PUBLIC_SEARCH_FRAME_CLARIFICATION只做一次domain+date精确查询，输出部分观察框，pi及月份分母NULL，正文首发月独立检查，不补选失败或不合月份结果。搜索尚未执行，不能保证有5条可用文章。当前.entry-content selector也未经真实文章验证，许可例外及原创/成员转载映射pending；HTTP200、JSONLD和预览不算全文。

SLOT_TERMINAL_150.csv共150行：{"original_stop_preserved_no_article_request": 135, "scope_changed_not_applicable_before2017": 10, "scope_changed_not_attempted_pending_release_or_frame": 5}；所有original_source_success=False。0真实article_parent/version/全文/issue/OCR。若release，第二回合只执行该cell及局部检查，在03:45:48UTC（11:45:48上海）停止，无新窗口/扩调查/相邻月。截止或无命中则具体缺口终止。

预算最新free=20260474880byte；floor16106127360byte；保留gov2GiB+100m+64MiB及其他1GiB扣媒体占用，当前reserve3388132402byte。执行逐请求重核，单对象2MiB，跨轮128MiB且文本与搜索raw也计入，串行2秒+共享heavy lock，无自动retry/redirect。

修复差异见REPAIR_ISSUE_MAPPING.md、REPAIR_DIFF.patch、SCHEMA_DELTA.patch；操作见candidate/README.md。真实证据清单、输入复核及测试原始输出位于evidence/。本回合只声明代码/夹具验证完成，实采仍待release。
