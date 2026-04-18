from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import re
import xml.etree.ElementTree as ET

from fin_inform_push.models import Article


TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
LOCAL_TIMEZONE = ZoneInfo("America/Los_Angeles")
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (fin-inform-push preview)"}


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    category: str


DEFAULT_FEEDS = [
    FeedSource(
        name="CNBC Economy",
        url="https://www.cnbc.com/id/20910258/device/rss/rss.html",
        category="macro",
    ),
    FeedSource(
        name="Investing.com Economic Indicators",
        url="https://www.investing.com/rss/news_14.rss",
        category="macro",
    ),
]


def fetch_articles(feeds: Iterable[FeedSource], timeout: float = 10.0) -> list[Article]:
    articles: list[Article] = []
    for feed in feeds:
        try:
            xml_text = fetch_feed_xml(feed.url, timeout=timeout)
        except (HTTPError, URLError):
            continue
        articles.extend(parse_rss_items(feed, xml_text))
    return deduplicate_articles(articles)


def fetch_feed_xml(url: str, timeout: float = 10.0) -> str:
    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_rss_items(feed: FeedSource, xml_text: str) -> list[Article]:
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")
    articles: list[Article] = []
    for item in items:
        title = _child_text(item, "title") or "Untitled item"
        url = _child_text(item, "link") or feed.url
        published_at = _parse_published_at(_child_text(item, "pubDate"))
        raw_summary = (
            _child_text(item, "description")
            or _child_text(item, "{http://purl.org/rss/1.0/modules/content/}encoded")
            or ""
        )
        summary = _clean_text(raw_summary)
        market_impact = _infer_market_impact(feed.category, title, summary)
        thesis = _infer_thesis(feed.category, title, summary)
        articles.append(
            Article(
                title=_clean_text(title),
                source=feed.name,
                url=url.strip(),
                published_at=published_at,
                category=feed.category,
                summary=summary,
                market_impact=market_impact,
                thesis=thesis,
            )
        )
    return articles


def deduplicate_articles(articles: list[Article]) -> list[Article]:
    unique_by_url: dict[str, Article] = {}
    for article in sorted(articles, key=lambda item: item.published_at):
        if article.url not in unique_by_url:
            unique_by_url[article.url] = article
    return list(unique_by_url.values())


def _child_text(element: ET.Element, tag_name: str) -> str | None:
    child = element.find(tag_name)
    if child is None or child.text is None:
        return None
    return child.text


def _parse_published_at(raw_value: str | None) -> datetime:
    if not raw_value:
        return datetime.now(LOCAL_TIMEZONE).replace(tzinfo=None)
    try:
        parsed = parsedate_to_datetime(raw_value)
    except ValueError:
        parsed = _parse_datetime_fallback(raw_value)
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)


def _clean_text(raw_text: str) -> str:
    text = unescape(raw_text)
    text = TAG_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _infer_market_impact(category: str, title: str, summary: str) -> str:
    body = f"{title} {summary}".lower()
    if category == "macro":
        if "inflation" in body or "cpi" in body or "pce" in body:
            return "利率预期与股指期货通常会率先反应通胀信号变化。"
        if "fed" in body or "federal reserve" in body or "rate" in body:
            return "美债收益率、美元与成长股估值对政策路径最敏感。"
        return "宏观新闻通常先影响利率、美元，再传导到指数风格。"
    return "市场新闻更适合用来确认盘面方向与行业轮动是否延续。"


def _infer_thesis(category: str, title: str, summary: str) -> str:
    body = f"{title} {summary}".lower()
    if category == "macro":
        if "cool" in body or "slower" in body or "below" in body:
            return "若宏观压力缓和，成长板块与高估值资产更容易获得支撑。"
        if "strong" in body or "hot" in body or "higher" in body:
            return "若数据偏热，需要警惕收益率抬升压制估值扩张。"
        return "这类宏观信号需要结合利率和美元走势确认方向。"
    return "这类市场信号更适合作为仓位微调与风格确认依据。"


def _parse_datetime_fallback(raw_value: str) -> datetime:
    normalized = raw_value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(LOCAL_TIMEZONE).replace(tzinfo=None)
