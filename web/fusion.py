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


def _extract_brief_body(brief_html: str) -> str:
    match = _MAIN.search(brief_html)
    if not match:
        raise FusionBuildError("daily_info brief html has no <main> block")
    body = match.group(1).strip()
    if not body:
        raise FusionBuildError("daily_info brief <main> block is empty")
    return body


def _latest_report_manifest(output_dir: Path) -> tuple[str, str]:
    manifest_path = output_dir / "reports.json"
    if not manifest_path.is_file():
        raise FusionBuildError("reports.json missing; build the radar site first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    latest_url = str(manifest.get("latest", ""))
    latest_title = ""
    for report in manifest.get("reports", []):
        if report.get("url") == latest_url:
            latest_title = str(report.get("title", ""))
    if not latest_url:
        raise FusionBuildError("reports.json has no latest url")
    return latest_url, latest_title


_FUSION_STYLE = """
<style>
  .fusion-shell { max-width: 1180px; margin: 0 auto; padding: 18px 16px 40px; }
  .fusion-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
  .fusion-head h1 { margin: 0; font-size: 20px; color: var(--ink); }
  .fusion-head .fusion-date { color: var(--muted); font-size: 13px; }
  .fusion-tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--line); margin-bottom: 16px; }
  .fusion-tab-button {
    appearance: none; border: 1px solid var(--line); border-bottom: none; background: var(--surface);
    color: var(--muted); padding: 9px 22px; font-size: 14px; border-radius: 10px 10px 0 0;
    cursor: pointer; margin-bottom: -1px;
  }
  .fusion-tab-button[aria-selected="true"] {
    background: var(--canvas); color: var(--ink); border-color: var(--line);
    box-shadow: inset 0 2px 0 var(--nav-active); font-weight: 600;
  }
  .fusion-pane[hidden] { display: none; }

  /* morning-brief table styles adapted to the radar palette */
  .brief-body h1 { font-size: 19px; margin: 0 0 10px; color: var(--ink); }
  .brief-body h2 {
    font-size: 15px; margin: 22px 0 10px; padding: 7px 12px;
    border-left: 3px solid var(--accent); background: rgba(36, 87, 210, .07);
    border-radius: 0 6px 6px 0; color: var(--ink);
  }
  .brief-body h3 { font-size: 14px; margin: 16px 0 8px; color: var(--ink); }
  .brief-body p { margin: 6px 0; }
  .brief-body .meta, .brief-body .rule { color: var(--muted); font-size: 12.5px; margin: 3px 0; }
  .brief-body .table-wrap { width: 100%; overflow-x: auto; margin: 8px 0 14px; }
  .brief-body table {
    width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums;
    background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  }
  .brief-body th, .brief-body td { padding: 7px 10px; text-align: left; font-size: 13px; }
  .brief-body th {
    background: var(--surface); color: var(--muted); font-weight: 600; font-size: 12px;
    border-bottom: 1px solid var(--line); letter-spacing: .2px;
  }
  .brief-body td { border-bottom: 1px solid var(--line); }
  .brief-body tbody tr:last-child td { border-bottom: none; }
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
  .brief-body .tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px;
    border: 1px solid var(--line); color: var(--muted); background: var(--surface); }
  .brief-body .tag.official { color: #0c8f5e; border-color: rgba(12, 143, 94, .4); background: rgba(12, 143, 94, .08); }

  .fusion-news-frame { width: 100%; height: calc(100vh - 150px); min-height: 620px; border: 1px solid var(--line); border-radius: 12px; background: var(--canvas); }
</style>
"""

_FUSION_JS = """
<script>
  (function () {
    var tabs = document.querySelectorAll('.fusion-tab-button');
    var panes = document.querySelectorAll('.fusion-pane');
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', function () {
        var target = this.getAttribute('data-tab');
        for (var j = 0; j < tabs.length; j++) {
          var selected = tabs[j].getAttribute('data-tab') === target;
          tabs[j].setAttribute('aria-selected', selected ? 'true' : 'false');
        }
        for (var k = 0; k < panes.length; k++) {
          panes[k].hidden = panes[k].getAttribute('data-pane') !== target;
        }
      });
    }
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
  <div class="fusion-shell">
    <header class="fusion-head">
      <h1>A股晨报融合视图</h1>
      <span class="fusion-date">{date_label}</span>
    </header>
    <nav class="fusion-tabs" aria-label="视图切换">
      <button class="fusion-tab-button" type="button" data-tab="brief" aria-selected="true">晨报</button>
      <button class="fusion-tab-button" type="button" data-tab="news" aria-selected="false">新闻</button>
    </nav>
    <section class="fusion-pane brief-body" data-pane="brief">
      {brief_body}
    </section>
    <section class="fusion-pane" data-pane="news" hidden>
      <iframe class="fusion-news-frame" src="{latest_url}" title="{news_title}" loading="lazy"></iframe>
    </section>
  </div>
  {js}
</body>
</html>
"""


def build_fusion(output_dir: Path, daily_info_root: Path, date_label: str = "") -> Path:
    """Write fusion.html into output_dir and return its path."""
    output_dir = output_dir.expanduser().resolve()
    brief_path = daily_info_root.expanduser().resolve() / _BRIEF_HTML
    if not brief_path.is_file():
        raise FusionBuildError("daily_info brief html not found: {}".format(brief_path))
    brief_body = _extract_brief_body(brief_path.read_text(encoding="utf-8"))
    latest_url, latest_title = _latest_report_manifest(output_dir)

    if not date_label:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", latest_url)
        date_label = match.group(1) if match else ""
    page_title = "A股晨报融合视图{}".format(
        " · {}".format(date_label) if date_label else ""
    )
    page = _FUSION_TEMPLATE.format(
        page_title=html_mod.escape(page_title, quote=True),
        date_label=html_mod.escape(date_label, quote=True),
        style=_FUSION_STYLE,
        brief_body=brief_body,
        latest_url=html_mod.escape(latest_url, quote=True),
        news_title=html_mod.escape(latest_title, quote=True),
        js=_FUSION_JS,
    )
    target = output_dir / FUSION_NAME
    target.write_text(page, encoding="utf-8")
    return target
