#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 JSON 数据层 + evidence 自动生成符合解析器契约的盘前报告。

用法:
  python3 scripts/gen_report.py --data data/2026-08-18.json \\
      --sina "evidence/sina7x24-window-20260817-*.jsonl" \\
      --em "evidence/em7x24-window-20260817-*.jsonl" \\
      --out reports/2026-08-18-0800-news-ranking-preview.md

数据文件结构（JSON）:
{
  "date": "2026-08-18",
  "window": "2026-08-17 00:00:00—2026-08-18 08:20:00（北京时间）",
  "previous_trading_day": "2026-08-17（周一）12:00 之后发布/发生的事件为今日新事件（第一层），12:00 之前已定价旧闻按 0.4 折扣后置（第二层）",
  "cutoff": "2026-08-18 08:20",
  "NEW": [[evt_id, score, breakdown, title, core, [keys...], signal, feedback, boundary, heat, session, theme], ...],
  "OLD": [...同结构...],
  "THEMES": [[theme_id, name, catalyst, [evt_numbers...]], ...]
}
来源解析自动从 evidence 匹配 keys；无 docurl/url 的条目会把 keyword 标记为(no-link)，
生成器在输出前检查每卡至少 1 个 LINK，避免解析器 "needs a source link" 失败。
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _expand_pattern(pattern):
    """通配符按仓库根展开；绝对路径直接使用（便于外部管线/UAT 复用）。"""
    path = Path(pattern)
    if path.is_absolute():
        return [path] if path.is_file() else []
    return sorted(ROOT.glob(pattern))


def load_evidence(sina_patterns, em_patterns):
    sina, em = [], []
    for pat in sina_patterns:
        for p in _expand_pattern(pat):
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = r.get("rich_text", "") or ""
                if t:
                    sina.append((r.get("create_time", ""), r.get("docurl"), t))
    for pat in em_patterns:
        for p in _expand_pattern(pat):
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = (r.get("title") or "") + " " + (r.get("summary") or "")
                if t:
                    em.append((r.get("time", ""), r.get("url"), t))
    return sina, em


def parse_window(window_str):
    """解析 data["window"]（如 "2026-08-21 00:00:00—2026-08-24 08:00:00（北京时间）"）。

    返回 (start, end) 字符串元组；解析失败返回 None（不过滤，保持旧行为）。
    """
    if not window_str or "—" not in window_str:
        return None
    start, end = window_str.split("—", 1)
    start = start.strip()
    end = end.split("（")[0].strip()
    if len(start) >= 10 and len(end) >= 10:
        return start, end
    return None


def filter_window(rows, window_str, label=""):
    """只保留时间落在报告窗口内的来源条目（纵深防御）。

    即使 evidence 目录混入多日文件或参数传错，来源行也不会跨窗口污染
    （2026-08-24 审计事故的根本防线）。无法解析时间戳的条目一律丢弃。
    """
    bounds = parse_window(window_str)
    if not bounds:
        return rows
    start, end = bounds
    kept = [r for r in rows if r[0] and start <= r[0][:19] <= end]
    dropped = len(rows) - len(kept)
    if dropped:
        print("window-filter [{}]: dropped {} out-of-window entries".format(label, dropped),
              file=sys.stderr)
    return kept


def hits(sina, em, keywords):
    out = []
    for k in keywords:
        for time, url, t in sina:
            if k in t:
                out.append(("sina", time, url, t))
                break
        for time, url, t in em:
            if k in t:
                out.append(("em", time, url, t))
                break
    return out


def src_rows(sina, em, keys):
    rows = []
    for (channel, time, url, text) in hits(sina, em, keys):
        label = re.sub(r"^【(.*?)】.*$", r"\1", text)[:40]
        if url:
            rows.append("| {}7×24快讯 | {} | [{}]({}) |".format("新浪" if channel == "sina" else "东财", time, label, url))
    return "\n".join(rows)


def card(rank, evt, title, score, breakdown, core, keys, rows, signal, feedback, boundary, heat, session, theme, legacy):
    tag = "（昨日已定价）" if legacy and "（昨日已定价）" not in title else ""
    return (
        "#### 新闻：{}｜{}｜{}{}｜{}/100\n\n"
        "**热点权重：{}/100**（{}）\n\n"
        "**核心信息：** {}\n\n"
        "| 传播渠道 | 北京时间 | 时段与信息 |\n"
        "|---|---:|---|\n{}\n\n"
        "**关键信号/预期差：** {}\n\n"
        "**带时间市场反馈：** {}\n\n"
        "**判断边界：** {}\n\n"
        "**热度变化：** {}\n\n"
        "**发布时段：** {}\n\n"
        "**关联题材：** {}\n"
    ).format(rank, evt, title, tag, score, score, breakdown, core, rows, signal, feedback, boundary, heat, session, theme) if rows else None


def _contract_errors(data):
    """生成前一次列出全部契约错误（避免生成后解析器逐条失败→改→重生成）。"""
    errs = []
    new, old = data.get("NEW", []), data.get("OLD", [])
    themes = data.get("THEMES", [])
    cards = new + old
    evt_pfx = data.get("evt_prefix", "evt")
    def evt_id(n):
        return "{}-{:03d}".format(evt_pfx, int(n)) if str(n).isdigit() else str(n)

    if not new:
        errs.append("NEW 为空")
    # evt id 唯一
    seen = {}
    for c in cards:
        seen.setdefault(c[0], 0); seen[c[0]] += 1
    for e, cnt in seen.items():
        if cnt > 1:
            errs.append("重复 evt id: {}".format(e))
    # 分数非递增（跨层拼接顺序：NEW后OLD）
    scores = [c[1] for c in cards]
    for i in range(len(scores) - 1):
        if scores[i] < scores[i + 1]:
            errs.append("分数随排名递增(rank{}:{} < rank{}:{})：需重排或降分".format(i + 1, scores[i], i + 2, scores[i + 1]))
    # 主题：≥1 成员、evt 存在、无跨主题重复（2026-08-19 用户裁定：允许单条主题）
    meme = {}
    tid_count = {}
    for tid, _n, _c, nums in themes:
        full = [evt_id(n) for n in nums]
        tid_count[tid] = full
        if not full:
            errs.append("主题 {} 无成员".format(tid))
        for e in full:
            if e not in seen:
                errs.append("主题 {} 引用不存在的 {}(可并入相邻主题或补条目)".format(tid, e))
            meme.setdefault(e, []).append(tid)
    for e, tlist in meme.items():
        if len(tlist) > 1:
            errs.append("同一 evt {} 被多个主题引用 {}：需保持每主题成员互斥".format(e, tlist))
    # theme_ids 一致性：每主题成员必须在 NEWS 记录[11]标注对应 theme
    for tid, _n, _c, nums in themes:
        for n in nums:
            e = evt_id(n)
            rec = next((c for c in cards if c[0] == e), None)
            if rec is None:
                continue
            if len(rec) < 12 or rec[11] != tid:
                errs.append("evt {} 的关联题材(正文 last)为 {}，但主题 {} 声明它；应改为 {}".format(e, rec[11] if len(rec) >= 12 else "缺", tid, tid))
    return errs


def build(data, sina, em):
    new, old = data["NEW"], data["OLD"]
    themes = data["THEMES"]
    cards = new + old
    theme_of = {evt: tid for tid, *_th, nums in themes for n in nums for evt in [f"evt-{n:03d}"]}
    # 统一 evt 前缀：数据里 evt_id 可能是完整或编号 -> 由 generate 传入函数处理
    # THEMES 的成员用编号（1,9,13…），映射到完整 evt id（evt-20260818-001…）
    evt_pfx = data.get("evt_prefix", "evt")
    def evt_id(n):
        return "{}-{:03d}".format(evt_pfx, int(n)) if isinstance(n, int) or str(n).isdigit() else str(n)
    theme_of = {}
    for tid, _n, _c, nums in themes:
        for n in nums:
            theme_of[evt_id(n)] = tid
    preerr = _contract_errors(data)
    if preerr:
        print("CONTRACT PRE-CHECK FAILED ({} 项):".format(len(preerr)), file=sys.stderr)
        for e in preerr:
            print("  -", e, file=sys.stderr)
        sys.exit(3)

    lines = []
    lines.append("# {} A股盘前新闻热榜\n".format(data.get("date", "")))
    lines.append("> **新闻窗口：** {}\n".format(data.get("window", "")))
    lines.append("> **实际截点：** {}（北京时间）；报告在中国市场开盘前完成。\n".format(data.get("cutoff", "")))
    if data.get("trading_day"):
        lines.append("> **交易日：** {}\n".format(data["trading_day"]))
    lines.append("> **排序口径：** 热点权重＝覆盖 25 + 变化 30 + 绝对热度 20 + 新鲜度 15 + 频次 10；第一层为上一交易日 12:00 之后新事件，第二层为 12:00 前已定价旧闻按 0.4 系数折算。\n")
    lines.append("> **时间口径：** 全部换算为北京时间，只有日期的来源不补造分钟。\n")
    lines.append("> **阅读提示：** 标题只写消息事实；热度判断、市场反应和核验边界放在正文。本报告不提供操作建议。\n")
    lines.append("> **题材计分披露：** 同一新闻可向多个题材贡献完整热点分，因此题材分不能再次相加为全市场总分；第二层条目按折扣分计入题材总分。\n")
    lines.append("> **收录规则：** A股个股涨跌结果不收录；重要机构评级/目标价行动独立成条不合并。\n")
    lines.append("> **A股映射边界：** 直接映射与板块代表均不参与计分，均不构成投资建议。\n")
    lines.append("> **证券基础信息降级：** AmazingData认证不可用，本稿按已批准、已核证券基础信息及报告内公司/公告证据保守映射。\n")

    # 索引
    lines.append("## 单条新闻热榜索引\n")
    lines.append("| 排名 | 事件ID | 新闻标题 | 热点分 | 关联题材 | 跳转锚点 |")
    lines.append("|---:|---|---:|---|---:|---|")
    for i, (evt, score, _bd, title, *_rest) in enumerate(cards, 1):
        # OLD 识别：evt 在 old set；标题已含后缀时不重复追加
        # （与 card() 同款防御——2026-08-25 索引行重复事故）
        legacy = evt in {c[0] for c in old}
        suffix = "（昨日已定价）" if legacy and "（昨日已定价）" not in title else ""
        lines.append("| {} | {} | {}{} | {} | {} | [查看](#{}) |".format(
            i, evt, title, suffix, score, theme_of.get(evt, ""), evt))
    lines.append("")

    # 题材主线
    lines.append("## 题材主线\n")
    old_evts = {c[0] for c in old}
    card_rows = {}
    broken = []
    for idx, (tid, tname, tcore, nums) in enumerate(themes, 1):
        members = [evt_id(n) for n in nums]
        total = 0
        for evt in members:
            rec = next((c for c in cards if c[0] == evt), None)
            if not rec:
                continue
            total += int(rec[1])
        lines.append("### 主线{}：{}｜{}分｜关联新闻{}条\n".format(idx, tname, total, len(members)))
        lines.append("**题材ID：** {}\n".format(tid))
        lines.append("**核心催化：** {}\n".format(tcore))
        lines.append("**题材风险边界：** 企业披露与机构观点为口径，不构成投资建议。\n")
        for evt in members:
            rec = next((c for c in cards if c[0] == evt), None)
            if not rec:
                continue
            evt, score, bd, title, core, keys, signal, feedback, boundary, heat, session, theme = rec
            legacy = evt in old_evts
            rank = [i for i, (e, *_x) in enumerate(cards, 1) if e == evt][0]
            rows = src_rows(sina, em, keys)
            c = card(rank, evt, title, score, bd, core, keys, rows, signal, feedback, boundary, heat, session, theme, legacy)
            if c is None:
                broken.append(evt)
                c = "#### 新闻：{}｜{}｜{}｜{}/100\n\n（来源缺失：keys 未命中带链接条目 {}）\n".format(
                    rank, evt, title, score, keys)
            card_rows[evt] = c
            lines.append(c)
            lines.append("")

    # 尾部可选段：其他重要新闻 + 待核验线索 + 来源覆盖（JSON 提供，可为空）
    lines.append("")
    lines.append("## 其他重要新闻\n")
    lines.append((data.get("other_news") or "（本窗口无评分阈值以上、且未归入任一题材主线的独立达标事件。）") + "\n")
    pending = data.get("pending")
    if pending:
        lines.append("")
        lines.append("## 待核验线索\n")
        for item in pending:
            lines.append("### {}\n".format(item.get("title", "")))
            lines.append("**已知事实：** {}\n".format(item.get("facts", "")))
            lines.append("**待核原因：** {}\n".format(item.get("reason", "")))
            lines.append("")
    coverage = data.get("coverage")
    if coverage:
        lines.append("## 来源覆盖与核验缺口\n")
        for line in coverage:
            lines.append("- {}\n".format(line))

    return "\n".join(lines), broken


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    # default=None：传参时完全替换（append 到含通配符的 default 会把全部窗口
    # 的证据文件混入匹配，导致来源行跨窗口污染——2026-08-24 审计发现）
    ap.add_argument("--sina", action="append", default=None)
    ap.add_argument("--em", action="append", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    data.setdefault("other_news", ""); data.setdefault("pending", []); data.setdefault("coverage", [])
    sina, em = load_evidence(
        args.sina or ["evidence/sina7x24-window-*.jsonl"],
        args.em or ["evidence/em7x24-window-*.jsonl"])
    sina = filter_window(sina, data.get("window"), label="sina")
    em = filter_window(em, data.get("window"), label="em")
    text, broken = build(data, sina, em)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("generated:", out)
    if broken:
        print("MISSING SOURCE LINK:", broken, file=sys.stderr)
        sys.exit(2)
    print("cards:", len(data["NEW"]) + len(data["OLD"]))


if __name__ == "__main__":
    main()
