from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "OPERATIONS_RUNBOOK.md"
HANDOFF = ROOT / "HANDOFF.md"


class OperationsRunbookContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = RUNBOOK.read_text(encoding="utf-8")
        cls.handoff = HANDOFF.read_text(encoding="utf-8")

    def test_runbook_is_the_handoff_entrypoint(self) -> None:
        self.assertIn("docs/OPERATIONS_RUNBOOK.md", self.handoff[:1500])
        self.assertIn("单一权威操作手册", self.text)

    def test_markdown_generation_boundary_and_required_contract_are_explicit(self) -> None:
        for phrase in (
            "当前没有自动生成新闻 Markdown 的程序",
            "YYYY-MM-DD-HHMM-<slug>.md",
            "web/report_catalog.json",
            "北京时间",
            "发布时段",
            "市场反馈",
            "判断边界",
            "热点构成",
            "具体直链",
            "零静默丢弃",
            "ranked",
            "merged_into:<event_id>",
            "excluded:<明确原因>",
            "pending_verification",
        ):
            self.assertIn(phrase, self.text)

    def test_theme_and_heat_rules_are_migration_complete(self) -> None:
        for phrase in (
            "覆盖25 + 变化30 + 绝对热度20 + 新鲜度15 + 频次10",
            "至少两条",
            "跨题材",
            "题材分不是市场总分",
            "旧闻",
            "双时点",
            "申购日",
            "上市日",
            "盘后",
        ):
            self.assertIn(phrase, self.text)

    def test_performance_target_never_weakens_recall_or_completion(self) -> None:
        for phrase in (
            "15分钟",
            "海外与宏观",
            "国内与政策",
            "登录渠道与热度",
            "前10条",
            "不能停止来源发现",
            "超过15分钟",
            "继续运行直至完整交付",
        ):
            self.assertIn(phrase, self.text)

    def test_build_test_and_publish_commands_are_exact(self) -> None:
        commands = (
            "python3 -m web.build --project-root . --output web/dist",
            "python3 -m unittest discover -s tests -v",
            "node tests/report_layout_browser.mjs",
            "scripts/run_morning_site.sh",
            "SITE_PUBLISH_MODE=apply scripts/run_morning_site.sh",
        )
        for command in commands:
            self.assertIn(command, self.text)
        self.assertIn("默认 dry-run", self.text)
        self.assertIn("不会启用自动任务", self.text)
        self.assertIn("推送和发布需要单独明确授权", self.text)

    def test_cli_and_browser_capability_boundary_is_safe(self) -> None:
        for phrase in (
            "Codex CLI",
            "桌面客户端",
            "已登录浏览器会话",
            "密码、Cookie、Local Storage或浏览器历史",
            "不要伪造",
        ):
            self.assertIn(phrase, self.text)

    def test_local_links_and_commands_reference_existing_paths(self) -> None:
        links = re.findall(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)", self.text)
        self.assertGreaterEqual(len(links), 8)
        for target in links:
            path = target.split("#", 1)[0]
            self.assertTrue((RUNBOOK.parent / path).resolve().exists(), target)

    def test_new_session_prompt_has_minimum_read_order_and_no_placeholders(self) -> None:
        for phrase in (
            "先完整阅读",
            "docs/OPERATIONS_RUNBOOK.md",
            "docs/PROJECT_GUIDE.md",
            "docs/2026-08-11-theme-aggregation-method-uat.md",
            "HANDOFF.md",
        ):
            self.assertIn(phrase, self.text)
        self.assertNotRegex(self.text, r"\b(?:TBD|TODO|FIXME)\b")


if __name__ == "__main__":
    unittest.main()
