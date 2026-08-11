import json
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
    ReportDocument,
    ReportMeta,
    SourceLink,
    StockMapping,
    ThemeGroup,
)
from web.security import PublicTreeUnsafe


ROOT = Path(__file__).resolve().parents[1]


class WebBuildTest(unittest.TestCase):
    def _themed_document(self) -> ReportDocument:
        shared = NewsItem(
            rank=1, event_id="evt-shared", title="共享新闻", core="共享核心", score=90,
            market_feedback="共享反馈", boundary="共享边界", heat_change="共享热度",
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

    def test_themed_document_renders_index_groups_and_complete_other_news(self):
        page = render_report(self._themed_document(), [{
            "id": "themed-report", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertIn('data-component="news-index"', page)
        self.assertIn('href="#news-ascii-themed-report-ascii-theme-alpha-ascii-evt-shared"', page)
        self.assertIn("1. 共享新闻", page)
        self.assertIn("90/100", page)
        self.assertIn("theme-alpha", page)
        self.assertIn("theme-beta", page)
        self.assertLess(page.index("甲题材"), page.index("乙题材"))
        self.assertIn('data-component="theme-group" id="theme-ascii-theme-alpha"', page)
        self.assertIn("170分 · 关联新闻2条", page)
        self.assertIn("甲的共同催化", page)
        self.assertIn("甲公司（000001）：公告确认", page)
        self.assertIn("乙公司（000002）：未确认新增订单", page)
        self.assertIn("甲风险", page)
        self.assertIn("共享反馈", page)
        self.assertIn("共享边界", page)
        self.assertIn("08-11 08:00", page)
        self.assertIn('href="https://example.com/shared"', page)
        self.assertIn('data-component="other-important-news"', page)
        self.assertIn("其他新闻", page)
        self.assertIn("08-11 08:03", page)
        self.assertIn('href="https://example.com/other"', page)
        self.assertIn("跨题材新闻会在各关联题材中重复计分", page)

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
                "ascii-themed-report-ascii-theme-alpha-ascii-evt-shared",
                "ascii-themed-report-ascii-theme-beta-ascii-evt-shared",
            ],
            instance_ids,
        )
        self.assertEqual(
            [
                "news-ascii-themed-report-ascii-theme-alpha-ascii-evt-shared",
                "news-ascii-themed-report-ascii-theme-beta-ascii-evt-shared",
            ],
            [match.group(1) for row in shared_rows for match in re.finditer(r'(?<![-\w])id="([^"]+)"', row)],
        )
        normalized = [
            re.sub(r'(id|data-instance-id)="[^"]+"', r'\1="INSTANCE"', row)
            for row in shared_rows
        ]
        self.assertEqual(normalized[0], normalized[1])

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
            items=(NewsItem(rank=1, title="旧新闻", core="旧核心", score=50),),
        )
        page = render_report(document, [{
            "id": "legacy", "date": "2026-08-11", "label": "盘前",
            "url": "reports/2026-08-11-0800.html",
        }])

        self.assertIn('<section data-component="news-list">', page)
        self.assertIn("旧新闻", page)
        self.assertNotIn('data-component="news-index"', page)
        self.assertNotIn('data-component="theme-group"', page)

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

        self.assertIn("不安全线索", page)
        self.assertNotIn("javascript:alert(1)", page)
        self.assertNotIn('data-component="pending-sources"', page)

    def test_source_only_row_keeps_associations_when_app_script_enhances_dom(self):
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
'''
        result = subprocess.run(
            ["node", "-e", harness], cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_renderer_preserves_mustache_literals_in_report_text(self):
        document = ReportDocument(
            meta=ReportMeta(
                report_id="mustache", report_date="2026-08-01", slot="0800", slot_label="盘前",
                title="{{unresolved}}", window="window", cutoff="cutoff", source_name="",
            ),
            items=(NewsItem(
                rank=1, title="item", core="core", score=1,
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
            self.assertEqual(7, result.report_count)
            self.assertEqual(7, len(manifest["reports"]))
            self.assertEqual("reports/2026-08-11-0800.html", manifest["latest"])
            self.assertTrue((output / manifest["latest"]).exists())
            self.assertIn(manifest["latest"], (output / "index.html").read_text(encoding="utf-8"))

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
            self.assertIn("待核验线索", page)
            for title in (
                "韩国半导体投资覆盖材料、零部件与设备",
                "马斯克与自由电子激光EUV光源",
                "英伟达拟向Lancium投资最高30亿美元",
                "天津机器人会议",
            ):
                self.assertIn(title, page)

    def test_report_archive_links_resolve_from_report_directory(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            self.assertIn('href="2026-07-31-0800.html#archive-2026-07-31"', page)
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
        self.assertIn('href="2026-07-30-1800.html#archive-2026-07-30"', page)
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

    def test_fresh_build_renders_explicit_legacy_beijing_metadata(self):
        expected = {
            "2026-07-29-1800.html": (
                "<p>2026-07-29 · 收盘</p>",
                '<div class="filter-meta"><span>数据截止</span><span>2026-07-29 18:08（北京时间）</span></div>',
            ),
            "2026-07-30-0800.html": (
                "2026-07-29 00:00—2026-07-30 10:00（北京时间）",
                '<div class="filter-meta"><span>数据截止</span><span>10:00（北京时间）</span></div>',
            ),
            "2026-07-30-1500.html": (
                "2026-07-30 00:00—15:00（北京时间）",
                '<div class="filter-meta"><span>数据截止</span><span>15:00（北京时间）</span></div>',
            ),
        }
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            for filename, visible_values in expected.items():
                with self.subTest(filename=filename):
                    page = (output / "reports" / filename).read_text(encoding="utf-8")
                    for visible_value in visible_values:
                        self.assertIn(visible_value, page)

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
