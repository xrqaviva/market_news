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
    )
    details = "".join(
        "<p><strong>{}</strong>{}</p>".format(_escape(label), _escape(value))
        for label, value in detail_fields
        if value
    )
    detail_kind = "analysis" if details else "sources-inline"
    return (
        '<article data-component="news-detail" data-rank="{}" data-category="{}" data-detail-kind="{}" '
        'id="news-{}" data-instance-id="{}" data-event-id="{}">'
        '<h2>{}. {}</h2><p>{}</p>{}<p>热点权重：{}/100</p>{}{}</article>'
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
        association_labels,
        details,
    )


def _news_index(document: ReportDocument, theme_names: dict[str, str]) -> str:
    if not document.news_index:
        return ""
    rows = []
    for entry in document.news_index:
        scope_id = entry.theme_ids[0] if entry.theme_ids else "other"
        instance_id = _news_instance_id(document.meta.report_id, scope_id, entry.event_id)
        rows.append(
            '<li><a href="#news-{}"><span class="news-index-rank">{:02d}</span>'
            '<span class="news-index-title">{}</span><strong>{}/100</strong></a>{}</li>'.format(
                _escape(instance_id),
                entry.rank,
                _escape(entry.title),
                _escape(entry.score),
                _association_badges(entry.theme_ids, theme_names),
            )
        )
    return (
        '<section class="news-index" data-component="news-index"><h2>单条新闻热榜索引</h2>'
        '<ol>{}</ol></section>'
    ).format("".join(rows))


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


def _theme_group(document: ReportDocument, theme, theme_names: dict[str, str]) -> str:
    rows = "".join(
        _news_item(
            item,
            _news_instance_id(document.meta.report_id, theme.theme_id, item.event_id),
            _association_badges(item.theme_ids, theme_names),
        )
        for item in theme.items
    )
    return (
        '<section class="theme-group" data-component="theme-group" id="theme-{}">'
        '<header><h2>{}</h2><p class="theme-total">{}分 · 关联新闻{}条</p></header>'
        '<p class="theme-catalyst"><strong>核心催化</strong>{}</p>{}{}'
        '<p class="theme-risk"><strong>题材风险边界</strong>{}</p>'
        '<section class="theme-news-list" data-component="news-list">{}</section></section>'
    ).format(
        _escape(_safe_dom_id(theme.theme_id)),
        _escape(theme.name),
        _escape(theme.total_score),
        _escape(len(theme.items)),
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
            _association_badges(item.theme_ids, theme_names),
        )
        for item in document.other_items
    )
    return (
        '<section class="other-important-news" data-component="other-important-news">'
        '<h2>其他重要新闻</h2><section data-component="news-list">{}</section></section>'
    ).format(rows)


def _theme_content(document: ReportDocument) -> str:
    if not document.themes:
        return ""
    theme_names = {theme.theme_id: theme.name for theme in document.themes}
    has_repeated_item = any(len(item.theme_ids) > 1 for theme in document.themes for item in theme.items)
    disclosure = (
        '<p class="theme-disclosure">跨题材新闻会在各关联题材中重复计分；各处保留完整详情。</p>'
        if has_repeated_item else ""
    )
    return "{}{}{}{}".format(
        _news_index(document, theme_names),
        disclosure,
        "".join(_theme_group(document, theme, theme_names) for theme in document.themes),
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
        '<section class="pending-section" data-component="pending-list">'
        '<h2>待核验线索</h2><p>以下线索不参与主榜计分；补齐具体原文和北京时间后再转入主榜。</p>'
        '{}'
        '</section>'
    ).format("".join(rows))


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
        target_url = "{}#{}".format(Path(str(target.get("url", ""))).name, anchor)
        slot_links = []
        for report in reports:
            url = "{}#{}".format(Path(str(report.get("url", ""))).name, anchor)
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
    metadata = '<div class="filter-meta"><span>数据截止</span><span>{}</span></div>'.format(
        _escape(document.meta.cutoff)
    )
    if document.themes:
        return (
            '<nav class="filter-bar" data-component="filters" aria-label="报告元数据">'
            '{}'
            '</nav>'
        ).format(metadata)
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


def render_report(document: ReportDocument, report_index: list[dict]) -> str:
    """Render fixed template with escaped text and allowlisted http/https source URLs."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    topbar_meta = " · ".join(
        part for part in (
            document.meta.report_date,
            document.meta.slot_label,
            document.meta.window,
        ) if part
    )
    replacements = {
        "PAGE_TITLE": _escape(document.meta.title),
        "REPORT_ID": _escape(document.meta.report_id),
        "TOPBAR": "<h1>{}</h1><p>{}</p>".format(
            _escape(document.meta.title),
            _escape(topbar_meta),
        ),
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
        "PENDING_ITEMS": _pending_items(document),
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
    escaped_url = _escape(latest_url)
    destination.write_text(
        "<!doctype html>\n"
        '<html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url={}">'
        '<title>新闻雷达</title><link rel="icon" href="data:,">'
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
        raise ValueError("index page does not redirect to latest report")


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


def build_site(project_root: Path, output_dir: Path) -> BuildResult:
    """Build next to output_dir, validate, then atomically replace only output_dir."""
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
            page = render_report(document, report_index)
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
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    try:
        result = build_site(args.project_root, output)
    except Exception as error:
        print("build failed: {}".format(error), file=sys.stderr)
        return 1
    print("built {} reports ({} items) in {}".format(result.report_count, result.item_count, result.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
