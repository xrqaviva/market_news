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
