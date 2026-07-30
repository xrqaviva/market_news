# 15分钟全量交付流水线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一个从统一结构化事件卡一次生成新闻报告、证据表、热度基线、验收结果和进度记录的流水线，并用双波子agent调度尽量在端到端15分钟内完成，超时后继续运行直至全部交付。

**Architecture:** 三个子agent第一波并行采集，第二波复用为Top 10深挖与热度补齐，完成后滚动交叉复核；主任务持续接收JSON事件卡，以`event_key`去重并生成单一规范数据集。Python标准库流水线从该数据集原子生成全部Markdown/JSON产物，执行语义验收并记录从任务触发到最终交付的真实耗时；15分钟仅设置SLA状态，不触发停止。

**Tech Stack:** Python 3.9标准库（`dataclasses`、`datetime`、`json`、`pathlib`、`unittest`）、Markdown、JSON、Git。

## Global Constraints

- 全面性和准确性均为硬约束；不得通过减少既定来源、新闻数量、时间节点或事实复核提速。
- 15分钟从任务或自动任务实际触发时开始，到报告、证据、热度基线、验收结果和进度记录全部落盘且可交付时结束。
- 超过15分钟不得中断；必须继续运行至全部产物完成，并记录实际耗时、超时阶段和原因。
- 主榜展示所有满足入榜条件的新闻；仅热点权重前10增加深度模块。
- 热点权重固定为覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10；深度、可靠性、行情和个股映射不参与排序。
- 标题只展示新闻内容，不出现“升温”“激增”“双时点”“趋势未知”等热度或核验判断；使用“锂库存帖子称单周去库约七千吨”一类事实标题。
- 热度变化仍参与排序，但只在标题下方展示；只有同一具体链接、同一字段和两个北京时间快照才计算变化。
- 所有时间统一为北京时间并按从早到晚排列；不能证明首发时使用“最早可核”，不得宣称绝对首发。
- 所有核验链接必须指向具体公告、文章或帖子，不得以平台首页替代。
- 自动任务保持暂停；本计划不启用任何自动任务。
- 不读取或输出密码、Cookie、Local Storage或浏览器历史。
- 现有未跟踪文件属于用户；每次提交只加入本任务明确列出的文件，不执行`git add -A`。

---

## Planned File Structure

```text
.gitignore                                      # 忽略本地运行缓存和macOS杂项
pyproject.toml                                  # Python包和unittest入口约定
news_radar/
  __init__.py                                   # 包版本
  models.py                                     # 事件卡、快照、计分和运行清单模型
  clock.py                                      # 端到端计时、里程碑和SLA状态
  merge.py                                      # 事件去重、时间归一、热度比较和排序
  render.py                                     # 从规范数据一次生成全部交付物
  validate.py                                   # 结构、语义、链接、标题、排序验收
  cli.py                                        # start、compile、validate命令入口
config/news_sources.json                        # 每轮必须尝试及尽力获取的来源登记表
prompts/news_radar/
  wave1-overseas.md                             # 第一波海外采集JSON契约
  wave1-domestic.md                             # 第一波国内采集JSON契约
  wave1-heat.md                                 # 第一波登录渠道热度JSON契约
  wave2-depth.md                                # 第二波Top 10深挖补丁契约
  review.md                                     # 滚动交叉复核问题契约
docs/runbooks/15min-news-radar.md                # 主任务双波调度和超时继续运行手册
tests/
  fixtures/run-input/                           # 小型完整运行样本
  test_models.py
  test_clock.py
  test_merge.py
  test_render.py
  test_validate.py
  test_cli.py
  test_prompt_contracts.py
```

运行时文件写入`runs/`下以run ID命名的子目录，例如`runs/20260730-0800/`；`runs/`加入`.gitignore`，不与已交付的`reports/`和`evidence/`混用。`compile`成功后再将最终文件写入正式目录。

---

### Task 1: 建立运行骨架和端到端计时器

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `news_radar/__init__.py`
- Create: `news_radar/clock.py`
- Create: `tests/test_clock.py`

**Interfaces:**
- Consumes: ISO 8601北京时间字符串和可注入的`now: Callable[[], datetime]`。
- Produces: `RunClock.start(triggered_at: datetime, sla_minutes: int = 15) -> RunClock`、`mark(name: str, at: Optional[datetime] = None) -> None`、`snapshot(at: Optional[datetime] = None) -> dict`和`finish(at: Optional[datetime] = None) -> dict`。

- [ ] **Step 1: 写入项目骨架和失败测试**

`.gitignore`只包含：

```gitignore
.DS_Store
__pycache__/
*.pyc
runs/
```

`pyproject.toml`写入：

```toml
[project]
name = "market-news-radar"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = []
```

`news_radar/__init__.py`写入`__version__ = "0.1.0"`。

`tests/test_clock.py`覆盖两个行为：14分59秒时`within_sla=True`；15分01秒时`within_sla=False`但`should_continue=True`，且`finish()`保存真实秒数和全部里程碑。

```python
from datetime import datetime, timedelta, timezone
import unittest

from news_radar.clock import RunClock

BJT = timezone(timedelta(hours=8))

class RunClockTests(unittest.TestCase):
    def test_just_before_sla_is_within_target(self):
        start = datetime(2026, 7, 30, 8, 0, tzinfo=BJT)
        clock = RunClock.start(start)
        snap = clock.snapshot(start + timedelta(minutes=14, seconds=59))
        self.assertTrue(snap["within_sla"])

    def test_sla_miss_never_requests_stop(self):
        start = datetime(2026, 7, 30, 8, 0, tzinfo=BJT)
        clock = RunClock.start(start)
        snap = clock.snapshot(start + timedelta(minutes=15, seconds=1))
        self.assertFalse(snap["within_sla"])
        self.assertTrue(snap["should_continue"])

    def test_finish_keeps_real_elapsed_and_milestones(self):
        start = datetime(2026, 7, 30, 8, 0, tzinfo=BJT)
        clock = RunClock.start(start)
        clock.mark("candidates_frozen", start + timedelta(minutes=4))
        result = clock.finish(start + timedelta(minutes=16))
        self.assertEqual(result["elapsed_seconds"], 960)
        self.assertEqual(result["milestones"]["candidates_frozen"], "2026-07-30T08:04:00+08:00")
        self.assertTrue(result["completed"])
        self.assertFalse(result["should_continue"])
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python3 -m unittest tests.test_clock -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'news_radar'`.

- [ ] **Step 3: 实现最小计时器**

在`news_radar/clock.py`使用带时区`datetime`，拒绝naive时间；`snapshot()`始终返回：

```python
{
    "triggered_at_bjt": "2026-07-30T08:00:00+08:00",
    "checked_at_bjt": "2026-07-30T08:15:01+08:00",
    "elapsed_seconds": 901,
    "sla_seconds": 900,
    "within_sla": False,
    "should_continue": True,
    "completed": False,
    "milestones": {},
}
```

`finish()`把`completed`置为`True`并将`should_continue`置为`False`，因为全部工作已经完成；不得仅因SLA超时抛出异常或提前返回停止信号。

- [ ] **Step 4: 运行计时器测试**

Run: `python3 -m unittest tests.test_clock -v`

Expected: 3 tests PASS.

- [ ] **Step 5: 提交运行骨架**

```bash
git add .gitignore pyproject.toml news_radar/__init__.py news_radar/clock.py tests/test_clock.py
git commit -m "feat: add end-to-end SLA clock"
```

---

### Task 2: 定义固定事件卡和运行清单模型

**Files:**
- Create: `news_radar/models.py`
- Create: `tests/test_models.py`
- Create: `config/news_sources.json`
- Create: `tests/fixtures/run-input/manifest.json`
- Create: `tests/fixtures/run-input/cards/overseas.json`
- Create: `tests/fixtures/run-input/cards/domestic.json`
- Create: `tests/fixtures/run-input/cards/heat.json`

**Interfaces:**
- Consumes: `dict`或JSON文件。
- Produces: `RunManifest.from_dict(data) -> RunManifest`、`EventCard.from_dict(data) -> EventCard`、`ScoreComponents.total -> int`、`EventCard.to_dict() -> dict`、`CheckResult`和`ValidationReport`数据类型。

- [ ] **Step 1: 写事件卡解析失败测试**

`tests/test_models.py`至少验证：

```python
class ModelTests(unittest.TestCase):
    def test_score_total_and_caps(self):
        score = ScoreComponents(coverage=25, change=30, absolute=20, freshness=15, frequency=10)
        self.assertEqual(score.total, 100)
        with self.assertRaisesRegex(ValueError, "coverage must be between 0 and 25"):
            ScoreComponents(coverage=26, change=0, absolute=0, freshness=0, frequency=0)

    def test_event_requires_specific_http_link(self):
        data = valid_event_dict()
        data["timeline"][0]["url"] = "https://www.jiuyangongshe.com/"
        with self.assertRaisesRegex(ValueError, "platform homepage is not a specific evidence link"):
            EventCard.from_dict(data)
```

有效事件fixture使用标题`锂库存帖子称单周去库约七千吨`，包含：

- `event_id`和跨agent一致的`event_key`；
- `title`、`core_info`、`first_verifiable_at_bjt`；
- 按时间排列的`timeline`；
- 具体`https://xueqiu.com/6238316110/402667020`链接；
- `score`五分项；
- `heat_snapshots`；
- `accuracy_boundary`、`unconfirmed`；
- 可为空的`depth`。

- [ ] **Step 2: 运行模型测试并确认失败**

Run: `python3 -m unittest tests.test_models -v`

Expected: FAIL because `news_radar.models` does not exist.

- [ ] **Step 3: 实现不可变数据模型和显式校验**

使用`@dataclass(frozen=True)`定义：

```python
ScoreComponents(coverage, change, absolute, freshness, frequency)
TimelineNode(at_bjt, channel, detail, url, original_time=None)
HeatSnapshot(captured_at_bjt, channel, canonical_url, metrics, rank=None)
DepthBlock(signal, market_feedback, boundary, variables)
EventCard(event_id, event_key, title, core_info, first_verifiable_at_bjt,
          timeline, score, heat_snapshots, accuracy_boundary, unconfirmed,
          depth=None, tags=())
SourceAttempt(source, role, started_at_bjt, stopped_at_bjt, status, detail)
RunManifest(run_id, slot, triggered_at_bjt, window_start_bjt, cutoff_bjt,
            sla_minutes, milestones, source_attempts)
CheckResult(name, passed, details)
ValidationReport(passed, checks, blocking_errors)
```

时间字符串解析后必须带`+08:00`；`timeline`必须非空；链接必须为HTTP(S)具体路径。禁止的平台首页至少包括`https://www.jiuyangongshe.com/`、`https://xueqiu.com/`、`https://weibo.com/`和`https://www.cls.cn/`。

同一步创建`config/news_sources.json`，登记官方/监管/交易所与公司原页、财联社、东方财富、主流财经媒体、NewsNow、微博、雪球、X、淘股吧、韭研公社和开盘啦，并为每项保存`name`、`role`和`requirement`；`requirement`仅允许`required`或`best_effort`。

- [ ] **Step 4: 运行模型测试和fixture往返测试**

Run: `python3 -m unittest tests.test_models -v`

Expected: all tests PASS and `EventCard.from_dict(card.to_dict()) == card`.

- [ ] **Step 5: 提交模型与fixtures**

```bash
git add news_radar/models.py config/news_sources.json tests/test_models.py tests/fixtures/run-input
git commit -m "feat: define structured news event contracts"
```

---

### Task 3: 实现安全去重、时间归一和严格双时点热度比较

**Files:**
- Create: `news_radar/merge.py`
- Create: `tests/test_merge.py`

**Interfaces:**
- Consumes: `merge_event_cards(cards: Sequence[EventCard])`。
- Produces: `MergedRun(events: tuple[EventCard, ...], conflicts: tuple[MergeConflict, ...])`、`compare_heat(snapshots: Sequence[HeatSnapshot]) -> tuple[HeatChange, ...]`、`rank_events(events: Sequence[EventCard]) -> tuple[EventCard, ...]`。

- [ ] **Step 1: 写去重和热度比较失败测试**

测试必须包含：

1. 两个agent返回相同`event_key`时合并时间线和来源，而不是生成两条新闻；
2. 同一URL、相同指标键、两个北京时间快照可计算`437→501，+64，+14.6%`；
3. 不同URL、不同指标键或只有一个快照时不计算百分比，返回`not_comparable`；
4. 无上一窗口基线时返回`new_appearance=True`但`percent_change=None`；
5. 排序只按五项总分降序，同分以`first_verifiable_at_bjt`较新者优先，再以`event_key`稳定排序；
6. 合并时核心数字冲突进入`conflicts`，不得静默覆盖。

- [ ] **Step 2: 运行合并测试并确认失败**

Run: `python3 -m unittest tests.test_merge -v`

Expected: FAIL because `news_radar.merge` does not exist.

- [ ] **Step 3: 实现基于`event_key`的确定性合并**

`merge_event_cards`按`event_key`分组；合并相同时间节点和具体链接，按`at_bjt`升序排列。标题和核心事实不做模糊自动覆盖：完全相同则保留；不同则写入`MergeConflict(event_key, field, values)`，由主任务或复核补丁解决。

- [ ] **Step 4: 实现严格热度比较和排序**

`compare_heat`仅在`canonical_url`完全相同且两个快照共有指标键时计算逐字段增量；允许对共有指标求总互动，但不得把榜位和互动相加。没有有效前点时标记新出现，变化分仍使用事件卡的明确评分，不由比较函数擅自改分。

- [ ] **Step 5: 运行合并测试**

Run: `python3 -m unittest tests.test_merge -v`

Expected: all tests PASS.

- [ ] **Step 6: 提交合并逻辑**

```bash
git add news_radar/merge.py tests/test_merge.py
git commit -m "feat: merge events and compare strict heat snapshots"
```

---

### Task 4: 从单一规范数据一次生成全部交付物

**Files:**
- Create: `news_radar/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `render_content(manifest: RunManifest, events: Sequence[EventCard], heat_changes: Mapping[str, Sequence[HeatChange]]) -> RenderedBundle`，以及`publish_all(bundle: RenderedBundle, validation: ValidationReport, destinations: OutputPaths) -> RenderedFiles`。
- Produces: 先在内存中生成报告Markdown、证据Markdown、热度基线对象和进度Markdown片段；Task 5验收后，`publish_all`连同验收JSON原子发布五类产物。所有文件携带相同`run_id`和`data_version`。

`news_radar.render`同时定义`RenderedBundle(report, evidence, baseline, progress, run_id, data_version)`、`OutputPaths(report, evidence, baseline, validation, progress, completion_marker)`和`RenderedFiles`，避免渲染层依赖CLI内部类型。

- [ ] **Step 1: 写五产物一致性失败测试**

`tests/test_render.py`使用fixtures并断言：

```python
self.assertIn("## 1. 锂库存帖子称单周去库约七千吨", report)
self.assertNotIn("## 1. 锂库存帖子继续升温", report)
self.assertIn("**热度变化：**", report)
self.assertIn("10:00", report)
self.assertIn("16:16", report)
self.assertEqual(report_run_id, evidence_run_id)
self.assertEqual(report_run_id, baseline["run_id"])
self.assertIn("SLA未达标，任务已继续至完整交付", progress_when_late)
```

同时验证Top 10包含四个深度字段，第11名以后不强制深度块，但仍包含核心信息、时间表和具体链接。

- [ ] **Step 2: 运行渲染测试并确认失败**

Run: `python3 -m unittest tests.test_render -v`

Expected: FAIL because `news_radar.render` does not exist.

- [ ] **Step 3: 实现紧凑报告和证据渲染器**

报告单条顺序固定为：标题、核心信息、热点权重、传播渠道与北京时间表、热度变化、紧凑尾注；Top 10尾注后增加`关键信号/预期差`、`带时间市场反馈`、`判断边界`和`后续变量`。热度状态不得拼接到标题。

证据表保留完整事件卡、合并冲突处理记录、来源失败记录和复核结果。所有Markdown链接使用事件卡内具体URL。

- [ ] **Step 4: 实现基线、验收和进度渲染器**

基线JSON只保存未来可比所需的具体URL、采集北京时间、原始指标和榜位，不保存浏览器凭据。进度片段写端到端起止时间、各里程碑、实际耗时、是否达标、超时阶段和来源降级。

最终输出先写入运行目录下的`staging/`，验收通过后写入每轮唯一的新文件名，再以`delivery-complete.json`作为最后一个完成标记；任一生成失败不得覆盖已有正式报告，也不得写完成标记。

- [ ] **Step 5: 运行渲染测试**

Run: `python3 -m unittest tests.test_render -v`

Expected: all tests PASS.

- [ ] **Step 6: 提交渲染逻辑**

```bash
git add news_radar/render.py tests/test_render.py
git commit -m "feat: render all news radar deliverables from one dataset"
```

---

### Task 5: 建立机械验收和标题语义守卫

**Files:**
- Create: `news_radar/validate.py`
- Create: `tests/test_validate.py`

**Interfaces:**
- Consumes: `validate_run(manifest: RunManifest, events: Sequence[EventCard], conflicts: Sequence[MergeConflict], rendered: RenderedBundle, source_registry: Mapping[str, object]) -> ValidationReport`。
- Produces: `ValidationReport(passed: bool, checks: tuple[CheckResult, ...], blocking_errors: tuple[str, ...])`。

- [ ] **Step 1: 写语义验收失败测试**

覆盖以下阻断项：

- 标题包含`升温`、`激增`、`双时点`、`趋势未知`；
- 标题和核心信息为空；
- 时间节点不是北京时间或未按升序；
- 使用平台首页链接；
- 五项分数超上限、总分不等于分项之和或主榜非降序；
- Top 10缺任一深度字段；
- 双时点变化来自不同帖子或不同字段；
- `config/news_sources.json`中标为`required`的来源既没有成功记录也没有结构化失败记录；
- 报告、证据、基线、验收和进度的`run_id`或`data_version`不一致；
- 存在未解决的核心事实冲突；
- 出现“一眼结论”、操作建议、买入、卖出或交易信号。

- [ ] **Step 2: 运行验收测试并确认失败**

Run: `python3 -m unittest tests.test_validate -v`

Expected: FAIL because `news_radar.validate` does not exist.

- [ ] **Step 3: 实现逐项可读的验收报告**

每个检查返回`CheckResult(name, passed, details)`；阻断错误使`ValidationReport.passed=False`。SLA超时是必须记录的非阻断状态，不得导致流水线停止或跳过交付；交付完整性、事实冲突和链接错误仍为阻断项。

- [ ] **Step 4: 运行验收测试**

Run: `python3 -m unittest tests.test_validate -v`

Expected: all tests PASS.

- [ ] **Step 5: 提交验收逻辑**

```bash
git add news_radar/validate.py tests/test_validate.py
git commit -m "feat: validate report semantics and artifact consistency"
```

---

### Task 6: 实现可恢复CLI和超时后持续完成

**Files:**
- Create: `news_radar/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `python3 -m news_radar.cli start|compile|validate`命令。
- Produces: 可恢复的运行目录，例如`runs/20260730-0800/manifest.json`、`canonical-events.json`、staging产物和正式交付物。

- [ ] **Step 1: 写CLI端到端失败测试**

使用`tempfile.TemporaryDirectory()`测试：

```bash
python3 -m news_radar.cli start \
  --run-id 20260730-0800 \
  --slot premarket \
  --triggered-at 2026-07-30T08:00:00+08:00 \
  --window-start 2026-07-29T00:00:00+08:00 \
  --cutoff 2026-07-30T08:00:00+08:00 \
  --run-root /tmp/market-news-cli-test/runs
```

断言`start`立即写入真实触发时间，重复执行同一`run_id`不会重置计时。复制fixture事件卡后运行`compile`，断言五类产物同时生成。使用超过15分钟的`--finished-at`运行时，命令仍返回成功并写`within_sla=false`、`should_continue=false`、`completed=true`和真实耗时。

- [ ] **Step 2: 运行CLI测试并确认失败**

Run: `python3 -m unittest tests.test_cli -v`

Expected: FAIL because `news_radar.cli` does not exist.

- [ ] **Step 3: 实现`start`和幂等恢复**

`start`使用排他创建；已有同名manifest时读取原`triggered_at_bjt`并继续，不覆盖里程碑。每次阶段更新通过临时文件加`Path.replace()`原子写入。

- [ ] **Step 4: 实现`compile`和`validate`**

`compile`读取三路卡、深挖补丁和复核补丁，拒绝未解决冲突，生成规范数据，调用`render_content`、`validate_run`和`publish_all`；来源登记表默认读取`config/news_sources.json`。SLA超过15分钟只记录状态，不触发`TimeoutError`。`validate`可以对已完成run重复执行，输出相同结果而不改新闻内容。

- [ ] **Step 5: 运行CLI测试和全套单元测试**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 6: 提交CLI**

```bash
git add news_radar/cli.py tests/test_cli.py
git commit -m "feat: add resumable news radar pipeline CLI"
```

---

### Task 7: 固化双波子agent JSON契约和运行手册

**Files:**
- Create: `prompts/news_radar/wave1-overseas.md`
- Create: `prompts/news_radar/wave1-domestic.md`
- Create: `prompts/news_radar/wave1-heat.md`
- Create: `prompts/news_radar/wave2-depth.md`
- Create: `prompts/news_radar/review.md`
- Modify: `config/news_sources.json`
- Create: `docs/runbooks/15min-news-radar.md`
- Create: `tests/test_prompt_contracts.py`

**Interfaces:**
- Consumes: manifest窗口、上一轮基线、分配给agent的事件ID和输入路径。
- Produces: 运行目录`cards/`、`patches/`和`reviews/`下按角色命名的JSON文件；字段与`news_radar.models`完全一致。

- [ ] **Step 1: 写prompt契约失败测试**

`tests/test_prompt_contracts.py`读取五个prompt并断言都明确：只输出JSON、北京时间、具体帖子链接、禁止读取凭据、失败结构、不得把热度判断写入标题。热度prompt额外包含同帖同字段规则；review prompt包含阻断事实冲突和SLA超时后继续完成规则。

- [ ] **Step 2: 运行prompt测试并确认失败**

Run: `python3 -m unittest tests.test_prompt_contracts -v`

Expected: FAIL because prompt files do not exist.

- [ ] **Step 3: 编写第一波prompt**

三份第一波prompt使用同一JSON envelope：

```json
{
  "run_id": "20260730-0800",
  "role": "overseas",
  "completed_at_bjt": "2026-07-30T08:03:40+08:00",
  "events": [],
  "source_attempts": []
}
```

海外和国内组不得操作登录Chrome；热度组独占Chrome，只读取可见内容。所有组对分配来源均返回`source_attempts`，状态限定为`success`、`failed`、`blocked`或`timed_out`，不得用长篇Markdown代替JSON。

- [ ] **Step 4: 编写第二波深挖和复核prompt**

深挖prompt只允许按`event_key`返回字段补丁，不重写排名。复核prompt返回：

```json
{
  "run_id": "20260730-0800",
  "reviewer": "heat",
  "issues": [
    {
      "event_key": "lithium-inventory-6950t",
      "field": "title",
      "severity": "blocking",
      "replacement": "锂库存帖子称单周去库约七千吨",
      "evidence_url": "https://xueqiu.com/6238316110/402667020"
    }
  ]
}
```

无证据链接的事实性替换不得自动应用。

- [ ] **Step 5: 编写分钟级主任务手册**

手册明确0分钟启动计时与三个agent，4分钟冻结临时候选并发起第二波，8分钟开始滚动复核，11分钟生成，13分钟验收，15分钟记录SLA状态；超过15分钟继续等待必要agent、修正和验收，直到完整交付。手册同时列出每阶段应写的manifest里程碑名称。

核对`config/news_sources.json`中的角色分配与三份第一波prompt一致。每项标记`required`或`best_effort`；`required`来源每轮必须有成功或结构化失败记录，`best_effort`来源不可访问时也必须在覆盖边界披露。

- [ ] **Step 6: 运行prompt测试**

Run: `python3 -m unittest tests.test_prompt_contracts -v`

Expected: all tests PASS.

- [ ] **Step 7: 提交prompt和手册**

```bash
git add prompts/news_radar config/news_sources.json docs/runbooks/15min-news-radar.md tests/test_prompt_contracts.py
git commit -m "docs: define two-wave agent delivery protocol"
```

---

### Task 8: 完整试跑、性能记录和项目文档更新

**Files:**
- Modify: `HANDOFF.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Create: `tests/fixtures/run-input/patches/depth-overseas.json`
- Create: `tests/fixtures/run-input/patches/depth-domestic.json`
- Create: `tests/fixtures/run-input/reviews/heat.json`

**Interfaces:**
- Consumes: Task 1—7的完整CLI、fixtures和运行手册。
- Produces: 一次可重复的fixture端到端运行、一次真实新闻试跑记录和更新后的项目交接信息。

- [ ] **Step 1: 补齐完整fixture并运行端到端测试**

Run:

```bash
python3 -m news_radar.cli start --run-id fixture-0800 --slot premarket --triggered-at 2026-07-30T08:00:00+08:00 --window-start 2026-07-29T00:00:00+08:00 --cutoff 2026-07-30T08:00:00+08:00 --run-root /tmp/market-news-fixture-runs
python3 -m news_radar.cli compile --run-id fixture-0800 --run-root /tmp/market-news-fixture-runs --input tests/fixtures/run-input --output /tmp/market-news-fixture-output --finished-at 2026-07-30T08:16:20+08:00
python3 -m news_radar.cli validate --run-id fixture-0800 --run-root /tmp/market-news-fixture-runs --output /tmp/market-news-fixture-output
```

Expected: compile and validate both succeed; output records `elapsed_seconds=980` and SLA miss but contains all five deliverables.

- [ ] **Step 2: 运行全套回归测试**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests PASS with no network or Chrome dependency.

- [ ] **Step 3: 按运行手册执行一次真实双波试跑**

任务触发即运行`start`，使用三个子agent完成两波采集、深挖和滚动复核，随后运行`compile`与`validate`。真实试跑不得覆盖V5、V6或15:00既有报告；使用新的run ID和文件名。若超过15分钟，继续至全部交付并如实记录。

- [ ] **Step 4: 核对真实性和完整性**

人工抽查Top 10的数字、北京时间、原始来源、具体链接和标题；确认热度描述位于详情中而非标题，旧闻异动与新出现仍参与排序，长尾新闻数量未因优化减少。

- [ ] **Step 5: 更新项目文档**

在`HANDOFF.md`将“目录不是Git仓库”改为已初始化Git，并写入新CLI、prompt和手册入口。在`task_plan.md`增加15分钟全量交付优化阶段。在`progress.md`记录测试数量、真实端到端耗时、各里程碑、SLA结果、超时原因、新闻数量和来源失败。

- [ ] **Step 6: 检查本任务变更并提交**

Run: `git status --short`

Expected: 只出现本任务明确修改的fixture和三个项目文档；用户原有未跟踪报告与证据仍未被意外加入暂存区。

```bash
git add HANDOFF.md task_plan.md progress.md tests/fixtures/run-input/patches tests/fixtures/run-input/reviews
git commit -m "test: verify full news radar delivery workflow"
```

---

## Final Verification

- Run: `python3 -m unittest discover -s tests -v`
- Expected: all unit, prompt-contract and end-to-end tests PASS.
- Run: `python3 -m news_radar.cli validate --run-id optimization-real-0800 --run-root runs --output reports/optimization-real-0800`
- Expected: `passed=true`; SLA是否达标单独记录，不阻断超时后的完整交付。
- Run: `git status --short`
- Expected: 没有本计划产生的未提交代码；用户既有未跟踪文件保持未跟踪，除非该文件在Task 8中被明确加入。
- Verify generated artifacts: 报告、证据、基线、验收、进度记录的`run_id`和`data_version`一致；标题不含热度判断；Top 10深度字段齐全；主榜新闻完整且严格降序。
