import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from web.build import build_site, render_report
from web.report_model import NewsItem, ReportDocument, ReportMeta, SourceLink


ROOT = Path(__file__).resolve().parents[1]


class WebBuildTest(unittest.TestCase):
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
            self.assertIn('href="2026-07-31-0800.html"', page)
            self.assertNotIn('href="reports/2026-07-31-0800.html"', page)

    def test_page_has_accessible_interaction_contract(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            self.assertIn('class="news-toggle"', page)
            self.assertIn('aria-expanded="false"', page)
            self.assertIn('class="mobile-report-select"', page)
            self.assertIn('class="filter-button is-active"', page)
            self.assertIn('data-category=', page)

    def test_page_uses_embedded_icon_without_local_asset_request(self):
        with TemporaryDirectory() as tmp:
            output = build_site(ROOT, Path(tmp) / "dist").output_dir
            page = (output / "reports/2026-07-31-0800.html").read_text(encoding="utf-8")
            self.assertIn('<link rel="icon" href="data:,">', page)

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
