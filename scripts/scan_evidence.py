#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 evidence JSONL 扫描候选账本：按主题词带输出命中摘要（时间+来源+是否有链接）。
用法: python3 scripts/scan_evidence.py --sina evidence/sina7x24-window-*.jsonl \
        --em evidence/em7x24-window-*.jsonl [--themes "存储,机器人,算力"] [--with-link-only]
分析阶段的发现层用（全窗口遍历），不替代最终报告的人工裁决。"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_THEMES = {
    "存储/半导体": ["存储芯片", "内存", "SK海力士", "铠侠", "DRAM", "长鑫", "HBM", "存储荒", "三星", "KOSPI", "美光", "闪迪", "NAND"],
    "算力/CPO/光通信": ["算力", "CPO", "光通信", "英伟达", "OpenAI", "液冷", "超节点", "硅光", "PCB", "载板", "Spectrum"],
    "机器人": ["宇树", "机器人", "人形", "LG电子", "机器人大会", "机械臂"],
    "宏观/政策": ["国务院", "李强", "统计局", "社零", "国新办", "逆回购", "六张网", "消费"],
    "材料/小金属": ["磷化铟", "铱", "锗", "锑", "铪", "ABF", "味之素", "CMP", "铜箔", "覆铜板"],
    "航天": ["朱雀", "蓝箭", "火箭", "发射", "卫星", "SpaceX"],
    "美股/隔夜": ["美股", "道指", "纳指", "标普", "收盘", "BTIG"],
    "海外利率": ["日本", "国债收益", "日债", "通胀"],
    "公司/公告": ["半年报", "半年报", "业绩", "公告", "惠誉", "评级"],
}


def load(paths, text_fn):
    rows = []
    for pat in paths:
        for p in sorted(Path(".").glob(pat)):
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = text_fn(r)
                if t:
                    rows.append((r, t))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sina", action="append", default=["evidence/sina7x24-window-*.jsonl"])
    ap.add_argument("--em", action="append", default=["evidence/em7x24-window-*.jsonl"])
    ap.add_argument("--themes", default=None, help="逗号分隔的主题名（默认全部）")
    ap.add_argument("--with-link-only", action="store_true", help="只输出带 docurl/url 的命中")
    ap.add_argument("--max", type=int, default=10, help="每个主题最多输出条数")
    args = ap.parse_args()

    def sina_text(r):
        return r.get("rich_text", "") or ""

    def em_text(r):
        return (r.get("title") or "") + " " + (r.get("summary") or "")

    sina = load(args.sina, sina_text)
    em = load(args.em, em_text)

    themes = DEFAULT_THEMES
    if args.themes:
        pick = {name.strip() for name in args.themes.split(",")}
        use = {k: v for k, v in themes.items() if k in pick}
        themes = use or themes

    for name, keys in themes.items():
        hits = []
        for r, t in sina:
            if any(k in t for k in keys):
                if args.with_link_only and not r.get("docurl"):
                    continue
                hits.append((r.get("create_time", ""), "sina", t, bool(r.get("docurl"))))
        for r, t in em:
            if any(k in t for k in keys):
                if args.with_link_only and not r.get("url"):
                    continue
                hits.append((r.get("time", ""), "em", t, bool(r.get("url"))))
        hits.sort(key=lambda h: h[0])
        print("\n===== {} | {} 条 (sina+em)".format(name, len(hits)))
        for h in hits[:args.max]:
            tag = "LINK" if h[3] else "    "
            print("  {} [{}][{}] {}".format(h[0], h[1], tag, h[2][:100]))


if __name__ == "__main__":
    main()
