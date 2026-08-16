#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch eastmoney 7x24 feed into a JSONL evidence file.

Eastmoney 7x24 is the SECOND discovery source alongside sina 7x24. It carries
CLS (财联社) telegrams and eastmoney-original research/industry articles that
sina 7x24 often misses (e.g. SK Hynix Dalian factory, CRO/CPO rotation, SST
solid-state transformer series). Run this for every report window so the two
feeds are traversed as a UNION.

Usage:
  python3 scripts/fetch_em7x24.py --start "2026-08-14 12:00:00" \
      --out evidence/em7x24-window-<start>-to-<end>.jsonl
"""
import argparse, json, time, urllib.request
from datetime import datetime, timedelta

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Referer": "https://finance.eastmoney.com/7x24.html",
}


def fetch(page: int) -> dict:
    url = (
        "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        "?client=web&biz=web_724&column=350&order=1&needInteractData=0"
        f"&page_index={page}&page_size=100&req_trace={page}"
    )
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help='window start, e.g. "2026-08-14 12:00:00"')
    ap.add_argument("--out", required=True, help="output JSONL path")
    args = ap.parse_args()

    rows, page, stop = [], 1, False
    while not stop and page <= 80:
        d = fetch(page)
        lst = (d.get("data") or {}).get("list") or []
        if not lst:
            break
        for x in lst:
            t = (x.get("showTime") or "").strip()
            rows.append({
                "time": t,
                "title": (x.get("title") or "").strip(),
                "summary": (x.get("summary") or "").strip(),
                "media": x.get("mediaName") or "",
                "url": x.get("uniqueUrl") or "",
            })
            if t and t < args.start:
                stop = True
        page += 1
        time.sleep(0.5)

    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("total:", len(rows), "| first:", rows[0]["time"] if rows else None,
          "| last:", rows[-1]["time"] if rows else None, "| stop:", stop)


if __name__ == "__main__":
    main()
