#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 WebFetch 返回的 X 大V帖文解析结果落盘为 evidence/x-<handle>-<date>.txt。

用途：主代理对 config/x-influencers.json 中每个 handle 执行 WebFetch 后，
把结构化的帖文列表喂给本脚本（stdin 或 --text 文件），自动生成标准 evidence 文件，
避免手工命名/格式不一致，确保 daily_scrum 能正确核查到。

用法：
  python3 scripts/save_x_scan.py --handle <handle> --date 2026-08-19 \\
      --text <webfetch-output.txt>            # 或从 stdin 传

落盘格式：
  [WebFetch <date> 采集 @<handle> 公开主页]
  <逐行帖文摘要 + 链接>
"""
import argparse
import sys
from datetime import date as _date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True, help="X handle（不含 @）")
    ap.add_argument("--date", default=str(_date.today()), help="YYYY-MM-DD")
    ap.add_argument("--text", default=None, help="WebFetch 输出文本文件；缺省读 stdin")
    args = ap.parse_args()

    if args.text:
        content = Path(args.text).read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    handle = args.handle.lstrip("@")
    out = ROOT / "evidence" / "x-{}-{}.txt".format(handle, args.date.replace("-", ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "[WebFetch {} 采集 @{} 公开主页]\n{}".format(args.date, handle, content),
        encoding="utf-8",
    )
    print("saved:", out)


if __name__ == "__main__":
    main()
