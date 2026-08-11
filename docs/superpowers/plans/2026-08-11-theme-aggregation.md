# Theme-First News Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Also use superpowers:test-driven-development before production changes and superpowers:verification-before-completion before claiming completion.

**Goal:** Make dynamically generated themes the primary report structure, rank themes by the sum of associated news scores, retain complete original news detail inside every theme, and preserve legacy-report compatibility.

**Architecture:** Extend the domain model and parser with a themed-report path while leaving the legacy numbered-news path intact. Parse a canonical news registry from the single-news index and validate every repeated themed instance by stable event_id. Render the index, ranked themes, ungrouped important news, and the pending-verification appendix from structured data. Theme membership affects grouping and additive theme scores only; it never changes individual news scores or assigns scores to mapped stocks.

**Tech Stack:** Python 3 standard library, dataclasses, existing Markdown parser/build pipeline, static HTML/CSS/JavaScript, unittest, and existing public-tree security checks.

## File map

- Modify web/report_model.py: add immutable models for stock mappings, index entries, and themes.
- Modify web/report_parser.py: detect and parse the themed grammar and enforce consistency.
- Modify web/build.py: render the news index, themes, other news, and unique detail instances.
- Modify web/templates/report.html: add themed placeholders while preserving the legacy path.
- Modify web/assets/app.js: key controls by unique render-instance ID instead of rank.
- Modify web/assets/app.css: add compact theme, catalyst, mapping, and index styles.
- Modify tests/test_web_parser.py and tests/test_web_build.py in the web worktree.
- Add root tests/test_aug11_theme_report_contract.py.
- Convert root and worktree copies of reports/2026-08-11-0800-premarket-news-ranking.md.
- Update the authoritative method, operations, UAT, and progress documents.
- Regenerate web/dist only through the existing build pipeline.

All web paths above are relative to:

    /Users/aviva/Projects/market_news/.worktrees/news-radar-web

All root paths are relative to:

    /Users/aviva/Projects/market_news

## Global constraints

- Preserve unrelated user changes; never reset or overwrite the dirty worktree.
- Do not read or expose passwords, cookies, browser storage, tokens, or history.
- Do not push, deploy, publish, email, or enable automations.
- Display Beijing time. Apply US session labels to US news and China session labels to China news.
- Link every source label to the exact article or post, never a source homepage.
- Individual news scores remain unchanged.
- Theme score equals the sum of all associated news scores. A cross-theme event contributes its full score to every associated theme.
- A theme needs at least two qualified ranked items and a coherent shared industry, catalyst, supply chain, policy, or event mechanism.
- Direct mapping and sector representative stocks remain separate, unscored, and non-advisory.
- Historical reports must continue to parse and render.
- Pending-verification items remain outside rankings and theme totals.

## Baseline and preservation checkpoint

Baseline recorded at 2026-08-11T11:02:57+08:00:

- Root suite: 36 passed, zero failures/errors.
- Web suite: 56 passed, zero failures/errors.
- assert_public_tree_safe(web/dist): PASS.
- Web git diff --check: PASS.

- [ ] Run git status --short and git diff --stat in root and worktree.
- [ ] Inspect and preserve the current pending-appendix/template behavior.
- [ ] Do not bundle unrelated root changes into feature commits.
- [ ] Re-run both baselines. Diagnose any delta before feature edits.

## Task 1: Define the themed model and parser contract

**Files:**

- tests/test_web_parser.py
- web/report_model.py
- web/report_parser.py

### Step 1: Write failing model/parser tests

- [ ] Add a complete fixture with a single-news index, two themes, one event repeated across themes, one ungrouped item, and one pending item.
- [ ] Assert immutable StockMapping, NewsIndexEntry, and ThemeGroup structures.
- [ ] Extend ReportDocument with default-empty news_index, themes, and other_items so legacy constructors remain valid.
- [ ] Add optional event_id and theme_ids fields to NewsItem with legacy-safe defaults.
- [ ] Assert exact sources, Beijing times, feedback, boundary, and heat-change data survive parsing.
- [ ] Assert deterministic ordering by total score descending, item count descending, maximum item score descending, then normalized theme name ascending.

Run:

    cd /Users/aviva/Projects/market_news/.worktrees/news-radar-web
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_web_parser -v

Expected RED: themed model attributes or parser path do not exist.

### Step 2: Add validation failure tests

- [ ] Reject themes with fewer than two ranked items.
- [ ] Reject declared totals that differ from summed member scores.
- [ ] Reject repeated event_id blocks whose title, score, core, sources, feedback, boundary, or heat detail differs.
- [ ] Reject theme references missing from the index.
- [ ] Reject index/body membership mismatches.
- [ ] Reject qualified index items missing from both themes and Other Important News.
- [ ] Reject items placed in both a theme and Other Important News.
- [ ] Accept full repeated contribution of one event to multiple themes.
- [ ] Confirm pending items never enter the ranked-event set.

### Step 3: Implement the smallest parser change

- [ ] Add StockMapping, NewsIndexEntry, and ThemeGroup dataclasses.
- [ ] Add legacy-safe fields to NewsItem and ReportDocument.
- [ ] Route only documents containing the single-news index heading to _parse_themed_report.
- [ ] Implement focused helpers:
  - _parse_news_index
  - _parse_stock_mappings
  - _parse_nested_news_blocks
  - _parse_theme_groups
  - _parse_other_items
  - _validate_themed_document
- [ ] Reuse existing source-table and field parsing.
- [ ] Normalize only the name used for tie-breaking; preserve display names.

### Step 4: Verify and commit

    cd /Users/aviva/Projects/market_news/.worktrees/news-radar-web
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_web_parser -v
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
    git diff --check

Expected GREEN: prior 56 tests plus new parser tests pass.

Commit only this slice:

    git add web/report_model.py web/report_parser.py tests/test_web_parser.py
    git commit -m "feat: parse theme-first news reports"

## Task 2: Render theme-first pages with unique controls

**Files:**

- tests/test_web_build.py
- web/build.py
- web/templates/report.html
- web/assets/app.js
- web/assets/app.css

### Step 1: Write failing renderer tests

- [ ] Index renders rank, title, score, all associations, and an anchor.
- [ ] Themes render in validated order with total, count, catalyst, mappings, and risk boundary.
- [ ] Every theme retains complete news detail and exact links/times.
- [ ] Cross-theme copies are content-identical but have distinct DOM IDs.
- [ ] Other Important News uses complete detail blocks.
- [ ] Pending items remain a separate unscored appendix.
- [ ] Legacy reports retain the flat layout without empty theme containers.

Expected RED command:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_web_build -v

### Step 2: Implement structured rendering

- [ ] Change _news_item to require instance_id and optional association labels.
- [ ] Derive safe instance IDs from report ID, theme ID or other, and event_id; never rank alone.
- [ ] Add _news_index, _theme_group, _theme_groups, and _other_important_news helpers.
- [ ] Add template placeholders for these sections.
- [ ] Keep NEWS_ITEMS active only for legacy documents.
- [ ] Render association badges and a cross-theme repeated-scoring disclosure.

### Step 3: Update interaction and styles

- [ ] Make app.js use data-instance-id and matching unique detail IDs.
- [ ] Ensure toggling one repeated event does not toggle another copy.
- [ ] Keep source-only details visible and buttonless.
- [ ] Add compact styles for index, theme totals, catalysts, risk, mappings, associations, and other news.
- [ ] Preserve the approved narrow hierarchical archive sidebar and responsive behavior.

### Step 4: Verify and commit

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_web_build -v
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
    git diff --check

Commit only this slice:

    git add web/build.py web/templates/report.html web/assets/app.js web/assets/app.css tests/test_web_build.py
    git commit -m "feat: render topic-ranked news reports"

## Task 3: Convert the 2026-08-11 report

**Files:**

- Root tests/test_aug11_theme_report_contract.py
- Root reports/2026-08-11-0800-premarket-news-ranking.md
- Worktree reports/2026-08-11-0800-premarket-news-ranking.md

### Step 1: Write the failing report-contract test

- [ ] Assert exactly 25 unique ranked events.
- [ ] Assert every rank/title/score pair is unchanged.
- [ ] Assert these six themes, memberships, and totals:

| Theme | Ranks | Total |
|---|---:|---:|
| AI算力 / 半导体 / 存储芯片 | 5, 6, 13, 14, 20 | 420 |
| 并购重组 | 10, 16, 22, 24 | 306 |
| 中东局势 / 油气 | 1, 7 | 184 |
| 低空经济 / 航空AI | 10, 15 | 166 |
| A股回购 / 资本运作 | 5, 21 | 165 |
| 人形机器人 / 具身智能 | 2, 25 | 161 |

- [ ] Assert rank 5 contributes 89 to AI and buyback.
- [ ] Assert rank 10 contributes 86 to M&A and low-altitude aviation.
- [ ] Assert all remaining qualified events occur exactly once in Other Important News.
- [ ] Assert repeated blocks are identical.
- [ ] Assert exactly four pending items, all unscored.
- [ ] Assert root and worktree Markdown copies are byte-identical.

Expected RED:

    cd /Users/aviva/Projects/market_news
    python3 -m unittest tests.test_aug11_theme_report_contract -v

### Step 2: Rewrite without losing details

- [ ] Add stable IDs evt-20260811-001 through evt-20260811-025.
- [ ] Add six themes in total-score order and member news in original rank order.
- [ ] Preserve full title, core, exact sources, Beijing times, channel, signal, observable market reaction, boundary, and heat history.
- [ ] Put non-theme qualified events in Other Important News with the same full contract.
- [ ] Preserve four pending items.
- [ ] Disclose that cross-theme repeated totals cannot be summed into a market-wide score.

### Step 3: Add conservative A-share mappings

- [ ] Direct mappings only when report evidence directly names or economically binds the company:
  - AI/storage: 江波龙 301308; 芯联集成 688469.
  - Buyback: 江波龙 301308; 兆驰股份 002429; 国联民生 601456; 永茂泰 605208; 威迈斯 688612.
  - M&A: 建设机械 600984.
- [ ] Sector representatives, explicitly not direct beneficiaries:
  - AI/storage: 浪潮信息 000977; 中科曙光 603019; 海光信息 688041; 中际旭创 300308; 天孚通信 300394; 北方华创 002371; 中微公司 688012; 兆易创新 603986; 佰维存储 688525.
  - Human robots: 绿的谐波 688017; 双环传动 002472; 鸣志电器 603728; 柯力传感 603662; 埃斯顿 002747; 拓普集团 601689.
  - Low altitude: 万丰奥威 002085; 中信海直 000099; 宗申动力 001696.
  - Middle East/oil: 中国石油 601857; 中国海油 600938; 中远海能 600026.
- [ ] Omit any code or mapping that cannot be verified.
- [ ] Attach an evidence phrase and state that representative stocks do not inherit scores.

### Step 4: Verify and commit

    cd /Users/aviva/Projects/market_news
    python3 -m unittest tests.test_aug11_theme_report_contract -v
    python3 -m unittest discover -s tests -v
    cmp reports/2026-08-11-0800-premarket-news-ranking.md .worktrees/news-radar-web/reports/2026-08-11-0800-premarket-news-ranking.md

Commit only feature files; do not include unrelated changes.

## Task 4: Persist the method and anti-omission rules

**Files:**

- Current authoritative files under docs/
- HANDOFF.md
- task_plan.md
- findings.md
- progress.md
- Relevant root documentation-contract tests

### Step 1: Locate authoritative documents

    cd /Users/aviva/Projects/market_news
    rg -n "热点权重|纯新闻热榜|题材|首次时间|热度变化|待核验" HANDOFF.md task_plan.md findings.md progress.md docs

- [ ] Select only the active spec, user guide, UAT, and integration-test records.
- [ ] Do not rewrite superseded drafts except to point to the current spec.

### Step 2: Add failing documentation-contract tests

Assert that active documents define:

- theme score and repeated full scoring;
- at least two semantically coherent items;
- dynamic naming plus synonym normalization;
- full news detail under themes;
- direct versus representative mappings;
- non-additivity of totals across themes;
- old-news heat-surge eligibility;
- Beijing-time conversion;
- relevant-market session labels;
- observable post-release market reaction;
- pending-item exclusion.

### Step 3: Update method, workflow, UAT, and status

- [ ] Add the exact Markdown grammar and one valid compact example.
- [ ] Add UAT cases for cross-theme membership, totals, coherence rejection, exact links, duplicate equality, other-news coverage, pending exclusion, market reaction, and legacy compatibility.
- [ ] Persist Aug 11 anti-omission controls: source breadth, finance/policy substreams, overseas macro, semiconductor financing/infrastructure, synonym expansion, and final completeness reconciliation.
- [ ] Record implementation and deployment status accurately.

### Step 4: Verify and commit selected documentation

    python3 -m unittest discover -s tests -v
    git diff --check

## Task 5: Build deterministic HTML

**Files:**

- Generated files under web/dist/
- Build tests only when a missing invariant is first demonstrated by RED.

### Step 1: Add generated-output assertions

- [ ] Six themes appear in exact total-score order.
- [ ] Totals are 420, 306, 184, 166, 165, 161.
- [ ] Index has exactly 25 unique event IDs.
- [ ] Repeated instances have unique DOM IDs.
- [ ] Exact source URLs are clickable.
- [ ] Pending appendix has four items and no score.
- [ ] Archive navigation and reports.json select the latest report.

### Step 2: Rebuild through the existing generator

- [ ] Use the same build entry point exercised by tests/test_web_build.py.
- [ ] Confirm all historical reports are generated.
- [ ] Confirm historical output changes only where shared template/assets intentionally changed.
- [ ] Confirm Aug 11 HTML comes from Markdown, never hand editing.

### Step 3: Security and determinism checks

    cd /Users/aviva/Projects/market_news/.worktrees/news-radar-web
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
    git diff --check

- [ ] Run assert_public_tree_safe(web/dist).
- [ ] Search output for local paths, secrets, cookies, browser state, and file URLs.
- [ ] Build twice and assert no second-build diff beyond existing accepted metadata.
- [ ] Commit generated artifacts locally only; do not push or deploy.

## Task 6: Browser UAT, independent review, final verification

### Step 1: Browser UAT

- [ ] Default archive selection is the latest date's latest report.
- [ ] Date to session to report hierarchy retains approved behavior.
- [ ] Index links reach the correct complete detail.
- [ ] Themes show score, count, catalyst, mappings, and boundary compactly.
- [ ] Every source reaches the exact article/post.
- [ ] Repeated toggles operate independently.
- [ ] Source-only details have no redundant button.
- [ ] Desktop and narrow layouts do not overflow.
- [ ] Console has no JavaScript errors or duplicate-ID warnings.

Use only a permitted local browser/preview surface. Do not bypass browser security.

### Step 2: Independent read-only review

Reviewer checks:

- arithmetic and theme order;
- exact 25-event coverage;
- repeated-event equality;
- stock mapping classifications;
- links and Beijing times;
- relevant-market session and reaction wording;
- pending exclusion;
- legacy compatibility;
- generated-output security.

Resolve each correctness or high-risk issue with another RED-to-GREEN cycle.

### Step 3: Fresh final verification

Root:

    cd /Users/aviva/Projects/market_news
    python3 -m unittest discover -s tests -v
    git diff --check

Web:

    cd /Users/aviva/Projects/market_news/.worktrees/news-radar-web
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
    git diff --check

Also verify:

- [ ] public-tree safety passes;
- [ ] report copies are byte-identical;
- [ ] 25 events occur once in the index and at least once in the body;
- [ ] totals and ordering are exact;
- [ ] four pending items remain unscored;
- [ ] no automation was enabled;
- [ ] no push, deployment, email, or publication occurred.

### Step 4: Handoff

- [ ] Report exact final test counts and commands.
- [ ] Link Markdown, HTML, design spec, plan, method, and UAT documents.
- [ ] Disclose degraded sources or omitted unverified mappings.
- [ ] State that output remains local.
- [ ] Offer the next separately authorized action: preview, commit consolidation, push, or GitHub Pages deployment.

## Acceptance criteria

- [ ] Theme blocks form the main body.
- [ ] Themes are dynamic, normalized, coherent, and contain at least two items.
- [ ] Totals use full additive scores and deterministic sorting.
- [ ] Cross-theme associations and repeated scoring are visible.
- [ ] Every theme copy retains complete detail and exact verification links.
- [ ] The index contains every unique event once.
- [ ] Non-theme events remain complete in Other Important News.
- [ ] Direct and representative mappings are separate and unscored.
- [ ] Pending items remain separate and unscored.
- [ ] Historical reports still parse and render.
- [ ] HTML is deterministic, safe, compact, and interaction-safe.
- [ ] Root tests, web tests, browser UAT, security checks, and independent review all pass.
