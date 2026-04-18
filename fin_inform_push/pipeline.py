from __future__ import annotations

from datetime import datetime
import re

from fin_inform_push.macro_snapshot import static_macro_metrics
from fin_inform_push.models import Article, BriefingNote, BriefingWindow, MacroMetric, ResearchItem
from fin_inform_push.research_fetch import latest_research_items

MAX_ARTICLES_PER_BRIEFING = 3
MACRO_SIGNAL_KEYWORDS = (
    "fed",
    "federal reserve",
    "rate",
    "rates",
    "inflation",
    "cpi",
    "pce",
    "jobs",
    "labor",
    "employment",
    "payroll",
    "gdp",
    "growth",
    "yield",
    "treasury",
    "dollar",
    "oil",
    "crude",
    "tariff",
    "economy",
    "recession",
)


def select_articles_for_window(
    articles: list[Article], window: BriefingWindow
) -> list[Article]:
    selected = [
        article
        for article in articles
        if window.start_hour <= article.published_at.hour < window.end_hour
    ]
    return sorted(selected, key=lambda article: article.published_at)


def build_briefing_note(
    articles: list[Article],
    window: BriefingWindow,
    date_label: str,
    macro_metrics: list[MacroMetric] | None = None,
    research_items: list[ResearchItem] | None = None,
) -> BriefingNote:
    resolved_macro_metrics = macro_metrics if macro_metrics is not None else static_macro_metrics()
    resolved_research_items = research_items if research_items is not None else latest_research_items(live=False)
    macro_articles = [
        article
        for article in articles
        if article.category == "macro" and _is_macro_signal(article)
    ]
    ordered_articles = select_articles_for_window(macro_articles, window)
    ordered_articles = list(reversed(ordered_articles))[:MAX_ARTICLES_PER_BRIEFING]
    headline = (
        f"{window.title}暂无宏观新信号，先观察美债收益率、美元和股指期货。"
        if not ordered_articles
        else f"{window.title}提炼出 {len(ordered_articles)} 条最重要宏观信号。"
    )
    takeaways = [
        summarize_article_for_briefing(article)
        for article in ordered_articles
    ]
    scenario_analysis = _build_scenarios(ordered_articles, resolved_macro_metrics, resolved_research_items, window)
    investment_summary = _build_investment_summary(
        ordered_articles,
        resolved_macro_metrics,
        resolved_research_items,
    )
    return BriefingNote(
        window=window,
        date_label=date_label,
        headline=headline,
        key_takeaways=takeaways,
        macro_metrics=resolved_macro_metrics,
        research_items=resolved_research_items,
        scenario_analysis=scenario_analysis,
        investment_summary=investment_summary,
        articles=ordered_articles,
    )


def render_markdown(note: BriefingNote) -> str:
    lines = [
        f"# {note.date_label} {note.window.title}",
        "",
        f"> {note.headline}",
        "",
        "## 关键结论",
    ]

    if note.key_takeaways:
        lines.extend(f"- {takeaway}" for takeaway in note.key_takeaways)
    else:
        lines.append("- 当前时间窗内暂无新内容，维持观察。")

    lines.extend(
        [
            "",
            "## 重点宏观数据",
            "",
            "| 指标 | 最新值 | 数据日期 | 当前解读 | 盘前重点 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {metric.name} | {metric.value} | {metric.as_of} | {metric.interpretation} | {metric.focus} |"
        for metric in note.macro_metrics
    )

    lines.extend(["", "## 研报/观点补充"])
    lines.extend(
        f"- {summarize_research_item(item)} | {item.source} | {item.as_of} | [原文链接]({item.url})"
        for item in note.research_items
    )

    lines.extend(["", "## 情景分析"])
    lines.extend(f"- {item}" for item in note.scenario_analysis)

    lines.extend(["", "## 投资总结", "", note.investment_summary])

    lines.extend(["", "## 参考原文"])
    if note.articles:
        for article in note.articles:
            lines.extend(
                [
                    f"- {article.title} | {article.source} | [原文链接]({article.url})"
                ]
            )
    else:
        lines.append("- 暂无可引用原文。")

    return "\n".join(lines).strip() + "\n"


def _build_scenarios(
    articles: list[Article],
    macro_metrics: list[MacroMetric],
    research_items: list[ResearchItem],
    window: BriefingWindow,
) -> list[str]:
    metric_map = {metric.name: metric for metric in macro_metrics}
    inflation = metric_map.get("通胀预期（5Y Breakeven）")
    growth = metric_map.get("增长预期（GDPNow）")
    yields = metric_map.get("美债收益率（2Y / 10Y）")
    dollar = metric_map.get("美元（广义美元指数）")
    oil = metric_map.get("油价（WTI）")
    jobs = metric_map.get("就业数据（最新非农 / 失业率)") or metric_map.get("就业数据（3月非农 / 失业率）")
    english_snippet = _pick_english_snippet(articles, research_items)

    if not articles:
        return [
            f"基准情景：{window.strategy_prompt} 盘前先看 2Y/10Y、美债和美元方向是否共振。",
            "乐观情景：若收益率回落且美元转弱，风险偏好有望改善。",
            "悲观情景：若收益率与美元重新走强，先保持谨慎。",
        ]
    return [
        (
            f"基准情景：当前 5Y 通胀预期在 {inflation.value}，GDPNow 在 {growth.value}，"
            f"2Y/10Y 美债位于 {yields.value}，美元指数 {dollar.value}，油价 {oil.value}，"
            f"就业仍是 {jobs.value}。这说明增长没有失速，但通胀和利率约束仍在，市场更可能维持区间内的风险偏好修复，"
            f"而不是直接交易全面宽松。英文原话可抓住 {english_snippet}。"
        ),
        (
            f"乐观情景：如果后续数据继续偏软，尤其是 breakeven 从 {inflation.value} 回落、2Y 收益率从 {yields.value.split('/')[0].strip()} 下行，"
            f"同时美元不再走强，那么成长和高估值资产会更容易继续修复。"
        ),
        (
            f"悲观情景：如果油价从 {oil.value} 一带继续抬升，或就业与通胀重新走强，市场会再次交易“higher for longer”，"
            f"届时高估值板块和长久期资产压力会重新放大。"
        ),
    ]


def _is_macro_signal(article: Article) -> bool:
    body = f"{article.title} {article.summary} {article.market_impact} {article.thesis}".lower()
    return any(keyword in body for keyword in MACRO_SIGNAL_KEYWORDS)


def _compress_thesis(thesis: str) -> str:
    return thesis.strip().rstrip("。.;；")


def summarize_article_for_briefing(article: Article) -> str:
    segments = [
        _clean_english_clause(article.title),
        _clean_english_clause(article.summary),
    ]
    line = ". ".join(segment for segment in segments if segment).strip()
    if not line:
        line = _clean_english_clause(article.thesis)
    return line.rstrip(".") + "."


def summarize_research_item(item: ResearchItem) -> str:
    title = item.title.lower()
    summary = item.summary.lower()
    if "waller" in title:
        return "沃勒讲话：强调通胀冲击可能反复，政策仍需保持谨慎。"
    if "barr" in title:
        return "巴尔讲话：强调长期投资与融资环境对增长韧性的重要性。"
    if "gdpnow" in title or "gdpnow" in summary:
        return "GDPNow 评论：当前季度增长估计维持温和水平，继续用于校准增长预期。"
    if "money market" in title or "two tools" in title:
        return "纽约联储研究：联储可同时通过利率与资产负债表影响货币市场条件。"
    return _translate_text(f"{item.title}. {item.summary}".strip())


def _pick_english_snippet(articles: list[Article], research_items: list[ResearchItem]) -> str:
    text_candidates = [article.title for article in articles] + [item.title for item in research_items]
    for candidate in text_candidates:
        if "stay on hold" in candidate.lower():
            return '"stay on hold"'
        if "transitory shock" in candidate.lower():
            return '"transitory shock"'
        if "uncertainty" in candidate.lower():
            return '"uncertainty"'
    return '"higher for longer"'


def _build_investment_summary(
    articles: list[Article],
    macro_metrics: list[MacroMetric],
    research_items: list[ResearchItem],
) -> str:
    metric_map = {metric.name: metric for metric in macro_metrics}
    inflation = metric_map.get("通胀预期（5Y Breakeven）")
    growth = metric_map.get("增长预期（GDPNow）")
    yields = metric_map.get("美债收益率（2Y / 10Y）")
    dollar = metric_map.get("美元（广义美元指数）")
    oil = metric_map.get("油价（WTI）")
    jobs = metric_map.get("就业数据（最新非农 / 失业率)") or metric_map.get("就业数据（3月非农 / 失业率）")
    english_snippet = _pick_english_snippet(articles, research_items)

    if not all([inflation, growth, yields, dollar, oil, jobs]):
        return "当前判断：数据还不完整，先不做方向性买点判断，等待利率和美元给出更清晰确认。"

    yield_parts = [part.strip() for part in yields.value.split("/")]
    short_yield = yield_parts[0] if yield_parts else yields.value
    valuation_pressure = "偏高" if any(char.isdigit() for char in short_yield) else "中性"
    oil_risk = "偏高" if "$" in oil.value else "可控"

    return (
        f"当前判断：宏观环境仍然偏紧，不算便宜区。5Y 通胀预期 {inflation.value} 说明市场还没有完全放下 "
        f'"higher for longer"，GDPNow {growth.value} 与就业 {jobs.value} 又说明增长没有明显失速，'
        f"所以这里更像震荡市里的 selective buying，而不是全面抄底。2Y / 10Y 在 {yields.value}、"
        f"美元指数 {dollar.value} 代表估值压制还在，油价 {oil.value} 也让再通胀交易随时可能回头。"
        f"如果你问现在有没有买点，我的简单判断是：可以等回调分批买优质资产，但不适合追高；"
        f"只有当 breakeven 和 2Y 收益率一起回落、美元转弱时，买点才会更扎实。"
        f" 盘面上先按 {valuation_pressure} 利率压力、{oil_risk} 油价风险处理，英文关键词继续盯 {english_snippet}。"
    )


def _translate_text(text: str) -> str:
    lower = text.lower()
    replacements = [
        ("cpi surprise cools rate fears", "通胀走弱缓解了市场对利率继续上行的担忧"),
        ("core inflation came in below consensus", "核心通胀低于市场预期"),
        ("cooling inflation supports a softer-rate narrative for equities", "通胀走弱有利于市场交易更温和的利率路径"),
        ("new york fed president williams worries war will slow growth, aggravate inflation", "纽约联储主席威廉姆斯警告地缘冲突可能拖累增长并推升通胀"),
        ("williams noted that the conflict has intensified the uncertainty around national and local conditions", "他强调当前宏观不确定性正在上升"),
        ("cleveland fed president hammack expects interest rates to stay on hold 'for a good while'", "克利夫兰联储主席哈马克认为利率还需要维持高位更久"),
        ("the central bank official advocated a patient approach as officials watch incoming data for clues about where the u.s. economy is heading", "官员倾向继续观察数据，再决定下一步政策路径"),
        ("trump threatens to fire powell if the fed chair doesn't leave office on his own", "特朗普与鲍威尔相关表态增加了政策沟通层面的噪音"),
        ("though most fed chairs in the past have left after being replaced, powell has demurred on what he plans to do", "这类消息更多影响市场情绪而非短期基本面"),
        ("higher-for-longer remains in play", "更久高利率的风险仍在"),
        ("policy remains restrictive", "政策环境仍然偏紧"),
        ("fed governor signals rates may stay higher", "联储官员释放利率可能维持高位的信号"),
        ("a softer dollar can help risk appetite", "美元走弱通常有利于风险偏好修复"),
        ("falling yields help long-duration sectors", "收益率回落有利于长久期资产表现"),
    ]
    for old, new in replacements:
        lower = lower.replace(old, new)
    lower = re.sub(r"\s+", " ", lower).strip(" .")
    if any("\u4e00" <= ch <= "\u9fff" for ch in lower):
        lower = re.sub(r"[a-zA-Z].*$", "", lower).strip(" .;；")
        return lower[0].upper() + lower[1:] if lower else ""
    return ""


def _clean_english_clause(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" .;；")
    return cleaned


def _unique_in_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
