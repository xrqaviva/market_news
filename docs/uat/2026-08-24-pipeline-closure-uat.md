# 盘前管线闭环审计与 UAT 记录（2026-08-24）

## 背景

用户裁定（2026-08-24）：对过往全部要求做第三轮审计，设计 UAT 测试让流程整体闭环——
"测试通过才允许修改与发布"的前提是**测试本身覆盖内容正确性，而不只是结构合法性**。
此前两轮审计已修复：晨报新鲜度兜底、金龙成分股、daily_scrum 文件名匹配、
sync_layout 插入位置。本轮聚焦"同类问题如何自动被拦住"。

## 本轮新发现与处置

| # | 问题 | 根因 | 处置 |
|---|---|---|---|
| 1 | 08-24/08-20 报告来源表混入 08-14~08-20 旧闻 | `gen_report --sina/--em` 为 append action 且 default 含通配符，传精确文件名只是追加；多日文件共存时关键词宽匹配命中错误窗口 | argparse default 改 None；新增 `filter_window()` 按 `data["window"]` 纵深过滤（即使参数/文件再错也不污染）；三份报告重生成 |
| 2 | 契约预检自身无测试 | 预检逻辑从未被断言过 | 新增 7 个用例（见下） |
| 3 | OLD 标题"（昨日已定价）"重复追加（08-20、08-24 各发生一次，均人工修） | card() 无条件追加 tag | title 已含后缀时不重复 |
| 4 | sync_layout 插入点曾两次插错（Promise.race 数组 / map 收尾偏移），靠人眼发现 | 字符串定位无回归测试 | 新增 UAT：插入必须落在 map 内部 + node --check + 幂等 |
| 5 | daily_scrum 只查文件存在，缺口标记文件（"采集失败"说明）也算 [OK] | 存在性≠内容真实性 | 新增 [WARN]：小体积且含失败标记的文件显式列出，要求写入 coverage（不阻塞，与自愈规则一致） |
| 6 | gen_report 不接受绝对路径证据（ROOT.glob 限制） | 实现细节 | `_expand_pattern` 支持绝对路径直接读 |
| 7 | （承接上轮）08-19 报告跨概念主题残留、leads 生产端缺失、cron prompt 过时 | — | 已在上轮修复并纳入本轮回归范围 |

## UAT 用例与结果

`tests/test_gen_report_uat.py`（12 用例，全过）：

- **窗口隔离**：混合三时段+无时间戳条目，过滤后仅剩窗口内；window 缺失/非法时保持旧行为；
  parse_window 解析校验
- **端到端**：subprocess 跑 gen_report 全流程，窗口外时间戳不得出现在生成 md 的来源行
- **契约预检**：合法数据放行；分数递增/空主题/theme_id 不一致/同 evt 多主题/引用不存在 evt
  全部拦截；单条主题合法（2026-08-19 用户裁定）
- **OLD 标签防重**：标题含"（昨日已定价）"时全卡仅出现一次

`tests/test_sync_layout_uat.py`（2 用例，全过）：

- 新报告条目插入 EXPECTED_REPORT_OUTPUT_BY_INPUT map 内部，map 之后代码零污染，
  node --check 通过
- 删除已有条目再同步 → 恢复且二次运行为幂等（no change）

`scripts/daily_scrum.py` 行为验证：

- 雪球缺口标记文件（502 页面）触发 `[WARN] xueqiu-hot-20260824.txt 为缺口标记文件`
- 晨报新鲜度兜底（模拟 state=08-21）自动 force 补跑 exit=0 后恢复 [OK]（上轮实测）

## 结论

- 三类历史事故（跨窗口污染、契约预检盲信、标签重复）均有对应自动化用例锁定。
- "文件存在≠数据在"以 [WARN] 显式化，发布前主代理必须把缺口写入 coverage。
- 剩余已知缺口（非缺陷，持续标注）：雪球反爬（headless 502 + WebFetch WAF）、
  X Home timeline 登录态依赖、X pending_verification 两账号未实测、
  cron 触发落会话的平台层可靠性（以 cron-runs.jsonl 留痕对账）。
