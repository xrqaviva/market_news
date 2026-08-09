# 进度记录

## 2026-08-09

- 设计规格已确认并提交：`af8a7ad`。
- 实施计划已确认并提交：`bc8fd81`。
- 用户选择Subagent-Driven执行方式。
- 创建隔离工作树`/Users/aviva/Projects/market_news/.worktrees/project-guide`，分支`codex/project-guide`。
- SDD任务1—5待执行。
- 预检发现无受跟踪`tests/`目录，既有测试基线不可用；已记录，不误报为测试回归。
- 用户允许隔离分支阶段性提交；最终审阅通过前不合入`main`。
- Task 1 RED：`python3 -m unittest tests/test_project_guide.py -v`按预期报错，`docs/PROJECT_GUIDE.md`不存在（`FileNotFoundError`）。
- Task 1 GREEN：同一命令通过，`ProjectGuideContractTest`的1项契约断言成功。
- Task 1新增：`docs/PROJECT_GUIDE.md`最小骨架与`tests/test_project_guide.py`；说明书包含标题、最后核验日期、适用版本、权威入口说明及22个约定一级章节。
- Task 2完成：第1—9章写入项目目标/非目标、状态标签、三路事件卡数据流、交易日窗口、来源矩阵、事件去重、热度评分、主榜与报告专项规则。
- Task 2 RED：`python3 -m unittest tests/test_project_guide.py -v`运行4项测试，原有1项通过；新增热度、时间/链接测试失败，来源矩阵的9个子断言失败（合计11个失败断言），原因均为说明书第1—9章尚为空。
- Task 2 GREEN：同一命令运行4项测试并全部通过；`git diff --check`通过。
- Task 2按2026-08-03证据和最新设计解决了早期`HANDOFF.md`的登录/权重历史口径冲突；来源表记录最近验证日期，不承诺登录长期有效。
