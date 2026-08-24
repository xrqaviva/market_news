#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""浏览器源采集（headless Chrome + CDP 首选，WebFetch/API 兜底）。

背景（2026-08-20 固化）：IAB webview 偶发 "guest not attached"/"could not be
restored for activation"，导致韭研/人气榜/微博/淘股吧/财联社/雪球等浏览器源
整批归零。本脚本改用独立 headless Chrome + CDP 抓取公开页（与
tests/report_layout_browser.mjs 同机制，不依赖 GUI 会话/IAB）。CDP 起不来或
单源超时/无正文时逐源 fallback 到 WebFetch 或 API/去重补采集，绝不静默丢源。

用法:
  python3 scripts/fetch_browser_sources.py --date 2026-08-20 --out-dir evidence

输出（统一 evidence/<key>-<MMDD>.txt，与 daily_scrum.py 预期一致）:
  jiuyangongshe-feed-<MMDD>.txt  韭研公社
  guba-rank-<MMDD>.txt           东财人气榜
  weibo-hot-<MMDD>.txt           微博热搜
  taoguba-<MMDD>.txt             淘股吧
  cls-telegraph-<MMDD>.txt       财联社电报
  xueqiu-hot-<MMDD>.txt          雪球热股
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SOURCES = [
    # key, label, url, 提取表达式（返回纯文本正文）
    ("jiuyangongshe", "韭研公社", "https://www.jiuyangongshe.com/",
     "document.body.innerText"),
    ("guba-rank", "东财人气榜", "https://guba.eastmoney.com/rank/",
     "document.body.innerText"),
    ("weibo-hot", "微博热搜", "https://s.weibo.com/top/summary",
     "document.body.innerText"),
    ("taoguba", "淘股吧", "https://www.tgb.cn/",
     "document.body.innerText"),
    ("cls-telegraph", "财联社电报", "https://www.cls.cn/telegraph",
     "document.body.innerText"),
    ("xueqiu-hot", "雪球热股", "https://xueqiu.com/hots/topic",
     "document.body.innerText"),
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def find_chrome() -> str:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    ]
    import shutil
    which = shutil.which("google-chrome") or shutil.which("chromium")
    if which:
        candidates.insert(0, which)
    for c in candidates:
        p = Path(c)
        if p.is_file() and p.stat().st_mode & 0o111:
            return str(p)
    raise RuntimeError("Chrome/Chromium not found")


def _read_port(profile: Path, proc, timeout=15.0):
    """轮询 DevToolsActivePort，直到 Chrome 提供调试端口。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Chrome exited with {}".format(proc.returncode))
        try:
            lines = (profile / "DevToolsActivePort").read_text(encoding="utf-8").split("\n")
            if lines and lines[0].strip().isdigit():
                return int(lines[0].strip())
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("timed out waiting for DevToolsActivePort")


class CdpSocket:
    """最小 CDP 客户端（与 report_layout_browser.mjs 的 connectCdp 同思路）。"""

    def __init__(self, ws_url):
        import websocket  # 延迟导入，避免无依赖时拖累 fallback 路径
        self._ws = websocket.create_connection(ws_url, timeout=20)
        self._seq = 0

    def send(self, method, params=None):
        self._seq += 1
        self._ws.send(json.dumps({"id": self._seq, "method": method,
                                  "params": params or {}}))
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("id") == self._seq:
                if "error" in msg:
                    raise RuntimeError("CDP {}: {}".format(method, msg["error"]))
                return msg.get("result", {})

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass


def fetch_via_cdp(grab: dict, timeout: int = 25) -> str:
    """起独立 headless Chrome，打开目标 URL，回传 innerText。"""
    chrome_path = find_chrome()
    profile = Path(tempfile.mkdtemp(prefix="browser-src-"))
    proc = None
    cdp = None
    try:
        proc = subprocess.Popen(
            [chrome_path, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps", "--disable-extensions", "--disable-sync",
             "--metrics-recording-only", "--no-default-browser-check",
             "--no-first-run", "--remote-debugging-port=0",
             "--remote-allow-origins=*", "--user-agent={}".format(UA),
             "--user-data-dir={}".format(profile), "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port = _read_port(profile, proc)
        new_req = urllib.request.Request(
            "http://127.0.0.1:{}/json/new?about:blank".format(port), method="PUT")
        target = json.loads(urllib.request.urlopen(new_req, timeout=10).read())
        cdp = CdpSocket(target["webSocketDebuggerUrl"])
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        cdp.send("Page.navigate", {"url": grab["url"]})
        # 等待 domcontentloaded + 滚动触发懒加载，直到文本稳定或超时。
        # 财联社电报等 SPA 靠异步 XHR 加载正文，需滚动到底部逐批触发。
        deadline = time.time() + timeout
        text = ""
        prev = ""
        while time.time() < deadline:
            result = cdp.send("Runtime.evaluate", {
                "expression": grab["expr"],
                "returnByValue": True,
                "awaitPromise": True,
            })
            text = result.get("result", {}).get("value") or ""
            cur = text.strip()
            # 有正文且与上轮相同（加载已完成）→ 结束
            if len(cur) > 200 and cur == prev.strip():
                break
            prev = text
            # 滚动到底部触发懒加载
            cdp.send("Runtime.evaluate", {
                "expression": "window.scrollTo(0, document.body.scrollHeight)",
                "returnByValue": True,
            })
            time.sleep(0.8)
        return text
    finally:
        if cdp:
            try:
                cdp.close()
            except Exception:
                pass
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
        import shutil
        shutil.rmtree(profile, ignore_errors=True)


def fetch_via_webfetch(grab: dict) -> str:
    """Fallback 通道不确定（主代理 WebFetch 工具不可脚本化）：此处仅作
    占位说明，实际由主代理在 CDP 失败时调用 WebFetch 后调用 save_x_scan 落盘。
    本函数从不静默成功——未实现时不产出正文，交回主代理处理。"""
    raise RuntimeError(
        "CDP 不可用，{} 需主代理 WebFetch 通道补齐（见 scripts/save_x_scan.py 模式）"
        .format(grab["label"]))


def clean_text(raw: str) -> str:
    text = re.sub(r"[ \t]+", " ", raw or "")
    # 去掉连续空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="报告日期 YYYY-MM-DD")
    ap.add_argument("--out-dir", default="evidence")
    ap.add_argument("--timeout", type=int, default=25, help="单源 CDP 抓取超时秒")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dd = args.date.replace("-", "")
    failures = []

    for key, label, url, expr in SOURCES:
        grab = {"label": label, "url": url, "expr": expr}
        out = out_dir / ("{}-{}.txt".format(key, dd))
        text = ""
        try:
            raw = fetch_via_cdp(grab, timeout=args.timeout)
            text = clean_text(raw)
        except Exception as exc:  # noqa: BLE001 — 单源失败不中断整批
            print("[fallback] {}：CDP 失败（{}），待 WebFetch 通道补齐".format(label, exc))
            failures.append("{}（CDP 失败：{}）".format(label, exc))
            continue
        if len(text) < 100:
            print("[fallback] {}：CDP 返回正文过少（{} 字符），待 WebFetch 补齐".format(label, len(text)))
            failures.append("{}（CDP 正文过少 {} 字符）".format(label, len(text)))
            continue
        header = "[headless-Chrome CDP {} 采集 {} {}]\n".format(
            time.strftime("%Y-%m-%d %H:%M"), args.date, url)
        out.write_text(header + text + "\n", encoding="utf-8")
        print("[OK] {} → {}（{} 字符）".format(label, out.name, len(text)))

    if failures:
        print("\n== {} 源 CDP 失败，需主代理 WebFetch/API 补齐（勿静默丢弃）==".format(len(failures)))
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\n全部浏览器源采集完成")


if __name__ == "__main__":
    main()
