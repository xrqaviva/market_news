# A股新闻雷达静态网页与GitHub Pages实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将既有Markdown新闻报告通过固定模板生成可切换日期与时段的独立HTML，并在明确授权后发布到独立公开GitHub Pages仓库。

**Architecture:** `web/report_parser.py`把Markdown解析成只读数据模型，`web/build.py`使用固定模板与静态资源在临时目录生成完整网站并原子替换`web/dist/`。`web/publish.py`以dry-run为默认值，在明确参数下完成安全扫描、同步、提交和非强制推送；GitHub创建、首次推送、Pages启用和08:00自动任务修改属于独立授权阶段。

**Tech Stack:** Python 3.9标准库、HTML5、CSS3、原生JavaScript、`unittest`、Git、GitHub CLI 2.94、GitHub Pages。

## Global Constraints

- Markdown是唯一内容源；结果HTML不得手工修改。
- 固定模板采用已确认的B方案“研究终端”，日报只替换数据。
- 每份报告生成`reports/<YYYY-MM-DD>-<slot>.html`稳定URL。
- 当前仓库保留模板、转换器、测试与证据；公开仓库只接收`web/dist/`。
- 不新增运行时Python或JavaScript第三方依赖。
- 所有报告时间按北京时间展示，排序与热点权重完全沿用Markdown。
- 不输出买卖建议，不根据缺失字段补造内容。
- 发布前扫描本机绝对路径、凭据模式和私有文件名；命中即失败。
- 构建在临时目录完成，全部验证通过后才替换`web/dist/`。
- 中午12:00和下午15:00自动任务保持暂停。
- 不读取或输出密码、Cookie、Token、Local Storage或浏览器历史。
- 当前工作树包含用户已有的修改和大量未跟踪研究文件；每个任务只暂存计划列出的路径，不清理、不回退、不批量暂存其他文件。
- 任何`git commit`、公开仓库创建、首次推送、Pages启用和自动任务修改都必须在执行时有用户明确授权。

## Discovery and Baseline

- Repository root: `/Users/aviva/Projects/market_news`。
- Current branch: `main`；当前仓库无远端。
- Existing test harness: `python3 -m unittest discover -s tests -v`。
- Python: 3.9.6；GitHub CLI: 2.94.0。
- GitHub CLI当前账号`xrqaviva`的Token无效；公网阶段必须由用户重新执行`gh auth login -h github.com`，不得绕过认证。
- 现有网页代码为空；不存在`.openai/hosting.json`，本项目不采用Sites托管。
- 首批历史源报告固定为设计文档列出的4份，避免重复发布测试草稿。

## File Map

| Path | Responsibility |
|---|---|
| `web/__init__.py` | 声明网页生成包 |
| `web/report_model.py` | 只读报告、新闻、来源数据类型 |
| `web/report_catalog.json` | 4份历史报告兼容映射 |
| `web/report_parser.py` | 发现、解析和校验Markdown |
| `web/templates/report.html` | 固定HTML语义模板 |
| `web/assets/app.css` | B方案视觉、响应式和打印样式 |
| `web/assets/app.js` | 报告跳转、筛选和详情展开 |
| `web/security.py` | 公开目录敏感信息与范围扫描 |
| `web/build.py` | 原子构建HTML、索引和资源 |
| `web/publish.py` | 验证并发布到独立公开仓库，默认dry-run；显式开启同步、提交和非强制推送 |
| `scripts/run_morning_site.sh` | 08:00任务调用的固定构建/发布入口 |
| `tests/test_web_parser.py` | 模型、目录和解析单元测试 |
| `tests/test_web_build.py` | 多报告、模板、原子构建集成测试 |
| `tests/test_web_security.py` | 敏感内容和公开范围测试 |
| `tests/test_web_publish.py` | 临时Git仓库内的发布脚本测试 |
| `web/dist/` | 生成结果；不作为手工编辑源 |

---

### Task 1: 报告数据模型、历史目录与Markdown解析器

**Files:**
- Create: `web/__init__.py`
- Create: `web/report_model.py`
- Create: `web/report_catalog.json`
- Create: `web/report_parser.py`
- Create: `tests/test_web_parser.py`

**Interfaces:**
- Produces: `SourceLink`, `NewsItem`, `ReportMeta`, `ReportDocument` frozen dataclasses.
- Produces: `load_catalog(project_root: Path) -> list[CatalogEntry]`.
- Produces: `discover_reports(project_root: Path) -> list[tuple[Path, CatalogEntry]]`.
- Produces: `parse_report(path: Path, entry: CatalogEntry) -> ReportDocument`.
- Consumers: Tasks 2–5 import these exact names.

- [ ] **Step 1: Establish and record the pre-change baseline**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: existing report contract suite passes with 7 tests, 0 failures and 0 errors. Record the timestamp and exact result in `progress.md`; do not claim a comparative baseline if the count differs.

- [ ] **Step 2: Write failing catalog and model tests**

Create `tests/test_web_parser.py` with these assertions:

```python
from pathlib import Path
import unittest

from web.report_parser import discover_reports, parse_report


ROOT = Path(__file__).resolve().parents[1]


class WebReportParserTest(unittest.TestCase):
    def test_catalog_selects_exactly_four_legacy_reports(self):
        found = discover_reports(ROOT)
        self.assertEqual(4, len(found))
        self.assertEqual(
            ["20260729-1800", "20260730-0800", "20260730-1500", "20260731-0800"],
            [entry.report_id for _, entry in found],
        )

    def test_latest_report_parses_ranked_news_and_sources(self):
        found = dict((entry.report_id, (path, entry)) for path, entry in discover_reports(ROOT))
        document = parse_report(*found["20260731-0800"])
        self.assertEqual("2026-07-31", document.meta.report_date)
        self.assertEqual("0800", document.meta.slot)
        self.assertEqual("盘前", document.meta.slot_label)
        self.assertEqual(22, len(document.items))
        self.assertEqual(1, document.items[0].rank)
        self.assertEqual(96, document.items[0].score)
        self.assertTrue(document.items[0].sources)

    def test_unitree_item_keeps_subscription_date_and_direct_link(self):
        found = dict((entry.report_id, (path, entry)) for path, entry in discover_reports(ROOT))
        document = parse_report(*found["20260731-0800"])
        item = next(item for item in document.items if "宇树科技" in item.title)
        self.assertIn("2026年8月10日", item.core)
        self.assertTrue(any("20260731_1-A25" in source.url for source in item.sources))
```

- [ ] **Step 3: Run parser tests and verify RED**

Run:

```bash
python3 -m unittest tests/test_web_parser.py -v
```

Expected: import failure for missing `web.report_parser`; this is the intended RED.

- [ ] **Step 4: Implement frozen data models**

Create `web/report_model.py` with these exact public fields:

```python
from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class SourceLink:
    channel: str
    time_bj: str
    label: str
    url: str


@dataclass(frozen=True)
class NewsItem:
    rank: int
    title: str
    core: str
    score: int
    score_breakdown: str = ""
    signal: str = ""
    market_feedback: str = ""
    pricing: str = ""
    boundary: str = ""
    variables: str = ""
    heat_change: str = ""
    category: str = "其他"
    sources: Tuple[SourceLink, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReportMeta:
    report_id: str
    report_date: str
    slot: str
    slot_label: str
    title: str
    window: str
    cutoff: str
    source_name: str


@dataclass(frozen=True)
class ReportDocument:
    meta: ReportMeta
    items: Tuple[NewsItem, ...]
```

- [ ] **Step 5: Implement the explicit legacy catalog**

Create `web/report_catalog.json` with four entries and no glob patterns:

```json
[
  {"report_id":"20260729-1800","path":"reports/2026-07-29-pure-news-hot-ranking-v4.md","date":"2026-07-29","slot":"1800","label":"收盘"},
  {"report_id":"20260730-0800","path":"reports/2026-07-30-premarket-news-ranking-v6-depth-test.md","date":"2026-07-30","slot":"0800","label":"盘前"},
  {"report_id":"20260730-1500","path":"reports/2026-07-30-1500-next-trading-day-news-baseline.md","date":"2026-07-30","slot":"1500","label":"盘后"},
  {"report_id":"20260731-0800","path":"reports/2026-07-31-0800-premarket-news-ranking.md","date":"2026-07-31","slot":"0800","label":"盘前"}
]
```

- [ ] **Step 6: Implement minimal parser behavior**

Create `web/report_parser.py` using only `json`, `re`, `dataclasses`, `html`, `pathlib` and `typing`. Requirements:

```python
@dataclass(frozen=True)
class CatalogEntry:
    report_id: str
    path: str
    report_date: str
    slot: str
    label: str


def load_catalog(project_root: Path) -> list:
    """Load explicit legacy entries, verify relative paths, then append standard-named reports."""


def discover_reports(project_root: Path) -> list:
    """Return (path, entry) sorted by date and slot ascending; reject duplicate report_id."""


def parse_report(path: Path, entry: CatalogEntry) -> ReportDocument:
    """Parse heading sections and compact numbered lines without inventing missing fields."""
```

Parser rules:

- Match Top 10 headings with `^##\s+(\d+)\.\s+(.+)$`.
- Match compact rows with `^(\d+)\.\s+\*\*(.+?)｜(\d+)/100\*\*`.
- Extract bold labels by their Chinese field names, not by fixed line number.
- Parse Markdown tables only inside the current item section.
- Convert each Markdown link `[label](url)` in the channel table into `SourceLink`; reject `javascript:`, `data:` and empty URLs.
- Keep Markdown inline text as plain text; do not execute embedded HTML.
- Categorize with deterministic keywords: policy, financial results, industry, geopolitics, or other.
- Require unique ranks, descending scores and at least one source link for each item.

- [ ] **Step 7: Run parser tests and full baseline**

Run:

```bash
python3 -m unittest tests/test_web_parser.py -v
python3 -m unittest discover -s tests -v
```

Expected: parser tests pass; full suite passes with no failures or errors.

- [ ] **Step 8: Review Task 1 diff and request commit authorization**

Run:

```bash
git diff --check -- web tests/test_web_parser.py
git status --short
```

Verify only Task 1 files would be staged. If authorized:

```bash
git add web/__init__.py web/report_model.py web/report_catalog.json web/report_parser.py tests/test_web_parser.py
git commit -m "feat: parse news radar markdown reports"
```

---

### Task 2: 固定模板、独立HTML和原子网站构建

**Files:**
- Create: `web/templates/report.html`
- Create: `web/build.py`
- Create: `tests/test_web_build.py`
- Generate: `web/dist/index.html`
- Generate: `web/dist/reports.json`
- Generate: `web/dist/reports/*.html`

**Interfaces:**
- Consumes: `discover_reports()` and `parse_report()` from Task 1.
- Produces: `render_report(document: ReportDocument, report_index: list[dict]) -> str`.
- Produces: `build_site(project_root: Path, output_dir: Path) -> BuildResult`.
- Produces: `BuildResult(output_dir: Path, report_count: int, item_count: int, latest_url: str)`.

- [ ] **Step 1: Write failing multi-report build tests**

Create `tests/test_web_build.py`:

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from web.build import build_site


ROOT = Path(__file__).resolve().parents[1]


class WebBuildTest(unittest.TestCase):
    def test_build_creates_index_manifest_and_four_report_pages(self):
        with TemporaryDirectory() as tmp:
            result = build_site(ROOT, Path(tmp) / "dist")
            output = result.output_dir
            manifest = json.loads((output / "reports.json").read_text(encoding="utf-8"))
            self.assertEqual(4, result.report_count)
            self.assertEqual(4, len(manifest["reports"]))
            self.assertEqual("reports/2026-07-31-0800.html", manifest["latest"])
            self.assertTrue((output / manifest["latest"]).exists())
            self.assertIn(manifest["latest"], (output / "index.html").read_text(encoding="utf-8"))

    def test_report_page_has_fixed_semantic_contract(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            for marker in ('data-component="report-archive"', 'data-component="news-list"',
                           'data-component="news-detail"', 'data-component="sources"'):
                self.assertIn(marker, page)
            self.assertIn("宇树科技8月5日初步询价、8月10日申购", page)
            self.assertNotIn("/Users/", page)
```

- [ ] **Step 2: Run build tests and verify RED**

Run:

```bash
python3 -m unittest tests/test_web_build.py -v
```

Expected: import failure for missing `web.build`.

- [ ] **Step 3: Create fixed semantic template**

Create `web/templates/report.html` with these stable markers and escaped placeholders:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{PAGE_TITLE}}</title>
  <link rel="stylesheet" href="../assets/app.css">
</head>
<body data-report-id="{{REPORT_ID}}">
  <header class="topbar">{{TOPBAR}}</header>
  <div class="terminal-layout">
    <aside data-component="report-archive">{{REPORT_ARCHIVE}}</aside>
    <main>
      <nav data-component="filters">{{FILTERS}}</nav>
      <section data-component="news-list">{{NEWS_ITEMS}}</section>
    </main>
  </div>
  <script src="../assets/app.js" defer></script>
</body>
</html>
```

The renderer must own placeholder substitution and HTML escaping. Parsed Markdown must never be concatenated into attributes without `html.escape(..., quote=True)`.

- [ ] **Step 4: Implement renderer and atomic build**

Create `web/build.py` with:

```python
@dataclass(frozen=True)
class BuildResult:
    output_dir: Path
    report_count: int
    item_count: int
    latest_url: str


def render_report(document: ReportDocument, report_index: list) -> str:
    """Render fixed template with escaped text and allowlisted http/https source URLs."""


def build_site(project_root: Path, output_dir: Path) -> BuildResult:
    """Build next to output_dir, validate, then atomically replace only output_dir."""
```

Atomic behavior:

1. Resolve `output_dir` and reject `/`, the project root, home directory and any path not named `dist` in production mode.
2. Create `dist.next-<pid>` beside `dist`.
3. Generate all HTML, `reports.json`, `index.html` and copied assets into the next directory.
4. Validate expected count, stable markers and relative asset paths.
5. Rename existing `dist` to `dist.previous-<pid>`, rename next directory to `dist`, then remove only the explicit previous directory.
6. On exception, restore the previous directory and return nonzero from CLI.

The CLI must support:

```bash
python3 -m web.build --project-root /Users/aviva/Projects/market_news --output web/dist
```

The generated `index.html` uses a static meta refresh and visible link to the latest report; it contains no JavaScript-based remote fetch.

- [ ] **Step 5: Run build tests and inspect generated structure**

Run:

```bash
python3 -m unittest tests/test_web_build.py -v
python3 -m web.build --project-root /Users/aviva/Projects/market_news --output web/dist
find web/dist -maxdepth 3 -type f -print
```

Expected: 4 report pages, `index.html`, `reports.json`; no files outside `web/dist/` are generated.

- [ ] **Step 6: Run full suite and review Task 2 diff**

Run:

```bash
python3 -m unittest discover -s tests -v
git diff --check -- web tests/test_web_build.py
```

If commit authorization exists, stage only Task 2 files and generated site:

```bash
git add web/templates/report.html web/build.py web/dist tests/test_web_build.py
git commit -m "feat: build static news report pages"
```

---

### Task 3: B方案视觉、响应式布局与前端交互

**Files:**
- Create: `web/assets/app.css`
- Create: `web/assets/app.js`
- Modify: `web/templates/report.html`
- Modify: `tests/test_web_build.py`
- Regenerate: `web/dist/`

**Interfaces:**
- Consumes: fixed `data-component` markers from Task 2.
- Produces: `.news-toggle` buttons with `aria-expanded` and `aria-controls`.
- Produces: `.filter-button[data-category]` and `.mobile-report-select` behavior.

- [ ] **Step 1: Add failing interaction contract tests**

Extend `tests/test_web_build.py`:

```python
def test_page_has_accessible_interaction_contract(self):
    with TemporaryDirectory() as tmp:
        output = build_site(ROOT, Path(tmp) / "dist").output_dir
        page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
        self.assertIn('class="news-toggle"', page)
        self.assertIn('aria-expanded="false"', page)
        self.assertIn('class="mobile-report-select"', page)
        self.assertIn('class="filter-button is-active"', page)
        self.assertIn('data-category=', page)
```

- [ ] **Step 2: Run the contract test and verify RED**

Run:

```bash
python3 -m unittest tests.test_web_build.WebBuildTest.test_page_has_accessible_interaction_contract -v
```

Expected: FAIL because interaction classes are missing.

- [ ] **Step 3: Implement fixed B-scheme CSS**

Create `web/assets/app.css` with fixed design tokens and responsive behavior:

```css
:root {
  --ink: #152033;
  --muted: #657287;
  --nav: #111827;
  --nav-active: #223047;
  --surface: #ffffff;
  --canvas: #eef2f7;
  --line: #dce2ea;
  --accent: #2563eb;
  --positive-bg: #eaf8f1;
  --positive-fg: #11734b;
  --negative-bg: #fff0f0;
  --negative-fg: #b42318;
  --mixed-bg: #fff6df;
  --mixed-fg: #8a4f0a;
}
```

Required layout rules:

- Desktop grid `220px minmax(0, 1fr)`.
- News rows use `rank / content / score` grid and compact 12px vertical padding.
- Details are hidden with `[hidden]`, expanded within the row, never in a modal.
- At `max-width: 820px`, sidebar hides and `.mobile-report-select` displays.
- Focus ring is visible using `outline: 3px solid var(--accent)`.
- Labels include text in addition to color.
- Print view hides navigation and expands all visible article details.

- [ ] **Step 4: Implement vanilla JavaScript interactions**

Create `web/assets/app.js`:

```javascript
document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".news-toggle");
  if (toggle) {
    const detail = document.getElementById(toggle.getAttribute("aria-controls"));
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!expanded));
    detail.hidden = expanded;
    return;
  }
  const filter = event.target.closest(".filter-button");
  if (filter) applyCategoryFilter(filter.dataset.category);
});

document.querySelector(".mobile-report-select")?.addEventListener("change", (event) => {
  window.location.assign(event.target.value);
});
```

`applyCategoryFilter(category)` must toggle the `hidden` property on `.news-row` elements and update the active button; it must not renumber or reorder rows.

- [ ] **Step 5: Regenerate and rerun focused tests**

Run:

```bash
python3 -m web.build --project-root /Users/aviva/Projects/market_news --output web/dist
python3 -m unittest tests/test_web_build.py -v
```

Expected: all build and interaction contract tests pass.

- [ ] **Step 6: Exercise the real page in a browser**

Start a local server:

```bash
python3 -m http.server 8765 --directory web/dist
```

Using the in-app browser control skill, verify:

1. Open `http://localhost:8765/` and arrive at the latest report.
2. Click the 07-30 15:00 archive entry and observe its stable result URL.
3. Return to 07-31 08:00 and expand Microsoft; verify detail and source links become visible.
4. Select the financial-results filter; verify ranks remain original and nonmatching items hide.
5. Test a viewport at or below 820px; verify sidebar hides, selector appears and no horizontal scroll exists.
6. Inspect browser console and network; require 0 JavaScript errors and 0 local asset 404s.

Record screenshots or browser observations in `progress.md`; do not store browser session data.

- [ ] **Step 7: Run full suite and commit if authorized**

Run:

```bash
python3 -m unittest discover -s tests -v
git diff --check -- web tests/test_web_build.py
```

If authorized:

```bash
git add web/assets/app.css web/assets/app.js web/templates/report.html web/dist tests/test_web_build.py
git commit -m "feat: add research terminal web interface"
```

---

### Task 4: 公开目录安全扫描与失败保护

**Files:**
- Create: `web/security.py`
- Create: `tests/test_web_security.py`
- Modify: `web/build.py`

**Interfaces:**
- Produces: `scan_public_tree(root: Path) -> list[SecurityFinding]`.
- Produces: `assert_public_tree_safe(root: Path) -> None` raising `PublicTreeUnsafe`.
- Consumed by: `build_site()` before atomic replacement and Task 5 publisher before sync.

- [ ] **Step 1: Write failing sensitive-content tests**

Create `tests/test_web_security.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from web.security import PublicTreeUnsafe, assert_public_tree_safe, scan_public_tree


class WebSecurityTest(unittest.TestCase):
    def test_rejects_private_names_and_absolute_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("/Users/aviva/Projects/market_news", encoding="utf-8")
            findings = scan_public_tree(root)
            self.assertTrue(any(item.rule == "absolute-local-path" for item in findings))
            with self.assertRaises(PublicTreeUnsafe):
                assert_public_tree_safe(root)

    def test_accepts_public_report_and_https_links(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<a href="https://apnews.com/article/example">AP</a>', encoding="utf-8"
            )
            self.assertEqual([], scan_public_tree(root))
```

- [ ] **Step 2: Run security tests and verify RED**

Run:

```bash
python3 -m unittest tests/test_web_security.py -v
```

Expected: import failure for missing `web.security`.

- [ ] **Step 3: Implement security scanner**

Create `web/security.py` with:

```python
@dataclass(frozen=True)
class SecurityFinding:
    path: str
    rule: str
    excerpt: str


class PublicTreeUnsafe(RuntimeError):
    pass


def scan_public_tree(root: Path) -> list:
    """Scan only regular files below resolved root; never follow symlinks."""


def assert_public_tree_safe(root: Path) -> None:
    findings = scan_public_tree(root)
    if findings:
        raise PublicTreeUnsafe("; ".join(f"{f.path}:{f.rule}" for f in findings))
```

Rules must reject:

- symlinks;
- filenames matching `evidence`, `findings.md`, `progress.md`, `task_plan.md`, `HANDOFF.md`, `.env`, `.git`, `.superpowers`, `.planning`;
- text containing `/Users/`, `file://`, `BEGIN OPENSSH PRIVATE KEY`, `ghp_`, `github_pat_`, `Authorization: Bearer`, `Cookie:` or `Local Storage`;
- URLs with `javascript:` or `data:`.

For excerpts, replace any matched token after its first 4 characters with `…`; never echo a full possible secret.

- [ ] **Step 4: Integrate scanner before atomic replacement**

In `web/build.py`, call:

```python
assert_public_tree_safe(next_dir)
```

after all files are generated and before any rename. Add a test that injects an unsafe template value and confirms the old output directory remains byte-for-byte unchanged.

- [ ] **Step 5: Run security, build and full suites**

Run:

```bash
python3 -m unittest tests/test_web_security.py tests/test_web_build.py -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass; no secrets or full matched tokens appear in output.

- [ ] **Step 6: Review and commit if authorized**

Run:

```bash
git diff --check -- web/security.py web/build.py tests/test_web_security.py tests/test_web_build.py
```

If authorized:

```bash
git add web/security.py web/build.py tests/test_web_security.py tests/test_web_build.py
git commit -m "test: protect public site output"
```

---

### Task 5: 独立公开仓库固定发布器与本地dry-run

**Files:**
- Create: `web/publish.py`
- Create: `tests/test_web_publish.py`

**Interfaces:**
- Consumes: `assert_public_tree_safe(dist_dir)`.
- Produces: `validate_site_repo(site_repo: Path, expected_name: str) -> None`.
- Produces: `sync_dist(dist_dir: Path, site_repo: Path, dry_run: bool = True) -> PublishResult`.
- Produces: `publish_site(dist_dir: Path, site_repo: Path, apply: bool = False, commit: bool = False, push: bool = False) -> PublishResult`.
- Produces: CLI that defaults to dry-run and requires the ordered flags `--apply --commit --push` for a complete publication.

- [ ] **Step 1: Write failing repository-boundary tests**

Create `tests/test_web_publish.py` using temporary directories and local Git only:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest

from web.publish import PublishBoundaryError, publish_site, sync_dist


class WebPublishTest(unittest.TestCase):
    def test_dry_run_does_not_modify_site_repo(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            repo = base / "market-news-site"
            dist.mkdir(); repo.mkdir()
            (dist / "index.html").write_text("safe", encoding="utf-8")
            subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
            result = sync_dist(dist, repo, dry_run=True)
            self.assertEqual(["index.html"], result.changed_paths)
            self.assertFalse((repo / "index.html").exists())

    def test_rejects_wrong_repository_directory_name(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"; dist.mkdir()
            repo = base / "wrong-name"; repo.mkdir()
            with self.assertRaises(PublishBoundaryError):
                sync_dist(dist, repo, dry_run=False)

    def test_push_requires_apply_and_commit(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"; dist.mkdir()
            repo = base / "market-news-site"; repo.mkdir()
            (dist / "index.html").write_text("safe", encoding="utf-8")
            subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
            with self.assertRaises(PublishBoundaryError):
                publish_site(dist, repo, push=True)

    def test_apply_commit_and_push_to_local_bare_remote(self):
        """Use only a temporary local bare remote; assert one non-force push and clean worktree."""
```

- [ ] **Step 2: Run publisher tests and verify RED**

Run:

```bash
python3 -m unittest tests/test_web_publish.py -v
```

Expected: import failure for missing `web.publish`.

- [ ] **Step 3: Implement safe dry-run-first synchronization**

Create `web/publish.py` with:

```python
@dataclass(frozen=True)
class PublishResult:
    site_repo: Path
    changed_paths: list
    applied: bool
    commit_sha: str = ""
    pushed: bool = False


class PublishBoundaryError(RuntimeError):
    pass


def validate_site_repo(site_repo: Path, expected_name: str = "market-news-site") -> None:
    """Require resolved basename, .git directory, expected origin name, and no symlinks."""


def sync_dist(dist_dir: Path, site_repo: Path, dry_run: bool = True) -> PublishResult:
    """Compare files; with --apply copy exact dist tree and delete only stale tracked site assets."""


def publish_site(
    dist_dir: Path,
    site_repo: Path,
    apply: bool = False,
    commit: bool = False,
    push: bool = False,
) -> PublishResult:
    """Run the validated sync, deterministic commit and ordinary push pipeline."""
```

Boundary requirements:

- `dist_dir` must resolve to a directory named `dist` and pass `assert_public_tree_safe()`.
- `site_repo` must resolve to a directory named exactly `market-news-site`, contain `.git`, and not equal project root, home, `/` or `dist_dir`.
- For an initialized remote, `origin` must end with `/market-news-site.git` or `:market-news-site.git`.
- Ignore `.git` and preserve no other out-of-band files; a nonempty unexpected file in the public repo causes failure unless it is already tracked.
- `dry_run=True` lists changes without writing.
- `--commit` requires `--apply`; `--push` requires both `--apply` and `--commit`.
- Before commit, rerun the public-tree scan and `git diff --cached --check`; refuse an empty or out-of-scope index.
- Use a deterministic message derived from the newest manifest entry, such as `publish: 2026-07-31 0800 news radar`.
- Push only the checked-out branch to its configured `origin` with ordinary `git push`; never use force, delete refs or print remote credentials.
- Unit tests exercise commit and push only against a temporary local bare Git remote; no test contacts GitHub.

- [ ] **Step 4: Run publisher and full tests**

Run:

```bash
python3 -m unittest tests/test_web_publish.py -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass; tests use only temporary local Git repositories.

- [ ] **Step 5: Exercise local dry-run against generated output**

After a real site repository exists, run only:

```bash
python3 -m web.publish --dist web/dist --site-repo /Users/aviva/Projects/market-news-site
```

Expected: prints the intended file list and `applied=false`; no public repository file changes.

Also run the full flow only against a temporary local bare remote through the unit test. Do not use `--push` against GitHub before Task 8 authorization.

- [ ] **Step 6: Review and commit if authorized**

If authorized:

```bash
git add web/publish.py tests/test_web_publish.py
git commit -m "feat: add safe static site publisher"
```

---

### Task 6: 固定早间构建入口

**Files:**
- Create: `scripts/run_morning_site.sh`
- Create: `tests/test_morning_site_entrypoint.py`
- Modify: `HANDOFF.md`

**Interfaces:**
- Produces: one fixed local command that builds, scans and optionally runs the complete site publication.
- Does not mutate automations or contain credentials; Git operations stay inside the tested Python publisher.

- [ ] **Step 1: Write failing entrypoint contract test**

Create `tests/test_morning_site_entrypoint.py`:

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MorningSiteEntrypointTest(unittest.TestCase):
    def test_entrypoint_builds_before_optional_publish(self):
        script = (ROOT / "scripts/run_morning_site.sh").read_text(encoding="utf-8")
        build_at = script.index("python3 -m web.build")
        publish_at = script.index("python3 -m web.publish")
        self.assertLess(build_at, publish_at)
        self.assertIn('SITE_PUBLISH_MODE:-dry-run', script)
        self.assertIn("--apply --commit --push", script)
        self.assertNotIn("git push", script)
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
python3 -m unittest tests/test_morning_site_entrypoint.py -v
```

Expected: file-not-found failure for missing script.

- [ ] **Step 3: Implement safe shell entrypoint**

Create executable `scripts/run_morning_site.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

project_dir="/Users/aviva/Projects/market_news"
site_repo="/Users/aviva/Projects/market-news-site"
publish_mode="${SITE_PUBLISH_MODE:-dry-run}"

cd "$project_dir"
python3 -m web.build --project-root "$project_dir" --output web/dist

if [[ "$publish_mode" == "apply" ]]; then
  python3 -m web.publish --dist web/dist --site-repo "$site_repo" --apply --commit --push
else
  python3 -m web.publish --dist web/dist --site-repo "$site_repo"
fi
```

The script intentionally does not contain raw `git commit`, `git push`, credentials or automation logic. Complete publishing is implemented once in the tested Python publisher and remains unusable against GitHub until the Task 8 repository and authorization gates are complete.

- [ ] **Step 4: Document operations and failure separation**

Add to `HANDOFF.md`:

- manual build command;
- dry-run sync command;
- meaning of `SITE_PUBLISH_MODE=apply`, including that it performs validated sync, commit and ordinary push;
- statement that Markdown success is preserved when HTML or publish fails;
- statement that noon and post-close automations remain paused.

- [ ] **Step 5: Run focused and full tests**

Run:

```bash
python3 -m unittest tests/test_morning_site_entrypoint.py -v
bash -n scripts/run_morning_site.sh
python3 -m unittest discover -s tests -v
```

Expected: all tests pass and shell syntax check exits 0.

- [ ] **Step 6: Review and commit if authorized**

If authorized:

```bash
git add scripts/run_morning_site.sh tests/test_morning_site_entrypoint.py HANDOFF.md
git commit -m "feat: add morning site build entrypoint"
```

---

### Task 7: 独立金融与安全审阅、完整本地验收

**Files:**
- Review: all `web/`, `scripts/run_morning_site.sh`, `tests/test_web_*.py`, generated `web/dist/`
- Modify only if review findings have failing reproductions.

**Interfaces:**
- Produces: reviewed, locally complete website artifact before any external publication.

- [ ] **Step 1: Run fresh complete verification**

Run after the last local artifact change:

```bash
python3 -m unittest discover -s tests -v
python3 -m web.build --project-root /Users/aviva/Projects/market_news --output web/dist
python3 -m web.security web/dist
git diff --check
```

Record exact passed/failed/error/skipped counts and timestamps.

- [ ] **Step 2: Perform browser acceptance**

Repeat the six browser checks from Task 3 on the final build. Capture desktop and mobile screenshots in a temporary QA directory outside `web/dist/`; do not publish screenshots unless the user asks.

- [ ] **Step 3: Dispatch independent read-only review**

Because the page publishes financial content and public-source links, dispatch an internal read-only reviewer. Review requirements:

- compare 4 generated pages against their Markdown sources;
- verify scores, order, dates, market-feedback labels and Unitree subscription date;
- verify the public tree excludes private evidence and local paths;
- verify no headline gains heat methodology or trading advice;
- return blocking and nonblocking findings without editing files.

- [ ] **Step 4: Reproduce and fix blocking findings with RED → GREEN**

For each blocking finding, add a focused failing `unittest`, observe expected failure, implement the minimum fix, rerun focused and full suites, then request reviewer confirmation.

- [ ] **Step 5: Inspect exact release scope**

Run:

```bash
git status --short
git diff -- web scripts/run_morning_site.sh tests HANDOFF.md
find web/dist -maxdepth 3 -type f -print
```

Explicitly exclude `.DS_Store`, `.planning/`, `.superpowers/`, evidence, findings, progress and unrelated user changes.

---

### Task 8: GitHub公开仓库、Pages和08:00自动任务授权阶段

**Files/External State:**
- Create externally after authorization: GitHub public repository `market-news-site`.
- Create locally after authorization: `/Users/aviva/Projects/market-news-site`.
- Update after authorization: automation `a-08-00` only.
- Keep unchanged: `a-12-00`, `a-15-00` statuses remain `PAUSED`.

**Interfaces:**
- Consumes: verified `web/dist/` and `web.publish`.
- Produces: public GitHub Pages URL and an enabled morning build/publish workflow that calls only the fixed entrypoint.

- [ ] **Step 1: Stop for explicit external authorization and GitHub login**

Report that `gh auth status` currently shows invalid credentials for account `xrqaviva`. Ask the user to authorize:

1. interactive `gh auth login -h github.com`;
2. creation of public repository `market-news-site`;
3. first push and Pages enablement;
4. update of automation `a-08-00` to call the fixed site workflow.

Do not continue until authorization is explicit and login succeeds.

- [ ] **Step 2: Verify GitHub identity without printing credentials**

Run:

```bash
gh auth status
gh api user --jq .login
```

Expected: authenticated login name only; no token output.

- [ ] **Step 3: Create or clone the exact public repository**

Set a task-specific shell variable, never a system option:

```bash
github_owner="$(gh api user --jq .login)"
gh repo view "$github_owner/market-news-site" --json nameWithOwner,visibility,url
```

If it does not exist and creation was authorized:

```bash
gh repo create "$github_owner/market-news-site" --public --description "A股新闻雷达静态报告"
gh repo clone "$github_owner/market-news-site" /Users/aviva/Projects/market-news-site
```

Ensure the clone is located exactly at `/Users/aviva/Projects/market-news-site`, its `origin` points to the exact repository, and its checked-out publication branch is `main` before invoking the publisher.

- [ ] **Step 4: Dry-run generated site synchronization**

Run:

```bash
python3 -m web.publish --dist web/dist --site-repo /Users/aviva/Projects/market-news-site
```

Inspect the proposed public-repo file list and confirm the dry-run made no changes.

- [ ] **Step 5: Run the fixed publisher and enable Pages only under explicit authorization**

Run the same fixed publication path used by the future morning automation:

```bash
python3 -m web.publish --dist web/dist --site-repo /Users/aviva/Projects/market-news-site --apply --commit --push
gh api --method POST "repos/$github_owner/market-news-site/pages" -f source[branch]=main -f source[path]=/
```

Inspect the resulting commit and clean worktree. If Pages already exists, read its configuration and update only when necessary. Never force-push.

- [ ] **Step 6: Verify public deployment**

Read the Pages URL using:

```bash
gh api "repos/$github_owner/market-news-site/pages" --jq .html_url
```

Open the returned URL and verify latest report, one historical report, CSS/JS, report switching and public links. Confirm local public-repo `HEAD` equals `origin/main`.

- [ ] **Step 7: Update only the 08:00 automation**

Use the app automation API to update `a-08-00`, preserving name, schedule, model, reasoning effort, notification policy and project. Append to its prompt:

```text
Markdown报告及原有验收全部成功后，运行固定入口：
SITE_PUBLISH_MODE=apply bash scripts/run_morning_site.sh
固定入口已包含公开仓库复核、提交和普通推送；不要另行拼装Git命令。网页发布失败不得删除或覆盖已成功生成的Markdown，且必须明确记录为部署失败。
```

Before and after the update, view `a-08-00`, `a-12-00`, `a-15-00`; require statuses `ACTIVE`, `PAUSED`, `PAUSED` respectively.

- [ ] **Step 8: Final end-to-end verification and handoff**

Run one authorized manual dry-run that generates the same report again, confirms stable HTML URL and produces no duplicate manifest entry. Verify the public URL remains accessible. Report:

- source and public repository paths;
- GitHub Pages URL;
- exact test counts;
- automation statuses;
- commits and pushes performed;
- any N/A or unresolved environment limitations.

Do not enable the noon or post-close automations.
