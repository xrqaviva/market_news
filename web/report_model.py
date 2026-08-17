from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class SourceLink:
    channel: str
    time_bj: str
    label: str
    url: str


@dataclass(frozen=True)
class StockMapping:
    name: str
    ticker: str
    evidence: str


@dataclass(frozen=True)
class NewsIndexEntry:
    rank: int
    event_id: str
    title: str
    score: int
    theme_ids: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NewsItem:
    rank: int
    title: str
    core: str
    score: int
    score_breakdown: str = ""
    signal: str = ""
    market_feedback: str = ""
    pricing: str = ""
    boundary: str = ""
    variables: str = ""
    heat_change: str = ""
    release_session: str = ""
    event_date: str = ""
    category: str = "其他"
    sources: Tuple[SourceLink, ...] = field(default_factory=tuple)
    event_id: str = ""
    theme_ids: Tuple[str, ...] = field(default_factory=tuple)
    supplemental_details: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PendingItem:
    title: str
    known: str
    reason: str
    sources: Tuple[SourceLink, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReportInline:
    text: str
    url: str = ""


@dataclass(frozen=True)
class ReportBlock:
    kind: str
    spans: Tuple[ReportInline, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReportSection:
    title: str
    blocks: Tuple[ReportBlock, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReportMeta:
    report_id: str
    report_date: str
    slot: str
    slot_label: str
    title: str
    window: str
    cutoff: str
    source_name: str


@dataclass(frozen=True)
class ThemeGroup:
    theme_id: str
    name: str
    total_score: int
    catalyst: str
    risk_boundary: str
    direct_mappings: Tuple[StockMapping, ...] = field(default_factory=tuple)
    sector_representatives: Tuple[StockMapping, ...] = field(default_factory=tuple)
    event_ids: Tuple[str, ...] = field(default_factory=tuple)
    items: Tuple[NewsItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReportDocument:
    meta: ReportMeta
    items: Tuple[NewsItem, ...]
    pending_items: Tuple[PendingItem, ...] = field(default_factory=tuple)
    news_index: Tuple[NewsIndexEntry, ...] = field(default_factory=tuple)
    themes: Tuple[ThemeGroup, ...] = field(default_factory=tuple)
    other_items: Tuple[NewsItem, ...] = field(default_factory=tuple)
    intro_blocks: Tuple[ReportBlock, ...] = field(default_factory=tuple)
    report_sections: Tuple[ReportSection, ...] = field(default_factory=tuple)
