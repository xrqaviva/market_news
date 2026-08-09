import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from web.build import build_site, render_report
from web.report_model import NewsItem, ReportDocument, ReportMeta, SourceLink
from web.security import PublicTreeUnsafe


ROOT = Path(__file__).resolve().parents[1]


class WebBuildTest(unittest.TestCase):
    def _article(self, page: str, rank: int) -> str:
        match = re.search(
            r'<article data-component="news-detail" data-rank="{}".*?</article>'.format(rank),
            page,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "missing rendered news row for rank {}".format(rank))
        return match.group(0)

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
            for marker in (
                'data-component="report-archive"',
                'data-component="news-list"',
                'data-component="news-detail"',
                'data-component="sources"',
            ):
                self.assertIn(marker, page)
            self.assertIn("宇树科技8月5日初步询价、8月10日申购", page)
            self.assertNotIn("/Users/", page)

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
