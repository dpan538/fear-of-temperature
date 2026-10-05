# 单一406证据与候选修正

固定发表区间1988-01-01–2026-09-21。此文诊断已保存请求，不请求CELLAR Item，不更改冻结选择或历史停止状态。

## 现有事实

第21项Work为`3df58e03-97cd-11e4-b8a5-01aa75ed71a1`；ENG Expression`.0006`、选定PDF/A-1A Manifestation`.0006.01`、选定Item`.0006.01/DOC_1`。请求与最终URL相同，未发生重定向。2026-10-04T18:38:17 GMT服务器返回406、`application/xml;charset=UTF-8`、声明长度1000；错误正文未保存，实际新增raw/partial均为0。`Last-Modified: 1970`不能当作原件发表时间。

V3固定发送`Accept: application/pdf`和`Accept-Encoding: identity`，未发送Accept-Language。前20项中13项同为PDF/A-1A且在相同头下成功，另7项为PDF1X。因此“所有PDF/A-1A都不能使用此头”被现有反例否定。失败Work保存的关系有4条：选定PDF/A-1A一个Item、XHTML一个、FMX4两个；没有获得更换Item或补齐sibling的许可。

| 命题 | 证据与判断 |
|---|---|
| 406按HTTP语义涉及协商可接受表示 | [RFC9110 §15.5.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.7)支持这个含义；无法据状态码确定是哪个头或哪层服务造成 |
| direct Item与Work协商应区别 | [CELLAR机器学习指南](https://op.europa.eu/documents/d/cellar/cellar_ml_dataset_guide)第4页给出含Expression/Manifestation/`DOC_1`的直接文件URL；仅Work URL的例子使用格式和语言协商 |
| 精确Item可用通配Accept | [官方接口规范R1.0.6](https://op.europa.eu/documents/10530/676542/ao10463_annex_17_cellar_dissemination_interface_en.pdf)第21–22页允许`*/*`，前提是URI自身足以确定语言及类型；这是旧规范，有当前指南的直接Item模式作为补充，不等于对该Item的在线保证 |
| PDF/A-1A专用媒体参数存在 | [CELLAR Publications](https://op.europa.eu/en/web/cellar/cellar-data/publications)列有`application/pdf;type=pdfa1a`；其Work协商例子不能证明本次direct Item必须换成该头 |
| 权限限制 | 本次没有401/403、登录或权限挑战正文证据；不能把406直接改报为“权限拒绝”，也不能宣称已排除服务策略限制 |
| 其他可能 | Item元数据与当前流不一致、服务实现/缓存差异或暂时状态均未证实；没有错误正文或服务端日志，不能细化根因 |

## 一次可审查的修正

候选原因是固定generic-PDF Accept可能对这个精确流形成了不必要的协商约束；这是推断，根因仍未在线证实。新代码只给这个失败Item使用`Accept: */*`。URL、Work、Expression、Manifestation、Item、格式选择、身份/date元数据和对象cap不变；不加语言协商，不尝试专用type、Work URL、sibling、外部缓存等第二路线。后续958个未尝试Item继续使用V3的`Accept: application/pdf`。

通配Accept不放宽结果验收：只接受同一URL的200、PDF/octet-stream类型及`%PDF-`签名；HTML/挑战/错误页、编码、截断、超cap或任一非200均持久停止，重定向也只记录并停止，无第二请求。即使正确响应，身份、日期、组件及历史版本仍需验收。

`transport_continuation.py`是独立候选版本，不覆盖V3。默认离线；执行必须有协调者新签发的`control/GOV_CONTINUATION_RELEASE.json`，绑定新代码、输入包、旧A/B停止状态、旧406 sidecar和冻结979队列的hash。先复核复用20项；只准这一个纠正后验证。失败则留下新停止/sidecar，队列不继续；成功才按原序处理958项。不得删旧失败、重写旧release或自行创建ready=true release。原A Hansard403仍有效；两条AU独立检查须在同一新release中明确分阶段接受。

16项网络禁止夹具验证了同一Item、日期/路径不变、一次请求、HTML和错误签名拒绝、截断partial保留、cap/floor、Retry-After、持久停止、checkpoint不覆盖、未尝试Item头不变、cap停止后的979项完整记账，以及AU精确链接和四请求上限。夹具不证明线上406修正成功。政府A+B累计raw及partial上限2 GiB，15 GiB floor和原inflight/checkpoint/other reserves保留；媒体128 MiB计入既有other reserve，共用heavy-I/O锁。
