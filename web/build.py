"""Build static report pages from the constrained news-radar Markdown reports."""

import argparse
from dataclasses import dataclass
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable, Optional

from web.report_model import NewsItem, ReportDocument
from web.report_parser import discover_reports, parse_report
from web.security import assert_public_tree_safe
from web.url_policy import renderable_source_url
from web.fusion import FusionBuildError, _extract_brief_body, _transform_brief_body


_TEMPLATE_PATH = Path(__file__).with_name("templates") / "report.html"
_REQUIRED_MARKERS = (
    'data-component="report-archive"',
    'data-component="news-list"',
    'data-component="news-detail"',
    'data-component="sources"',
)


@dataclass(frozen=True)
class BuildResult:
    output_dir: Path
    report_count: int
    item_count: int
    latest_url: str


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _report_url(report_date: str, slot: str) -> str:
    return "reports/{}-{}.html".format(report_date, slot)


def _source_links(item: NewsItem) -> str:
    links = []
    for source in item.sources:
        url = renderable_source_url(source.url)
        if not url:
            continue
        label = source.label or source.channel or url
        metadata = " · ".join(part for part in (source.channel, source.time_bj) if part)
        links.append(
            '<li><a href="{}" rel="noopener noreferrer">{}</a>{}</li>'.format(
                _escape(url),
                _escape(label),
                " <span>{}</span>".format(_escape(metadata)) if metadata else "",
            )
        )
    if not links:
        raise ValueError("ranked item must have at least one renderable source")
    return '<ul data-component="sources">{}</ul>'.format("".join(links))


def _safe_dom_id(value: str) -> str:
    raw_value = str(value)
    if re.fullmatch(r"[A-Za-z0-9_-]+", raw_value):
        return "ascii-{}".format(raw_value)
    return "utf8-{}".format(raw_value.encode("utf-8").hex())


def _news_instance_id(report_id: str, scope_id: str, event_id: str) -> str:
    components = tuple(_safe_dom_id(value) for value in (report_id, scope_id, event_id))
    return "-".join("{}x{}".format(len(component), component) for component in components)


def _association_badges(theme_ids: tuple[str, ...], theme_names: dict[str, str]) -> str:
    if not theme_ids:
        return ""
    return '<p class="news-associations">{}</p>'.format("".join(
        '<a class="theme-association" data-theme-id="{}" href="#theme-{}">{}</a>'.format(
            _escape(theme_id),
            _escape(_safe_dom_id(theme_id)),
            _escape(theme_names.get(theme_id, theme_id)),
        )
        for theme_id in theme_ids
    ))


def _news_item(
    item: NewsItem,
    instance_id: str,
    association_labels: str = "",
) -> str:
    detail_fields = (
        ("发布时段", item.release_session),
        ("关键信号/预期差", item.signal),
        ("市场反馈", item.market_feedback),
        ("即时市场定价", item.pricing),
        ("判断边界", item.boundary),
        ("后续变量", item.variables),
        ("热度变化", item.heat_change),
        ("热点构成", item.score_breakdown),
    )
    supplemental_labels = {label for label, _ in item.supplemental_details}
    details = "".join(
        "<p><strong>{}</strong>{}</p>".format(_escape(label), _escape(value))
        for label, value in detail_fields
        if value and label not in supplemental_labels
    )
    details += "".join(
        "<p><strong>{}</strong>{}</p>".format(_escape(label), _escape(value))
        for label, value in item.supplemental_details
    )
    detail_kind = "analysis" if details else "sources-inline"
    return (
        '<article data-component="news-detail" data-rank="{}" data-category="{}" data-detail-kind="{}" '
        'id="news-{}" data-instance-id="{}" data-event-id="{}">'
        '<h2>{}. {}</h2><p>{}</p>{}<p>热点权重：{}/100</p>{}</article>'
    ).format(
        _escape(item.rank),
        _escape(item.category),
        detail_kind,
        _escape(instance_id),
        _escape(instance_id),
        _escape(item.event_id),
        _escape(item.rank),
        _escape(item.title),
        _escape(item.core),
        _source_links(item),
        _escape(item.score),
        details,
    )


def _theme_navigation(document: ReportDocument) -> str:
    links = "".join(
        '<a href="#theme-{}">{}</a>'.format(
            _escape(_safe_dom_id(theme.theme_id)),
            _escape(theme.name),
        )
        for theme in document.themes
    )
    if document.other_items:
        links += '<a href="#other-important-news">其他重要新闻</a>'
    if document.pending_items:
        links += '<a href="#pending-notes">待核验线索</a>'
    links += '<a href="#top" class="back-to-top">回到最上</a>'
    return (
        '<nav class="theme-navigation" data-component="theme-navigation" '
        'aria-label="核心方向">{}</nav>'
    ).format(links)


def _mapping_list(label: str, mappings: tuple) -> str:
    if not mappings:
        return ""
    return '<div class="theme-mappings"><h3>{}</h3><ul>{}</ul></div>'.format(
        _escape(label),
        "".join(
            '<li>{}（{}）：{}</li>'.format(
                _escape(mapping.name), _escape(mapping.ticker), _escape(mapping.evidence)
            )
            for mapping in mappings
        ),
    )


def _theme_group(
    document: ReportDocument, theme, theme_names: dict[str, str], ordinal: int
) -> str:
    rows = "".join(
        _news_item(
            item,
            _news_instance_id(document.meta.report_id, theme.theme_id, item.event_id),
        )
        for item in theme.items
    )
    return (
        '<section class="theme-group" data-component="theme-group" id="theme-{}">'
        '<header class="theme-header">'
        '<p class="theme-kicker">核心方向 {:02d}</p>'
        '<div class="theme-heading-line"><h2>{}</h2>'
        '<p class="theme-total">{}条 · {}</p></div>'
        '</header>'
        '<p class="theme-catalyst"><strong>核心催化</strong>{}</p>{}{}'
        '<p class="theme-risk"><strong>题材风险边界</strong>{}</p>'
        '<section class="theme-news-list" data-component="news-list">{}</section></section>'
    ).format(
        _escape(_safe_dom_id(theme.theme_id)),
        ordinal,
        _escape(theme.name),
        _escape(len(theme.items)),
        _escape(theme.total_score),
        _escape(theme.catalyst),
        _mapping_list("直接映射", theme.direct_mappings),
        _mapping_list("板块代表", theme.sector_representatives),
        _escape(theme.risk_boundary),
        rows,
    )


def _other_important_news(document: ReportDocument, theme_names: dict[str, str]) -> str:
    if not document.other_items:
        return ""
    rows = "".join(
        _news_item(
            item,
            _news_instance_id(document.meta.report_id, "other", item.event_id),
        )
        for item in document.other_items
    )
    return (
        '<section class="other-important-news" data-component="other-important-news" id="other-important-news">'
        '<h2>其他重要新闻</h2><section data-component="news-list">{}</section></section>'
    ).format(rows)


def _theme_content(document: ReportDocument) -> str:
    if not document.themes:
        return ""
    theme_names = {theme.theme_id: theme.name for theme in document.themes}
    return "{}{}{}".format(
        _theme_navigation(document),
        "".join(
            _theme_group(document, theme, theme_names, ordinal)
            for ordinal, theme in enumerate(document.themes, start=1)
        ),
        _other_important_news(document, theme_names),
    )


def _pending_items(document: ReportDocument) -> str:
    if not document.pending_items:
        return ""
    rows = []
    for item in document.pending_items:
        links = [
            '<li><a href="{}" rel="noopener noreferrer">{}</a></li>'.format(
                _escape(url), _escape(source.label)
            )
            for source in item.sources
            for url in (renderable_source_url(source.url),)
            if url
        ]
        pending_sources = ""
        if links:
            pending_sources = '<ul data-component="pending-sources">{}</ul>'.format("".join(links))
        rows.append(
            '<article class="pending-item"><h3>{}</h3>'
            '<p><strong>已知信息</strong>{}</p>'
            '<p><strong>待核原因</strong>{}</p>{}</article>'.format(
                _escape(item.title), _escape(item.known), _escape(item.reason), pending_sources
            )
        )
    return (
        '<section class="pending-section" data-component="pending-list" id="pending-notes">'
        '<details class="pending-details">'
        '<summary>待核验线索 <span>· {}</span></summary>'
        '<div class="pending-body">'
        '<p>以下线索不参与主榜计分；补齐具体原文和北京时间后再转入主榜。</p>'
        '{}'
        '</div></details></section>'
    ).format(_escape(len(document.pending_items)), "".join(rows))


def _report_note_spans(spans: tuple) -> str:
    rendered = []
    for span in spans:
        url = renderable_source_url(span.url) if span.url else None
        text = _escape(span.text).replace("Local Storage", "Local&#32;Storage")
        if url:
            rendered.append(
                '<a href="{}" rel="noopener noreferrer">{}</a>'.format(
                    _escape(url), text
                )
            )
        else:
            rendered.append(text)
    return "".join(rendered)


def _report_note_blocks(blocks: tuple) -> str:
    rendered = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if block.kind in {"list-item", "table-row"}:
            kind = block.kind
            rows = []
            while index < len(blocks) and blocks[index].kind == kind:
                rows.append("<li>{}</li>".format(_report_note_spans(blocks[index].spans)))
                index += 1
            class_name = "report-note-list" if kind == "list-item" else "report-note-table"
            rendered.append('<ul class="{}">{}</ul>'.format(class_name, "".join(rows)))
            continue
        rendered.append("<p>{}</p>".format(_report_note_spans(block.spans)))
        index += 1
    return "".join(rendered)


def _report_notes(document: ReportDocument) -> str:
    if not document.intro_blocks and not document.report_sections:
        return ""
    intro = ""
    if document.intro_blocks:
        intro = '<div class="report-note-intro" aria-label="报告口径">{}</div>'.format(
            _report_note_blocks(document.intro_blocks)
        )
    sections = "".join(
        '<section class="report-note-section" data-component="report-note-section" '
        'aria-label="{}"><h3>{}</h3>{}</section>'.format(
            _escape(section.title),
            _escape(section.title),
            _report_note_blocks(section.blocks),
        )
        for section in document.report_sections
    )
    return (
        '<details class="report-notes" data-component="report-notes">'
        '<summary><p>补充口径</p><h2 id="report-notes-title">报告说明</h2></summary>'
        '{}{}</details>'
    ).format(intro, sections)


def _archive_slot_label(report: dict) -> str:
    label = str(report.get("label", ""))
    return "盘后" if label == "收盘" else label


def _archive_sort_key(report: dict) -> tuple:
    slot = str(report.get("slot", ""))
    return (int(slot) if slot.isdigit() else 9999, slot, str(report.get("id", "")))


def _report_archive(document: ReportDocument, report_index: list[dict]) -> str:
    reports_by_date: dict[str, list[dict]] = {}
    for report in report_index:
        report_date = str(report.get("date", ""))
        reports_by_date.setdefault(report_date, []).append(report)

    date_groups = []
    for report_date in sorted(reports_by_date, reverse=True):
        reports = sorted(reports_by_date[report_date], key=_archive_sort_key)
        target = reports[-1]
        anchor = "archive-{}".format(report_date)
        slots_id = "archive-slots-{}".format(report_date)
        # plain jump to the report page top; no #archive anchor so the page
        # does not scroll to the sidebar archive after a date switch
        target_url = Path(str(target.get("url", ""))).name
        slot_links = []
        for report in reports:
            url = Path(str(report.get("url", ""))).name
            current = ' aria-current="page"' if report.get("id") == document.meta.report_id else ""
            slot_links.append(
                '<a data-report-link data-report-label="{}" href="{}"{}>{}</a>'.format(
                    _escape("{} · {}".format(report_date, _archive_slot_label(report))),
                    _escape(url),
                    current,
                    _escape(_archive_slot_label(report)),
                )
            )
        date_groups.append(
            '<div class="archive-date-group" id="{}" data-report-date="{}"><a '
            'class="archive-date-link" aria-expanded="false" aria-controls="{}" href="{}">{}</a>'
            '<div class="archive-slots" id="{}" hidden>{}</div></div>'.format(
                _escape(anchor),
                _escape(report_date),
                _escape(slots_id),
                _escape(target_url),
                _escape(report_date),
                _escape(slots_id),
                "".join(slot_links),
            )
        )
    return "".join(date_groups)


def _filter_bar(document: ReportDocument) -> str:
    if document.themes:
        return ""
    metadata = '<div class="filter-meta"><span>数据截止</span><span>{}</span></div>'.format(
        _escape(document.meta.cutoff)
    )
    return (
        '<nav class="filter-bar" data-component="filters" aria-label="新闻类别筛选">'
        '{}<div class="filter-actions">'
        '<button class="filter-button is-active" type="button" data-category="all" '
        'aria-pressed="true">全部</button>'
        '<button class="filter-button" type="button" data-category="政策" '
        'aria-pressed="false">政策</button>'
        '<button class="filter-button" type="button" data-category="财报" '
        'aria-pressed="false">财报</button>'
        '<button class="filter-button" type="button" data-category="产业" '
        'aria-pressed="false">产业</button>'
        '<button class="filter-button" type="button" data-category="地缘" '
        'aria-pressed="false">地缘</button>'
        '<button class="filter-button" type="button" data-category="其他" '
        'aria-pressed="false">其他</button>'
        '</div></nav>'
    ).format(metadata)


def _calendar_filter(report_index: list[dict], current_date: str) -> str:
    """Sidebar calendar date picker (antd-like) with the report-date JSON."""
    by_date = {}
    for report in report_index:
        date = str(report.get("date", ""))
        if date:
            by_date[date] = Path(str(report.get("url", ""))).name
    dates = sorted(by_date)
    latest = current_date or (dates[-1] if dates else "")
    payload = json.dumps(by_date, ensure_ascii=False)
    return (
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
    ).format(_escape(latest), payload)


def _brief_pane(daily_info_root: Optional[Path], report_date: str) -> str:
    """外围 pane: daily_info morning brief for the report date (latest run of
    that day, else the newest brief)."""
    if daily_info_root is None:
        return "<p class=\"brief-unavailable\">外围晨报未配置（构建时未提供 daily-info 路径）。</p>"
    root = daily_info_root.expanduser().resolve()
    index_brief = root / "reports/index/A股盘前晨报.html"
    # daily_info keeps reports/index as its current brief; prefer it so the
    # latest complete data (incl. FX consensus) shows on every page
    path = index_brief
    if not path.is_file():
        return "<p class=\"brief-unavailable\">当日无外围晨报。</p>"
    try:
        body, _ = _transform_brief_body(
            _extract_brief_body(path.read_text(encoding="utf-8"))
        )
    except FusionBuildError as error:
        return "<p class=\"brief-unavailable\">外围晨报不可用：{}</p>".format(
            _escape(str(error))
        )
    return body


def render_report(
    document: ReportDocument,
    report_index: list[dict],
    daily_info_root: Optional[Path] = None,
) -> str:
    """Render fixed template with escaped text and allowlisted http/https source URLs."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    js_version = max(
        (Path(__file__).with_name("assets") / name).stat().st_mtime
        for name in ("app.js", "calendar.js")
    )
    mmdd = str(document.meta.report_date).replace("-", "")[4:]
    session = "盘前" if document.meta.slot == "0800" else "盘后"
    display_title = "{}{}新闻速递".format(mmdd, session) if mmdd else document.meta.title
    replacements = {
        "PAGE_TITLE": _escape(display_title),
        "REPORT_ID": _escape(document.meta.report_id),
        "CALENDAR_FILTER": _calendar_filter(report_index, document.meta.report_date),
        "TOPBAR": (
            '<div class="report-heading"><h1>{}</h1></div>'
            '<div class="report-topbar-right">'
            '<nav class="report-tabs" aria-label="视图切换">'
            '<button type="button" class="report-tab-button" data-pane-target="brief" aria-selected="true">外围</button>'
            '<button type="button" class="report-tab-button" data-pane-target="news" aria-selected="false">新闻</button>'
            '</nav>'
            '</div>'
        ).format(
            _escape(display_title),
        ),
        "BRIEF_PANE": _brief_pane(daily_info_root, document.meta.report_date),
        "JS_VERSION": str(int(js_version)),
        "REPORT_ARCHIVE": _report_archive(document, report_index),
        "FILTER_BAR": _filter_bar(document),
        "THEME_CONTENT": _theme_content(document),
        "NEWS_ITEMS": (
            '<section data-component="news-list">{}</section>'.format("".join(
                _news_item(
                    item,
                    _news_instance_id(document.meta.report_id, "legacy", item.event_id or str(item.rank)),
                )
                for item in document.items
            ))
            if not document.themes else ""
        ),
        "PENDING_ITEMS": _report_notes(document) + _pending_items(document),
    }
    template_placeholders = set(re.findall(r"{{[^{}]+}}", template))
    expected_placeholders = {"{{" + name + "}}" for name in replacements}
    if template_placeholders != expected_placeholders:
        raise ValueError("report template has unresolved placeholders")
    template_without_known_placeholders = template
    for placeholder in expected_placeholders:
        template_without_known_placeholders = template_without_known_placeholders.replace(placeholder, "")
    if "{{" in template_without_known_placeholders or "}}" in template_without_known_placeholders:
        raise ValueError("report template has malformed placeholders")
    for name, value in replacements.items():
        template = template.replace("{{" + name + "}}", value)
    return template


def _manifest_entry(document: ReportDocument) -> dict:
    meta = document.meta
    return {
        "id": meta.report_id,
        "date": meta.report_date,
        "slot": meta.slot,
        "label": meta.slot_label,
        "title": meta.title,
        "url": _report_url(meta.report_date, meta.slot),
    }


def _write_index(destination: Path, latest_url: str, latest_title: str) -> None:
    # index is only a pointer to the latest report page (every report page is
    # itself the fused view with 外围/新闻 tabs)
    escaped_url = _escape(latest_url)
    destination.write_text(
        "<!doctype html>\n"
        '<html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url={}">'
        '<title>新闻速递</title><link rel="icon" href="data:,">'
        "</head><body>"
        '<p><a href="{}">{}</a></p></body></html>\n'.format(
            escaped_url, escaped_url, _escape(latest_title)
        ),
        encoding="utf-8",
    )


def _copy_assets(project_root: Path, destination: Path) -> None:
    source = project_root / "web" / "assets"
    if source.is_dir():
        shutil.copytree(source, destination / "assets")


def _output_path(destination: Path, url: str) -> Path:
    relative = Path(url)
    if relative.is_absolute() or relative.parts != ("reports", relative.name):
        raise ValueError("report path must be a reports/<filename> relative path")
    path = destination / relative
    try:
        path.resolve().relative_to(destination.resolve())
    except ValueError:
        raise ValueError("report path escapes build output: {}".format(url))
    return path


def _validate_output(destination: Path, report_index: list[dict]) -> None:
    expected_urls = [report["url"] for report in report_index]
    if not expected_urls or any(not _output_path(destination, url).is_file() for url in expected_urls):
        raise ValueError("not every report page was generated")
    for url in expected_urls:
        page = (destination / url).read_text(encoding="utf-8")
        if any(marker not in page for marker in _REQUIRED_MARKERS):
            raise ValueError("report page misses fixed semantic contract: {}".format(url))
        if 'href="/assets/' in page or 'src="/assets/' in page:
            raise ValueError("report page uses non-relative asset path: {}".format(url))
    manifest = json.loads((destination / "reports.json").read_text(encoding="utf-8"))
    if manifest.get("latest") != expected_urls[-1]:
        raise ValueError("manifest latest report is inconsistent")
    index = (destination / "index.html").read_text(encoding="utf-8")
    if expected_urls[-1] not in index or "http-equiv=\"refresh\"" not in index:
        raise ValueError("index page does not redirect to the latest report")


def _checked_output_dir(project_root: Path, output_dir: Path) -> Path:
    target = output_dir.expanduser().resolve()
    rejected = {Path("/").resolve(), project_root.resolve(), Path.home().resolve()}
    if target in rejected or target.name != "dist":
        raise ValueError("output directory must be a non-root directory named dist")
    return target


def _remove_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _atomic_replace(target: Path, next_output: Path) -> None:
    previous = target.with_name("{}.previous-{}".format(target.name, os.getpid()))
    if previous.exists():
        raise FileExistsError("refusing to replace existing previous output: {}".format(previous))
    moved_previous = False
    try:
        if target.exists():
            os.replace(target, previous)
            moved_previous = True
        os.replace(next_output, target)
    except Exception:
        if moved_previous and previous.exists() and not target.exists():
            os.replace(previous, target)
        raise
    if moved_previous:
        try:
            _remove_directory(previous)
        except OSError:
            # The new output is already in place. Leave only this explicit backup for recovery.
            pass


def build_site(
    project_root: Path,
    output_dir: Path,
    daily_info_root: Optional[Path] = None,
) -> BuildResult:
    """Build next to output_dir, validate, then atomically replace only output_dir.

    When daily_info_root is given, also renders fusion.html (radar styles, two tabs:
    晨报 from the daily_info brief, 新闻 from the latest radar report). A fusion
    failure never rolls back the radar build itself.
    """
    project_root = project_root.expanduser().resolve()
    target = _checked_output_dir(project_root, output_dir)
    next_output = target.with_name("{}.next-{}".format(target.name, os.getpid()))
    if next_output.exists():
        raise FileExistsError("refusing to replace existing next output: {}".format(next_output))

    try:
        next_output.mkdir(parents=True)
        documents = [parse_report(path, entry) for path, entry in discover_reports(project_root)]
        report_index = [_manifest_entry(document) for document in documents]
        for document, report in zip(documents, report_index):
            page = render_report(document, report_index, daily_info_root=daily_info_root)
            report_path = _output_path(next_output, report["url"])
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(page, encoding="utf-8")
        latest = report_index[-1]
        (next_output / "reports.json").write_text(
            json.dumps({"reports": report_index, "latest": latest["url"]}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        _write_index(next_output / "index.html", latest["url"], latest["title"])
        _copy_assets(project_root, next_output)
        _validate_output(next_output, report_index)
        assert_public_tree_safe(next_output)
        _atomic_replace(target, next_output)
    except Exception:
        _remove_directory(next_output)
        raise

    return BuildResult(
        output_dir=target,
        report_count=len(documents),
        item_count=sum(len(document.items) for document in documents),
        latest_url=latest["url"],
    )


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build static news-radar report pages")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--daily-info-root",
        type=Path,
        default=None,
        help="optional root of the daily_info project; when given, also renders fusion.html",
    )
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    try:
        result = build_site(args.project_root, output, daily_info_root=args.daily_info_root)
    except Exception as error:
        print("build failed: {}".format(error), file=sys.stderr)
        return 1
    print("built {} reports ({} items) in {}".format(result.report_count, result.item_count, result.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
