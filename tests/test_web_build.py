import json
from collections import Counter
from dataclasses import replace
from html import escape, unescape
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from web.build import _news_instance_id, _safe_dom_id, build_site, render_report
from web.report_model import (
    NewsIndexEntry,
    NewsItem,
    PendingItem,
    ReportBlock,
    ReportDocument,
    ReportInline,
    ReportMeta,
    ReportSection,
    SourceLink,
    StockMapping,
    ThemeGroup,
)
from web.report_parser import discover_reports
from web.security import PublicTreeUnsafe


ROOT = Path(__file__).resolve().parents[1]
DAILY_INFO_ROOT = Path("/Users/aviva/Projects/daily_info")


class WebBuildTest(unittest.TestCase):
    def _themed_document(self) -> ReportDocument:
        shared = NewsItem(
            rank=1, event_id="evt-shared", title="共享新闻", core="共享核心", score=90,
            market_feedback="共享反馈", boundary="共享边界", heat_change="共享热度",
            release_session="美国市场盘后发布",
            sources=(SourceLink("官方", "08-11 08:00", "共享直链", "https://example.com/shared"),),
            theme_ids=("theme-alpha", "theme-beta"),
        )
        alpha_only = NewsItem(
            rank=2, event_id="evt-alpha", title="甲题材新闻", core="甲核心", score=80,
            sources=(SourceLink("官方", "08-11 08:01", "甲直链", "https://example.com/alpha"),),
            theme_ids=("theme-alpha",),
        )
        beta_only = NewsItem(
            rank=3, event_id="evt-beta", title="乙题材新闻", core="乙核心", score=70,
            sources=(SourceLink("官方", "08-11 08:02", "乙直链", "https://example.com/beta"),),
            theme_ids=("theme-beta",),
        )
        other = NewsItem(
            rank=4, event_id="evt-other", title="其他新闻", core="其他核心", score=60,
            sources=(SourceLink("官方", "08-11 08:03", "其他直链", "https://example.com/other"),),
        )
        return ReportDocument(
            meta=ReportMeta(
                report_id="themed-report", report_date="2026-08-11", slot="0800",
                slot_label="盘前", title="题材测试", window="window", cutoff="cutoff", source_name="",
            ),
            items=(shared, alpha_only, beta_only, other),
            news_index=(
                NewsIndexEntry(1, "evt-shared", "共享新闻", 90, ("theme-alpha", "theme-beta")),
                NewsIndexEntry(2, "evt-alpha", "甲题材新闻", 80, ("theme-alpha",)),
                NewsIndexEntry(3, "evt-beta", "乙题材新闻", 70, ("theme-beta",)),
                NewsIndexEntry(4, "evt-other", "其他新闻", 60),
            ),
            themes=(
                ThemeGroup(
                    "theme-alpha", "甲题材", 170, "甲的共同催化", "甲风险",
                    (StockMapping("甲公司", "000001", "公告确认"),),
                    (StockMapping("乙公司", "000002", "未确认新增订单"),),
                    ("evt-shared", "evt-alpha"), (shared, alpha_only),
                ),
                ThemeGroup(
                    "theme-beta", "乙题材", 160, "乙的共同催化", "乙风险",
                    event_ids=("evt-shared", "evt-beta"), items=(shared, beta_only),
                ),
            ),
            other_items=(other,),
        )

    def _article(self, page: str, rank: int) -> str:
        match = re.search(
            r'<article data-component="news-detail" data-rank="{}".*?</article>'.format(rank),
            page,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "missing rendered news row for rank {}".format(rank))
        return match.group(0)

    def test_themed_document_renders_navigation_sequential_groups_and_complete_news(self):
        page = render_report(self._themed_document(), [{
            "id": "themed-report", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertNotIn('data-component="news-index"', page)
        self.assertNotIn("单条新闻热榜索引", page)
        self.assertNotIn("接下来的方向", page)
        self.assertIn('data-component="news-mode-switch"', page)
        self.assertIn('class="news-mode-button is-active" data-news-mode="themed"', page)
        self.assertIn('>板块概念模式</button>', page)
        self.assertIn('class="news-mode-button" data-news-mode="ranked"', page)
        self.assertIn('>排序模式</button>', page)
        self.assertIn('data-component="themed-view"', page)
        self.assertIn('<section class="ranked-list" data-component="ranked-list" '
                      'hidden aria-label="按新闻热度排序的列表"></section>', page)
        self.assertLess(
            page.index('data-component="news-mode-switch"'),
            page.index('data-component="themed-view"'),
        )
        self.assertLess(
            page.index('data-component="themed-view"'),
            page.index('data-component="theme-navigation"'),
        )
        self.assertIn(
            '<nav class="theme-navigation" data-component="theme-navigation" '
            'aria-label="核心方向">',
            page,
        )
        self.assertIn('href="#theme-ascii-theme-alpha">甲题材</a>', page)
        self.assertIn('href="#theme-ascii-theme-beta">乙题材</a>', page)
        self.assertLess(page.index("核心方向 01"), page.index("核心方向 02"))
        self.assertLess(page.index("核心方向 02"), page.index('id="other-important-news"'))
        self.assertIn('data-component="theme-group" id="theme-ascii-theme-alpha"', page)
        self.assertIn('<p class="theme-total">2条 · 170</p>', page)
        self.assertIn('<p class="theme-total">2条 · 160</p>', page)
        self.assertIn("甲的共同催化", page)
        self.assertIn("甲公司（000001）：公告确认", page)
        self.assertIn("乙公司（000002）：未确认新增订单", page)
        self.assertIn("甲风险", page)
        self.assertIn("共享反馈", page)
        self.assertIn("共享边界", page)
        self.assertIn("<strong>发布时段</strong>美国市场盘后发布", page)
        self.assertIn("08-11 08:00", page)
        self.assertIn('href="https://example.com/shared"', page)
        self.assertIn('data-component="other-important-news"', page)
        self.assertIn("其他新闻", page)
        self.assertIn("08-11 08:03", page)
        self.assertIn('href="https://example.com/other"', page)
        self.assertIn('href="#theme-ascii-theme-alpha"', page)
        self.assertIn('href="#theme-ascii-theme-beta"', page)
        for target in re.findall(r'class="theme-navigation"[^>]*href="#([^"]+)"', page):
            self.assertIn(f'id="{target}"', page)
        self.assertNotIn("news-associations", page)

    def test_themed_page_omits_legacy_category_filters(self):
        page = render_report(self._themed_document(), [{
            "id": "themed-report", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertNotIn('class="filter-bar"', page)
        self.assertNotIn('class="filter-actions"', page)
        self.assertNotIn('class="filter-button', page)

    def test_report_notes_render_after_news_before_pending_with_safe_semantics(self):
        document = replace(
            self._themed_document(),
            intro_blocks=(
                ReportBlock("paragraph", (
                    ReportInline('顶部 <口径> & "风险"'),
                    ReportInline("安全链接", "https://example.com/method"),
                    ReportInline("危险链接", "javascript:alert(1)"),
                )),
            ),
            report_sections=(
                ReportSection("覆盖 <边界>", (
                    ReportBlock("list-item", (ReportInline("第一项"),)),
                    ReportBlock("table-row", (ReportInline("渠道 · 已覆盖"),)),
                )),
            ),
            pending_items=(PendingItem("待核", "已知", "原因"),),
        )

        page = render_report(document, [{
            "id": "themed-report", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertEqual(1, page.count('data-component="report-notes"'))
        self.assertEqual(1, page.count('<h2 id="report-notes-title">报告说明</h2>'))
        self.assertIn('<details class="report-notes" data-component="report-notes">', page)
        self.assertNotIn('<section class="report-notes"', page)
        self.assertLess(page.index("其他重要新闻"), page.index('data-component="report-notes"'))
        self.assertLess(page.index('data-component="report-notes"'), page.index('data-component="pending-list"'))
        self.assertIn('顶部 &lt;口径&gt; &amp; &quot;风险&quot;', page)
        self.assertIn('<a href="https://example.com/method" rel="noopener noreferrer">安全链接</a>', page)
        self.assertIn("危险链接", page)
        self.assertNotIn('href="javascript:', page)
        self.assertIn('<h3>覆盖 &lt;边界&gt;</h3>', page)
        self.assertIn('<ul class="report-note-list"><li>第一项</li></ul>', page)
        self.assertIn('<ul class="report-note-table"><li>渠道 · 已覆盖</li></ul>', page)

    def test_all_report_note_sections_and_direct_content_reach_fresh_html(self):
        expected_titles = {
            "2026-07-29-1800.html": ("渠道状态与本轮增量", "完整性边界"),
            "2026-07-30-0800.html": ("覆盖边界",),
            "2026-07-30-1500.html": ("7月31日08:00比较基线", "覆盖与安全边界"),
            "2026-07-31-0800.html": ("来源覆盖与限制",),
            "2026-08-03-0800.html": ("盘前待补节点", "来源覆盖与限制"),
            "2026-08-10-0800.html": ("08:00正式版待补节点", "来源覆盖与限制"),
            "2026-08-11-0800.html": ("来源覆盖与核验缺口",),
        }
        source_by_output = {
            "2026-07-29-1800.html": ROOT / "reports/2026-07-29-pure-news-hot-ranking-v4.md",
            "2026-07-30-0800.html": ROOT / "reports/2026-07-30-premarket-news-ranking-v6-depth-test.md",
            "2026-07-30-1500.html": ROOT / "reports/2026-07-30-1500-next-trading-day-news-baseline.md",
            "2026-07-31-0800.html": ROOT / "reports/2026-07-31-0800-premarket-news-ranking.md",
            "2026-08-03-0800.html": ROOT / "reports/2026-08-03-0800-premarket-news-ranking.md",
            "2026-08-10-0800.html": ROOT / "reports/2026-08-10-0800-premarket-news-ranking.md",
            "2026-08-11-0800.html": ROOT / "reports/2026-08-11-0800-premarket-news-ranking.md",
        }

        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            rendered_section_count = 0
            for filename, titles in expected_titles.items():
                page = (output / "reports" / filename).read_text(encoding="utf-8")
                notes = re.search(
                    r'<details class="report-notes".*?</details>',
                    page,
                    re.DOTALL,
                )
                self.assertIsNotNone(notes, filename)
                notes_html = notes.group(0)
                self.assertEqual(1, notes_html.count('<h2 id="report-notes-title">报告说明</h2>'))
                self.assertNotIn("**", notes_html)
                for title in titles:
                    self.assertEqual(1, notes_html.count("<h3>{}</h3>".format(title)))
                    rendered_section_count += 1
                    source = source_by_output[filename].read_text(encoding="utf-8")
                    body = re.search(
                        r"^## {}\n(.*?)(?=^## |\Z)".format(re.escape(title)),
                        source,
                        re.MULTILINE | re.DOTALL,
                    ).group(1)
                    for label, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", body):
                        self.assertIn('href="{}"'.format(escape(url, quote=True)), notes_html)
                        self.assertIn(escape(label, quote=True), notes_html)
                    for raw_line in body.splitlines():
                        line = raw_line.strip()
                        if not line or set(line.replace("|", "")) <= {"-", ":"}:
                            continue
                        if line.startswith("|"):
                            line = " · ".join(part.strip() for part in line.strip("|").split("|"))
                        line = re.sub(r"^[-*]\s+", "", line)
                        fragments = re.split(r"\[[^\]]+\]\([^)]+\)", line)
                        for fragment in fragments:
                            fragment = re.sub(r"[*`]", "", fragment)
                            fragment = re.sub(r"\s+", " ", fragment).strip()
                            if fragment:
                                rendered_fragment = escape(fragment, quote=True).replace(
                                    "Local Storage", "Local&#32;Storage"
                                )
                                self.assertIn(rendered_fragment, notes_html)
            self.assertEqual(11, rendered_section_count)

    def test_all_25_themed_markdown_instances_render_score_breakdown_once(self):
        source = (ROOT / "reports/2026-08-11-0800-premarket-news-ranking.md").read_text(
            encoding="utf-8"
        )
        headings = list(re.finditer(
            r"^#### 新闻：\d+｜([^｜]+)｜.+?｜\d+/100$", source, re.MULTILINE
        ))
        expected = Counter()
        for index, heading in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
            next_section = re.search(r"^## ", source[heading.end():end], re.MULTILINE)
            if next_section:
                end = heading.end() + next_section.start()
            score = re.search(
                r"\*\*热点权重：\d+/100\*\*（([^）]+)）", source[heading.end():end]
            )
            self.assertIsNotNone(score, heading.group(1))
            expected[(heading.group(1), score.group(1))] += 1
        self.assertEqual(25, sum(expected.values()))

        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-08-11-0800.html").read_text(encoding="utf-8")
            actual = Counter()
            for article in re.findall(
                r'(<article(?=[^>]*data-event-id="[^"]+")[^>]*>.*?</article>)', page, re.DOTALL
            ):
                event_id = re.search(r'data-event-id="([^"]+)"', article).group(1)
                values = re.findall(r"<p><strong>热点构成</strong>(.*?)</p>", article, re.DOTALL)
                self.assertEqual(1, len(values), event_id)
                actual[(event_id, unescape(values[0]))] += 1
            self.assertEqual(expected, actual)

    def test_postclose_unique_inline_ap_source_is_clickable_in_fresh_html(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-30-1500.html").read_text(encoding="utf-8")
            article = self._article(page, 1)
            self.assertIn(
                'href="https://apnews.com/article/stock-markets-rates-korea-ai-oil-99b5702d93a2b5c6e513fb952ccdcc92"',
                article,
            )
            # plain (non-themed) reports keep the filter-bar and must not
            # render the news mode switch / ranked list.
            self.assertIn('class="filter-bar"', page)
            self.assertNotIn('data-component="news-mode-switch"', page)
            self.assertNotIn('data-component="ranked-list"', page)
            self.assertNotIn('data-component="themed-view"', page)

    def test_report_shell_matches_reference_structure(self):
        page = render_report(self._themed_document(), [{
            "id": "themed-report", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertIn('<div class="page-shell">', page)
        self.assertIn('<section class="report-card">', page)
        self.assertIsNotNone(
            re.search(
                r'<aside class="report-sidebar"[^>]*>.*?class="brand".*?'
                r'</aside>\s*<div class="report-workspace">',
                page,
                re.DOTALL,
            ),
            "report sidebar and workspace must remain siblings inside the report card",
        )
        self.assertNotIn('class="report-eyebrow"', page)
        self.assertNotIn('data-component="report-window"', page)
        self.assertIn('<h1>0811盘前新闻速递</h1>', page)
        self.assertNotIn("report-cutoff", page)
        self.assertNotIn('class="filter-bar"', page)

    def test_themed_cross_theme_instances_are_unique_and_source_only_has_no_toggle(self):
        page = render_report(self._themed_document(), [{
            "id": "themed-report", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        shared_rows = re.findall(
            r'(<article(?=[^>]*data-event-id="evt-shared")[^>]*>.*?</article>)', page, re.DOTALL,
        )
        self.assertEqual(2, len(shared_rows))
        instance_ids = [re.search(r'data-instance-id="([^"]+)"', row).group(1) for row in shared_rows]
        self.assertEqual(
            [
                "19xascii-themed-report-17xascii-theme-alpha-16xascii-evt-shared",
                "19xascii-themed-report-16xascii-theme-beta-16xascii-evt-shared",
            ],
            instance_ids,
        )
        self.assertEqual(
            [
                "news-19xascii-themed-report-17xascii-theme-alpha-16xascii-evt-shared",
                "news-19xascii-themed-report-16xascii-theme-beta-16xascii-evt-shared",
            ],
            [match.group(1) for row in shared_rows for match in re.finditer(r'(?<![-\w])id="([^"]+)"', row)],
        )
        normalized = [
            re.sub(r'(?<![-\w])(id|data-instance-id)="[^"]+"', r'\1="INSTANCE"', row)
            for row in shared_rows
        ]
        self.assertEqual(normalized[0], normalized[1])
        self.assertIn('data-event-id="evt-shared"', normalized[0])
        self.assertNotIn('theme-association', page)
        self.assertNotIn('news-associations', page)

        other_row = re.search(
            r'<article(?=[^>]*data-event-id="evt-other")[^>]*>.*?</article>', page, re.DOTALL,
        ).group(0)
        self.assertIn('data-detail-kind="sources-inline"', other_row)
        self.assertNotIn('class="news-toggle"', other_row)

    def test_legacy_document_keeps_flat_news_list_without_theme_containers(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="legacy", report_date="2026-08-11", slot="0800", slot_label="盘前",
                title="旧报告", window="window", cutoff="cutoff", source_name="",
            ),
            items=(NewsItem(
                rank=1, title="旧新闻", core="旧核心", score=50,
                sources=(SourceLink("官方", "", "旧新闻来源", "https://example.com/legacy"),),
            ),),
        )
        page = render_report(document, [{
            "id": "legacy", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertIn('<section data-component="news-list">', page)
        self.assertIn("旧新闻", page)
        self.assertNotIn('data-component="news-index"', page)
        self.assertNotIn('data-component="theme-group"', page)
        self.assertIn('class="filter-actions"', page)
        self.assertIn('class="filter-button is-active"', page)

    def test_renderer_rejects_ranked_items_without_a_renderable_source(self):
        for unsafe_url in ("file:///tmp/source", "ftp://example.com/source", "../relative-source"):
            with self.subTest(unsafe_url=unsafe_url):
                document = ReportDocument(
                    meta=ReportMeta(
                        report_id="unsafe-source", report_date="2026-08-11", slot="0800",
                        slot_label="盘前", title="不安全来源", window="window", cutoff="cutoff",
                        source_name="",
                    ),
                    items=(NewsItem(
                        rank=1, title="新闻", core="核心", score=50,
                        sources=(SourceLink("来源", "", "不安全", unsafe_url),),
                    ),),
                )
                with self.assertRaisesRegex(ValueError, "renderable source"):
                    render_report(document, [{
                        "id": "unsafe-source", "date": "2026-08-11", "label": "盘前",
                        "url": "reports/2026-08-11-0800.html",
                    }])

    def test_non_ascii_instance_components_remain_distinct_safe_dom_ids(self):
        alpha = _news_instance_id("报告", "题材甲", "事件")
        beta = _news_instance_id("报告", "题材乙", "事件")

        self.assertNotEqual(alpha, beta)
        self.assertRegex(alpha, r"^[a-z0-9_-]+$")
        self.assertRegex(beta, r"^[a-z0-9_-]+$")

    def test_safe_dom_id_keeps_ascii_and_utf8_encodings_disjoint(self):
        self.assertEqual("utf8-e4b8ad", _safe_dom_id("中"))
        self.assertEqual("ascii-utf8-e4b8ad", _safe_dom_id("utf8-e4b8ad"))
        self.assertEqual("ascii-Alpha", _safe_dom_id("Alpha"))
        self.assertNotEqual(_safe_dom_id("Alpha"), _safe_dom_id("alpha"))

    def test_instance_id_length_prefixes_components_to_avoid_delimiter_collisions(self):
        left = _news_instance_id("report", "a-ascii-b", "c")
        right = _news_instance_id("report", "a", "b-ascii-c")

        self.assertEqual("12xascii-report-15xascii-a-ascii-b-7xascii-c", left)
        self.assertEqual("12xascii-report-7xascii-a-15xascii-b-ascii-c", right)
        self.assertNotEqual(left, right)

    def test_pending_renderer_filters_unsafe_source_urls(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="pending-url", report_date="2026-08-11", slot="0800", slot_label="盘前",
                title="待核链接", window="window", cutoff="cutoff", source_name="",
            ),
            items=(),
            pending_items=(PendingItem(
                title="不安全线索", known="已知", reason="待核",
                sources=(SourceLink("来源", "", "不安全链接", "javascript:alert(1)"),),
            ),),
        )

        page = render_report(document, [{
            "id": "pending-url", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertIn('<details class="pending-details">', page)
        self.assertIn('<summary>待核验线索 <span>· 1</span></summary>', page)
        self.assertNotIn('<details class="pending-details" open>', page)
        self.assertIn('<div class="pending-body">', page)
        self.assertIn("不安全线索", page)
        self.assertNotIn("javascript:alert(1)", page)
        self.assertNotIn('data-component="pending-sources"', page)

    def test_app_script_keeps_source_only_associations_and_mutes_score_metadata(self):
        harness = r'''
const fs = require("fs");
const vm = require("vm");
class Node {
  constructor(tag = "div", text = "") {
    this.tag = tag; this.textContent = text; this.children = []; this.dataset = {};
    this.className = ""; this.hidden = false;
    this.classList = { values: new Set(), add: (...names) => names.forEach((name) => this.classList.values.add(name)) };
  }
  append(...nodes) { this.children.push(...nodes); }
  appendChild(node) { this.children.push(node); return node; }
  replaceChildren(...nodes) { this.children = nodes; }
  querySelector(selector) {
    if (selector === "h2") return this.heading || null;
    if (selector === ":scope > [data-component='sources']") return this.sources || null;
    if (selector === ":scope > .news-associations") return this.associations || null;
    return null;
  }
  querySelectorAll(selector) {
    if (selector === ":scope > p") return this.paragraphs || [];
    return [];
  }
}
const row = new Node("article");
row.dataset = { rank: "4", instanceId: "unique-other", detailKind: "sources-inline", category: "其他" };
row.heading = new Node("h2", "4. 来源型新闻");
const summary = new Node("p", "核心信息");
const score = new Node("p", "热点权重：60/100");
const associations = new Node("p", "题材甲");
associations.className = "news-associations";
row.paragraphs = [summary, score, associations];
row.associations = associations;
row.sources = new Node("ul", "来源链接");
const document = {
  createElement: () => new Node(),
  querySelector: (selector) => selector === ".mobile-report-select" ? null : null,
  querySelectorAll: (selector) => selector === "[data-component='news-detail']" ? [row] : [],
  getElementById: () => null,
  addEventListener: () => {},
};
const sandbox = { document, window: { location: { hash: "" }, addEventListener: () => {} }, console };
vm.runInNewContext(fs.readFileSync("web/assets/app.js", "utf8"), sandbox);
const content = row.children[1];
if (!content.children.includes(associations)) throw new Error("source-only associations were discarded");
if (content.children.some((node) => node.className === "news-toggle")) throw new Error("source-only row gained a toggle");
const scoreCell = row.children[2];
if (scoreCell.innerHTML !== '<span>热度 60</span>') {
  throw new Error(`unexpected score markup: ${scoreCell.innerHTML}`);
}
if (scoreCell.innerHTML.includes('<strong>')) {
  throw new Error('score remains visually prominent');
}
'''
        result = subprocess.run(
            ["node", "-e", harness], cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_renderer_preserves_mustache_literals_in_report_text(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="mustache", report_date="2026-08-01", slot="0800", slot_label="盘前",
                title="0810新闻速递", window="window", cutoff="cutoff", source_name="",
            ),
            items=(NewsItem(
                rank=1, title="item", core="core {{unresolved}}", score=1,
                sources=(SourceLink("source", "", "source", "https://example.com"),),
            ),),
        )
        page = render_report(document, [{
            "id": "mustache", "date": "2026-08-01", "label": "盘前",
            "url": "reports/2026-08-01-0800.html",
        }])
        self.assertIn("{{unresolved}}", page)

    def test_renderer_rejects_malformed_template_delimiters(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="template", report_date="2026-08-01", slot="0800", slot_label="盘前",
                title="title", window="window", cutoff="cutoff", source_name="",
            ),
            items=(NewsItem(
                rank=1, title="item", core="core", score=1,
                sources=(SourceLink("source", "", "source", "https://example.com"),),
            ),),
        )
        with TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "report.html"
            template_path.write_text(
                (ROOT / "web/templates/report.html").read_text(encoding="utf-8") + "{{",
                encoding="utf-8",
            )
            with patch("web.build._TEMPLATE_PATH", template_path):
                with self.assertRaises(ValueError):
                    render_report(document, [{
                        "id": "template", "date": "2026-08-01", "label": "盘前",
                        "url": "reports/2026-08-01-0800.html",
                    }])

    def test_build_creates_index_manifest_and_all_report_pages(self):
        with TemporaryDirectory() as tmp:
            result = build_site(ROOT, Path(tmp) / "dist")
            output = result.output_dir
            manifest = json.loads((output / "reports.json").read_text(encoding="utf-8"))
            self.assertEqual(20, result.report_count)
            self.assertEqual(20, len(manifest["reports"]))
            self.assertEqual("reports/2026-08-31-0800.html", manifest["latest"])
            self.assertTrue((output / manifest["latest"]).exists())
            self.assertIn(manifest["latest"], (output / "index.html").read_text(encoding="utf-8"))

    def test_checked_in_dist_is_byte_identical_to_a_fresh_build(self):
        with TemporaryDirectory() as tmp:
            fresh = build_site(
                ROOT, Path(tmp) / "dist", daily_info_root=DAILY_INFO_ROOT
            ).output_dir
            checked = ROOT / "web/dist"
            # fusion.html depends on the external daily_info project's latest
            # output, so it is excluded here and covered by test_fusion_build.
            fresh_files = {
                path.relative_to(fresh): path.read_bytes()
                for path in fresh.rglob("*") if path.is_file()
                if path.relative_to(fresh).as_posix() != "fusion.html"
            }
            checked_files = {
                path.relative_to(checked): path.read_bytes()
                for path in checked.rglob("*") if path.is_file()
                if path.relative_to(checked).as_posix() != "fusion.html"
            }
            self.assertEqual(fresh_files, checked_files)

    def test_report_page_has_fixed_semantic_contract(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            for marker in (
                'data-component="report-archive"',
                'data-component="news-list"',
                'data-component="news-detail"',
                'data-component="sources"',
            ):
                self.assertIn(marker, page)
            self.assertIn("宇树科技8月5日初步询价、8月10日申购", page)
            self.assertNotIn("/Users/", page)

    def test_aug11_page_renders_pending_verification_appendix(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-08-11-0800.html").read_text(encoding="utf-8")
            self.assertIn('data-component="pending-list"', page)
            self.assertIn('<details class="pending-details">', page)
            self.assertIn('<summary>待核验线索 <span>· 5</span></summary>', page)
            self.assertNotIn('<details class="pending-details" open>', page)
            self.assertIn('<div class="pending-body">', page)
            for title in (
                "韩国半导体投资覆盖材料、零部件与设备",
                "马斯克与自由电子激光EUV光源",
                "英伟达拟向Lancium投资最高30亿美元",
                "天津机器人会议",
            ):
                self.assertIn(title, page)

    def test_checked_in_aug11_artifact_keeps_themed_news_contract(self):
        """Catch a stale dist page that drops Aug. 11's themed report behavior."""
        page = (ROOT / "web/dist/reports/2026-08-11-0800.html").read_text(encoding="utf-8")

        self.assertEqual(
            [
                ("AI算力 / 半导体 / 存储芯片", "420"),
                ("中东局势 / 油气", "184"),
                ("低空经济 / 航空AI", "166"),
                ("A股回购 / 资本运作", "165"),
                ("人形机器人 / 具身智能", "161"),
            ],
            re.findall(
                r'<div class="theme-heading-line"><h2>([^<]+)</h2>'
                r'<p class="theme-total">\d+条 · (\d+)</p>',
                page,
            ),
        )
        self.assertNotIn('data-component="news-index"', page)
        self.assertNotIn("单条新闻热榜索引", page)
        self.assertNotIn("接下来的方向", page)
        self.assertEqual(5, page.count('data-component="theme-group"'))
        self.assertEqual(
            ["01", "02", "03", "04", "05"],
            re.findall(r'<p class="theme-kicker">核心方向 (\d{2})</p>', page),
        )
        self.assertLess(page.index("核心方向 05"), page.index('id="other-important-news"'))
        self.assertLess(page.index("其他重要新闻"), page.index("待核验线索"))
        self.assertIn('<summary>待核验线索 <span>· 5</span></summary>', page)
        self.assertNotIn('<details class="pending-details" open>', page)

        event_ids = re.findall(r'data-event-id="([^"]+)"', page)
        instance_ids = re.findall(r'data-instance-id="([^"]+)"', page)
        self.assertEqual(24, len(set(event_ids)))
        self.assertEqual(len(instance_ids), len(set(instance_ids)))
        self.assertIn('data-component="other-important-news"', page)
        self.assertGreaterEqual(page.count('data-component="news-detail"'), 25)
        for marker in ("发布时段", "关键信号/预期差", "市场反馈", "判断边界", "热度变化"):
            self.assertIn(marker, page)
        self.assertEqual(25, page.count("<strong>发布时段</strong>"))
        self.assertNotIn("report-window", page)
        self.assertNotIn("report-cutoff", page)
        self.assertNotIn('class="filter-actions"', page)
        self.assertNotIn('data-event-id="evt-20260811-011"', page)
        self.assertIn(
            'href="https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2026081018132329141/index.html"',
            page,
        )
        self.assertIn(
            'href="https://nvidianews.nvidia.com/news/nvidia-partners-with-apollo-blackrock-blackstone-brookfield-goldman-sachs-and-kkr-to-establish-ai-compute-infrastructure-financing-platforms-to-mobilize-over-500-billion-of-third-party-capital"',
            page,
        )

        pending = re.search(
            r'<section class="pending-section"[^>]*data-component="pending-list"[^>]*>.*?</details></section>',
            page,
            re.DOTALL,
        )
        self.assertIsNotNone(pending)
        pending_html = pending.group(0)
        self.assertEqual(5, pending_html.count('class="pending-item"'))
        self.assertIn("豆包回应推荐酒店抽取12%佣金争议", pending_html)
        self.assertNotIn("热点权重", pending_html)
        self.assertNotIn("/100", pending_html)
        self.assertNotIn("分 ·", pending_html)

        manifest = json.loads((ROOT / "web/dist/reports.json").read_text(encoding="utf-8"))
        self.assertEqual("reports/2026-08-31-0800.html", manifest["latest"])
        self.assertIn('href="2026-08-11-0800.html"', page)
        self.assertIn(manifest["latest"], (ROOT / "web/dist/index.html").read_text(encoding="utf-8"))

    def test_report_archive_links_resolve_from_report_directory(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            self.assertIn('href="2026-07-31-0800.html"', page)
            self.assertNotIn('href="reports/2026-07-31-0800.html"', page)

    def test_archive_groups_dates_and_targets_latest_real_report(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="2026-08-10-0800", report_date="2026-08-10", slot="0800",
                slot_label="盘前", title="title", window="window", cutoff="cutoff",
                source_name="",
            ),
            items=(),
        )

        page = render_report(document, [
            {
                "id": "2026-07-30-1800", "date": "2026-07-30", "slot": "1800",
                "label": "收盘", "url": "reports/2026-07-30-1800.html",
            },
            {
                "id": "2026-08-10-0800", "date": "2026-08-10", "slot": "0800",
                "label": "盘前", "url": "reports/2026-08-10-0800.html",
            },
            {
                "id": "2026-07-30-0800", "date": "2026-07-30", "slot": "0800",
                "label": "盘前", "url": "reports/2026-07-30-0800.html",
            },
        ])

        self.assertLess(page.index("2026-08-10"), page.index("2026-07-30"))
        self.assertEqual(1, page.count('data-report-date="2026-07-30"'))
        self.assertIn('href="2026-07-30-1800.html"', page)
        self.assertLess(page.index(">盘前</a>"), page.index(">盘后</a>"))
        self.assertNotIn(">盘中</a>", page)
        self.assertIn('data-report-label="2026-07-30 · 盘后"', page)

    def test_page_has_accessible_interaction_contract(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            self.assertIn('class="news-toggle"', page)
            self.assertIn('aria-expanded="false"', page)
            self.assertIn('class="mobile-report-select"', page)
            self.assertIn('class="filter-button is-active"', page)
            self.assertIn('data-category=', page)
            self.assertIn('class="archive-date-link"', page)
            self.assertIn('aria-expanded="false"', page)
            self.assertIn('class="archive-slots"', page)
            self.assertIn('data-report-link', page)
            self.assertNotIn('<p class="sidebar-label">报告归档</p>', page)
            self.assertIn(
                '<div class="archive-date-group" id="archive-2026-07-31" '
                'data-report-date="2026-07-31"><a class="archive-date-link" '
                'aria-expanded="false" aria-controls="archive-slots-2026-07-31"',
                page,
            )
            self.assertIn(
                '<div class="archive-slots" id="archive-slots-2026-07-31" hidden>',
                page,
            )

    def test_renderer_distinguishes_source_only_rows_from_analysis_details(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="detail-kinds", report_date="2026-08-10", slot="0800",
                slot_label="盘前", title="title", window="window", cutoff="cutoff",
                source_name="",
            ),
            items=(
                NewsItem(
                    rank=1, title="source only", core="core", score=70,
                    sources=(SourceLink("原始来源", "", "来源页面", "https://example.com/1"),),
                ),
                NewsItem(
                    rank=2, title="analysis", core="core", score=60,
                    signal="signal",
                    sources=(SourceLink("官方", "", "来源页面", "https://example.com/2"),),
                ),
            ),
        )

        page = render_report(document, [{
            "id": "detail-kinds", "date": "2026-08-10", "label": "盘前",
            "url": "reports/2026-08-10-0800.html",
        }])

        self.assertIn(
            'data-rank="1" data-category="其他" data-detail-kind="sources-inline"',
            page,
        )
        self.assertIn('data-rank="2" data-category="其他" data-detail-kind="analysis"', page)

    def test_fresh_build_keeps_empty_data_favicon(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            pages = (
                (output / "index.html").read_text(encoding="utf-8"),
                (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8"),
            )
            for page in pages:
                with self.subTest(page=page[:40]):
                    self.assertIn('<link rel="icon" href="data:,">', page)
                    self.assertNotIn('href="/favicon.ico"', page)

    def test_fresh_build_omits_cutoff_and_embeds_calendar_filter(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            for page_path in (output / "reports").glob("*.html"):
                with self.subTest(page=page_path.name):
                    page = page_path.read_text(encoding="utf-8")
                    self.assertNotIn("report-cutoff", page)
                    self.assertIn('id="calendar-filter"', page)
                    self.assertIn('id="calendar-dates"', page)
                    self.assertIn("assets/calendar.js", page)

    def test_report_window_is_no_longer_rendered_on_any_page(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            for page_path in (output / "reports").glob("*.html"):
                with self.subTest(page=page_path.name):
                    page = page_path.read_text(encoding="utf-8")
                    self.assertEqual(0, page.count('data-component="report-window"'))
                    self.assertNotIn("报告窗口 ·", page)

    def test_report_window_escapes_special_characters_once(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="window-escape", report_date="2026-08-01", slot="0800",
                slot_label="盘前", title="window", window='<窗口 & "测试">',
                cutoff="", source_name="",
            ),
            items=(),
        )

        page = render_report(document, [{
            "id": "window-escape", "date": "2026-08-01", "label": "盘前",
            "url": "reports/2026-08-01-0800.html",
        }])

        self.assertEqual(0, page.count('data-component="report-window"'))
        self.assertNotIn('报告窗口 ·', page)
        self.assertNotIn('<窗口 & "测试">', page)

    def test_july29_markdown_news_fields_reach_fresh_html_in_source_order(self):
        source = (ROOT / "reports/2026-07-29-pure-news-hot-ranking-v4.md").read_text(
            encoding="utf-8"
        )
        headings = list(re.finditer(r"^## (\d+)\. .+$", source, re.MULTILINE))
        self.assertEqual(35, len(headings))
        expected_labels = (
            "时间",
            "监控区间",
            "热度变化",
            "变化判定",
            "传播路径",
            "当前原始热度",
            "可靠性",
            "尚未确认",
            "可选A股附注",
        )

        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-29-1800.html").read_text(encoding="utf-8")
            for index, heading in enumerate(headings):
                end_match = re.search(r"^## ", source[heading.end():], re.MULTILINE)
                end = heading.end() + end_match.start() if end_match else len(source)
                block = source[heading.end():end]
                rank = int(heading.group(1))
                article = self._article(page, rank)
                summary = re.search(
                    r"^- \*\*消息详情：\*\* (.+)$", block, re.MULTILINE
                ).group(1)
                self.assertIn("<p>{}</p>".format(escape(summary, quote=True)), article)

                positions = []
                for label in expected_labels:
                    value = re.search(
                        r"^- \*\*{}：\*\* (.+)$".format(re.escape(label)),
                        block,
                        re.MULTILINE,
                    ).group(1)
                    rendered = "<p><strong>{}</strong>{}</p>".format(
                        label, escape(value, quote=True)
                    )
                    self.assertEqual(1, article.count(rendered))
                    positions.append(article.index(rendered))
                self.assertEqual(sorted(positions), positions)

    def test_every_markdown_score_breakdown_reaches_fresh_html_exactly_once(self):
        expected = []
        for source_path, _entry in discover_reports(ROOT):
            source = source_path.read_text(encoding="utf-8")
            report_match = re.match(r"(\d{4}-\d{2}-\d{2})-(.*)", source_path.name)
            slot = {
                "2026-07-29": "1800",
                "2026-07-30": "1500" if "1500" in source_path.name else "0800",
            }.get(report_match.group(1), "0800")
            output_name = "{}-{}.html".format(report_match.group(1), slot)
            headings = list(re.finditer(r"^## (\d+)\. .+$", source, re.MULTILINE))
            for heading in headings:
                next_heading = re.search(r"^## ", source[heading.end():], re.MULTILINE)
                end = heading.end() + next_heading.start() if next_heading else len(source)
                score = re.search(
                    r"\*\*热点权重：\d+/100\*\*（([^）]+)）",
                    source[heading.end():end],
                )
                if score:
                    expected.append((output_name, int(heading.group(1)), score.group(1)))
        self.assertEqual(85, len(expected))

        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            pages = {}
            for filename, rank, breakdown in expected:
                page = pages.setdefault(
                    filename,
                    (output / "reports" / filename).read_text(encoding="utf-8"),
                )
                article = self._article(page, rank)
                rendered = "<p><strong>热点构成</strong>{}</p>".format(
                    escape(breakdown, quote=True)
                )
                self.assertEqual(1, article.count(rendered))

    def test_every_legacy_markdown_status_reaches_fresh_html_exactly_once(self):
        expected = []
        for source_path, _entry in discover_reports(ROOT):
            source = source_path.read_text(encoding="utf-8")
            date = re.match(r"(\d{4}-\d{2}-\d{2})-", source_path.name).group(1)
            slot = "1500" if "1500" in source_path.name else "1800" if date == "2026-07-29" else "0800"
            filename = "{}-{}.html".format(date, slot)
            headings = list(re.finditer(r"^## (\d+)\. .+$", source, re.MULTILINE))
            for heading in headings:
                next_heading = re.search(r"^## ", source[heading.end():], re.MULTILINE)
                end = heading.end() + next_heading.start() if next_heading else len(source)
                status = re.search(
                    r"[|｜]\*\*状态：([^*]+)\*\*", source[heading.end():end]
                )
                if status:
                    expected.append((filename, int(heading.group(1)), status.group(1)))
        self.assertEqual(55, len(expected))

        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            pages = {}
            for filename, rank, status in expected:
                page = pages.setdefault(
                    filename,
                    (output / "reports" / filename).read_text(encoding="utf-8"),
                )
                article = self._article(page, rank)
                rendered = "<p><strong>状态</strong>{}</p>".format(
                    escape(status, quote=True)
                )
                self.assertEqual(1, article.count(rendered))

    def test_score_breakdown_is_auxiliary_escaped_and_omitted_when_empty(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="breakdown", report_date="2026-08-01", slot="0800",
                slot_label="盘前", title="breakdown", window="", cutoff="", source_name="",
            ),
            items=(
                NewsItem(
                    rank=1, title="有分项", core="核心", score=80,
                    score_breakdown='<覆盖20 & 变化"30">',
                    sources=(SourceLink("官方", "", "来源", "https://example.com/one"),),
                ),
                NewsItem(
                    rank=2, title="无分项", core="核心", score=70, score_breakdown="",
                    sources=(SourceLink("官方", "", "来源", "https://example.com/two"),),
                ),
            ),
        )

        page = render_report(document, [{
            "id": "breakdown", "date": "2026-08-01", "label": "盘前",
            "url": "reports/2026-08-01-0800.html",
        }])

        first = self._article(page, 1)
        second = self._article(page, 2)
        self.assertEqual(
            1,
            first.count(
                "<p><strong>热点构成</strong>&lt;覆盖20 &amp; 变化&quot;30&quot;&gt;</p>"
            ),
        )
        self.assertNotIn("热点构成", second)
        self.assertLess(first.index("热点权重：80/100"), first.index("热点构成"))

    def test_rendered_rows_keep_title_and_core_categories_for_filtering(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            latest = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            premarket = (output / "reports/2026-07-30-0800.html").read_text(encoding="utf-8")

            energy = self._article(latest, 8)
            middle_east = self._article(premarket, 3)

            self.assertIn('data-category="产业"', energy)
            self.assertIn("设备企业收入", energy)
            self.assertIn('data-category="地缘"', middle_east)
            self.assertIn("中东冲突", middle_east)

    def test_compact_rows_ignore_markdown_urls_when_classifying(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            postclose = (output / "reports/2026-07-30-1500.html").read_text(encoding="utf-8")

            for rank in (11, 13, 16):
                article = self._article(postclose, rank)
                self.assertIn('data-category="其他"', article)
                self.assertIn("https://www.cls.cn/detail/", article)

    def test_rendered_sources_follow_core_before_analysis_details(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            microsoft = self._article(page, 2)

            self.assertLess(
                microsoft.index("微软FY26第四财季Azure收入增长43%"),
                microsoft.index('data-component="sources"'),
            )
            self.assertLess(
                microsoft.index('data-component="sources"'),
                microsoft.index("关键信号/预期差"),
            )

    def test_build_rejects_report_paths_that_escape_next_output(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="bad", report_date="../../outside", slot="0800", slot_label="盘前",
                title="bad", window="", cutoff="", source_name="",
            ),
            items=(NewsItem(
                rank=1, title="item", core="core", score=1,
                sources=(SourceLink("source", "", "source", "https://example.com"),),
            ),),
        )
        with TemporaryDirectory() as tmp:
            temporary_root = Path(tmp)
            escaped_path = temporary_root / "outside-0800.html"
            with patch("web.build.discover_reports", return_value=[(Path("unused"), object())]), patch(
                "web.build.parse_report", return_value=document
            ):
                with self.assertRaises(ValueError):
                    build_site(ROOT, temporary_root / "dist")
            self.assertFalse(escaped_path.exists())

    def test_cleanup_failure_after_swap_does_not_report_build_failure(self):
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "dist"
            build_site(ROOT, target)
            real_rmtree = __import__("shutil").rmtree

            def reject_previous(path, *args, **kwargs):
                if ".previous-" in str(path):
                    raise OSError("simulated cleanup error")
                return real_rmtree(path, *args, **kwargs)

            with patch("web.build.shutil.rmtree", side_effect=reject_previous):
                result = build_site(ROOT, target)
            self.assertEqual(target.resolve(), result.output_dir)

    def test_unsafe_generated_content_preserves_existing_output(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="unsafe", report_date="2026-08-01", slot="0800", slot_label="盘前",
                title="/Users/aviva/private", window="window", cutoff="cutoff", source_name="",
            ),
            items=(NewsItem(
                rank=1, title="item", core="core", score=1,
                sources=(SourceLink("source", "", "source", "https://example.com"),),
            ),),
        )
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "dist"
            build_site(ROOT, target)
            before = {
                path.relative_to(target): path.read_bytes()
                for path in target.rglob("*") if path.is_file()
            }

            with patch("web.build.discover_reports", return_value=[(Path("unused"), object())]), patch(
                "web.build.parse_report", return_value=document
            ):
                with self.assertRaises(PublicTreeUnsafe):
                    build_site(ROOT, target)

            after = {
                path.relative_to(target): path.read_bytes()
                for path in target.rglob("*") if path.is_file()
            }
            self.assertEqual(before, after)
