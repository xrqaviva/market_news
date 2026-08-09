import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/PROJECT_GUIDE.md"


class ProjectGuideContractTest(unittest.TestCase):
    def test_local_markdown_links_exist(self):
        text = GUIDE.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            path = (GUIDE.parent / target.split("#", 1)[0]).resolve()
            with self.subTest(target=target):
                self.assertTrue(path.exists(), target)

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

    def test_old_news_quantification_requires_two_bjt_snapshots(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("量化“明显升温”或“激增”只接受同一永久URL、同一字段、两个明确北京时间快照", text)
        self.assertIn("跨平台同步只能作为覆盖、频次或重新出现证据", text)
        self.assertIn("重新出现、趋势数据不足", text)

    def test_fund_and_announcement_checks_are_not_ranking_or_entry_gates(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("资金验证、公告确认、可靠性、个股映射、市场反馈和深度判断均不参与排序", text)
        self.assertIn("资金验证和公告确认也不是入榜前提", text)

    def test_runtime_and_status_boundaries_are_explicit(self):
        text = GUIDE.read_text(encoding="utf-8")
        for phrase in ("海外宏观与财报", "国内政策与公告", "登录渠道热度", "超过15分钟仍继续完成"):
            self.assertIn(phrase, text)
        self.assertIn("codex/news-radar-web", text)
        self.assertIn("尚未合入main", text)
        self.assertIn("GitHub Pages", text)
        self.assertIn("暂停", text)

    def test_security_boundaries_are_explicit(self):
        text = GUIDE.read_text(encoding="utf-8")
        for forbidden_source in ("密码", "Cookie", "Token", "Local Storage", "浏览器历史"):
            self.assertIn(forbidden_source, text)
        self.assertIn("不得读取或输出", text)

    def test_status_ledger_uses_only_the_unified_status_enum(self):
        text = GUIDE.read_text(encoding="utf-8")
        ledger = text.split("## 17. 计划与完成情况", 1)[1].split("## 18. UAT测试用例", 1)[0]
        allowed = {"已完成", "已验证", "暂停", "受限", "规划中", "历史口径"}
        for line in ledger.splitlines():
            if not line.startswith("|") or line.startswith("|---") or "当前状态" in line:
                continue
            with self.subTest(row=line):
                self.assertIn(line.split("|")[2].strip(), allowed)

    def test_web_publish_and_full_security_boundaries_are_explicit(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("codex/news-radar-web隔离分支已实现且尚未合入main", text)
        for paused in ("GitHub认证：暂停", "首次推送：暂停", "GitHub Pages：暂停", "自动任务：暂停"):
            with self.subTest(paused=paused):
                self.assertIn(paused, text)
        self.assertIn("Markdown → 固定HTML → web/dist", text)
        self.assertIn("公开仓库只接收`web/dist`", text)
        self.assertIn("不得读取、写入、输出、持久化或复制", text)
        self.assertIn("本地文件、缓存、构建目录和日志/报告", text)

    def test_uat_and_integration_cases_have_stable_ids(self):
        text = GUIDE.read_text(encoding="utf-8")
        for case_id in ("UAT-001", "UAT-014", "IT-001", "IT-013"):
            self.assertIn(case_id, text)
        for field in ("前置条件", "操作步骤", "预期结果", "当前状态", "实际结果", "证据"):
            self.assertIn(field, text)

    def test_no_unresolved_placeholders(self):
        text = GUIDE.read_text(encoding="utf-8")
        for placeholder in ("TBD", "TODO", "待补", "稍后填写"):
            self.assertNotIn(placeholder, text)

    def test_final_maintenance_sections_are_not_empty(self):
        text = GUIDE.read_text(encoding="utf-8")
        headings = (
            "## 20. 已知限制与后续路线",
            "## 21. 文档维护规则",
            "## 22. 变更记录",
        )
        for index, heading in enumerate(headings):
            with self.subTest(heading=heading):
                section = text.split(heading, 1)[1]
                if index + 1 < len(headings):
                    section = section.split(headings[index + 1], 1)[0]
                self.assertTrue(section.strip())

    def test_uat_009_limits_pass_status_to_apple_bjt_evidence(self):
        text = GUIDE.read_text(encoding="utf-8")
        row = next(line for line in text.splitlines() if line.startswith("| UAT-009 |"))
        for phrase in (
            "苹果盘后市场反馈（北京时间样本）",
            "北京时间传播链",
            "04:54",
            "04:57",
            "已通过",
            "test_apple_keeps_early_and_later_after_hours_snapshots",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, row)

    def test_ledger_calls_report_contract_checks_test_methods(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("财报相关5个测试方法通过", text)
        self.assertIn("IPO相关2个测试方法通过", text)
        self.assertNotIn("财报相关5项断言", text)
        self.assertNotIn("IPO相关2项断言", text)


if __name__ == "__main__":
    unittest.main()
