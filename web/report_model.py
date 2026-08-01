from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class SourceLink:
    channel: str
    time_bj: str
    label: str
    url: str


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
    category: str = "其他"
    sources: Tuple[SourceLink, ...] = field(default_factory=tuple)


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
class ReportDocument:
    meta: ReportMeta
    items: Tuple[NewsItem, ...]
