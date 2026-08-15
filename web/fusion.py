"""Build the fusion page that combines the daily_info morning brief and the news radar report.

The two projects stay independent: each keeps producing its own outputs. This module only
reads those outputs and renders one HTML with two tabs (晨报 / 新闻) using the radar
styles (assets/app.css) so the fusion page looks like the radar reports.

Layout:
- Tab 1 "晨报": the daily_info brief body (`<main>` content of reports/index/A股盘前晨报.html)
  injected directly, styled by the fusion stylesheet inside this page.
- Tab 2 "新闻": the latest news-radar report embedded as an iframe (`reports/<latest>.html`),
  so the full report (archive, filters, expandable details) keeps working unchanged.

Safety: this page is part of the static dist tree; build_site runs assert_public_tree_safe
over the whole output, so injected brief content must not contain private paths, credentials
or unsafe URL schemes (verified before writing).
"""

import html as html_mod
import json
import re
from pathlib import Path

FUSION_NAME = "fusion.html"

_BRIEF_HTML = Path("reports/index/A股盘前晨报.html")
_MAIN = re.compile(r"<main[^>]*>(.*?)</main>", re.DOTALL)


class FusionBuildError(RuntimeError):
    """Raised when the fusion page cannot be built from project outputs."""


_SOURCE_SHORT_NAMES = {
    "tencent": "腾讯",
    "eastmoney_global_history": "东方财富",
    "eastmoney_futures": "东方财富",
    "sina_global_history": "新浪",
    "sina_futures": "新浪",
    "smm": "SMM",
    "ganzhou": "赣州钨协",
    "boc": "加拿大央行",
    "boe": "英国央行",
    "ecb": "欧央行",
}
_SOURCE_KEY_PATTERN = re.compile(
    r"^(?:{})$".format("|".join(re.escape(key) for key in _SOURCE_SHORT_NAMES)),
    re.IGNORECASE,
)
_NUM_PREFIX = re.compile(
    r"(?<![\w/])(?:{}|{})\s+".format(
        "|".join(re.escape(key) for key in _SOURCE_SHORT_NAMES),
        "|".join(re.escape(key).capitalize() for key in _SOURCE_SHORT_NAMES),
    )
)


def _extract_brief_body(brief_html: str) -> str:
    match = _MAIN.search(brief_html)
    if not match:
        raise FusionBuildError("daily_info brief html has no <main> block")
    body = match.group(1).strip()
    if not body:
        raise FusionBuildError("daily_info brief <main> block is empty")
    return body


def _clean_short_name(link_text: str) -> str:
    return _SOURCE_SHORT_NAMES.get(link_text.strip(), link_text.strip())


def _transform_brief_body(body: str) -> tuple[str, list[str]]:
    """Clean the daily_info brief body for the radar look.

    Returns (cleaned_body, verification_lines). The user-facing rules:
    - drop meta/rule/legend/disclaimer paragraphs (no information value)
    - drop the whole 重要宏观新闻 section (news lives in the 新闻 tab)
    - strip source prefixes from numeric cells, map source keys to short names
    - pull 核验状态/核验原因 paragraphs out of the tables and collect them
      into a verification summary rendered below
    """
    # 0. drop the brief headline entirely (redundant with the topbar)
    body = re.sub(r"<h1>[^<]*</h1>", "", body)
    # 1. drop informational paragraphs
    body = re.sub(r"<p class=\"(?:meta|rule|legend)\">.*?</p>", "", body, flags=re.DOTALL)
    body = re.sub(r"<footer>.*?</footer>", "", body, flags=re.DOTALL)
    body = re.sub(r"<p>本报告仅作信息整理，不构成投资建议。</p>", "", body)
    # 2. drop the whole 重要宏观新闻 section (heading through the next heading
    #    or the verification details block)
    body = re.sub(
        r"<h2>重要宏观新闻</h2>(?:(?!<h2>).)*?(?=<h2>|<details|<footer|\Z)",
        "",
        body,
        flags=re.DOTALL,
    )
    # 2.5 breadth single-source display: eastmoney only, plain line, no table
    breadth_match = re.search(
        r"<h2>上一交易日A股非ST涨跌家数</h2>(?:(?!<h2>).)*?</div>",
        body,
        flags=re.DOTALL,
    )
    if breadth_match:
        block = breadth_match.group(0)
        cells = [c.strip() for c in re.findall(r"<td[^>]*>([^<]*)</td>", block)]
        try:
            east_idx = cells.index("eastmoney")
        except ValueError:
            east_idx = -1
        if east_idx >= 0 and len(cells) >= east_idx + 6:
            date, up, down, flat = (
                cells[east_idx + 1], cells[east_idx + 3],
                cells[east_idx + 4], cells[east_idx + 5],
            )
            up, down, flat = (
                re.sub(r"\.0+$", "", value) for value in (up, down, flat)
            )
            if up and up != "—":
                line = "上涨 {} · 下跌 {} · 平盘 {}（数据日期 {}，东方财富）".format(
                    up, down, flat, date
                )
            else:
                line = "东方财富暂无有效值（数据日期 {}）".format(date)
            body = body.replace(
                block,
                "<h2>上一交易日A股非ST涨跌家数</h2>\n"
                '<p class="breadth-line">{}</p>'.format(line),
            )
    # 3. collect and remove inline verification status/reason paragraphs
    verification_lines = []
    heading_before = None
    for match in re.finditer(
        r"<h2>([^<]+)</h2>(?:(?!<h2>).)*?<p>核验状态：([^<]*)</p>\s*<p>核验原因：([^<]*)</p>",
        body,
        flags=re.DOTALL,
    ):
        section_title, status, reason = match.groups()
        verification_lines.append(
            "{}：{}——{}".format(section_title.strip(), status.strip(), reason.strip())
        )
        heading_before = section_title.strip()
    body = re.sub(
        r"<p>核验状态：[^<]*</p>\s*<p>核验原因：[^<]*</p>", "", body, flags=re.DOTALL
    )
    # 4. strip source prefixes from numeric cells
    def _strip_num(match: re.Match) -> str:
        cell = match.group(0)
        inner = match.group(2)
        inner = _NUM_PREFIX.sub("", inner)
        return "{}{}{}".format(match.group(1), inner, match.group(3))

    body = re.sub(
        r"(<td class=\"num[^\"]*\">)(.*?)(</td>)",
        _strip_num,
        body,
        flags=re.DOTALL,
    )
    # 5. map source keys to short names; rewrite raw API endpoints to
    #    human-readable quote pages so the links open real pages
    def _readable_url(raw_url: str) -> str:
        if "qt.gtimg.cn" in raw_url:
            match = re.search(r"q=([A-Za-z0-9_]+)", raw_url)
            if match:
                return "https://gu.qq.com/{}".format(match.group(1))
        if "push2his.eastmoney.com" in raw_url or "push2.eastmoney.com" in raw_url:
            return "https://quote.eastmoney.com/"
        if "stock2.finance.sina.com.cn" in raw_url or "hq.sinajs.cn" in raw_url:
            return "https://finance.sina.com.cn/7x24/"
        if "cdn.cboe.com" in raw_url:
            return "https://www.cboe.com/us/indices/dashboard/spx/"
        if "data-api.ecb.europa.eu" in raw_url:
            return (
                "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/"
                "euro_reference_exchange_rates/html/index.en.html"
            )
        if "bankofcanada.ca" in raw_url:
            return "https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/"
        return raw_url

    def _rename_source(match: re.Match) -> str:
        url = match.group(1)
        key = match.group(2)
        return '<a href="{}">{}</a>'.format(_readable_url(url), _clean_short_name(key))

    body = re.sub(r'<a href="([^"]+)">([^<]+)</a>', _rename_source, body)
    return body, verification_lines


def _latest_report_manifest(output_dir: Path) -> tuple[str, str, list[dict]]:
    manifest_path = output_dir / "reports.json"
    if not manifest_path.is_file():
        raise FusionBuildError("reports.json missing; build the radar site first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    latest_url = str(manifest.get("latest", ""))
    latest_title = ""
    reports = manifest.get("reports", [])
    for report in reports:
        if report.get("url") == latest_url:
            latest_title = str(report.get("title", ""))
    if not latest_url:
        raise FusionBuildError("reports.json has no latest url")
    return latest_url, latest_title, reports


def _date_archive(reports: list[dict], latest_url: str) -> str:
    """Sidebar date list mirroring the radar report archive: one row per date,
    newest date marked as current, each date linking to that day's report."""
    by_date: dict[str, str] = {}
    for report in reports:
        date = str(report.get("date", ""))
        if date:
            by_date[date] = str(report.get("url", ""))
    groups = []
    for date in sorted(by_date, reverse=True):
        url = by_date[date]
        current = ' aria-current="page"' if url == latest_url else ""
        groups.append(
            '<div class="archive-date-group" data-report-date="{}">'
            '<a class="archive-date-link" href="{}"{}>{}</a></div>'.format(
                html_mod.escape(date, quote=True),
                html_mod.escape(url, quote=True),
                current,
                html_mod.escape(date, quote=True),
            )
        )
    return "".join(groups)


_FUSION_STYLE = """
<style>
  /* tab bar inside the topbar, filled buttons */
  .fusion-tabs {
    display: flex; align-items: center; gap: 5px;
    padding: 3px; border: 1px solid #cbd3df; border-radius: 7px; background: #f8fafc;
  }
  .fusion-tab-button {
    padding: 5px 10px; font-size: 10px; color: #425069; background: #f8fafc;
    border: 1px solid #cbd3df; border-radius: 3px; cursor: pointer;
  }
  .fusion-tab-button:hover { color: #1749a8; border-color: #8ab1f3; }
  .fusion-tab-button[aria-selected="true"] {
    color: #ffffff; background: var(--accent); border-color: var(--accent); font-weight: 700;
  }
  .fusion-pane[hidden] { display: none; }

  .fusion-brief-card,
  .fusion-news-card {
    background: #eef1f5;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 16px 20px;
  }

  /* morning-brief content styled with the radar palette */
  .brief-body h1 { font-size: 19px; margin: 0 0 10px; color: var(--ink); }
  .brief-body h2 {
    font-size: 15px; margin: 24px 0 10px; padding: 7px 12px;
    border-left: 3px solid var(--accent); background: rgba(36, 87, 210, .07);
    border-radius: 0 6px 6px 0; color: var(--ink);
  }
  .brief-body h3 { font-size: 13px; margin: 16px 0 8px; color: var(--ink); }
  .brief-body p { margin: 6px 0; font-size: 13px; }
  .brief-body .meta, .brief-body .rule { color: var(--muted); font-size: 11px; margin: 3px 0; }
  .brief-body .table-wrap { width: 100%; overflow-x: auto; margin: 8px 0 16px; }
  .brief-body table {
    width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums;
    background: var(--surface); border: 1px solid #a9b4c3; border-radius: 10px; overflow: hidden;
  }
  .brief-body th, .brief-body td { padding: 8px 12px; text-align: left; font-size: 12.5px; border: 1px solid var(--line); }
  .brief-body th {
    background: var(--surface); color: var(--muted); font-weight: 600; font-size: 11px;
    letter-spacing: .2px;
  }
  .brief-body tbody tr:hover td { background: rgba(36, 87, 210, .05); }
  .brief-body .num { text-align: right; }
  .brief-body .up { color: #d9384a; }   /* A-share convention: red up */
  .brief-body .down { color: #0c8f5e; } /* green down */
  .brief-body .flat { color: var(--muted); }
  .brief-body .breadth-line {
    padding: 10px 14px; border: 1px solid var(--line); border-radius: 8px;
    background: var(--surface); font-size: 13px;
  }
  .brief-body .src a { color: var(--accent); text-decoration: none; }
  .brief-body .src a:hover { text-decoration: underline; }
  .brief-body ul { margin: 6px 0; padding-left: 20px; }
  .brief-body details { margin: 12px 0; border: 1px solid var(--line); border-radius: 10px; padding: 8px 14px; }
  .brief-body details.alert { border-color: rgba(138, 79, 10, .4); background: var(--mixed-bg); }
  .brief-body summary { cursor: pointer; font-weight: 600; color: var(--ink); }
  .brief-body .tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px;
    border: 1px solid var(--line); color: var(--muted); background: var(--surface); }
  .brief-body .tag.official { color: #0c8f5e; border-color: rgba(12, 143, 94, .4); background: rgba(12, 143, 94, .08); }

</style>
"""

_FUSION_JS = """
<script>
  (function () {
    var tabs = document.querySelectorAll('.fusion-tab-button');
    var panes = document.querySelectorAll('.fusion-pane');
    function select(target) {
      for (var j = 0; j < tabs.length; j++) {
        tabs[j].setAttribute('aria-selected', tabs[j].getAttribute('data-tab') === target ? 'true' : 'false');
      }
      for (var k = 0; k < panes.length; k++) {
        panes[k].hidden = panes[k].getAttribute('data-pane') !== target;
      }
    }
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', function () { select(this.getAttribute('data-tab')); });
    }
    function applyHash() {
      var target = (location.hash || '').replace('#', '');
      if (target === 'brief' || target === 'news') { select(target); }
    }
    window.addEventListener('hashchange', applyHash);
    document.addEventListener('DOMContentLoaded', applyHash);
    applyHash();

  })();
</script>
"""

_FUSION_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{page_title}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="assets/app.css">
  {style}
  <script src="assets/app.js" defer></script>
  <script src="assets/calendar.js" defer></script>
</head>
<body>
  <div class="page-shell">
    <section class="report-card">
      <aside class="report-sidebar">
        <div class="brand" aria-label="新闻速递">新闻速递</div>
        {calendar_filter}
        {date_archive}
      </aside>
      <div class="report-workspace">
        <header class="topbar">
          <div class="report-heading">
            <h1>{heading_title}</h1>
          </div>
          <div class="report-topbar-right">
            <nav class="fusion-tabs" aria-label="视图切换">
              <button class="fusion-tab-button" type="button" data-tab="brief" aria-selected="true">外围</button>
              <button class="fusion-tab-button" type="button" data-tab="news" aria-selected="false">新闻</button>
            </nav>
          </div>
        </header>
        <main class="report-main">
          <section class="fusion-pane brief-body" data-pane="brief">
            <div class="fusion-brief-card">
              {brief_body}
            </div>
          </section>
          <section class="fusion-pane" data-pane="news" hidden>
            <div class="fusion-news-card">
              {news_content}
            </div>
          </section>
        </main>
      </div>
    </section>
  </div>
  <template id="news-toggle-template">
    <button class="news-toggle" type="button" aria-expanded="false" aria-controls="">展开详情</button>
  </template>
  {js}
</body>
</html>
"""



def _extract_report_main(report_html: str) -> str:
    match = re.search(r'<main class="report-main">(.*?)</main>', report_html, re.DOTALL)
    if not match:
        raise FusionBuildError("report page has no report-main block")
    return match.group(1).strip()


def build_fusion(output_dir: Path, daily_info_root: Path, date_label: str = "") -> Path:
    """Write fusion.html into output_dir and return its path."""
    output_dir = output_dir.expanduser().resolve()
    brief_path = daily_info_root.expanduser().resolve() / _BRIEF_HTML
    if not brief_path.is_file():
        raise FusionBuildError("daily_info brief html not found: {}".format(brief_path))
    brief_body, verification_lines = _transform_brief_body(
        _extract_brief_body(brief_path.read_text(encoding="utf-8"))
    )
    if verification_lines:
        lines = "".join("<li>{}</li>".format(html_mod.escape(line)) for line in verification_lines)
        brief_body += (
            '<details class="status"><summary>核验明细（{} 条）</summary>'
            "<ul>{}</ul></details>".format(len(verification_lines), lines)
        )
    latest_url, latest_title, reports = _latest_report_manifest(output_dir)
    news_content = _extract_report_main((output_dir / latest_url).read_text(encoding="utf-8"))
    # date filter data: per-date last report URL + min/max bounds
    dates = sorted({str(report.get("date", "")) for report in reports if report.get("date")})
    date_targets = {}
    for date in dates:
        urls = [
            str(report.get("url", ""))
            for report in reports
            if report.get("date") == date and report.get("url")
        ]
        if urls:
            date_targets[date] = Path(urls[-1]).name  # last slot of the day
    min_date = dates[0] if dates else ""
    max_date = dates[-1] if dates else ""
    latest_date = max_date
    calendar_filter = (
        '<div class="calendar-filter" id="calendar-filter">'
        '<input type="text" readonly value="{}" aria-label="按日期筛选报告">'
        '<div class="calendar-pop" hidden>'
        '<div class="calendar-head">'
        '<button type="button" data-nav="year-prev">«</button>'
        '<button type="button" data-nav="month-prev">‹</button>'
        '<span class="calendar-title"></span>'
        '<button type="button" data-nav="month-next">›</button>'
        '<button type="button" data-nav="year-next">»</button>'
        '</div>'
        '<div class="calendar-week"><span>一</span><span>二</span><span>三</span>'
        '<span>四</span><span>五</span><span>六</span><span>日</span></div>'
        '<div class="calendar-grid"></div>'
        '<div class="calendar-foot"><button type="button" data-nav="today">今天</button></div>'
        '</div></div>'
        '<script type="application/json" id="calendar-dates">{}</script>'
    ).format(
        html_mod.escape(latest_date, quote=True),
        json.dumps(date_targets, ensure_ascii=False),
    )

    if not date_label:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", latest_url)
        date_label = match.group(1) if match else ""
    mmdd = date_label.replace("-", "")[4:] if date_label else ""
    latest_slot = ""
    for report in reports:
        if report.get("url") == latest_url:
            latest_slot = str(report.get("slot", ""))
            break
    session = "盘前" if latest_slot == "0800" else "盘后"
    page_title = "{}{}新闻速递".format(mmdd, session) if mmdd else "新闻速递"
    js = _FUSION_JS.replace(
        "__DATE_TARGETS__", json.dumps(date_targets, ensure_ascii=False)
    )
    page = _FUSION_TEMPLATE.format(
        page_title=html_mod.escape(page_title, quote=True),
        heading_title=html_mod.escape(page_title, quote=True),
        date_label=html_mod.escape(date_label, quote=True),
        date_archive=_date_archive(reports, latest_url),
        min_date=html_mod.escape(min_date, quote=True),
        max_date=html_mod.escape(max_date, quote=True),
        calendar_filter=calendar_filter,
        style=_FUSION_STYLE,
        brief_body=brief_body,
        news_content=news_content,
        js=js,
    )
    target = output_dir / FUSION_NAME
    target.write_text(page, encoding="utf-8")
    return target
