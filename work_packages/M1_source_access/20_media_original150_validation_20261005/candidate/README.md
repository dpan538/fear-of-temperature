# Round20 candidate

19包只读；本轮数据库media_execution.sqlite持续保存，不删除重建。Python3、requests、beautifulsoup4为当前已存在依赖，不安装软件。

断网针对性检查：`python3 -B candidate/test_changed.py`；整链临时模拟：`python3 -B candidate/test_chain.py`。整链使用与ROUTE_PLAN相同的EDJNet source/edition/frame并禁止socket，临时目录销毁；真实输出无模拟文章。

准备：`python3 -B candidate/run.py`。冻结之后不得修改执行代码/ROUTE_PLAN/SCOPE来绕过digest。

执行只在control/MEDIA_EXECUTION_RELEASE.json批准true，六个执行文件SHA、scope SHA、route SHA和截止时间全部一致后：`python3 -B candidate/run.py --execute-bodies`。候选只有EDJNet2025-07；名称released_candidates在待验收计划里表示拟释放cells，代码仍必须验证实际release。

先由当前拥有窗口在截止前进行一次计划中精确domain/date-only查询，保存工具响应到raw/（最大2MiB，预算计入）、SHA；保存evidence/frames/edjnet_2025-07_search.json，包括query、search_provider、observed_at_utc、article_urls、frame_pages=1、monthly_denominator=null、pi=null、raw_receipt_path和raw_receipt_sha256。此框仅部分搜索观察，不证明月份完整。查询不增加topic/length/fear词、不分页。先冻结唯一原生URL字典序first5；正文不合日期或失败不补选。

每次实际请求保持intent/checkpoint、已存stop与2秒间隔，raw/version/request证据关联。解析selector为候选，JSONLD/HTTP200不自动证明全文。个人离线检查实际raw与正文，保存evidence/reviews/<request_id>.json：status=complete_boundary_verified、raw_sha256、body_sha256、body_selector、article_url、rights_review=route_licence_applies_no_observed_exception；必须真正检查文章完整边界和例外，再执行`python3 -B candidate/run.py --finalise-reviews`。该步骤只读已取raw，无新增请求。边界/许可证/发布日期有疑问保留pending；当前正文不冒充历史版本。

运行再次启动跳过已完成candidate_sample，不重试CP/旧source，写150行输出且旧sample_slot.parent仍NULL。延期或无搜索命中保留缺口；截止后不得网络调用。OCR、原始成员转载判定未新增，明确unknown。
