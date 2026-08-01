import re
import unittest
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/2026-07-31-0800-premarket-news-ranking.md"


def section(text: str, start: str, end: Optional[str] = None) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index) if end else len(text)
    return text[start_index:end_index]


class ReportContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT.read_text(encoding="utf-8")

    def test_new_earnings_show_first_market_reaction_and_interpretation(self) -> None:
        blocks = {
            "微软": section(self.text, "## 2.", "## 3."),
            "亚马逊": section(self.text, "## 3.", "## 4."),
            "苹果": section(self.text, "## 5.", "## 6."),
            "三星": section(self.text, "## 6.", "## 7."),
            "Meta": section(self.text, "12. **Meta", "13. **"),
        }
        for company, block in blocks.items():
            with self.subTest(company=company):
                self.assertRegex(block, r"财报后(?:盘后|首个可交易时段|发布日余下交易时段)反馈：")
                self.assertRegex(block, r"即时市场定价：(正向|负向|分化|不可得)")

    def test_unitree_includes_official_subscription_schedule(self) -> None:
        block = section(self.text, "## 9.", "## 10.")
        self.assertIn("2026年8月10日", block)
        self.assertIn("网上申购", block)
        self.assertIn("787836", block)
        self.assertRegex(block, r"8月5日.*初步询价")

    def test_earnings_reaction_is_not_used_as_long_term_endorsement(self) -> None:
        self.assertIn("即时市场定价仅表示财报发布后的短线价格反馈，不等于长期认可", self.text)

    def test_apple_keeps_early_and_later_after_hours_snapshots(self) -> None:
        block = section(self.text, "## 5.", "## 6.")
        for value in ("04:54", "跌2.3%", "04:57", "跌约4%"):
            with self.subTest(value=value):
                self.assertIn(value, block)

    def test_samsung_distinguishes_absolute_and_relative_reaction(self) -> None:
        block = section(self.text, "## 6.", "## 7.")
        self.assertIn("财报后发布日余下交易时段反馈", block)
        self.assertIn("即时市场定价：分化", block)
        self.assertIn("绝对方向偏弱、相对表现略强", block)

    def test_microsoft_and_meta_keep_different_source_snapshots(self) -> None:
        microsoft = section(self.text, "## 2.", "## 3.")
        meta = section(self.text, "12. **Meta", "13. **")
        self.assertIn("同期不同来源快照", microsoft)
        self.assertIn("约涨9%", microsoft)
        self.assertIn("f7dff4fb9d51a2bdec56a13e5da1053d", microsoft)
        self.assertIn("同期不同来源快照", meta)
        self.assertIn("跌4.2%", meta)
        self.assertIn("bcbc62dde6d2cac724e3b3385fcabeab", meta)

    def test_unitree_does_not_imply_a_published_listing_date(self) -> None:
        block = section(self.text, "## 9.", "## 10.")
        self.assertIn("当前发行安排未列上市日期，待后续公告", block)


if __name__ == "__main__":
    unittest.main()
