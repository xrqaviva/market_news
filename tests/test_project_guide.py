import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/PROJECT_GUIDE.md"


class ProjectGuideContractTest(unittest.TestCase):
    def test_guide_exists_with_title_and_verification_date(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# A股短线新闻雷达项目说明书\n"))
        self.assertRegex(text, r"最后核验日期：2026-08-09")


if __name__ == "__main__":
    unittest.main()
