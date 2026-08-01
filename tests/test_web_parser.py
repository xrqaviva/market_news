from pathlib import Path
import unittest

from web.report_parser import discover_reports, parse_report


ROOT = Path(__file__).resolve().parents[1]


class WebReportParserTest(unittest.TestCase):
    def _documents(self):
        return {
            entry.report_id: parse_report(path, entry)
            for path, entry in discover_reports(ROOT)
        }

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

    def test_selected_headlines_use_exact_event_titles(self):
        documents = self._documents()
        expected = {
            ("20260729-1800", 1): "多家MLCC厂商发布涨价函",
            ("20260729-1800", 13): "游戏版号与Kimi算力容量引发讨论",
            ("20260730-0800", 9): "锂库存帖子称单周去库约七千吨",
            ("20260730-1500", 10): "锂库存帖子称单周去库约七千吨",
        }
        for (report_id, rank), title in expected.items():
            with self.subTest(report_id=report_id, rank=rank):
                item = next(item for item in documents[report_id].items if item.rank == rank)
                self.assertEqual(title, item.title)

    def test_headlines_exclude_heat_method_terms(self):
        for document in self._documents().values():
            for item in document.items:
                with self.subTest(report_id=document.meta.report_id, rank=item.rank):
                    self.assertNotRegex(item.title, r"双时点|激增|新出现|热度变化")

    def test_legacy_reports_parse_only_explicit_beijing_metadata(self):
        documents = self._documents()
        expected = {
            "20260729-1800": ("", "2026-07-29 18:08（北京时间）"),
            "20260730-0800": (
                "2026-07-29 00:00—2026-07-30 10:00（北京时间）",
                "10:00（北京时间）",
            ),
            "20260730-1500": (
                "2026-07-30 00:00—15:00（北京时间）",
                "15:00（北京时间）",
            ),
            "20260731-0800": (
                "2026-07-30 00:00—2026-07-31 08:29（北京时间）",
                "08:19:40",
            ),
        }
        for report_id, (window, cutoff) in expected.items():
            with self.subTest(report_id=report_id):
                self.assertEqual(window, documents[report_id].meta.window)
                self.assertEqual(cutoff, documents[report_id].meta.cutoff)
