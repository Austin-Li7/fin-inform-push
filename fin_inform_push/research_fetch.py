from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from fin_inform_push.models import ResearchItem


DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (fin-inform-push research-fetch)"}
FED_SPEECHES_URL = "https://www.federalreserve.gov/feeds/speeches.xml"
NYFED_RESEARCH_URL = "https://libertystreeteconomics.newyorkfed.org/monetary-policy/feed/"
GDPNOW_COMMENTARY_URL = "https://www.atlantafed.org/cqer/research/gdpnow/archives"


def latest_research_items(live: bool = False, timeout: float = 15.0) -> list[ResearchItem]:
    if not live:
        return static_research_items()
    try:
        return fetch_live_research_items(timeout=timeout)
    except Exception:
        return static_research_items()


def static_research_items() -> list[ResearchItem]:
    return [
        ResearchItem(
            title="Fed speeches：观察官员对通胀和利率路径的最新表态",
            source="Fed Speeches",
            as_of="fallback",
            summary="正式接 live 抓取前的回退项，用来保证简报结构稳定。",
            url="https://www.federalreserve.gov/newsevents/speeches.htm",
        ),
        ResearchItem(
            title="GDPNow Commentary：跟踪增长 nowcast 的最新上修或下修",
            source="GDPNow Commentary",
            as_of="fallback",
            summary="重点看增长预期有没有继续走弱，以及分项拖累来自哪里。",
            url="https://www.atlantafed.org/cqer/research/gdpnow/archives",
        ),
    ]


def fetch_live_research_items(timeout: float = 15.0) -> list[ResearchItem]:
    fed_items = parse_research_rss_items("Fed Speeches", fetch_text(FED_SPEECHES_URL, timeout))[:2]
    nyfed_items = parse_research_rss_items("NY Fed Research", fetch_text(NYFED_RESEARCH_URL, timeout))[:2]
    gdpnow_item = parse_gdpnow_commentary(fetch_text(GDPNOW_COMMENTARY_URL, timeout))
    items = [gdpnow_item, *fed_items, *nyfed_items]
    return items[:4]


def fetch_text(url: str, timeout: float = 15.0) -> str:
    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_research_rss_items(source: str, xml_text: str) -> list[ResearchItem]:
    root = ET.fromstring(xml_text)
    items: list[ResearchItem] = []
    for item in root.findall(".//item"):
        title = _child_text(item, "title") or "Untitled research item"
        link = _child_text(item, "link") or ""
        description = _clean_text(_child_text(item, "description") or "")
        pub_date = _child_text(item, "pubDate") or ""
        as_of = _normalize_pubdate(pub_date)
        items.append(
            ResearchItem(
                title=_clean_text(title),
                source=source,
                as_of=as_of,
                summary=description,
                url=link.strip(),
            )
        )
    return items


def parse_gdpnow_commentary(html: str) -> ResearchItem:
    clean = re.sub(r"<[^>]+>", " ", html)
    clean = " ".join(unescape(clean).split())
    match = re.search(
        r"([A-Za-z]+\s+\d{2},\s+\d{4}).{0,120}?The GDPNow model estimate for real GDP growth .*? is ([0-9.]+\s+percent.*?)\.",
        clean,
    )
    if not match:
        raise ValueError("Could not parse GDPNow commentary")
    date_label = datetime.strptime(match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    summary = f"The GDPNow model estimate {match.group(2)}."
    return ResearchItem(
        title="GDPNow Commentary",
        source="GDPNow Commentary",
        as_of=date_label,
        summary=summary,
        url=GDPNOW_COMMENTARY_URL,
    )


def _child_text(element: ET.Element, tag_name: str) -> str | None:
    child = element.find(tag_name)
    if child is None or child.text is None:
        return None
    return child.text


def _clean_text(raw_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_text)
    text = re.sub(r"\s+", " ", unescape(text))
    return text.strip()


def _normalize_pubdate(raw_value: str) -> str:
    if not raw_value:
        return ""
    parsed = parsedate_to_datetime(raw_value)
    if parsed.tzinfo is None:
        return parsed.strftime("%Y-%m-%d")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")
