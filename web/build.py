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
from urllib.parse import urlsplit

from web.report_model import NewsItem, ReportDocument
from web.report_parser import discover_reports, parse_report
from web.security import assert_public_tree_safe


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


def _safe_source_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return value


def _source_links(item: NewsItem) -> str:
    links = []
    for source in item.sources:
        url = _safe_source_url(source.url)
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
        return '<ul data-component="sources"></ul>'
    return '<ul data-component="sources">{}</ul>'.format("".join(links))


def _news_item(item: NewsItem) -> str:
    detail_fields = (
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
        '<article data-component="news-detail" data-rank="{}" data-category="{}" data-detail-kind="{}">'
        '<h2>{}. {}</h2><p>{}</p>{}<p>热点权重：{}/100</p>{}</article>'
    ).format(
        _escape(item.rank),
        _escape(item.category),
        detail_kind,
        _escape(item.rank),
        _escape(item.title),
        _escape(item.core),
        _source_links(item),
        _escape(item.score),
        details,
    )


def _report_archive(document: ReportDocument, report_index: list[dict]) -> str:
    entries = []
    for report in report_index:
        url = Path(str(report["url"])).name
        label = "{} {}".format(report["date"], report["label"])
        current = ' aria-current="page"' if report["id"] == document.meta.report_id else ""
        entries.append(
            '<a href="{}"{}>{}</a>'.format(_escape(url), current, _escape(label))
        )
    return "".join(entries)


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
        "FILTERS": "<span>{}</span>".format(_escape(document.meta.cutoff)),
        "NEWS_ITEMS": "".join(_news_item(item) for item in document.items),
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
