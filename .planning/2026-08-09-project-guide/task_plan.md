# 项目说明书任务计划

## 目标

生成`docs/PROJECT_GUIDE.md`，完整持久化项目方法、来源、工作步骤、设计、计划、完成情况、UAT与集成测试及其证据。

## 阶段

- [x] 读取并确认设计规格
- [x] 创建并确认实施计划
- [x] Task 1：说明书骨架与契约
- [x] Task 2：项目方法、来源、时间、热度和报告规则
- [x] Task 3：运行、安全、降级和状态台账
- [x] Task 4：UAT与集成测试台账
- [x] Task 5：链接、完整测试、自审和提交
- [x] Final Fix：全分支最终审阅的4项Important与3项Minor闭环

## Final Fix测试矩阵

- 单元/文档契约：`python3 -m unittest tests/test_project_guide.py -v`；新契约在旧文档上应因七类缺口失败，修复后全部通过。
- 分支集成：`python3 -m unittest discover -s tests -v`；覆盖本分支全部可发现测试。
- 主工作区报告契约：在`/Users/aviva/Projects/market_news`运行`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_report_contract.py -v`，验证未跟踪本地报告与契约边界。
- 网页隔离分支：在`codex/news-radar-web`提交`bc16916`对应工作树运行`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`，不等于main或公网验收。
- UI：N/A；本轮不修改网页也不恢复浏览器/公网交互，UAT-013改为未执行，结构测试证据仅留IT-008—010。
- 安全/隐私：语境扫描、本地链接仓库根边界、Chrome降级不读取浏览器私密数据。
- 产物/构建：文档与Markdown契约即产物门禁；无编译或生成代码（N/A）。
- 发布：`git diff --check`、精确暂存5文件、审阅完整暂存补丁并提交；不推送、不合并、不发布。

## 边界

- 不恢复GitHub认证、Pages发布或自动任务。
- 不合并网页功能分支。
- 不读取或输出密码、Cookie、Token、Local Storage或浏览器历史。
- 只暂存实施计划列出的文件。

## 错误记录

| 错误 | 处理 |
|---|---|
| 主工作树包含大量未跟踪历史产物 | 在`codex/project-guide`隔离工作树实施，历史产物只作只读证据 |
| 隔离分支无受跟踪`tests/`目录，基线发现命令不可运行 | 记录为“无既有测试基线”，由Task 1创建首个文档契约测试 |
| Task 1计划写“不提交半成品”与SDD逐Task提交冲突 | 用户允许隔离分支阶段性提交；全部审阅通过前不合入main |
| Task 5自审发现第20—22章仅有标题 | 先新增非空章节契约并观察3个预期失败，再补齐限制、维护与变更记录；契约转为通过 |
| Final Fix首次追加`findings.md`的补丁上下文不匹配 | 读取文件尾部确认实际内容，改用更小的精确上下文追加，不覆盖Task 1—5历史 |
| 隔离工作树的`git add`因公用`.git/worktrees/.../index.lock`不在写入沙箱而失败 | 按已授权的精确5文件范围重试权限提升，不扩大暂存范围 |
