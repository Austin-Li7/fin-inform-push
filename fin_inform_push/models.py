from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Article:
    title: str
    source: str
    url: str
    published_at: datetime
    category: str
    summary: str
    market_impact: str
    thesis: str


@dataclass(frozen=True)
class BriefingWindow:
    slug: str
    title: str
    start_hour: int
    end_hour: int
    strategy_prompt: str


@dataclass(frozen=True)
class MacroMetric:
    name: str
    value: str
    as_of: str
    interpretation: str
    focus: str
    source: str


@dataclass(frozen=True)
class ResearchItem:
    title: str
    source: str
    as_of: str
    summary: str
    url: str


@dataclass(frozen=True)
class BriefingNote:
    window: BriefingWindow
    date_label: str
    headline: str
    key_takeaways: list[str] = field(default_factory=list)
    macro_metrics: list[MacroMetric] = field(default_factory=list)
    research_items: list[ResearchItem] = field(default_factory=list)
    scenario_analysis: list[str] = field(default_factory=list)
    investment_summary: str = ""
    articles: list[Article] = field(default_factory=list)
