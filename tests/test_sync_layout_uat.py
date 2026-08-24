# -*- coding: utf-8 -*-
"""sync_test_suite.sync_layout UAT（2026-08-24 闭环审计配套）。

回归背景：sync_layout 曾用 rfind 全文最后一个 "]);" 定位插入点，把新报告
条目插进文件末尾 Promise.race([...]) 的数组里，破坏 layout 测试脚本；
修复后又出现偏移一格（插到 "]);" 的 "]" 与 ")" 之间）。本测试锁定：
新条目必须插入 EXPECTED_REPORT_OUTPUT_BY_INPUT map 内部、其余代码原样。
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys_path = str(ROOT / "scripts")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

LAYOUT = ROOT / "tests" / "report_layout_browser.mjs"


class SyncLayoutTests(unittest.TestCase):
    def _prepare(self, tmp, drop_entry=None):
        """复制当前 layout 脚本到 tmp；可选删除某条目模拟“新增报告未同步”。"""
        work = Path(tmp) / "report_layout_browser.mjs"
        s = LAYOUT.read_text(encoding="utf-8")
        if drop_entry:
            line = '  ["{}", "{}"],\n'.format(*drop_entry)
            assert line in s, "fixture entry missing in current layout script"
            s = s.replace(line, "")
        work.write_text(s, encoding="utf-8")
        return work

    def _node_check(self, path):
        proc = subprocess.run(["node", "--check", str(path)],
                              capture_output=True, text=True)
        return proc.returncode == 0, proc.stderr

    def test_insert_new_entry_inside_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self._prepare(tmp)
            from sync_test_suite import sync_layout  # noqa: E402
            md_files = {"20260901": "2026-09-01-0800-news-ranking-preview.md"}
            changed = sync_layout(work, md_files)
            self.assertTrue(changed)
            s = work.read_text(encoding="utf-8")
            m = s.index("const EXPECTED_REPORT_OUTPUT_BY_INPUT = new Map([")
            e = s.index("]);", m)
            # 新条目必须落在 map 内部
            self.assertIn("reports/2026-09-01-0800-news-ranking-preview.md", s[m:e])
            # map 收尾之后不得再出现该条目（不污染后续代码）
            self.assertNotIn("2026-09-01-0800-news-ranking-preview.md", s[e + 3:])
            ok, err = self._node_check(work)
            self.assertTrue(ok, err)

    def test_reinsert_missing_entry_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = ("reports/2026-08-24-0800-news-ranking-preview.md",
                     "reports/2026-08-24-0800.html")
            work = self._prepare(tmp, drop_entry=entry)
            import sys
            sys.path.insert(0, sys_path)
            from sync_test_suite import sync_layout  # noqa: E402
            rid = "20260824"
            changed = sync_layout(work, {rid: entry[0].replace("reports/", "")})
            self.assertTrue(changed)
            s1 = work.read_text(encoding="utf-8")
            # 再跑一次应无变化（幂等）
            changed2 = sync_layout(work, {rid: entry[0].replace("reports/", "")})
            self.assertFalse(changed2)
            self.assertEqual(s1, work.read_text(encoding="utf-8"))
            ok, err = self._node_check(work)
            self.assertTrue(ok, err)


if __name__ == "__main__":
    unittest.main()
