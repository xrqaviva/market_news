import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/PROJECT_GUIDE.md"


class ProjectGuideContractTest(unittest.TestCase):
    def test_guide_exists_with_title_and_verification_date(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# A股短线新闻雷达项目说明书\n"))
        self.assertRegex(text, r"最后核验日期：2026-08-09")

    def test_current_heat_formula_and_comparison_rules_are_explicit(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10", text)
        self.assertIn("同一永久URL", text)
        self.assertIn("同一字段", text)
        self.assertIn("新出现", text)
        self.assertIn("不同平台的数字不得相加", text)

    def test_time_window_and_specific_link_rules_are_explicit(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("Asia/Shanghai", text)
        self.assertIn("前一交易日00:00", text)
        self.assertIn("全部自然日", text)
        self.assertIn("精确分钟未取得", text)
        self.assertIn("首页和搜索页不能替代", text)

    def test_source_matrix_contains_required_platforms(self):
        text = GUIDE.read_text(encoding="utf-8")
        for source in ("财联社", "NewsNow", "微博", "雪球", "X", "淘股吧", "韭研公社", "东方财富", "开盘啦"):
            with self.subTest(source=source):
                self.assertIn(source, text)


if __name__ == "__main__":
    unittest.main()
