# 原150媒体验证：本轮收束报告

必要修复与有界执行已结束，150个原来源名额仍全部缺正文。一次集中验收后，唯一放行的EDJNet欧洲英语／2025-07日期＋域名搜索返回0条结果，因此0正文请求、0真实article parent/version/完整正文、0issue/OCR。没有追加检索、补选、换候选或月份。搜索观察为空不等于该月出版量为0，不证明来源失效、月份覆盖完整或任何情绪缺失。

## 实际执行与证据

查询为`site:www.europeandatajournalism.eu after:2025-07-01 before:2025-08-01`。完整工具响应、query、provider、观察时间、page1与空URL列表已保存到raw及evidence/frames/。搜索引擎未暴露，provider记录web search工具。框是部分观察，月份分母和pi均NULL；approved runner正常执行空选择，没有文章HTTP。前回合政策文档4请求，本回合搜索1响应，搜索响应数与文章HTTP数分开。真实库request_attempt/raw_object均0，因为它们记录文章执行证据；文件系统另有4政策raw及1搜索raw。

新增raw201790字节（政策201722＋搜索响应68），加旧212字节合计202002字节；partial和正文文本0。单对象2MiB、跨轮128MiB、floor15GiB与政府/其他预留保持。网络在截止前结束，11:45:48上海时间硬截止不变。

## 五层名额与终态

| 层 | 原计划 | 原来源成功 | 新候选文章 | 完整正文 | 原名额缺额 |
|---|---:|---:|---:|---:|---:|
| EU/Europe（UK除外） |30|0|0|0|30|
| UK |30|0|0|0|30|
| AU |30|0|0|0|30|
| US |30|0|0|0|30|
| NZ |30|0|0|0|30|

SLOT_TERMINAL_150.csv保留旧source/frame/slot/月份/status/reason，parent与pi为空、原来源成功False。135行保留原来源停止；10行单列EDJNet2017年成立前不适用；5行标scope_changed_partial_search_empty_no_body_attempt，候选表登记终态但不制造文章。DW15个设计坐标的候选映射不计作DW成功，缺额没有转移。

EDJNet为欧洲英语数据新闻/聚合网络，非报纸；IT指OBC编辑协调机构，不是所有成员的出版者国家，也不是事件地点。默认CC BY4.0政策及文章例外已核实，无文章载荷，逐篇许可例外、原创/成员转载、canonical/首发日期/时区、preview/挑战、可见完整边界均未实际检查。当前selector和真实文章解析仅验证夹具，历史内容版本未知。其余原来源及未入选候选的公开访问、robots、挑战/超时、版次或许可缺口照旧，不重探旧障碍。

## 修复与验证

新持久库避免旧setup_db删除历史；事务失败回滚、幂等重开。新scope允许每source-month5正文、总150并按持久attempt计上限，本轮只释放1cell／最多5。slot和frame_membership新增source/edition插入及更新约束，parent/era/frame身份不可搬移。provenance与version的组合FK绑定同一parent。候选独立映射原source/region/month，不填旧槽位。真实raw/body/hash/version/request可存；日期校验日历、updated不代首发，JSONLD绑定canonical，普通captcha词不作挑战。HTTP200/JSONLD/任意DOM边界不自动证明全文，完整边界与实际raw/body hash须离线核对，许可例外单独核验。

19项socket禁用检查＋1个临时整链场景通过，协调者集中验收独立重跑通过。模拟5篇只在临时目录，真实库0模拟文章。真实空框证据和5条候选终态映射已持久化；离线重开不丢历史、无额外网络，SQLite完整性/外键检查通过。未重跑无关37项基线，未触及政府库或密封审计，没有执行主题/情绪/恐惧标注或语义排除。

## 固定月份下一次同额设计（仅记录，不执行）

后续若有明确研究需要及新访问事实，仍以1995-07、2015-12、2025-07、五层各30、source-month5、总150规划；不以现代月份补成立前缺口，不按主题/恐惧/长度选择。保留旧来源身份及停止证据，再登记清楚出版者/版次/时代/许可的新版本。旧停止只有新有效访问或权利证据才能评估，本次空搜索不授权再试。部分发现框与实际首发月分别验证；pi/全月分母未知继续NULL，缺额不移层。正文、OCR或历史版本条件由真实证据说明，不自动启动下一轮。

FINAL_RESULT.json为机器结果，FINAL_INPUT_RECEIPT.json记录9旧输入、6释放代码与输出digest；FINAL_COVERAGE_BY_REGION.csv和SLOT_TERMINAL_150.csv记录计划/缺额。修复差异及说明见REPAIR_ISSUE_MAPPING.md、REPAIR_DIFF.patch、SCHEMA_DELTA.patch、candidate/README.md。evidence/FINAL_DATABASE_CHECK.json、BODY_REVIEW_REGISTER.json、OWNER_RELEASE_RECHECK.json与搜索原始收据可核查。本轮确认代码修复、模拟链路和空框真实执行；150篇正文验证没有完成。
