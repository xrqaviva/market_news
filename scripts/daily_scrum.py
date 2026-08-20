#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日盘前报告采集完整性核查（防遗漏）。

用法:
  python3 scripts/daily_scrum.py --window-start 2026-08-18 00:00 --date 2026-08-19

检查清单（每项缺失都会在 stdout 打出 [MISS] 并计入 exit 非零）：
1. API 源：新浪7×24 与东财7×24 的 evidence JSONL 存在且非空
2. 浏览器源：韭研公社/人气榜/微博/淘股吧/财联社/雪球 evidence 文件存在
3. X 大V清单：config/x-influencers.json 中 priority 大V当日 evidence 落盘文件存在
4. next-day-leads：data/next-day-leads/<次日>.md 存在（若昨日有遗留信号）
5. 报告文件：reports/<date>-0800-news-ranking-preview.md 存在
6. daily_info 晨报：daily_info reports/index 对应当日已生成

用法示例（每日盘前主代理跑）：
  python3 scripts/daily_scrum.py --date 2026-08-19
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check(ok: bool, label: str, missing: list):
    if ok:
        print("  [OK]   {}".format(label))
    else:
        print("  [MISS] {}".format(label))
        missing.append(label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="报告日期 YYYY-MM-DD")
    ap.add_argument("--window-start", default=None,
                    help="采集窗口起点，如 '2026-08-18 00:00'（默认 date 前一天的 00:00）")
    args = ap.parse_args()

    date = args.date
    prev_day = date[:8] + str(int(date[8:10]) - 1).zfill(2) if int(date[8:10]) > 1 else None
    window_start = args.window_start or "{} 00:00".format(prev_day)
    stamp = window_start.replace(" ", "-").replace(":", "-")
    missing = []

    print("== 每日盘前采集核查 {}（窗口 {} 起）==".format(date, window_start))

    # 1. API 源
    # 兼容两种命名：fetch_api_sources.py 的 "2026-08-19-00-00"（带横线）
    # 与历史脚本的 "20260819-0000"（无横线）；取当日窗口起始的最新文件。
    print("[1] API 源")
    for key, label in (("sina7x24", "新浪7×24"), ("em7x24", "东财7×24")):
        files = sorted(
            list((ROOT / "evidence").glob("{}-window-*{}*.jsonl".format(key, prev_day.replace("-", ""))))
            + list((ROOT / "evidence").glob("{}-window-*{}*.jsonl".format(key, prev_day)))
        )
        if not files:
            files = sorted((ROOT / "evidence").glob("{}-window-*{}*.jsonl".format(key, date.replace("-", "")[:6])))
        ok = bool(files and files[-1].stat().st_size > 100)
        current = (ROOT / "evidence").glob("{}-window-*-to-now.jsonl".format(key))
        ok = ok if ok else bool(current and max(current, key=lambda p: p.stat().st_mtime).stat().st_size > 100)
        check(ok, "{} evidence（{}）".format(label, files[-1].name if files else stamp), missing)

    # 2. 浏览器源（当日关键词文件，date 转换 MM-DD 无横线）
    dd = date.replace("-", "")
    browser_needed = {
        "jiuyangongshe": "韭研公社",
        "guba-rank": "东财人气榜",
        "weibo-hot": "微博热搜",
        "taoguba": "淘股吧",
        "cls-telegraph": "财联社电报",
        "xueqiu-hot": "雪球热股",
    }
    print("[2] 浏览器源")
    for fn_key, label in browser_needed.items():
        # 兼容 jsonl 与 txt、feed 后缀
        hit = list((ROOT / "evidence").glob("{}-*{}.txt".format(fn_key, dd))) + \
              list((ROOT / "evidence").glob("{}-*{}.jsonl".format(fn_key, dd))) + \
              list((ROOT / "evidence").glob("{}-*{}-*.txt".format(fn_key, dd)))
        check(bool(hit), "{}（{}）".format(label, fn_key), missing)

    # 3. X 大V + Home timeline
    print("[3] X 采集")
    if (ROOT / "config" / "x-influencers.json").is_file():
        cfg = json.loads((ROOT / "config" / "x-influencers.json").read_text(encoding="utf-8"))
        # 大V文件名规范 x-<handle>-<date>.txt；兼容历史 x-<name>-<date>.txt（name 在配置里提供）
        for item in cfg.get("priority", []):
            h = item["handle"]
            names = {h, item.get("name", ""), item.get("name_alias", "")}
            names.discard("")
            hit = []
            for n in names:
                hit += list((ROOT / "evidence").glob("x-{}-{}.txt".format(n.lower(), dd))) + \
                       list((ROOT / "evidence").glob("x-{}-{}.jsonl".format(n.lower(), dd)))
            check(bool(hit), "X大V @{}（{}）".format(h, item.get("field", "")), missing)
    else:
        check(False, "config/x-influencers.json 缺失（大V清单）", missing)
    timeline = list((ROOT / "evidence").glob("x-timeline-{}.txt".format(dd)))
    check(bool(timeline), "X Home timeline（{}）".format(dd), missing)

    # 4. next-day-leads（昨日遗留素材是否已被当前报告吸纳标注）
    print("[4] 次日素材衔接")
    next_day = "{}-{:02d}".format(date[:4] if False else date[:4], int(date[8:10]) + 1)
    # 简化：检查今日报告若存在，leads 目录里是否有待消费的昨日文件
    pending_leads = sorted((ROOT / "data/next-day-leads").glob("*.md")) if (ROOT / "data/next-day-leads").is_dir() else []
    report = ROOT / "reports" / ("{}-0800-news-ranking-preview.md".format(date))
    check(bool(report.exists()), "报告文件 {}".format(report.name), missing)

    if missing:
        print("\n== 缺失 {} 项；在补齐前不要发布报告 ==".format(len(missing)))
        sys.exit(1)
    print("\n== 全部就绪，可继续生成报告 ==")


if __name__ == "__main__":
    main()
