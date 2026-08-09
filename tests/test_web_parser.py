from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from web.report_parser import CatalogEntry, discover_reports, parse_report


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

    def test_standard_report_keeps_explicit_window_and_actual_cutoff(self):
        with TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "2026-08-10-0800-premarket.md"
            report_path.write_text(
                "# 2026-08-10 A股盘前新闻热榜\n\n"
                "> **新闻窗口：** 2026-08-07 00:00—2026-08-09 19:44:27（北京时间）\n"
                "> **实际截点：** 2026-08-09 19:44:27。本稿为提前版。\n\n"
                "## 1. 示例新闻\n\n"
                "**核心信息：** 示例核心信息。\n\n"
                "**热点权重：80/100**（覆盖20 + 变化20 + 绝对热度15 + 新鲜度15 + 频次10）\n\n"
                "**财报市场反馈：** 周末发布，下一可交易时段尚未出现。\n\n"
                "| 传播渠道 | 北京时间 | 消息或热度 |\n"
                "|---|---:|---|\n"
                "| 官方 | 08-09 19:00 | [具体页面](https://example.com/post) |\n",
                encoding="utf-8",
            )
            entry = CatalogEntry(
                report_id="20260810-0800",
                path=report_path.name,
                report_date="2026-08-10",
                slot="0800",
                label="盘前",
            )

            document = parse_report(report_path, entry)

            self.assertEqual(
                "2026-08-07 00:00—2026-08-09 19:44:27（北京时间）",
                document.meta.window,
            )
            self.assertEqual("2026-08-09 19:44:27", document.meta.cutoff)
            self.assertEqual(
                "周末发布，下一可交易时段尚未出现。",
                document.items[0].market_feedback,
            )

    def test_compact_core_excludes_source_labels_and_keeps_descriptive_source(self):
        with TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "2026-08-10-0800-compact.md"
            report_path.write_text(
                "# 紧凑条目测试\n\n"
                "11. **示例新闻｜70/100**：事实说明。"
                "[财联社周末要闻汇总：示例主题](https://www.cls.cn/detail/1)\n",
                encoding="utf-8",
            )
            entry = CatalogEntry(
                report_id="20260810-0800",
                path=report_path.name,
                report_date="2026-08-10",
                slot="0800",
                label="盘前",
            )

            item = parse_report(report_path, entry).items[0]

            self.assertEqual("事实说明。", item.core)
            self.assertEqual("财联社周末要闻汇总：示例主题", item.sources[0].label)
            self.assertEqual("原始来源", item.sources[0].channel)
