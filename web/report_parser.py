"""Parse the constrained Markdown format used by news radar reports."""

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from web.report_model import NewsItem, ReportDocument, ReportMeta, SourceLink


_HEADING = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)
_COMPACT = re.compile(r"^(\d+)\.\s+\*\*(.+?)｜(\d+)/100\*\*(?:：\s*(.*))?$", re.MULTILINE)
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_SCORE = re.compile(r"\*\*热点权重：(\d+)/100\*\*(?:（(.+?)）)?")
_STANDARD_REPORT = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{4})-.+\.md$")


@dataclass(frozen=True)
class CatalogEntry:
    report_id: str
    path: str
    report_date: str
    slot: str
    label: str


def _plain(value: str) -> str:
    value = html.unescape(value)
    value = _LINK.sub(lambda match: match.group(1), value)
    value = re.sub(r"<[^>]*>", "", value)
    value = re.sub(r"\*{1,3}", "", value)
    return re.sub(r"\s+", " ", value).strip(" -：")


def _valid_url(value: str) -> str:
    value = html.unescape(value).strip()
    if not value or re.match(r"(?i)^(?:javascript|data):", value):
        return ""
    return value


def _slot_label(slot: str) -> str:
    return {"0800": "盘前", "1200": "午间", "1500": "盘后", "1800": "收盘"}.get(slot, slot)


def load_catalog(project_root: Path) -> List[CatalogEntry]:
    """Load explicit legacy entries, verify relative paths, then append standard-named reports."""
    project_root = project_root.resolve()
    catalog_path = Path(__file__).with_name("report_catalog.json")
    raw_entries = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = []
    explicit_paths = set()
    for raw in raw_entries:
        relative = Path(raw["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("catalog path must be project-relative: {}".format(raw["path"]))
        resolved = (project_root / relative).resolve()
        if project_root not in resolved.parents or not resolved.is_file():
            raise ValueError("catalog report is missing: {}".format(raw["path"]))
        explicit_paths.add(relative.as_posix())
        entries.append(CatalogEntry(
            report_id=raw["report_id"], path=relative.as_posix(),
            report_date=raw["date"], slot=raw["slot"], label=raw["label"],
        ))

    reports_dir = project_root / "reports"
    if reports_dir.is_dir():
        for candidate in reports_dir.iterdir():
            match = _STANDARD_REPORT.match(candidate.name)
            relative = candidate.relative_to(project_root).as_posix()
            if not match or not candidate.is_file() or relative in explicit_paths:
                continue
            report_date, slot = match.groups()
            entries.append(CatalogEntry(
                report_id=report_date.replace("-", "") + "-" + slot,
                path=relative, report_date=report_date, slot=slot,
                label=_slot_label(slot),
            ))
    return entries


def discover_reports(project_root: Path) -> List[Tuple[Path, CatalogEntry]]:
    """Return (path, entry) sorted by date and slot ascending; reject duplicate report_id."""
    seen = set()
    found = []
    for entry in load_catalog(project_root):
        if entry.report_id in seen:
            raise ValueError("duplicate report_id: {}".format(entry.report_id))
        seen.add(entry.report_id)
        found.append((project_root / entry.path, entry))
    return sorted(found, key=lambda pair: (pair[1].report_date, pair[1].slot))


def _field(block: str, label: str) -> str:
    pattern = re.compile(r"\*\*" + re.escape(label) + r"：\*\*\s*(.+)")
    match = pattern.search(block)
    return _plain(match.group(1)) if match else ""


def _pricing(block: str) -> str:
    match = re.search(r"\*\*即时市场定价：([^*]+)\*\*", block)
    return _plain(match.group(1)) if match else ""


def _category(title: str, core: str) -> str:
    text = title + " " + core
    categories = (
        ("政策", ("政策", "政治局", "央行", "利率", "监管", "国务院", "部委", "规划")),
        ("财报", ("财报", "业绩", "营收", "收入", "利润", "eps", "季度")),
        ("产业", ("芯片", "半导体", "人工智能", "ai", "储能", "能源", "汽车", "机器人", "订单")),
        ("地缘", ("伊朗", "美国", "中东", "航运", "战争", "关税", "出口", "制裁")),
    )
    lower = text.lower()
    for category, keywords in categories:
        if any(keyword.lower() in lower for keyword in keywords):
            return category
    return "其他"


def _sources_from_table(block: str) -> Tuple[SourceLink, ...]:
    sources = []
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(columns) < 3 or columns[0] == "传播渠道" or set("".join(columns)) <= {"-", ":"}:
            continue
        for label, raw_url in _LINK.findall(" ".join(columns[2:])):
            url = _valid_url(raw_url)
            if url:
                sources.append(SourceLink(_plain(columns[0]), _plain(columns[1]), _plain(label), url))
    return tuple(sources)


def _inline_sources(text: str) -> Tuple[SourceLink, ...]:
    sources = []
    for label, raw_url in _LINK.findall(text):
        url = _valid_url(raw_url)
        if url:
            sources.append(SourceLink("报告链接", "", _plain(label), url))
    return tuple(sources)


def _top_sections(text: str) -> Iterable[Tuple[int, str, str]]:
    headings = list(_HEADING.finditer(text))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        yield int(heading.group(1)), heading.group(2), text[heading.end():end]


def _make_top_item(rank: int, title: str, block: str) -> NewsItem:
    score_match = _SCORE.search(block)
    if not score_match:
        score_match = re.search(r"｜(\d+)/100", title)
    if not score_match:
        raise ValueError("missing score for rank {}".format(rank))
    score = int(score_match.group(1))
    breakdown = _plain(score_match.group(2) or "") if score_match.lastindex and score_match.lastindex >= 2 else ""
    title = _plain(re.sub(r"｜\d+/100$", "", title))
    core = _field(block, "核心信息")
    sources = _sources_from_table(block)
    if not sources:
        sources = _inline_sources(block)
    return NewsItem(
        rank=rank, title=title, core=core, score=score, score_breakdown=breakdown,
        signal=_field(block, "关键信号/预期差"),
        market_feedback=(
            _field(block, "带时间市场反馈") or _field(block, "财报后盘后反馈")
            or _field(block, "财报后首个可交易时段反馈")
            or _field(block, "财报后发布日余下交易时段反馈")
        ),
        pricing=_pricing(block), boundary=_field(block, "判断边界"),
        variables=_field(block, "后续变量"), heat_change=_field(block, "热度变化"),
        category=_category(title, core), sources=sources,
    )


def _compact_items(text: str) -> Iterable[NewsItem]:
    for match in _COMPACT.finditer(text):
        rank, title, score, core = match.groups()
        core = core or ""
        yield NewsItem(
            rank=int(rank), title=_plain(title), core=_plain(core), score=int(score),
            category=_category(title, core), sources=_inline_sources(core),
        )


def _validate_items(items: Tuple[NewsItem, ...]) -> None:
    ranks = [item.rank for item in items]
    scores = [item.score for item in items]
    if len(ranks) != len(set(ranks)):
        raise ValueError("report has duplicate ranks")
    if scores != sorted(scores, reverse=True):
        raise ValueError("report scores must descend")
    if any(not item.sources for item in items):
        raise ValueError("each report item needs a source link")


def parse_report(path: Path, entry: CatalogEntry) -> ReportDocument:
    """Parse heading sections and compact numbered lines without inventing missing fields."""
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    window_match = re.search(r"^>\s+\*\*窗口：\*\*\s*(.+)$", text, re.MULTILINE)
    cutoff_match = re.search(r"^>\s+\*\*生成任务启动：\*\*\s*([^。]+)", text, re.MULTILINE)
    top_items = [_make_top_item(rank, title, block) for rank, title, block in _top_sections(text)]
    heading_ranks = {item.rank for item in top_items}
    compact_items = [item for item in _compact_items(text) if item.rank not in heading_ranks]
    items = tuple(sorted(top_items + compact_items, key=lambda item: item.rank))
    _validate_items(items)
    return ReportDocument(
        meta=ReportMeta(
            report_id=entry.report_id, report_date=entry.report_date, slot=entry.slot,
            slot_label=entry.label, title=_plain(title_match.group(1)) if title_match else "",
            window=_plain(window_match.group(1)) if window_match else "",
            cutoff=_plain(cutoff_match.group(1)) if cutoff_match else "",
            source_name=entry.path,
        ),
        items=items,
    )
