"""Parse the constrained Markdown format used by news radar reports."""

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from web.report_model import (
    NewsIndexEntry, NewsItem, PendingItem, ReportDocument, ReportMeta, SourceLink,
    StockMapping, ThemeGroup,
)


_HEADING = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)
_COMPACT = re.compile(r"^(\d+)\.\s+\*\*(.+?)｜(\d+)/100\*\*(?:：\s*(.*))?$", re.MULTILINE)
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_SCORE = re.compile(r"\*\*热点权重：(\d+)/100\*\*(?:（(.+?)）)?")
_STANDARD_REPORT = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{4})-.+\.md$")
_PENDING_SECTION = re.compile(
    r"^##\s+待核验线索[^\n]*\n(.*?)(?=^##\s+|\Z)", re.MULTILINE | re.DOTALL
)
_PENDING_HEADING = re.compile(r"^###\s+(.+)$", re.MULTILINE)
_THEMED_INDEX_HEADING = re.compile(r"^##\s+单条新闻热榜索引[^\n]*$", re.MULTILINE)
_SECTION = re.compile(r"^##\s+([^\n]+)\n(.*?)(?=^##\s+|\Z)", re.MULTILINE | re.DOTALL)
_NESTED_NEWS = re.compile(
    r"^####\s+新闻：\s*(\d+)\s*[｜|]\s*([^｜|]+)\s*[｜|]\s*(.+?)\s*[｜|]\s*(\d+)(?:/100|分)?\s*$",
    re.MULTILINE,
)
_THEME_HEADING = re.compile(
    r"^###\s+主线\s*\d*\s*：\s*(.+?)\s*[｜|]\s*(\d+)(?:分)?\s*[｜|]\s*"
    r"(?:关联新闻(?:数)?\s*)?(\d+)(?:条)?\s*$",
    re.MULTILINE,
)


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
            sources.append(SourceLink("原始来源", "", _plain(label), url))
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
            _field(block, "带时间市场反馈") or _field(block, "财报市场反馈")
            or _field(block, "财报后盘后反馈")
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
        visible_title = _plain(title)
        visible_core = _plain(_LINK.sub("", core or "")).strip(" ｜")
        yield NewsItem(
            rank=int(rank), title=visible_title, core=visible_core, score=int(score),
            category=_category(visible_title, visible_core), sources=_inline_sources(core or ""),
        )


def _pending_items(text: str) -> Tuple[PendingItem, ...]:
    section_match = _PENDING_SECTION.search(text)
    if not section_match:
        return tuple()
    section = section_match.group(1)
    headings = list(_PENDING_HEADING.finditer(section))
    pending = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        block = section[heading.end():end]
        known = _field(block, "已知事实") or _field(block, "已知线索")
        reason = _field(block, "待核原因")
        sources = _inline_sources(block)
        if not known or not reason:
            raise ValueError("pending item needs known facts and verification reason")
        pending.append(PendingItem(
            title=_plain(heading.group(1)), known=known, reason=reason, sources=sources,
        ))
    return tuple(pending)


def _theme_ids(value: str) -> Tuple[str, ...]:
    value = re.sub(r"（[^）]*跨题材重复计分[^）]*）", "", value)
    return tuple(part.strip() for part in re.split(r"[、,，]", value) if part.strip() and part.strip() != "-")


def _section_body(text: str, name: str) -> str:
    for heading, body in _SECTION.findall(text):
        if _plain(heading) == name:
            return body
    return ""


def _parse_news_index(text: str) -> Tuple[NewsIndexEntry, ...]:
    section = _section_body(text, "单条新闻热榜索引")
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(columns) < 5 or columns[0] == "原排名" or set("".join(columns)) <= {"-", ":"}:
            continue
        score_match = re.search(r"\d+", columns[3])
        if not score_match:
            raise ValueError("news index item needs a score")
        rows.append(NewsIndexEntry(
            rank=int(columns[0]), event_id=_plain(columns[1]), title=_plain(columns[2]),
            score=int(score_match.group()), theme_ids=_theme_ids(_plain(columns[4])),
        ))
    if not rows:
        raise ValueError("single-news index needs ranked rows")
    return tuple(rows)


def _parse_stock_mappings(block: str, label: str) -> Tuple[StockMapping, ...]:
    match = re.search(
        r"^\*\*" + re.escape(label) + r"：\*\*\s*(.*?)(?=^\*\*[^\n]*：\*\*|^####\s+新闻：|\Z)",
        block, re.MULTILINE | re.DOTALL,
    )
    if not match:
        return tuple()
    mappings = []
    for line in match.group(1).splitlines():
        mapping = re.match(r"\s*[-*]\s*(.+?)（(\d{6})）：\s*(.+)$", line)
        if mapping:
            mappings.append(StockMapping(
                name=_plain(mapping.group(1)), ticker=mapping.group(2), evidence=_plain(mapping.group(3)),
            ))
    return tuple(mappings)


def _parse_nested_news_blocks(text: str) -> Tuple[NewsItem, ...]:
    headings = list(_NESTED_NEWS.finditer(text))
    items = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        rank, event_id, title, score = heading.groups()
        block = text[heading.end():end]
        sources = _sources_from_table(block) or _inline_sources(block)
        item = NewsItem(
            rank=int(rank), event_id=_plain(event_id), title=_plain(title), score=int(score),
            core=_field(block, "核心信息"), score_breakdown="",
            signal=_field(block, "关键信号/预期差"),
            market_feedback=(
                _field(block, "带时间市场反馈") or _field(block, "财报市场反馈")
                or _field(block, "财报后盘后反馈") or _field(block, "财报后首个可交易时段反馈")
                or _field(block, "财报后发布日余下交易时段反馈")
            ),
            pricing=_pricing(block), boundary=_field(block, "判断边界"),
            variables=_field(block, "后续变量"), heat_change=_field(block, "热度变化"),
            category=_category(_plain(title), _field(block, "核心信息")), sources=sources,
            theme_ids=_theme_ids(_field(block, "关联题材")),
        )
        if not item.sources:
            raise ValueError("each themed news item needs a source link")
        items.append(item)
    return tuple(items)


def _parse_theme_groups(text: str) -> Tuple[ThemeGroup, ...]:
    section = _section_body(text, "题材主线")
    themes = []
    headings = list(_THEME_HEADING.finditer(section))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        name, total_score, declared_count = heading.groups()
        block = section[heading.end():end]
        theme_id = _field(block, "题材ID")
        if not theme_id:
            raise ValueError("theme needs an id")
        catalyst_match = re.search(r"^\*\*核心催化：\*\*[ \t]*(.*)$", block, re.MULTILINE)
        catalyst = _plain(catalyst_match.group(1)) if catalyst_match else ""
        if not catalyst:
            raise ValueError("theme needs a nonempty core catalyst")
        items = tuple(sorted(_parse_nested_news_blocks(block), key=lambda item: item.rank))
        if len(items) != int(declared_count):
            raise ValueError("theme declared item count differs from members")
        themes.append(ThemeGroup(
            theme_id=theme_id, name=_plain(name), total_score=int(total_score),
            catalyst=catalyst, risk_boundary=_field(block, "题材风险边界"),
            direct_mappings=_parse_stock_mappings(block, "直接映射"),
            sector_representatives=_parse_stock_mappings(block, "板块代表"),
            event_ids=tuple(item.event_id for item in items), items=items,
        ))
    if not themes:
        raise ValueError("themed report needs theme groups")
    return tuple(themes)


def _parse_other_items(text: str) -> Tuple[NewsItem, ...]:
    section = _section_body(text, "其他重要新闻")
    if not section:
        raise ValueError("themed report needs Other Important News")
    return tuple(sorted(_parse_nested_news_blocks(section), key=lambda item: item.rank))


def _normalized_theme_name(name: str) -> str:
    return re.sub(r"\s+", "", _plain(name)).casefold()


def _validate_themed_document(
    news_index: Tuple[NewsIndexEntry, ...], themes: Tuple[ThemeGroup, ...], other_items: Tuple[NewsItem, ...],
) -> Tuple[NewsItem, ...]:
    index_by_event = {entry.event_id: entry for entry in news_index}
    if len(index_by_event) != len(news_index):
        raise ValueError("news index has duplicate event ids")
    if [entry.rank for entry in news_index] != sorted(entry.rank for entry in news_index):
        raise ValueError("news index ranks must ascend")
    if len({entry.rank for entry in news_index}) != len(news_index):
        raise ValueError("news index has duplicate ranks")
    theme_by_id = {theme.theme_id: theme for theme in themes}
    if len(theme_by_id) != len(themes):
        raise ValueError("report has duplicate theme ids")

    themed_event_ids = set()
    body_items = []
    for theme in themes:
        if len(theme.event_ids) != len(set(theme.event_ids)):
            raise ValueError("theme has duplicate event_id")
        if len(theme.items) < 2:
            raise ValueError("theme needs at least two ranked items")
        if sum(item.score for item in theme.items) != theme.total_score:
            raise ValueError("theme declared total differs from summed member scores")
        for item in theme.items:
            if item.event_id not in index_by_event:
                raise ValueError("theme references event missing from the index")
            if theme.theme_id not in item.theme_ids:
                raise ValueError("theme/body membership mismatch")
            themed_event_ids.add(item.event_id)
            body_items.append(item)

    other_event_ids = {item.event_id for item in other_items}
    if len(other_event_ids) != len(other_items):
        raise ValueError("Other Important News has duplicate event_id")
    both = themed_event_ids & other_event_ids
    if both:
        raise ValueError("item appears in both a theme and Other Important News")
    for item in other_items:
        if item.event_id not in index_by_event:
            raise ValueError("Other Important News references event missing from the index")
        body_items.append(item)

    canonical = {}
    for item in body_items:
        existing = canonical.get(item.event_id)
        if existing is not None and existing != item:
            raise ValueError("inconsistent event copies")
        canonical[item.event_id] = item
    for entry in news_index:
        item = canonical.get(entry.event_id)
        if item is None:
            raise ValueError("qualified index item missing from themes and Other Important News")
        if (item.rank, item.title, item.score) != (entry.rank, entry.title, entry.score):
            raise ValueError("index/body membership mismatch")
        if set(item.theme_ids) != set(entry.theme_ids):
            raise ValueError("index/body membership mismatch")
        if entry.theme_ids:
            if set(entry.theme_ids) != {theme.theme_id for theme in themes if entry.event_id in theme.event_ids}:
                raise ValueError("index/body membership mismatch")
        elif entry.event_id not in other_event_ids:
            raise ValueError("qualified index item missing from themes and Other Important News")
    return tuple(canonical[entry.event_id] for entry in news_index)


def _parse_themed_report(text: str, meta: ReportMeta) -> ReportDocument:
    news_index = _parse_news_index(text)
    themes = _parse_theme_groups(text)
    other_items = _parse_other_items(text)
    items = _validate_themed_document(news_index, themes, other_items)
    themes = tuple(sorted(
        themes,
        key=lambda theme: (
            -theme.total_score, -len(theme.items), -max(item.score for item in theme.items),
            _normalized_theme_name(theme.name),
        ),
    ))
    return ReportDocument(
        meta=meta, items=items, pending_items=_pending_items(text), news_index=news_index,
        themes=themes, other_items=other_items,
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
    actual_cutoff_match = re.search(r"^>\s+\*\*实际截点：\*\*\s*([^。]+)", text, re.MULTILINE)
    news_window_match = re.search(r"^>\s+\*\*新闻窗口：\*\*\s*(.+)$", text, re.MULTILINE)
    window = _plain(window_match.group(1)) if window_match else ""
    cutoff = (
        _plain(cutoff_match.group(1)) if cutoff_match
        else _plain(actual_cutoff_match.group(1)) if actual_cutoff_match
        else ""
    )
    if not window and news_window_match:
        window = _plain(news_window_match.group(1))
    if not window:
        legacy_news_window_match = re.search(r"^>\s+\*\*新闻窗口：([^*。]+)", text, re.MULTILINE)
        event_window_match = re.search(r"^>\s+\*\*事件窗口：([^*]+)\*\*", text, re.MULTILINE)
        if legacy_news_window_match:
            window = _plain(legacy_news_window_match.group(1)) + "（北京时间）"
        elif event_window_match:
            window = _plain(event_window_match.group(1))
    if not cutoff:
        legacy_cutoff_match = re.search(r"^>\s+截止：(.+)$", text, re.MULTILINE)
        beijing_cutoff_match = re.search(r"北京时间截点：([^｜*]+)", text)
        if legacy_cutoff_match:
            cutoff = _plain(legacy_cutoff_match.group(1)).replace(
                "（Asia/Shanghai）", "（北京时间）"
            )
        elif beijing_cutoff_match:
            cutoff = _plain(beijing_cutoff_match.group(1)) + "（北京时间）"
        else:
            event_end_match = re.search(r"—(\d{1,2}:\d{2})（北京时间）$", window)
            if event_end_match:
                cutoff = event_end_match.group(1) + "（北京时间）"
    meta = ReportMeta(
        report_id=entry.report_id, report_date=entry.report_date, slot=entry.slot,
        slot_label=entry.label, title=_plain(title_match.group(1)) if title_match else "",
        window=window, cutoff=cutoff, source_name=entry.path,
    )
    if _THEMED_INDEX_HEADING.search(text):
        return _parse_themed_report(text, meta)
    top_items = [_make_top_item(rank, title, block) for rank, title, block in _top_sections(text)]
    heading_ranks = {item.rank for item in top_items}
    compact_items = [item for item in _compact_items(text) if item.rank not in heading_ranks]
    items = tuple(sorted(top_items + compact_items, key=lambda item: item.rank))
    _validate_items(items)
    return ReportDocument(
        meta=meta,
        items=items,
        pending_items=_pending_items(text),
    )
