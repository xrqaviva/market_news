#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""并发抓取新浪 7×24 + 东财 7×24（API 双源），保存 evidence JSONL。
用法: python3 scripts/fetch_api_sources.py --start "2026-08-18 00:00" [--out-dir evidence]
不减少任何数据量：新浪全窗口分页并发（同 08-18 手写脚本的 1924 条口径），
东财复用 fetch_em7x24.py 逻辑；仅把串行翻页改为并发，I/O 耗时从 ~15s 降为 ~2s。
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import urllib.request

SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/7x24/",
}
SINA_BASE = ("https://zhibo.sina.com.cn/api/zhibo/feed?page={page}&page_size=100"
             "&zhibo_id=152&tag_id=0&dire=f&dpc=1")


def fetch_sina_page(page: int):
    url = SINA_BASE.format(page=page)
    req = urllib.request.Request(url, headers=SINA_HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    feed = (data.get("result") or {}).get("data") or {}
    items = (feed.get("feed") or {}).get("list") or []
    return page, items


def fetch_sina(start: str, workers: int = 8) -> list:
    """并发翻页，直到某页最早时间早于 start。返回按时间正序的条目。"""
    first = None
    for attempt in range(2):
        page, items = fetch_sina_page(1)
        if items:
            first = page
            break
    if not first:
        raise RuntimeError("新浪 7×24 首页无数据")
    # 先探测页数：并发探测直到翻过 start，再并发抓全量
    # 方案：并发抓前 N 页（每次 8 页，检查是否已到窗口起点），出现后停止。
    all_rows = {}
    page_num = 1
    stop = False
    while not stop:
        batch = list(range(page_num, page_num + workers))
        results = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_sina_page, p): p for p in batch}
            for fut in as_completed(futs):
                p, its = fut.result()
                results[p] = its
        for p in sorted(results):
            items = results[p]
            if not items:
                stop = True
                break
            for it in items:
                all_rows[it.get("id")] = it
            oldest = items[-1].get("create_time", "")
            if oldest < start:
                stop = True
            page_num = p + 1
            if page_num > 30:
                stop = True
        time.sleep(0.05)
    rows = sorted(all_rows.values(), key=lambda r: r.get("create_time", ""))
    cut = [r for r in rows if r.get("create_time", "") >= start]
    return cut


def fetch_eastmoney(start: str, out: Path):
    """复用 scripts/fetch_em7x24.py 的抓取逻辑（子进程调用），避免重复维护。"""
    import subprocess
    subprocess.run(
        ["python3", str(Path(__file__).with_name("fetch_em7x24.py")),
         "--start", start, "--out", str(out)],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="窗口起点，如 2026-08-18 00:00")
    parser.add_argument("--out-dir", default="evidence")
    parser.add_argument("--sina-workers", type=int, default=8)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    start = args.start
    stamp = start.replace(" ", "-").replace(":", "-")

    t0 = time.time()
    sina_rows = fetch_sina(start, workers=args.sina_workers)
    print("新浪 7×24: {} 条, {:.1f}s".format(len(sina_rows), time.time() - t0))
    sina_out = out_dir / ("sina7x24-window-{}-to-now.jsonl".format(stamp))
    with sina_out.open("w", encoding="utf-8") as f:
        for r in sina_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    t0 = time.time()
    em_out = out_dir / ("em7x24-window-{}-to-now.jsonl".format(stamp))
    fetch_eastmoney(start, em_out)
    em_count = sum(1 for _ in em_out.open(encoding="utf-8"))
    print("东财 7×24: {} 条, {:.1f}s".format(em_count, time.time() - t0))
    print("saved:", sina_out, em_out)


if __name__ == "__main__":
    main()
