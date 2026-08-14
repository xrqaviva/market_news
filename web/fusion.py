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
    # 0. rename the brief headline to 外围
    body = re.sub(r"<h1>A股盘前双源晨报", "<h1>外围", body)
    # 1. drop informational paragraphs
    body = re.sub(r"<p class=\"(?:meta|rule|legend)\">.*?</p>", "", body, flags=re.DOTALL)
    body = re.sub(r"<footer>.*?</footer>", "", body, flags=re.DOTALL)
    body = re.sub(r"<p>本报告仅作信息整理，不构成投资建议。</p>", "", body)
    # 2. drop the 重要宏观新闻 section (heading + following paragraph)
    body = re.sub(r"<h2>重要宏观新闻</h2>\s*<p>.*?</p>", "", body, flags=re.DOTALL)
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
    # 5. map source keys to short names (keep the href)
    def _rename_source(match: re.Match) -> str:
        url = match.group(1)
        key = match.group(2)
        return '<a href="{}">{}</a>'.format(url, _clean_short_name(key))

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
  /* tab bar in the report filter-bar idiom */
  .fusion-tabs {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    margin: 18px 0 14px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 7px;
  }
  .fusion-tabs .fusion-tabs-meta { color: var(--muted); font-size: 10px; }
  .fusion-tabs .fusion-tabs-actions { display: flex; flex-wrap: wrap; gap: 5px; }
  .fusion-tab-button {
    padding: 5px 10px; font-size: 10px; color: #425069; background: #f8fafc;
    border: 1px solid #cbd3df; border-radius: 3px; cursor: pointer;
  }
  .fusion-tab-button:hover { color: #1749a8; border-color: #8ab1f3; }
  .fusion-tab-button[aria-selected="true"] {
    color: #ffffff; background: var(--accent); border-color: var(--accent); font-weight: 700;
  }
  .fusion-pane[hidden] { display: none; }

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
  .brief-body .src a { color: var(--accent); text-decoration: none; }
  .brief-body .src a:hover { text-decoration: underline; }
  .brief-body ul { margin: 6px 0; padding-left: 20px; }
  .brief-body details { margin: 12px 0; border: 1px solid var(--line); border-radius: 10px; padding: 8px 14px; }
  .brief-body details.alert { border-color: rgba(138, 79, 10, .4); background: var(--mixed-bg); }
  .brief-body summary { cursor: pointer; font-weight: 600; color: var(--ink); }
  .brief-body .tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px;
    border: 1px solid var(--line); color: var(--muted); background: var(--surface); }
  .brief-body .tag.official { color: #0c8f5e; border-color: rgba(12, 143, 94, .4); background: rgba(12, 143, 94, .08); }

  .fusion-news-frame {
    width: 100%; height: calc(100vh - 210px); min-height: 620px;
    border: 1px solid var(--line); border-radius: 10px; background: var(--canvas);
  }
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
    window.addEventListener('hashchange', function () {
      var target = (location.hash || '').replace('#', '');
      if (target === 'brief' || target === 'news') { select(target); }
    });
    var hash = (location.hash || '').replace('#', '');
    if (hash === 'news') { select('news'); }
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
</head>
<body>
  <div class="page-shell">
    <section class="report-card">
      <aside class="report-sidebar">
        <div class="brand" aria-label="新闻速递">RADAR</div>
        {date_archive}
      </aside>
      <div class="report-workspace">
        <header class="topbar">
          <div class="report-heading">
            <p class="report-eyebrow">新闻速递 · 每日</p>
            <h1>{heading_title}</h1>
          </div>
          <p class="report-cutoff">{date_label}</p>
        </header>
        <main class="report-main">
          <nav class="fusion-tabs" aria-label="视图切换">
            <span class="fusion-tabs-meta">外围 · {date_label}</span>
            <div class="fusion-tabs-actions">
              <button class="fusion-tab-button" type="button" data-tab="brief" aria-selected="true">外围</button>
              <button class="fusion-tab-button" type="button" data-tab="news" aria-selected="false">新闻</button>
            </div>
          </nav>
          <section class="fusion-pane brief-body" data-pane="brief">
            {brief_body}
          </section>
          <section class="fusion-pane" data-pane="news" hidden>
            <iframe class="fusion-news-frame" src="{latest_url}" title="新闻 · {date_label}" loading="lazy"></iframe>
          </section>
        </main>
      </div>
    </section>
  </div>
  {js}
</body>
</html>
"""


def _collapse_empty_tables(body: str) -> str:
    """Wrap fully-empty value tables (every .num cell is —) in a folded details block,
    titled by the nearest preceding section heading."""

    def _nearest_h2(before: str) -> str:
        headings = list(re.finditer(r"<h2>([^<]+)</h2>", before))
        if not headings:
            return ""
        return headings[-1].group(1).strip()

    out = []
    cursor = 0
    for match in re.finditer(r'<div class="table-wrap">(.*?)</div>', body, flags=re.DOTALL):
        out.append(body[cursor:match.start()])
        block = match.group(1)
        num_values = re.findall(r'<td class="num[^"]*">([^<]*)</td>', block)
        if not num_values or any(value.strip() != "—" for value in num_values):
            out.append(match.group(0))
        else:
            title = _nearest_h2(body[:match.start()])
            rows = block.count("<tr>") - 1
            summary = "{}（{} 项暂无共识值，来源日期不一致未形成双源共识）".format(
                title or "数据表", rows
            )
            out.append(
                '<details class="status"><summary>{}</summary>'
                '<div class="table-wrap">{}</div></details>'.format(
                    html_mod.escape(summary), block
                )
            )
        cursor = match.end()
    out.append(body[cursor:])
    return "".join(out)


def build_fusion(output_dir: Path, daily_info_root: Path, date_label: str = "") -> Path:
    """Write fusion.html into output_dir and return its path."""
    output_dir = output_dir.expanduser().resolve()
    brief_path = daily_info_root.expanduser().resolve() / _BRIEF_HTML
    if not brief_path.is_file():
        raise FusionBuildError("daily_info brief html not found: {}".format(brief_path))
    brief_body, verification_lines = _transform_brief_body(
        _extract_brief_body(brief_path.read_text(encoding="utf-8"))
    )
    brief_body = _collapse_empty_tables(brief_body)
    if verification_lines:
        lines = "".join("<li>{}</li>".format(html_mod.escape(line)) for line in verification_lines)
        brief_body += (
            '<details class="status"><summary>核验明细（{} 条）</summary>'
            "<ul>{}</ul></details>".format(len(verification_lines), lines)
        )
    latest_url, latest_title, reports = _latest_report_manifest(output_dir)

    if not date_label:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", latest_url)
        date_label = match.group(1) if match else ""
    page_title = "新闻速递{}".format(
        " · {}".format(date_label) if date_label else ""
    )
    page = _FUSION_TEMPLATE.format(
        page_title=html_mod.escape(page_title, quote=True),
        heading_title=html_mod.escape("新闻速递", quote=True),
        date_label=html_mod.escape(date_label, quote=True),
        date_archive=_date_archive(reports, latest_url),
        style=_FUSION_STYLE,
        brief_body=brief_body,
        latest_url=html_mod.escape(latest_url, quote=True),
        js=_FUSION_JS,
    )
    target = output_dir / FUSION_NAME
    target.write_text(page, encoding="utf-8")
    return target
