#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键同步新增报告后的测试计数断言（避免每次手改十几个数字）。

每次生成新报告后运行本脚本，自动同步三处测试：
1. tests/test_web_parser.py 的 test_all_report_model_field_counts（字段计数）
2. tests/test_web_build.py 的 report_count / len(manifest) / latest
3. tests/report_layout_browser.mjs 的 EXPECTED_REPORT_OUTPUT_BY_INPUT 与
   buildInputs.length

用法: python3 scripts/sync_test_suite.py [--project-root .]

只重算随报告数/条数变化的聚合数字，不改采集/生成/数据逻辑。纯测试同步。
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_docs(root):
    from web.report_parser import discover_reports, parse_report
    found = dict((e.report_id, (p, e)) for p, e in discover_reports(root))
    docs = {}
    paths = {}
    for rid, (p, e) in found.items():
        docs[rid] = parse_report(p, e)
        paths[rid] = p
    return docs, paths


def _num(text, pat):
    m = re.search(pat, text)
    return int(m.group(1)) if m else None


def sync_parser(path, n, totals):
    s = path.read_text(encoding="utf-8")
    s2 = s
    # len(items)
    m = re.search(r"self\.assertEqual\((\d+), len\(items\)\)", s2)
    if m:
        s2 = s2.replace(m.group(0), "self.assertEqual({}, len(items))".format(n), 1)
    # sources
    m = re.search(r"self\.assertEqual\((\d+), sum\(len\(item\.sources\) for item in items\)\)", s2)
    if m:
        s2 = s2.replace(m.group(0), "self.assertEqual({}, sum(len(item.sources) for item in items))".format(totals["sources"]), 1)
    # supplemental_details
    m = re.search(r"self\.assertEqual\((\d+), sum\(len\(item\.supplemental_details\) for item in items\)\)", s2)
    if m:
        s2 = s2.replace(m.group(0), "self.assertEqual({}, sum(len(item.supplemental_details) for item in items))".format(totals["supplemental"]), 1)
    # boolean fields
    bool_map = {
        "core": "core", "score_breakdown": "score_breakdown", "signal": "signal",
        "market_feedback": "market_feedback", "boundary": "boundary",
        "heat_change": "heat_change", "release_session": "release_session",
    }
    for key, field in bool_map.items():
        pat = "sum(bool(item.{}) for item in items)".format(field)
        m = re.search(r"self\.assertEqual\((\d+), " + re.escape(pat) + r"\)", s2)
        if m:
            s2 = s2.replace(m.group(0), "self.assertEqual({}, {})".format(totals[key], pat), 1)
    # catalog: 报告数 len(found)
    m = re.search(r"self\.assertEqual\((\d+), len\(found\)\)", s2)
    if m:
        s2 = s2.replace(m.group(0), "self.assertEqual({}, len(found))".format(len(_RIDS_GLOBAL)), 1)
    if s2 != s:
        path.write_text(s2, encoding="utf-8")
        return True
    return False


def sync_catalog(path, rids):
    s = path.read_text(encoding="utf-8")
    pat = re.compile(r'\[\n(?:                "\d{8}-\d{4}",\n)*?            \]', re.MULTILINE)
    m = pat.search(s)
    if not m:
        return False
    entries = "\n".join('                "{}",'.format(r) for r in rids)
    s2 = s.replace(m.group(0), "[\n{}\n            ]".format(entries))
    s2 = re.sub(r"(self\.assertEqual\()\d+(, len\(found\)\))", lambda mo: "{}{}".format(mo.group(1), len(rids)) + mo.group(2), s2)
    if s2 != s:
        path.write_text(s2, encoding="utf-8")
        return True
    return False


def sync_build(path, rids, latest):
    s = path.read_text(encoding="utf-8")
    s2 = re.sub(
        r"(self\.assertEqual\()\d+(, result\.report_count\))",
        lambda mo: mo.group(1) + str(len(rids)) + mo.group(2), s)
    s2 = re.sub(
        r'(self\.assertEqual\()\d+(, len\(manifest\["reports"\]\)\))',
        lambda mo: mo.group(1) + str(len(rids)) + mo.group(2), s2)
    s2 = re.sub(
        r'self\.assertEqual\("reports/\d{4}-\d{2}-\d{2}-\d{4}\.html", manifest\["latest"\]\)',
        'self.assertEqual("{}", manifest["latest"])'.format(latest), s2)
    if s2 != s:
        path.write_text(s2, encoding="utf-8")
        return True
    return False


def sync_layout(path, md_files):
    # md_files: report_id -> 源文件名（带横线，如 2026-08-19-0800-news-ranking-preview.md）
    s = path.read_text(encoding="utf-8")
    s2 = s
    s2 = re.sub(
        r"if \(buildInputs\.length !== \d+\) \{",
        "if (buildInputs.length !== {}) {{".format(len(md_files)), s2)
    for rid, mdname in md_files.items():
        md = "reports/" + mdname
        if md not in s2:
            # html 名：2026-08-19-0800.html
            slot = rid[9:]  # 0800/1500/1800
            dt = rid[:4] + "-" + rid[4:6] + "-" + rid[6:8]
            html = "reports/{}-{}.html".format(dt, slot)
            insert = '  ["{}", "{}"],\n'.format(md, html)
            # 只插到 EXPECTED_REPORT_OUTPUT_BY_INPUT map 的收尾 "]);" 前，
            # 不能 rfind 全文件最后一个 "]);"（后面 Promise.race 等也有 "]);"）。
            m = re.search(
                r"const EXPECTED_REPORT_OUTPUT_BY_INPUT = new Map\(\[(.*?)\n\]\);",
                s2, re.S)
            if m:
                idx = m.end() - 2  # 落到 "]);" 前
                s2 = s2[:idx] + insert + s2[idx:]
    if s2 != s:
        path.write_text(s2, encoding="utf-8")
        return True
    return False


_RIDS_GLOBAL = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=str(ROOT))
    args = ap.parse_args()
    root = Path(args.project_root)
    sys.path.insert(0, str(root))

    docs, paths = load_docs(root)
    rids = sorted(docs.keys())
    global _RIDS_GLOBAL
    _RIDS_GLOBAL = rids
    items = [item for d in docs.values() for item in d.items]
    n = len(items)
    totals = {
        "sources": sum(len(i.sources) for i in items),
        "core": sum(bool(i.core) for i in items),
        "score_breakdown": sum(bool(i.score_breakdown) for i in items),
        "signal": sum(bool(i.signal) for i in items),
        "market_feedback": sum(bool(i.market_feedback) for i in items),
        "boundary": sum(bool(i.boundary) for i in items),
        "heat_change": sum(bool(i.heat_change) for i in items),
        "release_session": sum(bool(i.release_session) for i in items),
        "supplemental": sum(len(i.supplemental_details) for i in items),
    }
    latest_rid = rids[-1]
    slot = latest_rid[9:]  # 0800/1500/1800（report_id 形如 20260819-0800）
    late_dt = latest_rid[:4] + "-" + latest_rid[4:6] + "-" + latest_rid[6:8]
    latest_html = "reports/{}-{}.html".format(late_dt, slot)  # e.g. 2026-08-19-0800.html
    print("reports:", len(rids), "latest:", latest_html, "items:", n)
    print("totals:", totals)

    changed = []
    p1 = root / "tests/test_web_parser.py"
    if sync_parser(p1, n, totals): changed.append(str(p1))
    if sync_catalog(p1, rids): changed.append(str(p1) + " (catalog)")
    p2 = root / "tests/test_web_build.py"
    if sync_build(p2, rids, latest_html): changed.append(str(p2))
    p3 = root / "tests/report_layout_browser.mjs"
    md_files = {rid: paths[rid].name for rid in rids}
    if sync_layout(p3, md_files): changed.append(str(p3))
    print("synced:", changed if changed else "（无变化，已是最新）")


if __name__ == "__main__":
    main()
