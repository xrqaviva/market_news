from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from web.report_model import NewsIndexEntry, StockMapping, ThemeGroup
from web.report_parser import CatalogEntry, discover_reports, parse_report


ROOT = Path(__file__).resolve().parents[1]


class WebReportParserTest(unittest.TestCase):
    def _documents(self):
        return {
            entry.report_id: parse_report(path, entry)
            for path, entry in discover_reports(ROOT)
        }

    def _themed_report(self):
        return (
            "# 题材解析测试\n\n"
            "> **新闻窗口：** 2026-08-11 00:00—08:30（北京时间）\n"
            "> **实际截点：** 2026-08-11 08:30。\n\n"
            "## 单条新闻热榜索引\n\n"
            "| 原排名 | 事件ID | 新闻标题 | 热点分 | 关联题材 | 跳转锚点 |\n"
            "|---:|---|---|---:|---|---|\n"
            "| 1 | evt-1 | 共享新闻 | 90 | theme-alpha、theme-beta | #evt-1 |\n"
            "| 2 | evt-2 | 甲题材新闻 | 80 | theme-alpha | #evt-2 |\n"
            "| 3 | evt-3 | 乙题材新闻 | 70 | theme-beta | #evt-3 |\n"
            "| 4 | evt-4 | 其他新闻 | 60 | - | #evt-4 |\n\n"
            "## 题材主线\n\n"
            "### 主线1：甲题材｜170分｜关联新闻2条\n\n"
            "**题材ID：** theme-alpha\n\n"
            "**核心催化：** 甲的共同催化。\n\n"
            "**直接映射：**\n\n"
            "- 甲公司（000001）：公告确认\n\n"
            "**板块代表：**\n\n"
            "- 乙公司（000002）：本轮新闻未确认新增订单或直接受益\n\n"
            "**题材风险边界：** 甲风险。\n\n"
            "#### 新闻：1｜evt-1｜共享新闻｜90/100\n\n"
            "**核心信息：** 共享核心。\n\n"
            "| 传播渠道 | 北京时间 | 消息或热度 |\n"
            "|---|---:|---|\n"
            "| 官方 | 08-11 08:00 | [共享直链](https://example.com/shared) |\n\n"
            "**带时间市场反馈：** 共享反馈。\n\n"
            "**判断边界：** 共享边界。\n\n"
            "**热度变化：** 共享热度。\n\n"
            "**发布时段：** 美国市场盘后发布。\n\n"
            "**关联题材：** theme-alpha、theme-beta（跨题材重复计分）\n\n"
            "#### 新闻：2｜evt-2｜甲题材新闻｜80/100\n\n"
            "**核心信息：** 甲核心。\n\n"
            "| 传播渠道 | 北京时间 | 消息或热度 |\n"
            "|---|---:|---|\n"
            "| 官方 | 08-11 08:01 | [甲直链](https://example.com/alpha) |\n\n"
            "**关联题材：** theme-alpha\n\n"
            "### 主线2：乙题材｜160分｜关联新闻2条\n\n"
            "**题材ID：** theme-beta\n\n"
            "**核心催化：** 乙的共同催化。\n\n"
            "**题材风险边界：** 乙风险。\n\n"
            "#### 新闻：1｜evt-1｜共享新闻｜90/100\n\n"
            "**核心信息：** 共享核心。\n\n"
            "| 传播渠道 | 北京时间 | 消息或热度 |\n"
            "|---|---:|---|\n"
            "| 官方 | 08-11 08:00 | [共享直链](https://example.com/shared) |\n\n"
            "**带时间市场反馈：** 共享反馈。\n\n"
            "**判断边界：** 共享边界。\n\n"
            "**热度变化：** 共享热度。\n\n"
            "**发布时段：** 美国市场盘后发布。\n\n"
            "**关联题材：** theme-alpha、theme-beta（跨题材重复计分）\n\n"
            "#### 新闻：3｜evt-3｜乙题材新闻｜70/100\n\n"
            "**核心信息：** 乙核心。\n\n"
            "| 传播渠道 | 北京时间 | 消息或热度 |\n"
            "|---|---:|---|\n"
            "| 官方 | 08-11 08:02 | [乙直链](https://example.com/beta) |\n\n"
            "**关联题材：** theme-beta\n\n"
            "## 其他重要新闻\n\n"
            "#### 新闻：4｜evt-4｜其他新闻｜60/100\n\n"
            "**核心信息：** 其他核心。\n\n"
            "| 传播渠道 | 北京时间 | 消息或热度 |\n"
            "|---|---:|---|\n"
            "| 官方 | 08-11 08:03 | [其他直链](https://example.com/other) |\n\n"
            "## 待核验线索\n\n"
            "### 待核线索\n\n"
            "**已知事实：** 待核事实。\n\n"
            "**待核原因：** 待核原因。\n\n"
            "[待核直链](https://example.com/pending)\n"
        )

    def _parse_themed_report(self, text=None):
        with TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "2026-08-11-0800-themed.md"
            report_path.write_text(text or self._themed_report(), encoding="utf-8")
            entry = CatalogEntry(
                report_id="20260811-0800", path=report_path.name,
                report_date="2026-08-11", slot="0800", label="盘前",
            )
            return parse_report(report_path, entry)

    def test_themed_report_parses_immutable_model_and_preserves_news_detail(self):
        document = self._parse_themed_report()

        self.assertIsInstance(document.news_index[0], NewsIndexEntry)
        self.assertIsInstance(document.themes[0], ThemeGroup)
        self.assertIsInstance(document.themes[0].direct_mappings[0], StockMapping)
        with self.assertRaises(AttributeError):
            document.themes[0].name = "变化"
        with self.assertRaises(AttributeError):
            document.themes[0].direct_mappings[0].name = "变化"

        self.assertEqual(["evt-1", "evt-2", "evt-3", "evt-4"], [entry.event_id for entry in document.news_index])
        self.assertEqual(("theme-alpha", "theme-beta"), document.news_index[0].theme_ids)
        self.assertEqual(["theme-alpha", "theme-beta"], [theme.theme_id for theme in document.themes])
        self.assertEqual([170, 160], [theme.total_score for theme in document.themes])
        self.assertEqual(("evt-1", "evt-2"), document.themes[0].event_ids)
        self.assertEqual("000001", document.themes[0].direct_mappings[0].ticker)
        self.assertEqual("公告确认", document.themes[0].direct_mappings[0].evidence)
        self.assertEqual(["evt-4"], [item.event_id for item in document.other_items])
        self.assertEqual(["evt-1", "evt-2", "evt-3", "evt-4"], [item.event_id for item in document.items])

        shared = document.themes[0].items[0]
        self.assertEqual("https://example.com/shared", shared.sources[0].url)
        self.assertEqual("08-11 08:00", shared.sources[0].time_bj)
        self.assertEqual("共享反馈。", shared.market_feedback)
        self.assertEqual("共享边界。", shared.boundary)
        self.assertEqual("共享热度。", shared.heat_change)
        self.assertEqual("美国市场盘后发布。", shared.release_session)
        self.assertEqual(("theme-alpha", "theme-beta"), shared.theme_ids)
        self.assertEqual(1, len(document.pending_items))
        self.assertNotIn(document.pending_items[0].title, [item.title for item in document.items])

    def test_themed_report_sorts_tied_themes_by_normalized_name_after_other_ties(self):
        text = self._themed_report()
        text = text.replace("甲题材｜170分｜关联新闻2条", "Ｂ题材｜170分｜关联新闻2条")
        text = text.replace("乙题材｜160分｜关联新闻2条", "Ａ题材｜170分｜关联新闻2条")
        text = text.replace("| 3 | evt-3 | 乙题材新闻 | 70 |", "| 3 | evt-3 | 乙题材新闻 | 80 |")
        text = text.replace("#### 新闻：3｜evt-3｜乙题材新闻｜70/100", "#### 新闻：3｜evt-3｜乙题材新闻｜80/100")
        document = self._parse_themed_report(text)
        self.assertEqual(["theme-beta", "theme-alpha"], [theme.theme_id for theme in document.themes])

    def test_themed_report_rejects_single_item_theme(self):
        text = self._themed_report().replace("关联新闻2条", "关联新闻1条", 1)
        text = text.replace("#### 新闻：2｜evt-2｜甲题材新闻｜80/100", "#### 已删除：2｜evt-2｜甲题材新闻｜80/100")
        with self.assertRaisesRegex(ValueError, "at least two"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_duplicate_event_within_a_theme(self):
        text = self._themed_report()
        shared_start = text.index("#### 新闻：1｜evt-1｜共享新闻｜90/100")
        second_item_start = text.index("#### 新闻：2｜evt-2｜甲题材新闻｜80/100")
        second_theme_start = text.index("### 主线2：")
        shared = text[shared_start:second_item_start]
        text = text[:second_item_start] + shared + text[second_theme_start:]
        text = text.replace("甲题材｜170分｜关联新闻2条", "甲题材｜180分｜关联新闻2条")
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_duplicate_event_within_other_items(self):
        text = self._themed_report()
        other_start = text.index("#### 新闻：4｜evt-4｜其他新闻｜60/100")
        pending_start = text.index("## 待核验线索")
        other = text[other_start:pending_start]
        text = text[:pending_start] + other + text[pending_start:]
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            self._parse_themed_report(text)

    def test_themed_report_requires_a_nonempty_core_catalyst(self):
        text = self._themed_report().replace("**核心催化：** 甲的共同催化。", "**核心催化：**")
        with self.assertRaisesRegex(ValueError, "core catalyst"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_declared_total_mismatch(self):
        with self.assertRaisesRegex(ValueError, "declared total"):
            self._parse_themed_report(self._themed_report().replace("甲题材｜170分", "甲题材｜169分"))

    def test_themed_report_rejects_different_cross_theme_event_copy(self):
        text = self._themed_report().replace("共享反馈。", "漂移反馈。", 1)
        with self.assertRaisesRegex(ValueError, "inconsistent event"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_cross_theme_release_session_drift(self):
        text = self._themed_report().replace(
            "**发布时段：** 美国市场盘后发布。",
            "**发布时段：** 美国市场盘前发布。",
            1,
        )
        with self.assertRaisesRegex(ValueError, "inconsistent event"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_sources_the_renderer_cannot_link(self):
        for unsafe_url in ("file:///tmp/source", "ftp://example.com/source", "../relative-source"):
            with self.subTest(unsafe_url=unsafe_url):
                text = self._themed_report().replace("https://example.com/shared", unsafe_url)
                with self.assertRaisesRegex(ValueError, "source link"):
                    self._parse_themed_report(text)

    def test_themed_report_requires_consecutive_ranks_starting_at_one(self):
        text = self._themed_report()
        for old_rank, new_rank in ((4, 7), (3, 6), (2, 5)):
            text = text.replace(f"| {old_rank} | evt-{old_rank} |", f"| {new_rank} | evt-{old_rank} |")
            text = text.replace(f"#### 新闻：{old_rank}｜evt-{old_rank}｜", f"#### 新闻：{new_rank}｜evt-{old_rank}｜")
        with self.assertRaisesRegex(ValueError, "ranks must be consecutive"):
            self._parse_themed_report(text)

    def test_themed_report_requires_nonincreasing_ranked_scores(self):
        text = self._themed_report()
        text = text.replace("| 3 | evt-3 | 乙题材新闻 | 70 |", "| 3 | evt-3 | 乙题材新闻 | 85 |")
        text = text.replace("乙题材｜160分", "乙题材｜175分")
        text = text.replace("#### 新闻：3｜evt-3｜乙题材新闻｜70/100", "#### 新闻：3｜evt-3｜乙题材新闻｜85/100")
        with self.assertRaisesRegex(ValueError, "scores must not increase"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_scores_outside_zero_to_one_hundred(self):
        text = self._themed_report()
        text = text.replace("| 1 | evt-1 | 共享新闻 | 90 |", "| 1 | evt-1 | 共享新闻 | 101 |")
        text = text.replace("甲题材｜170分", "甲题材｜181分")
        text = text.replace("乙题材｜160分", "乙题材｜171分")
        text = text.replace("#### 新闻：1｜evt-1｜共享新闻｜90/100", "#### 新闻：1｜evt-1｜共享新闻｜101/100")
        with self.assertRaisesRegex(ValueError, "scores must be between 0 and 100"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_theme_reference_missing_from_index(self):
        text = self._themed_report().replace(
            "#### 新闻：2｜evt-2｜甲题材新闻｜80/100",
            "#### 新闻：2｜evt-missing｜甲题材新闻｜80/100",
        )
        with self.assertRaisesRegex(ValueError, "missing from the index"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_index_body_membership_mismatch(self):
        text = self._themed_report().replace("**关联题材：** theme-alpha\n\n### 主线2", "**关联题材：** theme-beta\n\n### 主线2")
        with self.assertRaisesRegex(ValueError, "membership"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_qualified_index_item_missing_from_body(self):
        text = self._themed_report().replace("#### 新闻：4｜evt-4｜其他新闻｜60/100", "#### 已删除：4｜evt-4｜其他新闻｜60/100")
        with self.assertRaisesRegex(ValueError, "missing from themes and Other"):
            self._parse_themed_report(text)

    def test_themed_report_rejects_item_in_theme_and_other_items(self):
        text = self._themed_report().replace(
            "## 其他重要新闻\n\n",
            "## 其他重要新闻\n\n#### 新闻：2｜evt-2｜甲题材新闻｜80/100\n\n"
            "**核心信息：** 甲核心。\n\n| 传播渠道 | 北京时间 | 消息或热度 |\n"
            "|---|---:|---|\n| 官方 | 08-11 08:01 | [甲直链](https://example.com/alpha) |\n\n",
        )
        with self.assertRaisesRegex(ValueError, "both a theme and Other"):
            self._parse_themed_report(text)

    def test_catalog_selects_legacy_and_current_reports(self):
        found = discover_reports(ROOT)
        self.assertEqual(7, len(found))
        self.assertEqual(
            [
                "20260729-1800",
                "20260730-0800",
                "20260730-1500",
                "20260731-0800",
                "20260803-0800",
                "20260810-0800",
                "20260811-0800",
            ],
            [entry.report_id for _, entry in found],
        )

    def test_aug11_report_parses_all_ranked_news(self):
        found = dict((entry.report_id, (path, entry)) for path, entry in discover_reports(ROOT))
        document = parse_report(*found["20260811-0800"])
        self.assertEqual(24, len(document.items))
        self.assertEqual(list(range(1, 25)), [item.rank for item in document.items])
        self.assertTrue(any("5000亿美元" in item.title for item in document.items))
        self.assertTrue(any("特朗普要求伊朗赔偿" in item.title for item in document.items))
        pboc = next(item for item in document.items if "央行发布" in item.title)
        longsys = next(item for item in document.items if "江波龙" in item.title)
        self.assertIn("金融服务实体经济", pboc.signal)
        self.assertIn("-31.51亿元", longsys.signal)
        self.assertTrue(pboc.market_feedback)
        self.assertTrue(longsys.boundary)
        self.assertEqual(5, len(document.pending_items))
        self.assertEqual("2026-08-11 08:30:39（北京时间，Asia/Shanghai）", document.meta.cutoff)
        self.assertTrue(all(item.release_session for item in document.items))
        self.assertEqual(
            ["韩国半导体投资覆盖材料、零部件与设备", "马斯克与自由电子激光EUV光源", "豆包回应推荐酒店抽取12%佣金争议", "英伟达拟向Lancium投资最高30亿美元", "天津机器人会议"],
            [item.title for item in document.pending_items],
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
                "> **实际截点：** 2026-08-09 19:44:27（北京时间，Asia/Shanghai）；本稿为提前版。\n\n"
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
            self.assertEqual(
                "2026-08-09 19:44:27（北京时间，Asia/Shanghai）",
                document.meta.cutoff,
            )
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
