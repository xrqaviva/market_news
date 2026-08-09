# Report Archive Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 220px flat desktop archive with a roughly 120px collapsed date tree whose date links open the latest real report for that day and reveal only locally available slots.

**Architecture:** Keep `report_index` as the single source of truth. Server rendering groups and sorts reports, emits hidden semantic date groups, and puts the target date in a URL fragment; a small JavaScript state function opens only the fragment-matched group without browser storage. The existing generated-static-site and public-tree security boundaries remain unchanged.

**Tech Stack:** Python 3 standard library renderer and `unittest`, fixed HTML template, dependency-free JavaScript, CSS, GitHub Pages static output.

## Global Constraints

- Desktop sidebar and brand column are approximately 120px; content, chevron, and tree line have approximately 30px total horizontal whitespace.
- Remove the visible “报告归档” label.
- Dates sort newest first; children sort by actual report slot and display only reports present in `report_index`.
- Clicking a date navigates to that date's latest real report and opens only that date; the latest report is selected by default.
- A no-fragment page load keeps all dates collapsed; the site index still opens the globally latest report.
- Normalize navigation label “收盘” to “盘后” without altering report body metadata or Markdown.
- Do not read or write Cookie, Local Storage, Session Storage, browser history, or credentials.
- Do not modify news content, ranking, filters, detail expansion, mobile layout, automations, or unrelated main-workspace changes.

## Discovery and Baseline

- Repository/worktree: `/Users/aviva/Projects/market_news/.worktrees/news-radar-web`, branch `codex/news-radar-web`.
- Approved design: `docs/superpowers/specs/2026-08-09-report-archive-tree-design.md`, commits `3f9e4e4` and `93a2008`.
- Relevant files: `web/build.py`, `web/assets/app.js`, `web/assets/app.css`, `web/templates/report.html`, `tests/test_web_build.py`, generated `web/dist/`.
- Pre-change baseline: `python3 -m unittest discover -s tests -v && node --check web/assets/app.js && git diff --check` completed on 2026-08-09 with 53 tests passed, 0 failed, 0 errors, 0 skipped; JavaScript syntax and diff whitespace checks passed.
- Existing isolated worktree was already created for the fixed web template. Main workspace planning files and research/report files remain outside the feature patch.

## Test Matrix

- Unit/rendering: grouped dates, descending date order, ascending real slot order, date latest-target, `收盘` normalization, no invented slots, current-link state.
- Integration/build: all discovered reports render, archive links remain relative/resolvable, manifest and index latest target remain unchanged.
- UI: initial collapse, date click navigation, only target group open, latest child selected, same-date child switching, 120px width, no clipping, mobile select count/current value, filters and news detail regression, console warnings/errors.
- Security/privacy: existing `assert_public_tree_safe`, explicit scan for host-local paths and storage/auth terms, no unsafe URL schemes.
- Artifacts: rebuild `web/dist`, compare source and built CSS/JS byte-for-byte, validate six report pages and manifest completeness.
- Quality/release: `node --check`, `git diff --check`, complete `unittest` suite, exact diff/staged review, independent read-only review, public dry-run, publish only after all gates pass.

---

### Task 1: Render grouped real-report archive data

**Files:**
- Modify: `tests/test_web_build.py`
- Modify: `web/build.py`

**Interfaces:**
- Consumes: `report_index: list[dict]` entries with `id`, `date`, `slot`, `label`, and `url`.
- Produces: `_report_archive(document: ReportDocument, report_index: list[dict]) -> str` containing `.archive-date-group`, `.archive-date-link`, `.archive-slots`, and child `data-report-link` / `data-report-label="日期 · 时段"` markup.

- [ ] **Step 1: Write the failing rendering test**

Add a real `render_report` fixture whose deliberately unordered index includes `2026-08-10/0800`, `2026-07-30/0800`, and `2026-07-30/1800` labeled `收盘`. Assert literal consumer-visible behavior:

```python
self.assertLess(page.index("2026-08-10"), page.index("2026-07-30"))
self.assertEqual(1, page.count('data-report-date="2026-07-30"'))
self.assertIn('href="2026-07-30-1800.html#archive-2026-07-30"', page)
self.assertLess(page.index(">盘前</a>"), page.index(">盘后</a>"))
self.assertNotIn(">盘中</a>", page)
self.assertIn('data-report-label="2026-07-30 · 盘后"', page)
```

The production mutation caught is reverting to flat input order, targeting the wrong daily report, retaining `收盘`, or inventing absent slots.

- [ ] **Step 2: Run the focused test and observe RED**

Run: `python3 -m unittest tests.test_web_build.WebBuildTest.test_archive_groups_dates_and_targets_latest_real_report -v`

Expected: FAIL because the current renderer emits one flat link per report and lacks `data-report-date` and date-fragment links.

- [ ] **Step 3: Implement the minimal grouped renderer**

In `web/build.py`, add small private helpers with exact responsibilities:

```python
def _archive_slot_label(report: dict) -> str:
    label = str(report.get("label", ""))
    return "盘后" if label == "收盘" else label

def _archive_sort_key(report: dict) -> tuple:
    slot = str(report.get("slot", ""))
    return (int(slot) if slot.isdigit() else 9999, slot, str(report.get("id", "")))
```

Group by exact `date`, sort date keys descending, sort each real group using `_archive_sort_key`, use the last item as the date-link target, and render child links only from the group. Add `#archive-<date>` to both date and child links, mark every child with `data-report-link`, and put its complete mobile option text in `data-report-label="<date> · <normalized slot>"`. Escape every interpolated value with `_escape`.

- [ ] **Step 4: Run focused and existing archive tests to GREEN**

Run: `python3 -m unittest tests.test_web_build.WebBuildTest.test_archive_groups_dates_and_targets_latest_real_report tests.test_web_build.WebBuildTest.test_report_archive_links_resolve_from_report_directory -v`

Expected: both pass; update the existing relative-link assertion to include its fragment while still rejecting `reports/...` links.

### Task 2: Add collapsed fragment-driven interaction and narrow styling

**Files:**
- Modify: `tests/test_web_build.py`
- Modify: `web/templates/report.html`
- Modify: `web/assets/app.js`
- Modify: `web/assets/app.css`

**Interfaces:**
- Consumes: `.archive-date-group[data-report-date]`, `.archive-date-link[aria-controls]`, `.archive-slots[hidden]`, and child anchors marked `data-report-link` with `data-report-label`.
- Produces: `applyArchiveState()` that derives the sole expanded date from `window.location.hash`; mobile options generated only from `a[data-report-link]`.

- [ ] **Step 1: Write failing accessibility and static-state assertions**

Extend the page interaction test to require date controls with `aria-expanded="false"`, matching `aria-controls`, hidden slot lists, and report-only link markers. Assert the removed label is absent from the rendered page:

```python
self.assertIn('class="archive-date-link"', page)
self.assertIn('aria-expanded="false"', page)
self.assertIn('class="archive-slots"', page)
self.assertIn('data-report-link', page)
self.assertNotIn('<p class="sidebar-label">报告归档</p>', page)
```

The production mutation caught is rendering visible children by default, repopulating the mobile select from date links, or restoring the removed heading.

- [ ] **Step 2: Run the focused test and observe RED**

Run: `python3 -m unittest tests.test_web_build.WebBuildTest.test_page_has_accessible_interaction_contract -v`

Expected: FAIL because current pages have no date controls or hidden archive slot lists and still contain the heading.

- [ ] **Step 3: Implement fragment-driven state without storage**

Remove the sidebar label from `web/templates/report.html`. In `web/assets/app.js`, change mobile option discovery to `[data-component='report-archive'] a[data-report-link]` and use each link's `data-report-label` as the option text. Add `applyArchiveState()` that accepts only hashes matching `#archive-YYYY-MM-DD`, sets exactly one matching group's list `hidden = false`, sets its date link `aria-expanded = "true"`, and collapses all others. Call it at startup and on `hashchange`. Do not call any storage, cookie, or history API.

- [ ] **Step 4: Implement the 120px visual contract**

In `web/assets/app.css`, change both desktop grid columns from `220px` to `120px`; keep the mobile breakpoint. Replace flat archive anchor rules with scoped date-link and child-link rules, remove obsolete `.sidebar-label`, use compact outer/inner padding totaling approximately 30px around the date content, add a chevron rotation for the expanded group, and preserve the existing active child colors.

- [ ] **Step 5: Run focused tests and JavaScript syntax to GREEN**

Run: `python3 -m unittest tests.test_web_build.WebBuildTest.test_page_has_accessible_interaction_contract tests.test_web_build.WebBuildTest.test_archive_groups_dates_and_targets_latest_real_report -v && node --check web/assets/app.js`

Expected: both tests pass and JavaScript syntax exits 0.

### Task 3: Rebuild, verify, review, and publish

**Files:**
- Modify generated: `web/dist/assets/app.css`, `web/dist/assets/app.js`, `web/dist/index.html`, `web/dist/reports.json`, `web/dist/reports/*.html`
- Create: `docs/uat/2026-08-09-report-archive-tree.md`

**Interfaces:**
- Consumes: approved fixed template plus reports discovered from `/Users/aviva/Projects/market_news/reports`.
- Produces: six consistent static report pages and a documented release record.

- [ ] **Step 1: Rebuild the complete site**

Run the established source-assets adapter so the isolated template reads the main workspace report catalog and atomically rebuilds `web/dist`:

```bash
python3 -c 'from pathlib import Path; import shutil; import web.build as b; source_assets=Path(b.__file__).with_name("assets"); b._copy_assets=lambda project_root,destination: shutil.copytree(source_assets,destination/"assets"); result=b.build_site(Path("/Users/aviva/Projects/market_news"),Path("/Users/aviva/Projects/market_news/.worktrees/news-radar-web/web/dist")); print(result)'
```

Record report count, item count, and latest URL from `BuildResult`.

- [ ] **Step 2: Run artifact and security gates**

Run:

```bash
cmp web/assets/app.js web/dist/assets/app.js
cmp web/assets/app.css web/dist/assets/app.css
node --check web/dist/assets/app.js
git diff --check
python3 -m unittest discover -s tests -v
```

Expected: byte-identical assets, clean syntax/diff, and every test passes with exact count recorded after the final generated change.

- [ ] **Step 3: Exercise the generated page in a browser**

Serve `web/dist` on `127.0.0.1`. Verify initial latest report has five collapsed dates and no visible child links; click `2026-07-30`, verify navigation to `2026-07-30-1500.html#archive-2026-07-30`, only that group opens, only盘前/盘后 appear, and盘后 is current. Click盘前, verify the same group remains open. Measure the sidebar at approximately120px, confirm dates are not clipped, verify mobile select options equal report count, exercise category filtering and Top 10 detail, and record zero console warnings/errors.

- [ ] **Step 4: Complete independent read-only review and UAT record**

Ask the available internal reviewer to inspect approved-requirement mapping, generated compatibility, privacy, and test coverage without modifying files. Reproduce any blocking finding with RED before fixing. Record findings and final disposition in `docs/uat/2026-08-09-report-archive-tree.md`.

- [ ] **Step 5: Review exact release scope**

Inspect `git diff`, generated page counts, public-tree scan, worktree status, and exclude `.superpowers/`, main workspace planning/research files, credentials, local URLs, and temporary servers. Commit only after fresh verification under the user's standing staged-commit authorization.

- [ ] **Step 6: Dry-run then publish the public tree**

Run the publisher dry-run:

```bash
python3 -m web.publish --dist web/dist --site-repo /Users/aviva/Projects/market-news-site
```

Only after it reports the expected static paths, publish under the user's standing publication authorization:

```bash
python3 -m web.publish --dist web/dist --site-repo /Users/aviva/Projects/market-news-site --apply --commit --push
```

Then use `gh api repos/xrqaviva/market-news-site/pages/builds/latest` to require status `built`, use HTTP HEAD checks to require 200 for the public homepage and latest report, and fetch the public report HTML to require the new archive contract.
