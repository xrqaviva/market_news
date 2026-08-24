# -*- coding: utf-8 -*-
"""报告生成管线 UAT（2026-08-24 闭环审计配套）。

覆盖三类历史事故的回归防线：
1. 来源跨窗口污染（append-default 通配符 + 无窗口过滤）——2026-08-24 发现
2. 契约预检自身的正确性（分数/主题/evt 一致性）
3. OLD 条目标题"（昨日已定价）"重复追加——2026-08-20 与 08-24 各发生一次
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import gen_report  # noqa: E402


def _sina_row(ts, url, text):
    return {"create_time": ts, "docurl": url, "rich_text": text}


def _load_rows(tmp, name, rows):
    p = Path(tmp) / name
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return str(p)


class WindowFilterTests(unittest.TestCase):
    """事故1回归：即使证据混入多日文件，来源也只取窗口内条目。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.in_window = _sina_row(
            "2026-08-21 07:30:00", "https://finance.sina.cn/a1",
            "美加贸易谈判破裂关税上调")
        self.before = _sina_row(
            "2026-08-14 10:00:00", "https://finance.sina.cn/a0",
            "美加贸易谈判旧闻旧闻旧闻")
        self.after = _sina_row(
            "2026-08-24 12:00:00", "https://finance.sina.cn/a2",
            "美加贸易谈判截点后消息")
        self.no_time = _sina_row(None, "https://finance.sina.cn/a3", "无时间戳条目")

    def test_filter_keeps_only_in_window(self):
        sina_path = _load_rows(self.tmp, "mix.jsonl",
                               [self.in_window, self.before, self.after, self.no_time])
        rows, _em = gen_report.load_evidence([sina_path], [])
        kept = gen_report.filter_window(rows, "2026-08-21 00:00:00—2026-08-24 08:00:00（北京时间）")
        self.assertEqual([r[1] for r in kept], ["https://finance.sina.cn/a1"])

    def test_unparseable_window_keeps_rows(self):
        rows = [self.in_window, self.before]
        self.assertEqual(gen_report.filter_window(rows, None), rows)
        self.assertEqual(gen_report.filter_window(rows, "bad-window"), rows)

    def test_parse_window(self):
        self.assertEqual(
            gen_report.parse_window("2026-08-21 00:00:00—2026-08-24 08:00:00（北京时间）"),
            ("2026-08-21 00:00:00", "2026-08-24 08:00:00"))
        self.assertIsNone(gen_report.parse_window("no separator"))

    def test_end_to_end_generated_md_has_no_out_of_window_source(self):
        """subprocess 端到端：证据含窗口外条目时，生成 md 的来源行不得出现。"""
        sina = _load_rows(self.tmp, "sina.jsonl", [self.in_window, self.before, self.after])
        em = _load_rows(self.tmp, "em.jsonl", [])
        data = {
            "date": "2026-08-21",
            "evt_prefix": "evt-20260821",
            "window": "2026-08-21 00:00:00—2026-08-21 08:00:00（北京时间）",
            "cutoff": "2026-08-21 08:00",
            "trading_day": "2026-08-21（星期五，A股正常开市）",
            "NEW": [[
                "evt-20260821-001", 80,
                "覆盖25 + 变化25 + 绝对热度15 + 新鲜度15 + 频次5",
                "美加贸易谈判破裂：测试事件",
                "测试核心信息（新浪7×24）。",
                ["美加贸易谈判"], "测试信号。", "08-21 测试反馈。", "测试边界。",
                "测试热度变化。", "08-21（北京时间）。", "theme-test"]],
            "OLD": [],
            "THEMES": [["theme-test", "测试主题", "测试催化。", [1]]],
            "other_news": "", "pending": [], "coverage": [],
        }
        data_path = Path(self.tmp) / "data.json"
        data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        out = Path(self.tmp) / "out.md"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "gen_report.py"),
             "--data", str(data_path), "--sina", sina, "--em", em,
             "--out", str(out)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        md = out.read_text(encoding="utf-8")
        self.assertIn("2026-08-21 07:30:00", md)
        self.assertNotIn("2026-08-14 10:00:00", md, "窗口前条目不得进入来源表")
        self.assertNotIn("2026-08-24 12:00:00", md, "窗口后条目不得进入来源表")


def _base_data():
    return {
        "date": "2026-08-21", "evt_prefix": "evt-20260821",
        "window": "2026-08-21 00:00:00—2026-08-21 08:00:00（北京时间）",
        "cutoff": "2026-08-21 08:00", "trading_day": "2026-08-21",
        "NEW": [
            ["evt-20260821-001", 90, "b", "事件一", "c", ["k1"], "s", "f", "bo", "h", "se", "theme-a"],
            ["evt-20260821-002", 70, "b", "事件二", "c", ["k2"], "s", "f", "bo", "h", "se", "theme-b"],
        ],
        "OLD": [["evt-20260821-101", 40, "b", "旧闻（昨日已定价）", "c", ["k3"], "s", "f", "bo", "h", "se", "theme-c"]],
        "THEMES": [
            ["theme-a", "A", "x", [1]],
            ["theme-b", "B", "x", [2]],
            ["theme-c", "C", "x", [101]],
        ],
    }


class ContractPrecheckTests(unittest.TestCase):
    """事故2回归：契约预检必须拦住全部已知违规，放行合法结构。"""

    def errs(self, mutate):
        d = _base_data()
        mutate(d)
        return gen_report._contract_errors(d)

    def test_valid_data_passes(self):
        self.assertEqual(self.errs(lambda d: None), [])

    def test_single_item_theme_is_legal(self):
        # 用户裁定 2026-08-19：允许单条主题；theme-c 本就是单条
        self.assertEqual([e for e in self.errs(lambda d: None) if "单条" in e], [])

    def test_score_ascending_rejected(self):
        def m(d):
            d["NEW"][0][1], d["NEW"][1][1] = 60, 90
        self.assertTrue(any("递增" in e for e in self.errs(m)))

    def test_empty_theme_rejected(self):
        def m(d):
            d["THEMES"].append(["theme-x", "X", "x", []])
        self.assertTrue(any("无成员" in e for e in self.errs(m)))

    def test_theme_id_mismatch_rejected(self):
        def m(d):
            d["NEW"][0][11] = "theme-wrong"
        self.assertTrue(any("应改为 theme-a" in e for e in self.errs(m)))

    def test_duplicate_evt_rejected(self):
        def m(d):
            d["THEMES"][1][3] = [1]  # theme-b 也引用 evt 1
        self.assertTrue(any("多个主题" in e for e in self.errs(m)))

    def test_missing_evt_reference_rejected(self):
        def m(d):
            d["THEMES"].append(["theme-y", "Y", "x", [99]])
        self.assertTrue(any("不存在" in e for e in self.errs(m)))


class LegacyTagDedupTests(unittest.TestCase):
    """事故3回归：OLD 标题已含"（昨日已定价）"时不重复追加。"""

    def test_card_tag_not_duplicated(self):
        rec = ["evt-20260821-101", 40, "b", "旧闻（昨日已定价）", "c", ["k"],
               "s", "f", "bo", "h", "se", "theme-c"]
        (evt, score, bd, title, core, keys, signal, feedback,
         boundary, heat, session, theme) = rec
        md = gen_report.card(3, evt, title, score, bd, core, keys,
                             "| ch | t | [x](https://e.com) |",
                             signal, feedback, boundary, heat, session, theme,
                             legacy=True)
        self.assertEqual(md.count("（昨日已定价）"), 1)


if __name__ == "__main__":
    unittest.main()
