# 权利、公开访问与伦理路径核验

## 结论

本批次把许可/权利与 UQ 伦理路线作为两条独立状态轴。公开 API 可读、GOV.UK 一般采用 OGL、可用于研究处理、可重新发布四者不互相替代。

当前可执行且已完成的是：Search API 元数据枚举、无正文 Content API 元数据投影、附件身份枚举、哈希、入库和覆盖审计。正文网页与附件字节没有下载，状态为 `blocked_pending_ethics_route`；这不是网络失败，也没有被写成空正文成功。

## 许可与权利证据

- GOV.UK Terms and Conditions 说明，大多数 GOV.UK 内容可按 Open Government Licence v3.0 使用，但存在第三方版权、徽标、个人数据等例外。
- OGL v3.0 一般允许复制、发布、改编及非商业/商业利用，同时要求注明来源，并排除未获信息提供者许可的第三方权利等内容。
- 因此，GOV.UK landing page 的一般 OGL 指示构成权利调查依据，但不能自动覆盖每个 PDF、图片、地图、数据表或第三方附件；重新发布也需逐件判断。

当前数据库状态：

- `public_access_status=publicly_listed_not_fetch_verified`：记录页面/附件 URL 在公开接口中可见，但正文 gate 下未逐件请求，因此不提前断言其实际可访问。
- `redistribution_status=item_and_attachment_review_required`：未声称可整体再发布。
- `licence_status=ogl_general_terms_recorded_item_exceptions_pending`：一般条款已记录，项目级例外审查未完成。

## UQ 伦理路径证据

仓库中 `proposal/thesis_proposal.md` 与 `03_database_pilot/data_quality_report.md` 仍把伦理状态记录为 pending；未找到覆盖本轮正文和附件研究处理的可核验 approval/exemption 记录。OGL 是版权许可，不是 UQ 伦理批准或豁免。

当前数据库状态：

- `ethics_status=pending`；
- `research_processing_status=pending`；
- 内容抓取配置 `enabled=false`；
- 3,025 个内容对象均在 `failed_or_pending_records.csv` 中有明确阻塞理由。

## 解锁正文抓取所需证据

1. 记录适用的 UQ approval、exemption 或正式无需审批路线，以及覆盖的数据源、用途和处理范围。
2. 确认网页正文是否在该路线内；不要用附件的权利判断替代网页判断，反之亦然。
3. 对附件的第三方权利、异常大文件和扫描件设置逐件状态。
4. 解锁后先运行最多 3 条 smoke fetch/extraction，人工对照 landing page、附件清单和提取文本，再恢复正式 manifest。

## 官方参考

- GOV.UK, *Terms and conditions*：https://www.gov.uk/help/terms-conditions
- The National Archives, *Open Government Licence for public sector information v3.0*：https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
