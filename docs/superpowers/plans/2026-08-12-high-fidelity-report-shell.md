# High-Fidelity Report Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the generated report shell so the production page faithfully matches the approved `layout-final-v3.html` geometry and typography while retaining every Markdown-derived field and existing interaction.

**Architecture:** Keep Markdown parsing, report models, theme aggregation, news rendering, archive data, and URL safety unchanged. Refactor the fixed report template and the small report-header rendering boundary so the sidebar and report workspace share one centered card, then replace the production layout CSS with values taken directly from the approved reference. Extend the existing Python artifact tests and rendered-browser gate to verify semantics, content completeness, computed geometry, responsive behavior, print behavior, and deterministic output.

**Tech Stack:** Python 3 `unittest`, fixed HTML template rendering, CSS, vanilla JavaScript, generated static HTML, headless Chrome behavior checks.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-12-high-fidelity-report-shell-design.md`.
- Visual reference: `.superpowers/brainstorm/54924-1786505081/content/layout-final-v3.html`.
- Desktop shell uses `#edf1f6`, `max-width: 980px`, `padding: 27px`, `76px` sidebar, `28px` content horizontal padding, `16px` card radius, and the reference border/shadow.
- Mobile at `700px` and below uses `12px` outer padding, no desktop sidebar, `18px` content padding, and no page-level horizontal overflow.
- Use `-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif`; do not use Inter or monospace for report body copy.
- Preserve every Markdown-derived core direction, full news item, other important news item, pending clue, explanatory field, source link, time, market session, market feedback, boundary, and heat change.
- Preserve archive tree behavior, stable IDs, source URL filtering, disclosure semantics, print completeness, and legacy report compatibility.
- Build only from the seven tracked report Markdown files in the isolated worktree.
- Preserve unrelated untracked `.superpowers/` and `task-5-report.md`; never stage them.
- No automation mutation, merge, push, PR, deployment, or publication.

## Discovery and Baseline

- Repository root: `/Users/aviva/Projects/market_news/.worktrees/news-radar-web`.
- Branch: `codex/news-radar-web`, linked worktree under `.worktrees/news-radar-web`.
- Design commit: `901c6fa docs: specify high-fidelity report shell`.
- Existing production boundaries: `web/templates/report.html`, `web/build.py::render_report`, `web/assets/app.css`, `web/assets/app.js`.
- Existing test boundaries: `tests/test_web_build.py`, `tests/report_layout_browser.mjs`, byte-identical build test, public-tree security tests.
- Baseline at `2026-08-12 20:44:06 CST`: `python3 -m unittest discover -s tests -v` ran 85 tests, 85 passed, 0 failed, 0 errors, 0 skipped.
- Browser gate requires permission to start headless Chrome; a sandbox launch failure is an environment failure, not a product pass.

## Test Matrix

- Unit/artifact structure: `python3 -m unittest tests.test_web_build.WebBuildTest.test_report_shell_matches_reference_structure -v`; RED because the current topbar sits outside the terminal layout and the sidebar is not inside a centered report card; GREEN when the fixed shell and header fields are present.
- Content completeness: `python3 -m unittest tests.test_web_build.WebBuildTest.test_checked_in_aug11_artifact_keeps_themed_news_contract -v`; extend its current 24-event/5-pending assertions with other-important and explanatory markers; GREEN must retain all existing counts and links.
- Integration/build: `python3 -m unittest tests.test_web_build.WebBuildTest.test_checked_in_dist_is_byte_identical_to_a_fresh_build -v`; RED after source changes and before rebuild, GREEN after the tracked seven-report build.
- UI geometry: `node tests/report_layout_browser.mjs`; RED on current 120px sidebar, missing 980px/27px shell, Inter body font, mismatched content padding, title sizes, and story grid; GREEN on exact computed metrics and zero console problems.
- UI interaction: the same browser gate clicks a theme anchor, toggles a news disclosure, opens/closes archive dates, and verifies pending print lifecycle.
- Responsive: browser gate at `390 × 844`; verify 12px outer padding, hidden sidebar, 18px workspace padding, horizontally scrollable direction navigation, and `scrollWidth === clientWidth` for the document.
- Security/privacy: full `tests/test_web_security.py` plus `assert_public_tree_safe`; generated public files must contain no `/Users/`, tokens, private paths, unsafe URL schemes, or symlinks.
- Syntax/quality: `node --check web/assets/app.js`, `node --check web/dist/assets/app.js`, `node --check tests/report_layout_browser.mjs`, `git diff --check`.
- Artifact parity: `cmp web/assets/app.css web/dist/assets/app.css` and `cmp web/assets/app.js web/dist/assets/app.js`.
- Release: inspect exact staged patch; include only plan-approved tracked files and generated artifacts; exclude `.superpowers/` and `task-5-report.md`.

---

### Task 1: Rebuild the Fixed Report Shell and Header Boundary

**Files:**
- Modify: `tests/test_web_build.py`
- Modify: `web/templates/report.html`
- Modify: `web/build.py`

**Interfaces:**
- Consumes: `ReportDocument.meta`, `_report_archive(document, report_index)`, `_filter_bar(document)`, and existing renderer replacements.
- Produces: `.page-shell > .report-card > aside.report-sidebar + .report-workspace`; `TOPBAR` contains `.report-heading` and `.report-cutoff`; themed reports omit the redundant metadata filter bar while legacy reports retain category filters.

- [ ] **Step 1: Add the failing fixed-shell test**

Add to `WebBuildTest`:

```python
def test_report_shell_matches_reference_structure(self):
    page = render_report(self._themed_document(), [{
        "id": "themed-report", "date": "2026-08-11", "label": "盘前",
        "url": "reports/2026-08-11-0800.html",
    }])
    self.assertIn('<div class="page-shell">', page)
    self.assertIn('<section class="report-card">', page)
    self.assertRegex(
        page,
        r'<aside class="report-sidebar"[^>]*>.*?class="brand".*?'
        r'</aside>\s*<div class="report-workspace">',
    )
    self.assertIn('<p class="report-eyebrow">2026-08-11 · 盘前</p>', page)
    self.assertIn('<h1>题材测试</h1>', page)
    self.assertIn('<p class="report-cutoff">截至 cutoff</p>', page)
    self.assertNotIn('class="filter-bar"', page)
```

- [ ] **Step 2: Run the focused test and observe RED**

Run: `python3 -m unittest tests.test_web_build.WebBuildTest.test_report_shell_matches_reference_structure -v`

Expected: FAIL because `.page-shell`, `.report-card`, `.report-workspace`, and the reference header markup do not exist.

- [ ] **Step 3: Refactor the template into the approved shell**

Use this hierarchy in `web/templates/report.html`:

```html
<body data-report-id="{{REPORT_ID}}">
  <div class="page-shell">
    <section class="report-card">
      <aside class="report-sidebar" data-component="report-archive">
        <div class="brand" aria-label="A股新闻雷达">RADAR</div>
        {{REPORT_ARCHIVE}}
      </aside>
      <div class="report-workspace">
        <header class="topbar">{{TOPBAR}}</header>
        <label class="mobile-report-control">
          <span>切换报告</span>
          <select class="mobile-report-select" aria-label="切换报告"></select>
        </label>
        <main class="report-main">
          {{FILTER_BAR}}{{THEME_CONTENT}}{{NEWS_ITEMS}}{{PENDING_ITEMS}}
        </main>
      </div>
    </section>
  </div>
  <template id="news-toggle-template">
    <button class="news-toggle" type="button" aria-expanded="false" aria-controls="">展开详情</button>
  </template>
  <script src="../assets/app.js" defer></script>
</body>
```

Do not include the visual reference's explanatory `.note` or `.legend` blocks.

- [ ] **Step 4: Render structured header fields and remove themed metadata duplication**

In `render_report`, replace the free-form title/meta block with:

```python
topbar = (
    '<div class="report-heading"><p class="report-eyebrow">{}</p>'
    '<h1>{}</h1></div><p class="report-cutoff">截至 {}</p>'
).format(_escape(topbar_meta), _escape(document.meta.title), _escape(document.meta.cutoff))
```

Return an empty string from `_filter_bar(document)` when `document.themes` is non-empty. Leave the legacy category filter markup unchanged.

- [ ] **Step 5: Run focused and compatibility tests**

Run:

```bash
python3 -m unittest \
  tests.test_web_build.WebBuildTest.test_report_shell_matches_reference_structure \
  tests.test_web_build.WebBuildTest.test_themed_page_omits_legacy_category_filters \
  tests.test_web_build.WebBuildTest.test_legacy_document_keeps_flat_news_list_without_theme_containers \
  tests.test_web_build.WebBuildTest.test_page_has_accessible_interaction_contract -v
```

Expected: 4 passed. Update the existing themed-filter assertion to require no redundant filter bar while leaving legacy controls covered.

- [ ] **Step 6: Review and commit Task 1**

Inspect `git diff -- web/templates/report.html web/build.py tests/test_web_build.py`, run `git diff --check`, stage only those three paths, inspect the staged patch, then commit:

```bash
git commit -m "refactor: rebuild report card shell"
```

### Task 2: Apply Reference Geometry and Typography with Computed-Style RED → GREEN

**Files:**
- Modify: `tests/report_layout_browser.mjs`
- Modify: `web/assets/app.css`

**Interfaces:**
- Consumes: Task 1 classes `.page-shell`, `.report-card`, `.report-sidebar`, `.report-workspace`, `.topbar`, `.report-heading`, `.report-eyebrow`, `.report-cutoff`, `.report-main`.
- Produces: desktop and mobile computed geometry matching the approved reference while preserving all existing class hooks used by JavaScript.

- [ ] **Step 1: Replace the obsolete terminal-layout assertions with reference metrics**

Extend the desktop evaluation to return computed rectangles/styles for the shell, card, sidebar, workspace, topbar, report main, theme header, theme heading, news row, news rank, and news title. Assert:

```js
if (desktop.shell.maxWidth !== "980px" || desktop.shell.paddingTop !== "27px") failures.push("desktop shell geometry mismatch");
if (Math.abs(desktop.card.width - 926) > 1) failures.push("desktop card width mismatch");
if (Math.abs(desktop.sidebar.width - 76) > 1) failures.push("desktop sidebar width mismatch");
if (desktop.workspacePaddingLeft !== "28px") failures.push("desktop workspace padding mismatch");
if (desktop.card.borderRadius !== "16px") failures.push("desktop card radius mismatch");
if (!desktop.bodyFont.includes("PingFang SC")) failures.push("body font stack mismatch");
if (desktop.reportTitleFontSize !== "21px") failures.push("report title size mismatch");
if (desktop.themeTitleFontSize !== "25px") failures.push("theme title size mismatch");
if (desktop.newsTitleFontSize !== "12px") failures.push("news title size mismatch");
if (Math.abs(desktop.newsContentLeft - desktop.firstDetailLeft) > 1) failures.push("news detail alignment mismatch");
```

At mobile width assert outer padding `12px`, workspace/content horizontal padding `18px`, hidden sidebar, `21px` theme title, and no page overflow. Preserve print visibility, contrast, theme-anchor, and browser-console checks.

- [ ] **Step 2: Run the browser gate and observe RED**

Run: `node tests/report_layout_browser.mjs`

Expected: FAIL with the old `120px` sidebar, absent `980px` shell and `27px` margin, `Inter` body font, `20px` main padding, and mismatched title/news sizes. If Chrome cannot start inside the sandbox, rerun with the already-scoped permission for this exact test command and record the environment boundary separately.

- [ ] **Step 3: Rebuild the CSS from the reference tokens**

Implement these core rules in `web/assets/app.css`:

```css
:root {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
}
.page-shell { max-width: 980px; margin: 0 auto; padding: 27px; }
.report-card {
  display: flex; overflow: hidden; min-height: calc(100vh - 54px);
  background: #f8f9fb; border: 2px solid #cad3e1; border-radius: 16px;
  box-shadow: 0 16px 40px rgba(30,40,60,.10);
}
.report-sidebar { flex: 0 0 76px; width: 76px; padding: 17px 9px; background: #1c2940; }
.report-workspace { min-width: 0; flex: 1; }
.topbar {
  position: static; display: flex; align-items: flex-end; justify-content: space-between;
  min-height: 0; margin: 0 28px; padding: 23px 0 15px;
  color: #182033; background: transparent; border-bottom: 1px solid #dce2ea;
}
.report-main { min-width: 0; padding: 0 28px 40px; }
```

Apply every remaining value from the approved design for `.report-eyebrow`, title, cutoff, theme navigation, theme sections, title/meta baselines, news two-column grid, details, sources, other important news, and pending appendix. Remove conflicting terminal-era values rather than stacking overrides.

- [ ] **Step 4: Implement the exact mobile rules**

At `max-width: 700px`, set `.page-shell { padding: 12px; }`, hide `.report-sidebar`, set `.topbar` and `.report-main` horizontal spacing to `18px`, retain the report-card border/radius, show the mobile report selector, make theme navigation scroll horizontally, and assert document width remains bounded.

- [ ] **Step 5: Run the browser gate to GREEN**

Run: `node tests/report_layout_browser.mjs`

Expected: PASS with the exact computed desktop/mobile metrics, theme navigation and disclosures operational, print pending items complete, and zero browser console warnings/errors.

- [ ] **Step 6: Run CSS/JS compatibility tests and commit Task 2**

Run:

```bash
python3 -m unittest tests.test_web_build.WebBuildTest.test_app_script_keeps_source_only_associations_and_mutes_score_metadata -v
node --check web/assets/app.js
node --check tests/report_layout_browser.mjs
git diff --check
```

Inspect and stage only `web/assets/app.css` and `tests/report_layout_browser.mjs`, inspect the staged patch, then commit:

```bash
git commit -m "style: match approved report reference"
```

### Task 3: Rebuild All Reports and Prove Content, Visual, and Public-Artifact Completeness

**Files:**
- Modify: `tests/test_web_build.py`
- Modify: `docs/uat/2026-08-12-high-fidelity-report-shell.md`
- Regenerate: `web/dist/reports/*.html`
- Regenerate: `web/dist/assets/app.css`
- Regenerate when changed: `web/dist/assets/app.js`, `web/dist/reports.json`, `web/dist/index.html`

**Interfaces:**
- Consumes: the Task 1 fixed shell, Task 2 production CSS, and the seven tracked Markdown reports inside the isolated worktree.
- Produces: deterministic checked-in `web/dist`, completeness regression coverage, and persistent UAT evidence. It does not publish the tree.

- [ ] **Step 1: Strengthen checked-artifact completeness before rebuilding**

In `test_checked_in_aug11_artifact_keeps_themed_news_contract`, preserve all current assertions and add checks that the generated page contains:

```python
self.assertIn('data-component="other-important-news"', page)
self.assertGreaterEqual(page.count('data-component="news-detail"'), 25)
for marker in ("发布时段", "关键信号/预期差", "市场反馈", "判断边界", "热度变化"):
    self.assertIn(marker, page)
```

- [ ] **Step 2: Run the checked-artifact and deterministic tests to observe stale-output RED**

Run:

```bash
python3 -m unittest \
  tests.test_web_build.WebBuildTest.test_checked_in_aug11_artifact_keeps_themed_news_contract \
  tests.test_web_build.WebBuildTest.test_checked_in_dist_is_byte_identical_to_a_fresh_build -v
```

Expected: at least the deterministic build test fails because checked-in HTML/CSS still contains the old shell.

- [ ] **Step 3: Rebuild exactly the seven tracked reports**

Run:

```bash
python3 -m web.build \
  --project-root /Users/aviva/Projects/market_news/.worktrees/news-radar-web \
  --output /Users/aviva/Projects/market_news/.worktrees/news-radar-web/web/dist
```

Expected: 7 report pages generated from the isolated worktree without importing main-checkout untracked candidates.

- [ ] **Step 4: Run artifact, security, syntax, and deterministic checks**

Run:

```bash
python3 -m unittest tests.test_web_build tests.test_web_security -v
node --check web/assets/app.js
node --check web/dist/assets/app.js
node --check tests/report_layout_browser.mjs
cmp web/assets/app.css web/dist/assets/app.css
cmp web/assets/app.js web/dist/assets/app.js
git diff --check
```

Build a second time to a temporary `dist` directory and require `diff -qr` to return no output against checked-in `web/dist`.

- [ ] **Step 5: Perform desktop/mobile visual UAT**

At a fixed desktop viewport, compare the approved reference and generated report for outer gray background, 27px margin, 980px centered shell, card border/radius/shadow, 76px sidebar, 28px content alignment, typography, theme spacing, story grid, and source/detail alignment. At `390 × 844`, verify 12px margin, 18px content padding, hidden sidebar, scrollable theme navigation, readable complete details, and no page overflow. Exercise theme anchors, a news disclosure, archive date/slot selection, and pending disclosure. Record computed measurements, visible observations, and console status in `docs/uat/2026-08-12-high-fidelity-report-shell.md`.

- [ ] **Step 6: Run the final full suite after the last generated change**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass with exact passed/failed/error/skipped counts recorded after the last production/generated change.

- [ ] **Step 7: Independent review and finding disposition**

Provide a read-only reviewer with the approved design, this plan, UAT record, and complete feature diff. Require requirement-to-diff mapping, content-loss review, legacy compatibility, geometry test reliability, security/privacy, generated-artifact synchronization, and exact staged-scope findings. Reproduce every blocking finding with a failing test before fixing it, then rerun affected and full gates.

- [ ] **Step 8: Review staged scope and commit Task 3**

Inspect exact tracked changes and staged patch. Include only the approved tests, UAT, source template/build/CSS, and deterministic `web/dist` artifacts. Exclude `.superpowers/`, `task-5-report.md`, temporary screenshots, browser profiles, and local server state. Commit:

```bash
git commit -m "test: verify high-fidelity report build"
```

Do not push, merge, deploy, publish, or enable automations.
