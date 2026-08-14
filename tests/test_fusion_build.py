import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from web.build import build_site
from web.fusion import FUSION_NAME, build_fusion
from web.security import PublicTreeUnsafe, assert_public_tree_safe


ROOT = Path(__file__).resolve().parents[1]
DAILY_INFO_ROOT = Path("/Users/aviva/Projects/daily_info")


def _fake_daily_info(base: Path) -> Path:
    root = base / "daily_info"
    brief_dir = root / "reports" / "index"
    brief_dir.mkdir(parents=True)
    (brief_dir / "A股盘前晨报.html").write_text(
        "<!doctype html><html lang=\"zh-CN\"><head><title>x</title></head>"
        "<body><main><h1>A股盘前双源晨报｜2026-08-13</h1>"
        "<div class=\"table-wrap\"><table><thead><tr><th>品种</th></tr></thead>"
        "<tbody><tr><td class=\"num up\">+0.65%</td></tr></tbody></table></div>"
        "</main></body></html>",
        encoding="utf-8",
    )
    return root


def _fake_radar_site(base: Path) -> Path:
    """Minimal dist tree: assets, reports.json, one report page."""
    dist = base / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "assets" / "app.css").write_text(":root{--ink:#182033}", encoding="utf-8")
    (dist / "reports").mkdir(parents=True)
    (dist / "reports" / "2026-08-14-0800.html").write_text(
        "<!doctype html><html><head></head><body><main class=\"report-main\">"
        "<h1>测试报告</h1></main></body></html>",
        encoding="utf-8",
    )
    (dist / "reports.json").write_text(
        json.dumps({
            "reports": [{
                "id": "20260814-0800", "date": "2026-08-14", "slot": "0800",
                "label": "盘前", "title": "测试报告", "url": "reports/2026-08-14-0800.html",
            }],
            "latest": "reports/2026-08-14-0800.html",
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return dist


class FusionBuildTest(unittest.TestCase):
    def test_build_fusion_writes_two_tabs_with_brief_and_iframe(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = _fake_radar_site(base)
            daily = _fake_daily_info(base)
            target = build_fusion(dist, daily)

            self.assertEqual(dist.resolve() / FUSION_NAME, target)
            page = target.read_text(encoding="utf-8")
            self.assertIn('data-tab="brief" aria-selected="true"', page)
            self.assertIn('data-tab="news" aria-selected="false"', page)
            self.assertIn('class="fusion-pane brief-body"', page)
            self.assertIn('src="reports/2026-08-14-0800.html"', page)
            self.assertIn("A股盘前双源晨报｜2026-08-13", page)
            self.assertIn("+0.65%", page)
            self.assertIn("assets/app.css", page)
            self.assertIn("2026-08-14", page)
            # radar report-card skeleton reused for a consistent look
            self.assertIn('class="page-shell"', page)
            self.assertIn('class="report-card"', page)
            self.assertIn('class="report-sidebar"', page)
            self.assertIn('class="report-workspace"', page)
            self.assertIn('href="#brief"', page)
            self.assertIn('href="reports/2026-08-14-0800.html"', page)

    def test_build_fusion_fails_without_brief(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = _fake_radar_site(base)
            with self.assertRaises(Exception):
                build_fusion(dist, base / "missing")

    def test_fusion_page_passes_public_tree_safety(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = _fake_radar_site(base)
            daily = _fake_daily_info(base)
            build_fusion(dist, daily)
            assert_public_tree_safe(dist)  # no raise

    def test_build_site_with_daily_info_root_writes_fusion(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            daily = _fake_daily_info(base)
            result = build_site(ROOT, base / "dist", daily_info_root=daily)
            fusion = result.output_dir / FUSION_NAME
            self.assertTrue(fusion.is_file())
            page = fusion.read_text(encoding="utf-8")
            self.assertIn('data-tab="brief"', page)
            self.assertIn('class="fusion-pane brief-body"', page)

    def test_build_site_without_daily_info_root_skips_fusion(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = build_site(ROOT, base / "dist")
            self.assertFalse((result.output_dir / FUSION_NAME).exists())

    @unittest.skipUnless(DAILY_INFO_ROOT.is_dir(), "daily_info project not present")
    def test_real_daily_info_brief_extracts(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = _fake_radar_site(base)
            build_fusion(dist, DAILY_INFO_ROOT)
            page = (dist / FUSION_NAME).read_text(encoding="utf-8")
            # real brief body must be present and must not leak private paths
            self.assertIn("美股三大指数", page)
            for forbidden in ("/Users/", "file://", "ghp_", "Authorization: Bearer", "Local Storage"):
                self.assertNotIn(forbidden, page)


if __name__ == "__main__":
    unittest.main()
