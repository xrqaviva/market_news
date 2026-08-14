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
        "<body><main>"
        "<h1>A股盘前双源晨报｜2026-08-13</h1>"
        "<p class=\"meta\">采集截止：中国时间 2026-08-13T07:30:00+08:00</p>"
        "<p class=\"meta\">上一A股交易日：2026-08-12</p>"
        "<p class=\"rule\">规则：只有同口径、同日期的两个独立来源在容差内才显示共识值；</p>"
        "<h2>美股三大指数</h2>"
        "<div class=\"table-wrap\"><table><thead><tr><th>品种</th><th>最新值</th></tr></thead><tbody>"
        "<tr><td>标普500</td><td class=\"num up\">+0.65%</td></tr>"
        "<tr><td>纳斯达克综合</td><td class=\"num\">tencent 26,803.03</td></tr>"
        "<tr><td>道琼斯工业</td><td class=\"num up\">tencent +69.7200</td>"
        "<td class=\"src\"><a href=\"https://example.com/tencent\">tencent</a>；"
        "<a href=\"https://example.com/east\">eastmoney_global_history</a></td></tr>"
        "</tbody></table></div>"
        "<h2>官方日度参考汇率</h2>"
        "<div class=\"table-wrap\"><table><thead><tr><th>品种</th><th>最新值</th></tr></thead><tbody>"
        "<tr><td>美元/在岸人民币</td><td class=\"num flat\">—</td>"
        "<td class=\"src\"><a href=\"https://example.com/boc\">boc</a></td></tr>"
        "<tr><td>美元/欧元</td><td class=\"num flat\">—</td>"
        "<td class=\"src\"><a href=\"https://example.com/ecb\">ecb</a></td></tr>"
        "</tbody></table></div>"
        "<h2>上一交易日A股非ST涨跌家数</h2>"
        "<p>核验状态：待核验（双源冲突）</p>"
        "<p>核验原因：eligible_code_set_mismatch</p>"
        "<div class=\"table-wrap\"><table><thead><tr><th>来源</th><th>数据日期</th><th>有效样本</th><th>上涨</th><th>下跌</th><th>平盘</th><th>上涨率</th><th>下跌率</th></tr></thead><tbody>"
        "<tr><td class=\"src\">eastmoney</td><td>2026-08-13</td><td class=\"num\">5,334.00</td><td class=\"num\">1,088.00</td><td class=\"num\">4,168.00</td><td class=\"num\">78.0000</td><td class=\"num up\">+20.40%</td><td class=\"num down\">+78.14%</td></tr>"
        "<tr><td class=\"src\">sina</td><td>2026-08-13</td><td class=\"num\">5,335.00</td><td class=\"num\">1,088.00</td><td class=\"num\">4,168.00</td><td class=\"num\">79.0000</td><td class=\"num up\">+20.39%</td><td class=\"num down\">+78.13%</td></tr>"
        "</tbody></table></div>"
        "<h2>国内期货</h2>"
        "<p>核验状态：待核验（双源冲突）</p>"
        "<p>核验原因：date_mismatch</p>"
        "<div class=\"table-wrap\"><table><tbody>"
        "<tr><td>上期所黄金</td><td class=\"num\">1,000.00</td></tr>"
        "</tbody></table></div>"
        "<h2>重要宏观新闻</h2>"
        "<p>本时间窗内没有通过严格来源规则的宏观新闻。</p>"
        "<p class=\"legend\">涨 ▲ / 跌 ▼（红涨绿跌）—— 颜色仅辅助展示，核验状态以表格为准。</p>"
        "<footer>本报告仅作信息整理，不构成投资建议。</footer>"
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
            self.assertIn("外围｜2026-08-13", page)
            self.assertIn("新闻速递", page)
            self.assertNotIn("融合视图", page)
            self.assertNotIn("双源晨报", page)
            # tabs-meta shows the plain date, not the internal report title
            self.assertIn("外围 · 2026-08-14", page)
            self.assertNotIn("测试报告", page)
            self.assertIn("#a9b4c3", page)  # visible outer table border
            self.assertIn("+0.65%", page)
            self.assertIn("assets/app.css", page)
            self.assertIn("2026-08-14", page)
            # radar report-card skeleton reused for a consistent look
            self.assertIn('class="page-shell"', page)
            self.assertIn('class="report-card"', page)
            self.assertIn('class="report-sidebar"', page)
            self.assertIn('class="report-workspace"', page)
            # sidebar is a date archive, newest date marked as current
            self.assertIn('data-report-date="2026-08-14"', page)
            self.assertIn('aria-current="page"', page)
            self.assertIn('href="reports/2026-08-14-0800.html"', page)
            self.assertNotIn('data-tab-link', page)
            # informational paragraphs and macro-news section dropped
            for dropped in (
                "采集截止", "上一A股交易日", "规则：只有同口径", "涨 ▲",
                "本报告仅作信息整理", "重要宏观新闻",
            ):
                self.assertNotIn(dropped, page)
            # source prefixes stripped from numeric cells, keys mapped to short names
            self.assertNotIn("tencent ", page)
            self.assertIn(">腾讯<", page)
            self.assertIn(">东方财富<", page)
            self.assertIn("+69.7200", page)
            self.assertIn("26,803.03", page)
            # fully-empty value tables collapse into a verification summary
            self.assertIn("官方日度参考汇率（2 项暂无共识值", page)
            # breadth becomes a single-source plain line (eastmoney, no table)
            self.assertIn("上涨 1,088 · 下跌 4,168 · 平盘 78（数据日期 2026-08-13，东方财富）", page)
            self.assertIn("breadth-line", page)
            self.assertNotIn("eligible_code_set_mismatch", page)
            # other tables' verification status/reason still moved to the bottom summary
            self.assertIn("核验明细（1 条）", page)
            self.assertIn("国内期货：待核验（双源冲突）——date_mismatch", page)
            # tables get full cell borders
            self.assertIn("border: 1px solid var(--line);", page)

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
            # internal report terminology must not surface on the fusion page
            self.assertNotIn("正式版", page)
            self.assertNotIn("旧闻后置", page)
            for forbidden in ("/Users/", "file://", "ghp_", "Authorization: Bearer", "Local Storage"):
                self.assertNotIn(forbidden, page)


if __name__ == "__main__":
    unittest.main()
