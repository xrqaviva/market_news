# AGENTS.md — A股新闻雷达运行规则

本项目每日生成 A股盘前新闻热榜报告并发布到 GitHub Pages。处理"出盘前报告 /
执行自动化任务 / 修复问题 / 新增需求"前，必须先完整阅读：

1. [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md) §8.5 每日固化流程
2. [docs/PROBLEM_CLOSURE_PROTOCOL.md](docs/PROBLEM_CLOSURE_PROTOCOL.md) 需求落地闭环协议
3. [docs/2026-08-19-interruption-recovery.md](docs/2026-08-19-interruption-recovery.md) 中断自愈规则

## 必须遵守

1. **需求落地闭环**：用户提出的每个需求/问题，必须在本次会话内落到配置/代码/
   断言测试/文档至少一层并走完闭环 Checklist（见协议文档），对话记忆不作数。
2. **修复必带回归用例**；新需求必同步扩充断言。测试通过 ≠ 数据正确。
3. **兜底优先于人工接管**：校验失败先自动恢复（如晨报过期自动 force 补跑），
   无法恢复才显式标注缺口；禁止静默跳过、禁止伪造数据。
4. **采集与来源窗口纪律**：`gen_report --sina/--em` 必须显式传当日窗口的精确
   evidence 文件名；发布前抽查线上正文内容，不只看 HTTP 200。
5. **收录规则**：严禁合并不同事件（主体/动作/对象不同即不同事件）；主题允许单条；
   A股个股涨跌结果不收录；机构评级独立成条不合并。
6. 一切运行留痕 `evidence/cron-runs.jsonl`；缺口写入报告 coverage。

未经用户明确授权，不修改 daily_info 项目或它的 launchd，不创建额外自动化任务，
不读取/输出任何密码、Cookie、Token 等凭据。本报告仅作信息整理，不构成投资建议。
