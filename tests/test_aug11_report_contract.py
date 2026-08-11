import re
import unittest
from pathlib import Path

from tests.test_aug11_theme_report_contract import EXPECTED_EVENT_IDS, EXPECTED_SESSIONS, _parse_report


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/2026-08-11-0800-premarket-news-ranking.md"
AUDIT = ROOT / "evidence/2026-08-11-0800-recall-audit.md"


class Aug11ReportContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT.read_text(encoding="utf-8")
        index = cls.text[
            cls.text.index("## 单条新闻热榜索引") : cls.text.index("## 题材主线")
        ]
        cls.index_rows = tuple(
            (int(rank), event_id, title, int(score))
            for rank, event_id, title, score in re.findall(
                r"^\|\s*(\d+)\s*\|\s*(evt-\d{8}-\d{3})\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|",
                index,
                re.MULTILINE,
            )
        )
        _index, themes, other = _parse_report(cls.text)
        cls.cards = {}
        for item in [member for theme in themes for member in theme["items"]] + list(other):
            cls.cards.setdefault(item["rank"], item)

    def test_all_ranked_news_have_unique_stable_event_ids(self) -> None:
        self.assertEqual(list(range(1, 25)), [row[0] for row in self.index_rows])
        self.assertEqual(24, len({row[1] for row in self.index_rows}))
        self.assertEqual(list(EXPECTED_EVENT_IDS), [row[1] for row in self.index_rows])

    def test_nine_previously_missed_events_are_visible(self) -> None:
        expected = (
            "韩国",
            "自由电子激光",
            "豆包",
            "爱丽家居",
            "天津机器人",
            "5000亿美元",
            "Lancium",
            "9月加息",
            "特朗普要求伊朗赔偿",
        )
        for keyword in expected:
            with self.subTest(keyword=keyword):
                self.assertIn(keyword, self.text)

    def test_titles_are_factual_and_do_not_contain_heat_judgements(self) -> None:
        titles = [row[2] for row in self.index_rows]
        self.assertEqual(24, len(titles))
        for title in titles:
            with self.subTest(title=title):
                self.assertNotRegex(title, r"升温|高热|新出现|持续传播|激增")

    def test_pboc_explains_scope_without_inventing_nine_plan_names(self) -> None:
        for phrase in (
            "货币政策体系与宏观审慎管理",
            "金融服务实体经济",
            "现代金融市场",
            "高水平金融开放",
            "金融基础设施和中央银行服务体系",
            "官方新闻稿未逐份列出九份方案名称",
        ):
            self.assertIn(phrase, self.text)

    def test_longsys_foregrounds_profit_growth_and_negative_operating_cash_flow(self) -> None:
        self.assertIn("71528.66%", self.text)
        self.assertIn("-31.51亿元", self.text)

    def test_release_session_and_observable_market_reaction_are_explicit(self) -> None:
        self.assertEqual(set(range(1, 25)), set(self.cards))
        for rank, card in self.cards.items():
            with self.subTest(rank=rank):
                self.assertEqual(EXPECTED_SESSIONS[rank], card["session"])
                self.assertTrue(card["market_feedback"], f"rank {rank} missing market feedback")
                self.assertTrue(card["boundary"], f"rank {rank} missing boundary")
                self.assertTrue(card["heat_change"], f"rank {rank} missing heat change")

    def test_recall_audit_has_a_disposition_for_each_missed_event(self) -> None:
        audit = AUDIT.read_text(encoding="utf-8")
        rows = {
            event_id: (event, disposition, boundary)
            for event_id, event, _miss, disposition, boundary in re.findall(
                r"^\| (MISS-\d{2}) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$",
                audit,
                re.MULTILINE,
            )
        }
        self.assertEqual(9, len(rows))
        expected = {
            "MISS-01": ("待核验保留", None),
            "MISS-02": ("待核验保留", None),
            "MISS-03": ("待核验保留", None),
            "MISS-04": ("进入主榜", 17),
            "MISS-05": ("待核验保留", None),
            "MISS-06": ("进入主榜", 6),
            "MISS-07": ("待核验保留", None),
            "MISS-08": ("进入主榜", 9),
            "MISS-09": ("进入主榜", 7),
        }
        for event_id, (disposition, rank) in expected.items():
            with self.subTest(event_id=event_id):
                self.assertEqual(disposition, rows[event_id][1])
                if rank is None:
                    self.assertIn("榜外待核", rows[event_id][2])
                else:
                    self.assertIn(f"第{rank}", rows[event_id][2])
        self.assertNotIn("静默丢弃", audit)

    def test_unverified_old_news_and_tianjin_meeting_are_not_scored_as_ranked_news(self) -> None:
        pending = self.text[self.text.index("## 待核验线索") :]
        for keyword in ("韩国", "自由电子激光", "豆包", "Lancium", "天津机器人会议"):
            self.assertIn(keyword, pending)
        ranked_titles = [row[2] for row in self.index_rows]
        for keyword in ("韩国", "自由电子激光", "豆包", "Lancium", "天津机器人会议"):
            self.assertFalse(any(keyword in title for title in ranked_titles))
        self.assertEqual(
            1,
            ranked_titles.count("天津提出到2028年智能机器人核心产业产值突破200亿元"),
        )


if __name__ == "__main__":
    unittest.main()
