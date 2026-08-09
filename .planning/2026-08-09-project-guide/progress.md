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
- Task 3完成：第10—17章写入交易日闸门、基线、三路采集、候选冻结、Top 10深挖、生成、验收与交付步骤；15分钟阶段预算及超时继续完成规则；目录与产物关系；Markdown到`web/dist`的公开边界；安全、降级、设计决策和状态台账。
- Task 3 RED：先新增运行/状态与安全契约，再运行`python3 -m unittest tests/test_project_guide.py -v`。8项中原有6项通过；新增运行/状态测试因缺少“海外宏观与财报”失败，新增安全测试因缺少“密码”失败，符合第10—17章尚为空的预期。
- Task 3 GREEN：补全第10—17章后，同一命令运行8项、全部通过；`git diff --check`通过。`python3 -m unittest discover -v`在本分支发现0项测试（`tests/`不是可发现包），故未将其作为全套通过结论；直接模块命令是本任务实际且完整的文档契约入口。
- Task 3状态核验：网页实现只读核验为隔离分支`codex/news-radar-web`，最新提交`bc16916`，工作树无未提交改动；说明书明确其“已完成于隔离分支，尚未合入main”。GitHub认证、首次推送、GitHub Pages和自动任务均明确为“暂停”，没有执行外部动作。
- Task 3历史证据处理：主工作树中的`reports/`、`evidence/`及早期设计/计划仍未跟踪；说明书仅以代码路径和状态记录，不创建会在干净克隆中失效的Markdown链接。
- Task 3 fix round 1：第17章状态列已收紧为`已完成`、`已验证`、`暂停`、`受限`、`规划中`、`历史口径`六种枚举；历史运行、隔离分支和未合入等限定移至证据/限制列。安全边界明确禁止对凭据和浏览器私密数据进行读取、写入、输出、持久化或复制，覆盖本地文件、缓存、构建目录和日志/报告。
- Task 3 fix round 1 RED/GREEN：新增状态枚举、网页分支/四项暂停、Markdown→固定HTML→`web/dist`及完整安全动词契约后，定向测试按预期报7项失败；修复后`python3 -m unittest tests/test_project_guide.py -v`与`python3 -m unittest discover -s tests -v`均运行10项且全部通过，`git diff --check`通过。
