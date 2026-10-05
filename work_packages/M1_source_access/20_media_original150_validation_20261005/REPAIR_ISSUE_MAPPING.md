# 定位问题与具体修复

- MEDIA-PERSISTENCE：19 prototype.setup_db删除输出库。20/store.open_db持久打开、幂等建表、schema版本检查；所有记录事务提交、失败回滚，不删除历史库。临时整链再次运行保持5request/version，原150槽位不丢。
- MEDIA-150-CAP：旧每cell1正文最多30。新SCOPE明确每cell5、总150；transport在重锁内按持久attempt核cap，且本次路线只提出1cell/最多5。未把修正写回历史scope。
- MEDIA-SLOT-FRAME：sample_slot及frame_membership新增insert/update source+edition匹配触发器；frame/era/parent/issue身份不可任意移动。候选单独mapping/sample表，固定原source/region/month，组合FK和跨层限制，旧槽位不被新来源填入。
- MEDIA-PROVENANCE-VERSION：article_version新增(parent,version)组合唯一；provenance_assertion组合FK禁止另一parent的version，insert/update均拒绝。
- MEDIA-REAL-BODY：读取真实raw、保存正文/hash与实际version/request/provenance映射。日期做真实日历校验，updated不代first date；canonical与Article节点绑定；captcha普通提及不误作gate；HTTP/JSONLD/DOM不自动全文。完整边界须离线复核对应raw/body hash，许可证例外单独核验，原始/成员/转载仍pending。

REPAIR_DIFF.patch是新增20文件的精确统一diff；SCHEMA_DELTA.patch比较被冻结19 schema与20新schema，供审阅，不能对19应用。19九项输入hash逐项保持。未读取sealed审计代码、隐藏reviewer夹具，未重跑37基线，无GovDB读写。
