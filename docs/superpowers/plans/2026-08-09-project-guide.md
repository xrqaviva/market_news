# A股短线新闻雷达项目说明书实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份面向使用者和维护者的权威项目说明书，并用自动化文档契约测试保证来源、热度、状态、计划、UAT和集成测试长期可追溯。

**Architecture:** `docs/PROJECT_GUIDE.md`是唯一权威入口，历史设计、计划、报告、证据和测试文件通过相对链接作为事实证据。`tests/test_project_guide.py`只验证说明书结构、状态词、稳定测试编号、关键口径和本地相对链接，不复制新闻采集或网页构建逻辑。

**Tech Stack:** Markdown、Python 3.9标准库、`unittest`、Git。

## Global Constraints

- 最终说明书固定为`docs/PROJECT_GUIDE.md`。
- 同时面向普通使用者和维护者，先讲业务方法，再讲运行与技术细节。
- 当前热点权重固定为覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10。
- 所有时间按`Asia/Shanghai`展示和判断窗口；仅有日期时不补造分钟。
- 具体文章、公告或帖子是事实核验路径；首页和搜索页只可用于发现或记录动态榜位。
- 可靠性、资金验证、个股映射、公告确认和深度判断不参与热度排序。
- 只有同一永久URL、同一字段和两个明确北京时间快照可以量化热度变化。
- 未执行、暂停、受限和规划中的能力不得写成已通过、已发布或已上线。
- 网页实现位于隔离分支`codex/news-radar-web`，尚未合入`main`；GitHub公开发布保持暂停。
- 不恢复GitHub认证、推送、Pages发布、自动任务或分支合并。
- 不读取或写入密码、Cookie、Token、Local Storage、浏览器历史或SSH密钥。
- 所有工作步骤、设计、计划、完成情况、UAT、集成测试和结果必须持久化。
- 本任务只暂存计划明确列出的文件，不批量暂存其他未跟踪报告、证据或用户文件。

## File Map

| Path | Responsibility |
|---|---|
| `docs/PROJECT_GUIDE.md` | 面向使用者和维护者的唯一权威项目说明书 |
| `tests/test_project_guide.py` | 说明书章节、关键口径、状态、测试编号和相对链接契约 |
| `.planning/2026-08-09-project-guide/task_plan.md` | 本轮阶段、边界和错误记录 |
| `.planning/2026-08-09-project-guide/findings.md` | 来源、实现与状态核验发现 |
| `.planning/2026-08-09-project-guide/progress.md` | 本轮实施、测试、提交和验收结果 |

---

### Task 1: 建立说明书骨架与文档契约

**Files:**
- Create: `docs/PROJECT_GUIDE.md`
- Create: `tests/test_project_guide.py`
- Modify: `.planning/2026-08-09-project-guide/progress.md`

**Interfaces:**
- Produces: 标题为`# A股短线新闻雷达项目说明书`的Markdown文档。
- Produces: `ProjectGuideContractTest`，供后续任务逐步增加契约断言。
- Consumes: `docs/superpowers/specs/2026-08-09-project-guide-design.md`。

- [ ] **Step 1: 编写最小失败测试**

创建`tests/test_project_guide.py`，先包含：

```python
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/PROJECT_GUIDE.md"


class ProjectGuideContractTest(unittest.TestCase):
    def test_guide_exists_with_title_and_verification_date(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# A股短线新闻雷达项目说明书\n"))
        self.assertRegex(text, r"最后核验日期：2026-08-09")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认RED**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: ERROR，`docs/PROJECT_GUIDE.md`不存在。

- [ ] **Step 3: 创建最小说明书骨架**

创建`docs/PROJECT_GUIDE.md`，包含标题、最后核验日期、适用版本、权威入口说明和以下一级章节：

```markdown
## 1. 项目定位与阅读方法
## 2. 当前状态总览
## 3. 架构与数据流
## 4. 新闻时间窗口与北京时间
## 5. 采集来源矩阵
## 6. 事件发现、去重与传播链
## 7. 热度体系
## 8. 主榜准入与排序
## 9. 报告结构与专项规则
## 10. 标准运行步骤
## 11. 15分钟并行流程
## 12. 文件目录与产物关系
## 13. Markdown、HTML与公网发布
## 14. 安全与公开边界
## 15. 失败降级与故障排查
## 16. 设计决策记录
## 17. 计划与完成情况
## 18. UAT测试用例
## 19. 集成测试用例
## 20. 已知限制与后续路线
## 21. 文档维护规则
## 22. 变更记录
```

- [ ] **Step 4: 运行最小契约并确认GREEN**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: 1 test passed。

- [ ] **Step 5: 记录Task 1结果**

在`.planning/2026-08-09-project-guide/progress.md`记录RED错误、GREEN结果和新增文件，不提交半成品骨架。

---

### Task 2: 写入项目方法、来源、时间、热度与报告规则

**Files:**
- Modify: `docs/PROJECT_GUIDE.md`
- Modify: `tests/test_project_guide.py`
- Modify: `.planning/2026-08-09-project-guide/findings.md`
- Modify: `.planning/2026-08-09-project-guide/progress.md`

**Interfaces:**
- Consumes: `HANDOFF.md`、`findings.md`、最新设计规格和`evidence/2026-08-03-0800-*.md/json`。
- Produces: 普通读者可独立理解的第1—9章。

- [ ] **Step 1: 增加业务方法契约测试**

在`ProjectGuideContractTest`新增断言：

```python
def test_current_heat_formula_and_comparison_rules_are_explicit(self):
    text = GUIDE.read_text(encoding="utf-8")
    self.assertIn("覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10", text)
    self.assertIn("同一永久URL", text)
    self.assertIn("同一字段", text)
    self.assertIn("新出现", text)
    self.assertIn("不同平台的数字不得相加", text)

def test_time_window_and_specific_link_rules_are_explicit(self):
    text = GUIDE.read_text(encoding="utf-8")
    self.assertIn("Asia/Shanghai", text)
    self.assertIn("前一交易日00:00", text)
    self.assertIn("全部自然日", text)
    self.assertIn("精确分钟未取得", text)
    self.assertIn("首页和搜索页不能替代", text)

def test_source_matrix_contains_required_platforms(self):
    text = GUIDE.read_text(encoding="utf-8")
    for source in ("财联社", "NewsNow", "微博", "雪球", "X", "淘股吧", "韭研公社", "东方财富", "开盘啦"):
        with self.subTest(source=source):
            self.assertIn(source, text)
```

- [ ] **Step 2: 运行新增测试并确认RED**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: 新增的3项测试失败，显示尚未写入当前口径和来源矩阵。

- [ ] **Step 3: 完成第1—9章**

逐章写入：

- 项目目标、非目标和阅读顺序；
- 当前有效口径与状态标签；
- 三路采集和事件处理数据流；
- 普通交易日、周一、节假日、旧闻异动和跨时区规则；
- 来源矩阵的角色、字段、登录、状态、限制和证据；
- 事件ID、去重边界、事实触发点和传播节点；
- 五项热度公式及严格可比、新出现、旧闻异动、不可比较示例；
- 主榜准入、降序和同分规则；
- Top 10深度、长尾、标题、财报反馈和IPO日程规则。

引用至少以下相对路径作为实例或依据：

```text
../evidence/2026-08-03-0800-heat-agent.md
../evidence/2026-08-03-0800-heat-baseline.json
../reports/2026-07-31-0800-premarket-news-ranking.md
superpowers/specs/2026-07-29-trading-window-compact-news-ranking-design.md
superpowers/specs/2026-07-30-15min-full-delivery-optimization-design.md
```

- [ ] **Step 4: 运行文档契约并确认GREEN**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: Task 1和Task 2的全部测试通过。

- [ ] **Step 5: 记录来源状态冲突的解决方式**

在`findings.md`明确记录：早期`HANDOFF.md`的登录状态和权重是历史口径；说明书以2026-08-03证据和最新设计为准，并保留“最近验证日期”，不承诺登录状态永久有效。

---

### Task 3: 写入运行步骤、文件关系、安全、降级和状态台账

**Files:**
- Modify: `docs/PROJECT_GUIDE.md`
- Modify: `tests/test_project_guide.py`
- Modify: `.planning/2026-08-09-project-guide/progress.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-07-30-15min-top10-depth-design.md`、`docs/superpowers/specs/2026-08-01-news-radar-web-github-pages-design.md`和隔离工作树文件清单。
- Produces: 维护者可执行的第10—17章。

- [ ] **Step 1: 增加运行和状态契约测试**

新增：

```python
def test_runtime_and_status_boundaries_are_explicit(self):
    text = GUIDE.read_text(encoding="utf-8")
    for phrase in ("海外宏观与财报", "国内政策与公告", "登录渠道热度", "超过15分钟仍继续完成"):
        self.assertIn(phrase, text)
    self.assertIn("codex/news-radar-web", text)
    self.assertIn("尚未合入main", text)
    self.assertIn("GitHub Pages", text)
    self.assertIn("暂停", text)

def test_security_boundaries_are_explicit(self):
    text = GUIDE.read_text(encoding="utf-8")
    for forbidden_source in ("密码", "Cookie", "Token", "Local Storage", "浏览器历史"):
        self.assertIn(forbidden_source, text)
    self.assertIn("不得读取或输出", text)
```

- [ ] **Step 2: 运行测试并确认RED**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: 运行和状态章节尚未完成导致新测试失败。

- [ ] **Step 3: 完成第10—17章**

写入：

- 交易日闸门、载入基线、三路采集、冻结候选、Top 10深挖、生成、验收和交付的逐步操作；
- 15分钟阶段预算与超时不停止规则；
- 根目录、`reports/`、`evidence/`、`docs/`、`tests/`、`.planning/`和网页隔离工作树的职责；
- Markdown是内容源，固定模板生成HTML，公开仓库只接收`web/dist`；
- 登录数据和公开目录安全边界；
- 来源超时、登录失效、无基线、字段缺失、网页解析失败、发布失败的降级表；
- 设计决策记录；
- 纯新闻热榜、V4、交易窗口、V5/V6、15分钟优化、财报/IPO修正、网页、自动任务和说明书的状态台账。

每个状态台账条目必须引用现有设计、计划、报告、测试或提交；网页实现标“已完成于隔离分支/尚未合入”，GitHub发布和自动任务标“暂停”。

- [ ] **Step 4: 运行契约并确认GREEN**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: 所有当前契约测试通过。

---

### Task 4: 持久化UAT、集成测试和实际结果

**Files:**
- Modify: `docs/PROJECT_GUIDE.md`
- Modify: `tests/test_project_guide.py`
- Modify: `.planning/2026-08-09-project-guide/progress.md`

**Interfaces:**
- Consumes: `tests/test_report_contract.py`、隔离分支`tests/test_web_*.py`、历史验证JSON和报告。
- Produces: 稳定编号`UAT-001`起和`IT-001`起的测试台账。

- [ ] **Step 1: 增加测试台账契约**

新增：

```python
def test_uat_and_integration_cases_have_stable_ids(self):
    text = GUIDE.read_text(encoding="utf-8")
    for case_id in ("UAT-001", "UAT-014", "IT-001", "IT-013"):
        self.assertIn(case_id, text)
    for field in ("前置条件", "操作步骤", "预期结果", "当前状态", "实际结果", "证据"):
        self.assertIn(field, text)

def test_no_unresolved_placeholders(self):
    text = GUIDE.read_text(encoding="utf-8")
    for placeholder in ("TBD", "TODO", "待补", "稍后填写"):
        self.assertNotIn(placeholder, text)
```

- [ ] **Step 2: 运行测试并确认RED**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: 稳定编号和测试字段尚未写入导致失败。

- [ ] **Step 3: 写入14个UAT用例**

使用`UAT-001`至`UAT-014`，分别覆盖：

1. 普通交易日盘前窗口；
2. 周一/节假日连续窗口；
3. 海外时间换算与日期跨越；
4. 具体帖子或公告直链；
5. 严格双时点激增参与排序；
6. 新出现不伪造增速；
7. 旧闻异动入主榜；
8. Top 10四段深度；
9. 财报后市场反馈；
10. IPO询价/申购/上市日边界；
11. 来源失败不等于零热度；
12. 禁止“一眼结论”和操作建议；
13. 不同报告网页切换；
14. 超过15分钟继续完成。

每例填写场景、前置条件、操作步骤、预期结果、当前状态、实际结果和证据。已有报告或测试证据的标“已通过”；网页切换和公网相关若尚未在主分支/公网验证，分别标“隔离分支已通过”或“未执行/暂停”。

- [ ] **Step 4: 写入13个集成测试用例**

使用`IT-001`至`IT-013`，覆盖：

1. 三路候选合并和去重；
2. 北京时间排序；
3. 热度基线比较；
4. 分数加总和降序；
5. 财报专项字段；
6. IPO专项字段；
7. Markdown结构契约；
8. 多报告解析与HTML生成；
9. 报告索引和最新入口；
10. 固定模板语义结构；
11. 敏感信息扫描；
12. 原子构建和发布目标保护；
13. GitHub/Pages失败时本地产物保留。

说明已有自动测试的命令、实际结果和证据路径；没有执行过外部发布的用例标“未执行/暂停”。

- [ ] **Step 5: 运行契约并确认GREEN**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
```

Expected: UAT、集成测试、字段和占位符契约全部通过。

---

### Task 5: 链接校验、完整测试、自审和提交

**Files:**
- Modify: `tests/test_project_guide.py`
- Modify: `docs/PROJECT_GUIDE.md`
- Modify: `.planning/2026-08-09-project-guide/task_plan.md`
- Modify: `.planning/2026-08-09-project-guide/findings.md`
- Modify: `.planning/2026-08-09-project-guide/progress.md`

**Interfaces:**
- Consumes: 完整说明书、现有主分支测试和隔离分支测试结果。
- Produces: 可交付、可追溯并已提交的项目说明书。

- [ ] **Step 1: 增加本地相对链接契约**

在测试中加入：

```python
import re

def test_local_markdown_links_exist(self):
    text = GUIDE.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        path = (GUIDE.parent / target.split("#", 1)[0]).resolve()
        with self.subTest(target=target):
            self.assertTrue(path.exists(), target)
```

隔离工作树中的实现证据不得伪装成普通相对链接；正文以代码路径加分支状态说明，或链接到已提交的设计/计划文件。

- [ ] **Step 2: 运行说明书契约和现有主分支测试**

Run:

```bash
python3 -m unittest tests/test_project_guide.py -v
python3 -m unittest discover -s tests -v
```

Expected: 全部通过，无失败或错误。记录实际测试数量，不预先声称固定数量。

- [ ] **Step 3: 执行Markdown和内容自审**

Run:

```bash
rg -n 'TBD|TODO|待补|稍后填写|一眼结论|操作建议|买入|卖出' docs/PROJECT_GUIDE.md
git diff --check -- docs/PROJECT_GUIDE.md tests/test_project_guide.py .planning/2026-08-09-project-guide
```

Expected: 占位符和交易建议0匹配；若“操作建议”等作为禁止规则文字出现，人工确认其上下文并在进度记录中说明；差异空白检查0错误。

- [ ] **Step 4: 对照规格逐项自审**

逐项检查`docs/superpowers/specs/2026-08-09-project-guide-design.md`第16节，确认：来源字段完整、状态有证据、测试编号稳定、暂停事项没有冒充完成、网页分支状态正确、无凭据和不必要绝对路径。

- [ ] **Step 5: 更新计划和完成记录**

在本任务`.planning`三个文件中记录：

- 每个Task完成状态；
- 测试命令、数量和结果；
- 发现并修正的问题；
- 最终文件和提交哈希；
- GitHub、自动任务和分支合并仍保持暂停。

- [ ] **Step 6: 精确暂存并提交**

只暂存：

```bash
git add docs/PROJECT_GUIDE.md tests/test_project_guide.py \
  .planning/2026-08-09-project-guide/task_plan.md \
  .planning/2026-08-09-project-guide/findings.md \
  .planning/2026-08-09-project-guide/progress.md
git diff --cached --check
git diff --cached --name-only
git commit -m "docs: add news radar project guide"
```

Expected: 缓存文件清单恰为上述5个文件；提交成功，不包含其他工作树改动。
