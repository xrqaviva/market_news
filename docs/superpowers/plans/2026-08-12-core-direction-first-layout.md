# Core-Direction-First Report Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the themed report's long single-news index with a compact direction navigation and render every ranked core direction sequentially with complete news details, followed by other important news and a collapsed pending appendix.

**Architecture:** Keep Markdown parsing, `ReportDocument`, theme scoring, and theme sorting unchanged. Change only the static renderer's themed composition, semantic markup, progressive enhancement, and responsive CSS; legacy flat reports keep their current category filter and list. Rebuild all static artifacts from the fixed template and verify the checked-in output against desktop and mobile browser UAT.

**Tech Stack:** Python 3 standard library renderer and `unittest`, HTML5, dependency-free JavaScript, CSS3, static `web/dist` output.

## Global Constraints

- Markdown remains the only report-content source of truth; do not hand-edit generated HTML.
- Do not modify collection, scoring, theme aggregation, theme sorting, fact verification, or report classification.
- Themed pages contain one compact direction navigation, then complete core directions 01 through N in ranked order, then “其他重要新闻”, then “待核验线索”.
- Remove the long single-news index, “接下来的方向”, theme-intensity displays, prominent statistic cards, and large score treatments.
- Theme score and news count render only as small muted metadata in the exact order `N条 · SCORE`.
- Every themed news instance retains its complete core text, sources, Beijing times, release session, market feedback, boundary, heat change, associations, and mappings when present.
- Source-only news remains inline and must not receive an empty detail toggle.
- Pending clues do not participate in score or ranking and are collapsed by default.
- Keep the existing narrow desktop archive and mobile report selector behavior unchanged.
- Preserve HTTP(S)-only source filtering, relative static asset paths, unique DOM IDs, and deterministic output.
- At 390 × 844 there must be no page-level horizontal overflow.
- Do not merge, push, deploy, publish, or re-enable automations as part of this plan.

## File Map

| File | Responsibility in this change |
|---|---|
| `web/build.py` | Render direction navigation, numbered theme headings, sequential complete theme blocks, other news, and collapsed pending markup. |
| `web/assets/app.js` | Keep news enhancement intact while reducing score markup to muted metadata; retain archive and legacy filter behavior. |
| `web/assets/app.css` | Implement the approved shallow research-terminal hierarchy and responsive behavior without changing the archive width. |
| `tests/test_web_build.py` | Lock themed structure, ordering, content completeness, collapsed pending semantics, legacy compatibility, and generated Aug. 11 output. |
| `web/dist/**` | Deterministically generated site artifacts; never edited directly. |
| `docs/uat/2026-08-12-core-direction-first-layout.md` | Persist commands, browser checks, dimensions, results, and residual boundaries. |

## Verified Baseline

- Worktree: `/Users/aviva/Projects/market_news/.worktrees/news-radar-web`
- Branch: `codex/news-radar-web`
- Approved design: `docs/superpowers/specs/2026-08-12-core-direction-first-layout-design.md`, commit `00d6a4d`.
- `python3 -m unittest discover -s tests -v`: 85 tests passed on 2026-08-12 before implementation.
- `node --check web/assets/app.js`: exited 0 before implementation.
- Existing unrelated untracked paths `.superpowers/` and `task-5-report.md` are excluded from every task and commit.

---

### Task 1: Render the direction-first themed document

**Files:**
- Modify: `tests/test_web_build.py`
- Modify: `web/build.py:131-227`

**Interfaces:**
- Consumes: `ReportDocument.themes: tuple[ThemeGroup, ...]` already sorted by `web.report_parser._parse_themed_report`, plus `ThemeGroup.theme_id`, `name`, `total_score`, `catalyst`, mappings, risk boundary, and complete items.
- Produces: `_theme_navigation(document: ReportDocument) -> str`, `_theme_group(document, theme, theme_names: dict[str, str], ordinal: int) -> str`, and `_theme_content(document: ReportDocument) -> str` with `data-component="theme-navigation"` followed by ordered `data-component="theme-group"` sections.

- [ ] **Step 1: Replace the old index expectations with a failing direction-first rendering test**

Rename `test_themed_document_renders_index_groups_and_complete_other_news` to `test_themed_document_renders_navigation_sequential_groups_and_complete_news`. Keep its full-content and cross-theme assertions, and replace the index-specific assertions with:

```python
self.assertNotIn('data-component="news-index"', page)
self.assertNotIn("单条新闻热榜索引", page)
self.assertNotIn("接下来的方向", page)
self.assertIn(
    '<nav class="theme-navigation" data-component="theme-navigation" '
    'aria-label="核心方向">',
    page,
)
self.assertIn('href="#theme-ascii-theme-alpha">甲题材</a>', page)
self.assertIn('href="#theme-ascii-theme-beta">乙题材</a>', page)
self.assertLess(page.index("核心方向 01"), page.index("核心方向 02"))
self.assertLess(page.index("核心方向 02"), page.index("其他重要新闻"))
self.assertIn('<p class="theme-total">2条 · 170</p>', page)
self.assertIn('<p class="theme-total">2条 · 160</p>', page)
```

Also retain assertions for `甲的共同催化`, both mapping lists, `甲风险`, the complete shared-news fields and links, and `其他新闻`. These prevent a visually correct but information-incomplete implementation.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest tests.test_web_build.WebBuildTest.test_themed_document_renders_navigation_sequential_groups_and_complete_news -v
```

Expected: FAIL because the current renderer emits `data-component="news-index"`, has no direction navigation or ordinal labels, and renders the theme total as `170分 · 关联新闻2条`.

- [ ] **Step 3: Implement the compact navigation and numbered theme headings**

Delete the unused `_news_index` renderer from `web/build.py`; keep `ReportDocument.news_index` because parsing and validation still use it. Add:

```python
def _theme_navigation(document: ReportDocument) -> str:
    links = "".join(
        '<a href="#theme-{}">{}</a>'.format(
            _escape(_safe_dom_id(theme.theme_id)),
            _escape(theme.name),
        )
        for theme in document.themes
    )
    return (
        '<nav class="theme-navigation" data-component="theme-navigation" '
        'aria-label="核心方向">{}</nav>'
    ).format(links)
```

Change `_theme_group` to accept `ordinal: int` and emit this header before the existing catalyst, mappings, risk, and complete news list:

```python
'<header class="theme-header">'
'<p class="theme-kicker">核心方向 {:02d}</p>'
'<div class="theme-heading-line"><h2>{}</h2>'
'<p class="theme-total">{}条 · {}</p></div>'
'</header>'
```

Pass `ordinal` first, followed by escaped theme name, `len(theme.items)`, and `theme.total_score`. Preserve the existing stable `id="theme-..."`, catalyst, both mapping lists, risk boundary, and news rows.

Compose themed content exactly once and in this order:

```python
return "{}{}{}".format(
    _theme_navigation(document),
    "".join(
        _theme_group(document, theme, theme_names, ordinal)
        for ordinal, theme in enumerate(document.themes, start=1)
    ),
    _other_important_news(document, theme_names),
)
```

Do not render `_news_index`, a second theme list, or the old cross-theme disclosure above the first direction. Association badges inside complete news rows remain the explicit cross-theme link.

- [ ] **Step 4: Run focused renderer and compatibility tests to GREEN**

Run:

```bash
python3 -m unittest \
  tests.test_web_build.WebBuildTest.test_themed_document_renders_navigation_sequential_groups_and_complete_news \
  tests.test_web_build.WebBuildTest.test_themed_cross_theme_instances_are_unique_and_source_only_has_no_toggle \
  tests.test_web_build.WebBuildTest.test_themed_page_omits_legacy_category_filters \
  tests.test_web_build.WebBuildTest.test_legacy_document_keeps_flat_news_list_without_theme_containers -v
```

Expected: all four pass. The legacy page still has category controls and no theme navigation; repeated themed events still have unique instance/detail IDs.

- [ ] **Step 5: Commit the renderer slice**

```bash
git add web/build.py tests/test_web_build.py
git diff --cached --check
git commit -m "feat: render reports by core direction"
```

### Task 2: Make pending clues a compact collapsed appendix

**Files:**
- Modify: `tests/test_web_build.py:233-255,387-455`
- Modify: `web/build.py:230-258`

**Interfaces:**
- Consumes: `ReportDocument.pending_items` and existing `renderable_source_url()` filtering.
- Produces: a `section.pending-section[data-component="pending-list"]` containing native `<details>` with a `<summary>` count and a `.pending-body`; native details semantics provide default collapse and keyboard operation without storage or custom JavaScript.

- [ ] **Step 1: Write failing semantic and safety tests**

Extend the pending renderer tests with exact assertions:

```python
self.assertIn('<details class="pending-details">', page)
self.assertIn('<summary>待核验线索 <span>· 1</span></summary>', page)
self.assertNotIn('<details class="pending-details" open>', page)
self.assertIn('<div class="pending-body">', page)
self.assertNotIn("热点权重", pending_html)
self.assertNotIn("/100", pending_html)
self.assertNotIn("分 ·", pending_html)
```

Retain the existing unsafe-URL assertions and Aug. 11 five-item/title assertions. Update the Aug. 11 section extraction to capture through `</details></section>` so the complete appendix is tested.

- [ ] **Step 2: Run pending tests and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_web_build.WebBuildTest.test_pending_renderer_filters_unsafe_source_urls \
  tests.test_web_build.WebBuildTest.test_aug11_page_renders_pending_verification_appendix -v
```

Expected: FAIL because current pending content is always visible and has no native disclosure control or count.

- [ ] **Step 3: Render native collapsed details while preserving all clues**

Keep the existing escaped item and allowlisted source rendering. Replace only the outer pending markup with:

```python
return (
    '<section class="pending-section" data-component="pending-list">'
    '<details class="pending-details">'
    '<summary>待核验线索 <span>· {}</span></summary>'
    '<div class="pending-body">'
    '<p>以下线索不参与主榜计分；补齐具体原文和北京时间后再转入主榜。</p>'
    '{}'
    '</div></details></section>'
).format(_escape(len(document.pending_items)), "".join(rows))
```

Do not add `open`, a score, rank, custom click handler, browser storage, or a second heading.

- [ ] **Step 4: Run pending, security, and renderer tests to GREEN**

Run:

```bash
python3 -m unittest \
  tests.test_web_build.WebBuildTest.test_pending_renderer_filters_unsafe_source_urls \
  tests.test_web_build.WebBuildTest.test_aug11_page_renders_pending_verification_appendix \
  tests.test_web_security -v
```

Expected: all tests pass; only HTTP(S) pending links render, and all pending facts/reasons remain present in HTML despite default visual collapse.

- [ ] **Step 5: Commit the pending appendix slice**

```bash
git add web/build.py tests/test_web_build.py
git diff --cached --check
git commit -m "feat: collapse pending verification appendix"
```

### Task 3: Apply the approved visual hierarchy and muted scores

**Files:**
- Modify: `web/assets/app.js:15-64`
- Modify: `web/assets/app.css:180-739`
- Modify: `tests/test_web_build.py`

**Interfaces:**
- Consumes: `.theme-navigation`, `.theme-group`, `.theme-kicker`, `.theme-heading-line`, `.theme-total`, existing `.news-row`, and native `.pending-details` markup from Tasks 1–2.
- Produces: one-line scrollable direction navigation; sequential border-light theme sections; compact news rows with muted scores; responsive pending appendix; unchanged archive, mobile report selector, source-only behavior, detail toggles, and legacy filters.

- [ ] **Step 1: Add a failing runtime DOM behavior test for compact score enhancement**

Extend the existing Node DOM harness used by `test_source_only_row_keeps_associations_when_app_script_enhances_dom`. After `web/assets/app.js` executes against a row whose raw score is `热点权重：60/100`, inspect the real enhanced output rather than the JavaScript source:

```javascript
const scoreCell = row.children[2];
if (scoreCell.innerHTML !== '<span>热度 60</span>') {
  throw new Error(`unexpected score markup: ${scoreCell.innerHTML}`);
}
if (scoreCell.innerHTML.includes('<strong>')) {
  throw new Error('score remains visually prominent');
}
```

Rename the test to `test_app_script_keeps_source_only_associations_and_mutes_score_metadata`. The structural requirements for navigation, theme sequence, removed index, and collapsed pending appendix remain covered by Tasks 1, 2, and 4; CSS dimensions, horizontal scrolling, and visual hierarchy are verified on the built page in Task 4 browser UAT.

- [ ] **Step 2: Run the asset contract and verify RED**

Run:

```bash
python3 -m unittest tests.test_web_build.WebBuildTest.test_app_script_keeps_source_only_associations_and_mutes_score_metadata -v
```

Expected: FAIL because the current runtime enhancement produces `<strong>60</strong><span>热点权重</span>` instead of the compact metadata span.

- [ ] **Step 3: Reduce news score markup without changing row enhancement**

In `enhanceRow`, keep rank parsing, title cleanup, associations, source-only handling, detail construction, and toggle semantics unchanged. Replace only the score markup:

```javascript
const score = scoreLine.textContent.match(/(\d+)\/100/);
scoreCell.innerHTML = `<span>热度 ${score ? score[1] : "—"}</span>`;
```

The score cell remains present for data visibility but no longer creates a large number plus label stack.

- [ ] **Step 4: Replace obsolete index styles with the approved direction hierarchy**

Remove every `.news-index*` rule and replace the themed outer-shell rules with the following exact visual behaviors:

```css
.theme-navigation {
  display: flex;
  gap: 22px;
  overflow-x: auto;
  margin: 0 0 22px;
  padding: 11px 2px 13px;
  border-bottom: 1px solid var(--line);
  scrollbar-width: thin;
  white-space: nowrap;
}

.theme-navigation a {
  flex: 0 0 auto;
  color: var(--muted);
  font-size: 13px;
  font-weight: 650;
  text-decoration: none;
}

.theme-navigation a:first-child,
.theme-navigation a:hover {
  color: var(--accent);
}

.theme-group,
.other-important-news {
  margin: 0 0 34px;
  background: var(--surface);
  border: 0;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
}

.theme-header {
  padding: 2px 0 12px;
}

.theme-kicker {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.04em;
}

.theme-heading-line {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.theme-heading-line h2 {
  margin: 0;
  font-size: clamp(22px, 2.4vw, 32px);
  line-height: 1.25;
}

.theme-total {
  margin: 0;
  color: #8a96a8;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}
```

Keep catalyst, mappings, risk, news detail, source, pricing badge, and association styles, but remove their card-like outer framing. Use a fine top rule for each `.theme-news-list`; keep the news content at the highest readable density.

Change `.news-row` to `grid-template-columns: 34px minmax(0, 1fr) auto`; set `.news-score` to one muted 10px line and remove the `.news-score strong` block. Preserve content/title/source sizes and unique expandable details.

Style the pending appendix as a small neutral footer rather than an amber panel:

```css
.pending-section {
  margin-top: 22px;
  border-top: 1px solid var(--line);
}

.pending-details summary {
  padding: 12px 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.pending-body {
  padding: 0 0 8px;
}

.pending-item h3 {
  font-size: 13px;
}
```

At the existing `max-width: 820px` breakpoint, add `gap: 14px` to navigation, set `.theme-heading-line { flex-wrap: wrap; }`, and use this exact two-column news layout:

```css
.news-row {
  grid-template-columns: 28px minmax(0, 1fr);
}

.news-score {
  grid-column: 2;
  justify-self: start;
  margin-top: -4px;
}
```

This fixes the score below the summary in the content column. The full viewport must remain at or below `document.documentElement.clientWidth` with no page-level horizontal overflow.

- [ ] **Step 5: Run focused tests and static syntax checks to GREEN**

Run:

```bash
python3 -m unittest \
  tests.test_web_build.WebBuildTest.test_app_script_keeps_source_only_associations_and_mutes_score_metadata \
  tests.test_web_build.WebBuildTest.test_themed_cross_theme_instances_are_unique_and_source_only_has_no_toggle \
  tests.test_web_build.WebBuildTest.test_page_has_accessible_interaction_contract -v
node --check web/assets/app.js
git diff --check
```

Expected: all tests pass, JavaScript parses, and the diff contains no whitespace errors.

- [ ] **Step 6: Commit the visual slice**

```bash
git add web/assets/app.css web/assets/app.js tests/test_web_build.py
git diff --cached --check
git commit -m "style: prioritize core directions in reports"
```

### Task 4: Rebuild artifacts and complete regression/UAT evidence

**Files:**
- Modify generated: `web/dist/assets/app.css`
- Modify generated: `web/dist/assets/app.js`
- Modify generated: `web/dist/reports/*.html`
- Verify unchanged after rebuild: `web/dist/index.html`, `web/dist/reports.json`
- Create: `docs/uat/2026-08-12-core-direction-first-layout.md`
- Modify: `tests/test_web_build.py:401-459`

**Interfaces:**
- Consumes: the approved fixed renderer/assets and reports discovered from `/Users/aviva/Projects/market_news`.
- Produces: deterministic checked-in `web/dist`, a current Aug. 11 contract test, and a persistent UAT record. It does not publish the tree.

- [ ] **Step 1: Update the checked-artifact test before rebuilding**

Replace Aug. 11's old index assertions with final consumer-facing assertions:

```python
self.assertNotIn('data-component="news-index"', page)
self.assertNotIn("单条新闻热榜索引", page)
self.assertNotIn("接下来的方向", page)
self.assertEqual(5, page.count('data-component="theme-group"'))
self.assertEqual(
    ["01", "02", "03", "04", "05"],
    re.findall(r'<p class="theme-kicker">核心方向 (\d{2})</p>', page),
)
self.assertLess(page.index("核心方向 05"), page.index("其他重要新闻"))
self.assertLess(page.index("其他重要新闻"), page.index("待核验线索"))
self.assertIn('<summary>待核验线索 <span>· 5</span></summary>', page)
self.assertNotIn('<details class="pending-details" open>', page)
```

Keep the exact five theme names/scores, 24 distinct event IDs, unique instance IDs, complete release-session count, cutoff, critical source URLs, five pending items, latest manifest URL, and archive-link assertions. Update only the theme-total regex to parse `N条 · SCORE`.

- [ ] **Step 2: Run the checked-artifact test and verify RED**

Run:

```bash
python3 -m unittest tests.test_web_build.WebBuildTest.test_checked_in_aug11_artifact_keeps_themed_news_contract -v
```

Expected: FAIL against the stale checked-in Aug. 11 HTML.

- [ ] **Step 3: Rebuild the complete static site from Markdown and fixed source assets**

Use the existing worktree adapter so report content comes from the main project while template assets come from this worktree:

```bash
python3 -c 'from pathlib import Path; import shutil; import web.build as b; source_assets=Path(b.__file__).with_name("assets"); b._copy_assets=lambda project_root,destination: shutil.copytree(source_assets,destination/"assets"); result=b.build_site(Path("/Users/aviva/Projects/market_news"),Path("/Users/aviva/Projects/market_news/.worktrees/news-radar-web/web/dist")); print(result)'
```

Record the exact `BuildResult` report count, item count, and latest URL in the UAT document.

- [ ] **Step 4: Run deterministic artifact and full regression gates**

Run:

```bash
cmp web/assets/app.js web/dist/assets/app.js
cmp web/assets/app.css web/dist/assets/app.css
node --check web/dist/assets/app.js
python3 -m unittest discover -s tests -v
git diff --check
```

Then build once more into a temporary `dist` using the same adapter and byte-compare every file to checked-in `web/dist`. Expected: assets match byte-for-byte, all tests pass, no whitespace errors, public-tree safety passes inside `build_site`, and the second complete build is byte-identical.

- [ ] **Step 5: Perform desktop and mobile browser UAT**

Serve `web/dist` on `127.0.0.1` and inspect `reports/2026-08-11-0800.html` using the in-app browser. Persist these results in `docs/uat/2026-08-12-core-direction-first-layout.md`:

```text
Desktop:
- narrow archive unchanged and operational
- one-line direction navigation, five anchors, correct anchor targets
- core directions 01→05 appear sequentially with complete news details
- no long index, no “接下来的方向”, no intensity/stat cards
- theme totals and news heat values are visually secondary
- other important news follows direction 05
- pending appendix is last and initially collapsed; native keyboard toggle works
- source-only news has no empty detail button
- detail buttons open only their own unique detail regions
- zero console errors or warnings

Mobile 390×844:
- desktop archive hidden and report selector remains usable
- direction navigation scrolls horizontally without page overflow
- theme title is not clipped by score metadata
- news rows remain readable; sources and details wrap
- pending appendix remains collapsed by default
- document.scrollWidth <= document.documentElement.clientWidth
```

- [ ] **Step 6: Record UAT and review the exact delivery scope**

Create `docs/uat/2026-08-12-core-direction-first-layout.md` containing: approved spec/plan paths and commits, build command/result, exact test count, deterministic comparison result, desktop/mobile checks, console result, public-tree safety result, and the explicit boundary “未合并、未推送、未部署、自动任务保持关闭”.

Inspect:

```bash
git status --short
git diff --stat
git diff -- web/build.py web/assets/app.js web/assets/app.css tests/test_web_build.py docs/uat/2026-08-12-core-direction-first-layout.md
git diff -- web/dist
```

Exclude `.superpowers/`, `task-5-report.md`, local server state, credentials, local URLs, and unrelated user changes.

- [ ] **Step 7: Commit generated artifacts and verification evidence**

```bash
git add web/dist tests/test_web_build.py docs/uat/2026-08-12-core-direction-first-layout.md
git diff --cached --check
git commit -m "test: verify core-direction-first report layout"
```

After the commit, rerun `python3 -m unittest discover -s tests -v`, `node --check web/assets/app.js`, and `git status --short`. Report remaining unrelated untracked files separately; do not push or publish.
