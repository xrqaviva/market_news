import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/PROJECT_GUIDE.md"

EXPECTED_HEADINGS = [
    "项目定位与阅读方法",
    "当前状态总览",
    "架构与数据流",
    "新闻时间窗口与北京时间",
    "采集来源矩阵",
    "事件发现、去重与传播链",
    "热度体系",
    "主榜准入与排序",
    "报告结构与专项规则",
    "标准运行步骤",
    "15分钟并行流程",
    "文件目录与产物关系",
    "Markdown、HTML与公网发布",
    "安全与公开边界",
    "失败降级与故障排查",
    "设计决策记录",
    "计划与完成情况",
    "UAT测试用例",
    "集成测试用例",
    "已知限制与后续路线",
    "文档维护规则",
    "变更记录",
]

UNIFIED_STATUSES = {"已完成", "已验证", "暂停", "受限", "规划中", "历史口径"}
TEST_STATUSES = {"已通过", "隔离分支已验证", "未执行", "受限", "失败", "暂停"}


def section(text, heading, next_heading=None):
    body = text.split(heading, 1)[1]
    return body.split(next_heading, 1)[0] if next_heading else body


def first_table(markdown):
    lines = [line for line in markdown.splitlines() if line.startswith("|")]
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    return rows[0], rows[2:]


def markdown_anchors(text):
    anchors = set()
    seen = {}
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


class ProjectGuideContractTest(unittest.TestCase):
    def test_local_markdown_links_exist(self):
        text = GUIDE.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            with self.subTest(target=target):
                self.assertTrue(target.strip(), "local link target must not be empty")
                relative_path = unquote(parsed.path)
                path = (GUIDE.parent / relative_path).resolve() if relative_path else GUIDE
                self.assertTrue(path == ROOT or ROOT in path.parents, f"link escapes repository root: {target}")
                self.assertTrue(path.exists(), target)
                if parsed.fragment and path.suffix.lower() == ".md":
                    self.assertIn(unquote(parsed.fragment), markdown_anchors(path.read_text(encoding="utf-8")))

    def test_numbered_top_level_headings_are_exact_unique_and_ordered(self):
        text = GUIDE.read_text(encoding="utf-8")
        headings = re.findall(r"^## (\d+)\. (.+)$", text, flags=re.MULTILINE)
        self.assertEqual(headings, [(str(number), title) for number, title in enumerate(EXPECTED_HEADINGS, 1)])

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

    def test_source_matrix_has_required_layers_columns_status_and_evidence(self):
        text = GUIDE.read_text(encoding="utf-8")
        source_section = section(text, "## 5. 采集来源矩阵", "## 6. 事件发现、去重与传播链")
        header, rows = first_table(source_section)
        self.assertEqual(
            header,
            ["来源层级/平台", "角色", "主要入口或具体直链规则", "页面可见字段", "登录/会员", "统一状态", "最近验证日期", "失败降级", "典型证据"],
        )
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(source=row[0]):
                self.assertEqual(len(row), len(header))
                self.assertIn(row[5], UNIFIED_STATUSES)
                self.assertTrue(row[8])
        matrix_text = " ".join(cell for row in rows for cell in row)
        for source in (
            "政府", "监管", "交易所", "法定公告", "公司IR", "国内财经媒体", "财联社",
            "海外通讯社", "产业垂直媒体", "NewsNow", "微博", "雪球", "X", "淘股吧", "韭研公社",
            "东方财富", "同花顺问财", "开盘啦", "付费或未稳定接入专业源",
        ):
            with self.subTest(source=source):
                self.assertIn(source, matrix_text)

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
        ledger = section(text, "## 17. 计划与完成情况", "## 18. UAT测试用例")
        header, rows = first_table(ledger)
        self.assertEqual(header, ["项目", "日期", "目标", "当前状态", "已完成内容", "未完成内容", "设计/计划文件", "实现/报告/测试/提交证据"])
        for row in rows:
            with self.subTest(project=row[0]):
                self.assertEqual(len(row), len(header))
                self.assertIn(row[3], UNIFIED_STATUSES)

    def test_guide_itself_has_final_status_and_no_stale_completion_language(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("适用版本：项目说明书初版（已验证）", text)
        self.assertIn("当前提交/验证边界", text)
        guide_row = next(row for row in first_table(section(text, "## 17. 计划与完成情况", "## 18. UAT测试用例"))[1] if row[0] == "项目说明书")
        self.assertEqual(guide_row[3], "已验证")
        for stale in ("建设中", "后续持续补全", "第18—22章后续补全"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, text)

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
        uat = section(text, "## 18. UAT测试用例", "## 19. 集成测试用例")
        integration = section(text, "## 19. 集成测试用例", "## 20. 已知限制与后续路线")
        uat_header, uat_rows = first_table(uat)
        it_header, it_rows = first_table(integration)
        self.assertEqual(uat_header, ["用例", "场景", "前置条件", "操作步骤", "预期结果", "当前状态", "实际结果", "证据"])
        self.assertEqual(it_header, ["用例", "场景", "涉及组件", "前置条件", "操作步骤", "预期结果", "当前状态", "实际结果", "证据"])
        self.assertEqual([row[0] for row in uat_rows], [f"UAT-{number:03d}" for number in range(1, 15)])
        self.assertEqual([row[0] for row in it_rows], [f"IT-{number:03d}" for number in range(1, 14)])
        for row in uat_rows:
            with self.subTest(case=row[0]):
                self.assertEqual(len(row), len(uat_header))
                self.assertIn(row[5], TEST_STATUSES)
        for row in it_rows:
            with self.subTest(case=row[0]):
                self.assertEqual(len(row), len(it_header))
                self.assertTrue(row[2])
                self.assertIn(row[6], TEST_STATUSES)

    def test_local_and_isolated_test_evidence_has_reproducible_boundaries(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("`tests/test_report_contract.py`与相关报告是主工作区未跟踪本地文件", text)
        self.assertNotIn("已跟踪`tests/test_report_contract.py`", text)
        self.assertIn("`codex/news-radar-web`提交`bc16916`", text)
        uat_rows = first_table(section(text, "## 18. UAT测试用例", "## 19. 集成测试用例"))[1]
        self.assertEqual(next(row for row in uat_rows if row[0] == "UAT-013")[5], "未执行")
        it_rows = first_table(section(text, "## 19. 集成测试用例", "## 20. 已知限制与后续路线"))[1]
        for case_id in ("IT-008", "IT-009", "IT-010", "IT-011", "IT-012"):
            with self.subTest(case=case_id):
                self.assertEqual(next(row for row in it_rows if row[0] == case_id)[6], "隔离分支已验证")

    def test_old_news_and_chrome_degradation_boundaries_are_explicit(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("尚无合格的旧闻异动样本", text)
        failure = section(text, "## 15. 失败降级与故障排查", "## 16. 设计决策记录")
        chrome_row = next(line for line in failure.splitlines() if line.startswith("| Chrome进程/控制通道/动态渲染不可用 |"))
        for phrase in ("公开路径降级", "动态字段未取得", "恢复前置条件", "禁止读取浏览器私密数据"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, chrome_row)

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
