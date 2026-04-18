from __future__ import annotations

import unittest
from datetime import datetime
from urllib.error import HTTPError
from urllib.request import Request
import ssl

from fin_inform_push.models import Article, BriefingWindow


PREMARKET = BriefingWindow(
    slug="premarket",
    title="开盘前简报",
    start_hour=4,
    end_hour=9,
    strategy_prompt="开盘前关注宏观驱动与期货方向。",
)


class PipelineTests(unittest.TestCase):
    def test_resolve_date_label_defaults_to_today(self) -> None:
        from fin_inform_push.cli import resolve_date_label

        resolved = resolve_date_label(None, now_fn=lambda: datetime(2026, 4, 17, 18, 30))

        self.assertEqual("2026-04-17", resolved)

    def test_resolve_date_label_keeps_explicit_value(self) -> None:
        from fin_inform_push.cli import resolve_date_label

        resolved = resolve_date_label("2026-04-18", now_fn=lambda: datetime(2026, 4, 17, 18, 30))

        self.assertEqual("2026-04-18", resolved)

    def test_publish_markdown_to_obsidian_builds_expected_request(self) -> None:
        from fin_inform_push.obsidian import ObsidianConfig, publish_markdown_to_obsidian

        captured: dict[str, object] = {}

        def fake_urlopen(request: Request, context=None):
            captured["full_url"] = request.full_url
            captured["method"] = request.get_method()
            captured["authorization"] = request.get_header("Authorization")
            captured["content_type"] = request.get_header("Content-type")
            captured["payload"] = request.data.decode("utf-8")
            captured["context"] = context

            class _Response:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            return _Response()

        config = ObsidianConfig(
            base_url="https://127.0.0.1:27124",
            api_key="secret-token",
            folder="Macro Briefings",
        )

        remote_path = publish_markdown_to_obsidian(
            "2026-04-17",
            "premarket",
            "# Test Note\n",
            config,
            urlopen_fn=fake_urlopen,
        )

        self.assertEqual("Macro Briefings/2026-04-17/premarket.md", remote_path)
        self.assertEqual(
            "https://127.0.0.1:27124/vault/Macro%20Briefings/2026-04-17/premarket.md",
            captured["full_url"],
        )
        self.assertEqual("PUT", captured["method"])
        self.assertEqual("Bearer secret-token", captured["authorization"])
        self.assertEqual("text/markdown; charset=utf-8", captured["content_type"])
        self.assertEqual("# Test Note\n", captured["payload"])
        self.assertIsInstance(captured["context"], ssl.SSLContext)

    def test_publish_markdown_to_obsidian_strips_api_key_whitespace(self) -> None:
        from fin_inform_push.obsidian import ObsidianConfig, publish_markdown_to_obsidian

        captured: dict[str, object] = {}

        def fake_urlopen(request: Request, context=None):
            captured["authorization"] = request.get_header("Authorization")

            class _Response:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            return _Response()

        config = ObsidianConfig(
            base_url="https://127.0.0.1:27124",
            api_key="secret-token\n",
            folder="Macro Briefings",
        )

        publish_markdown_to_obsidian(
            "2026-04-17",
            "premarket",
            "# Test Note\n",
            config,
            urlopen_fn=fake_urlopen,
        )

        self.assertEqual("Bearer secret-token", captured["authorization"])

    def test_publish_markdown_to_obsidian_raises_clear_error_on_http_failure(self) -> None:
        from fin_inform_push.obsidian import ObsidianConfig, ObsidianPublishError, publish_markdown_to_obsidian

        def failing_urlopen(request: Request, context=None):
            raise HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=None)

        config = ObsidianConfig(
            base_url="https://127.0.0.1:27124",
            api_key="secret-token",
            folder="Macro Briefings",
        )

        with self.assertRaises(ObsidianPublishError) as context:
            publish_markdown_to_obsidian(
                "2026-04-17",
                "premarket",
                "# Test Note\n",
                config,
                urlopen_fn=failing_urlopen,
            )

        self.assertIn("403", str(context.exception))

    def test_select_articles_for_window_filters_and_orders(self) -> None:
        from fin_inform_push.pipeline import select_articles_for_window

        articles = [
            Article(
                title="Later",
                source="Source B",
                url="https://example.com/later",
                published_at=datetime(2026, 4, 17, 8, 30),
                category="macro",
                summary="Later summary",
                market_impact="Treasury yields moved higher.",
                thesis="Higher yields pressure duration-sensitive growth.",
            ),
            Article(
                title="Too Early",
                source="Source C",
                url="https://example.com/early",
                published_at=datetime(2026, 4, 17, 3, 45),
                category="macro",
                summary="Early summary",
                market_impact="No market impact.",
                thesis="Ignore this item.",
            ),
            Article(
                title="Earlier",
                source="Source A",
                url="https://example.com/earlier",
                published_at=datetime(2026, 4, 17, 4, 5),
                category="macro",
                summary="Earlier summary",
                market_impact="Dollar softened after data.",
                thesis="A softer dollar can help risk appetite.",
            ),
        ]

        selected = select_articles_for_window(articles, PREMARKET)

        self.assertEqual(["Earlier", "Later"], [article.title for article in selected])

    def test_render_briefing_markdown_includes_links_and_strategy(self) -> None:
        from fin_inform_push.pipeline import build_briefing_note, render_markdown
        from fin_inform_push.models import ResearchItem

        article = Article(
            title="CPI surprise cools rate fears",
            source="Macro Wire",
            url="https://example.com/cpi",
            published_at=datetime(2026, 4, 17, 7, 0),
            category="macro",
            summary="Core inflation came in below consensus.",
            market_impact="Index futures strengthened and yields dipped.",
            thesis="Cooling inflation supports a softer-rate narrative for equities.",
        )
        research_item = ResearchItem(
            title="Waller, One Transitory Shock After Another",
            source="Fed Speeches",
            as_of="2026-04-17",
            summary="Speech At the David Kaserman Memorial Lecture, Department of Economics, Auburn University, Auburn, Alabama",
            url="https://example.com/waller",
        )

        note = build_briefing_note([article], PREMARKET, "2026-04-17", research_items=[research_item])
        markdown = render_markdown(note)

        self.assertIn("# 2026-04-17 开盘前简报", markdown)
        self.assertIn("## 关键结论", markdown)
        self.assertIn("## 重点宏观数据", markdown)
        self.assertIn("## 研报/观点补充", markdown)
        self.assertIn("## 情景分析", markdown)
        self.assertIn("## 投资总结", markdown)
        self.assertIn("## 参考原文", markdown)
        self.assertIn("[原文链接](https://example.com/cpi)", markdown)
        self.assertIn("CPI surprise cools rate fears", markdown)
        self.assertNotIn("## 原始信号", markdown)
        self.assertNotIn("## 重点宏观信号", markdown)
        self.assertIn("| 指标 | 最新值 | 数据日期 | 当前解读 | 盘前重点 |", markdown)
        self.assertIn("通胀预期（5Y Breakeven）", markdown)
        self.assertIn("就业数据（3月非农 / 失业率）", markdown)
        self.assertIn("沃勒讲话", markdown)
        self.assertIn("强调通胀冲击", markdown)
        self.assertIn("2.61%", markdown)
        self.assertTrue(
            any(snippet in markdown for snippet in ['"stay on hold"', '"transitory shock"', '"uncertainty"', '"higher for longer"'])
        )
        self.assertIn("当前判断", markdown)

    def test_build_briefing_note_keeps_only_macro_articles_and_top_three(self) -> None:
        from fin_inform_push.pipeline import build_briefing_note

        articles = [
            Article(
                title=f"Fed rates outlook {idx}",
                source="Macro Wire",
                url=f"https://example.com/macro-{idx}",
                published_at=datetime(2026, 4, 17, 7, idx),
                category="macro",
                summary="Inflation and rates remain the core focus.",
                market_impact="Treasury yields reacted modestly.",
                thesis="Fed path remains central for equities.",
            )
            for idx in range(4)
        ]
        articles.append(
            Article(
                title="Market Noise",
                source="Market Wire",
                url="https://example.com/market-noise",
                published_at=datetime(2026, 4, 17, 7, 30),
                category="market",
                summary="Market summary",
                market_impact="Market impact",
                thesis="Market thesis",
            )
        )

        note = build_briefing_note(articles, PREMARKET, "2026-04-17")

        self.assertEqual(3, len(note.articles))
        self.assertTrue(all(article.category == "macro" for article in note.articles))
        self.assertEqual(
            ["Fed rates outlook 3", "Fed rates outlook 2", "Fed rates outlook 1"],
            [article.title for article in note.articles],
        )

    def test_build_briefing_note_filters_out_macro_noise(self) -> None:
        from fin_inform_push.pipeline import build_briefing_note

        articles = [
            Article(
                title="Fed Governor signals rates may stay higher",
                source="Macro Wire",
                url="https://example.com/fed-rates",
                published_at=datetime(2026, 4, 17, 7, 0),
                category="macro",
                summary="Policy remains restrictive.",
                market_impact="Treasury yields ticked up.",
                thesis="Higher-for-longer remains in play.",
            ),
            Article(
                title="CEOs are betting AI will augment work rather than displace all workers",
                source="Macro Wire",
                url="https://example.com/ai-work",
                published_at=datetime(2026, 4, 17, 7, 30),
                category="macro",
                summary="Conference chatter on adoption trends.",
                market_impact="Little immediate macro read-through.",
                thesis="This should be filtered as noise.",
            ),
        ]

        note = build_briefing_note(articles, PREMARKET, "2026-04-17")

        self.assertEqual(["Fed Governor signals rates may stay higher"], [article.title for article in note.articles])

    def test_build_briefing_note_includes_macro_metrics(self) -> None:
        from fin_inform_push.pipeline import build_briefing_note

        article = Article(
            title="Fed governor warns inflation may stay sticky as oil climbs",
            source="Macro Wire",
            url="https://example.com/fed-oil",
            published_at=datetime(2026, 4, 17, 7, 15),
            category="macro",
            summary="Officials said yields and dollar reaction matter for the open.",
            market_impact="Treasury yields, dollar and crude oil all moved higher.",
            thesis="Higher-for-longer risk rises if inflation and oil stay firm.",
        )

        note = build_briefing_note([article], PREMARKET, "2026-04-17")

        self.assertEqual(6, len(note.macro_metrics))

    def test_build_briefing_note_includes_research_items(self) -> None:
        from fin_inform_push.pipeline import build_briefing_note

        article = Article(
            title="Fed governor warns inflation may stay sticky as oil climbs",
            source="Macro Wire",
            url="https://example.com/fed-oil",
            published_at=datetime(2026, 4, 17, 7, 15),
            category="macro",
            summary="Officials said yields and dollar reaction matter for the open.",
            market_impact="Treasury yields, dollar and crude oil all moved higher.",
            thesis="Higher-for-longer risk rises if inflation and oil stay firm.",
        )

        note = build_briefing_note([article], PREMARKET, "2026-04-17")

        self.assertGreaterEqual(len(note.research_items), 1)
        self.assertTrue(any("Fed" in item.title or "GDPNow" in item.title for item in note.research_items))

    def test_summarize_article_into_english_sentence(self) -> None:
        from fin_inform_push.pipeline import summarize_article_for_briefing

        article = Article(
            title="CPI surprise cools rate fears",
            source="Macro Wire",
            url="https://example.com/cpi",
            published_at=datetime(2026, 4, 17, 7, 0),
            category="macro",
            summary="Core inflation came in below consensus.",
            market_impact="Index futures strengthened and yields dipped.",
            thesis="Cooling inflation supports a softer-rate narrative for equities.",
        )

        line = summarize_article_for_briefing(article)

        self.assertIn("CPI surprise cools rate fears", line)
        self.assertIn("Core inflation came in below consensus", line)

    def test_summarize_research_item_into_chinese_sentence(self) -> None:
        from fin_inform_push.pipeline import summarize_research_item
        from fin_inform_push.models import ResearchItem

        item = ResearchItem(
            title="Waller, One Transitory Shock After Another",
            source="Fed Speeches",
            as_of="2026-04-17",
            summary="Speech At the David Kaserman Memorial Lecture, Department of Economics, Auburn University, Auburn, Alabama",
            url="https://example.com/waller",
        )

        line = summarize_research_item(item)

        self.assertIn("沃勒讲话", line)
        self.assertNotIn("Waller, One Transitory Shock After Another", line)

    def test_build_investment_summary_uses_actual_metric_values(self) -> None:
        from fin_inform_push.macro_snapshot import static_macro_metrics
        from fin_inform_push.pipeline import build_briefing_note
        from fin_inform_push.models import ResearchItem

        article = Article(
            title="Cleveland Fed President Hammack expects interest rates to stay on hold 'for a good while'",
            source="Macro Wire",
            url="https://example.com/hammack",
            published_at=datetime(2026, 4, 17, 7, 10),
            category="macro",
            summary="The central bank official advocated a patient approach as officials watch incoming data.",
            market_impact="Treasury yields held firm and the dollar stayed supported.",
            thesis="Higher-for-longer remains in play.",
        )
        research_item = ResearchItem(
            title="GDPNow Commentary",
            source="GDPNow Commentary",
            as_of="2026-04-09",
            summary="The GDPNow model estimate 1.3 percent on April 9, unchanged from April 7 after rounding.",
            url="https://example.com/gdpnow",
        )

        note = build_briefing_note(
            [article],
            PREMARKET,
            "2026-04-17",
            macro_metrics=static_macro_metrics(),
            research_items=[research_item],
        )

        self.assertIn("2.61%", note.investment_summary)
        self.assertIn("3.84% / 4.31%", note.investment_summary)
        self.assertIn("当前判断", note.investment_summary)
        self.assertTrue(any(word in note.investment_summary for word in ["买点", "追高", "回调"]))

    def test_build_scenarios_uses_actual_metric_values(self) -> None:
        from fin_inform_push.macro_snapshot import static_macro_metrics
        from fin_inform_push.pipeline import build_briefing_note
        from fin_inform_push.models import ResearchItem

        article = Article(
            title="Cleveland Fed President Hammack expects interest rates to stay on hold 'for a good while'",
            source="Macro Wire",
            url="https://example.com/hammack",
            published_at=datetime(2026, 4, 17, 7, 10),
            category="macro",
            summary="The central bank official advocated a patient approach as officials watch incoming data.",
            market_impact="Treasury yields held firm and the dollar stayed supported.",
            thesis="Higher-for-longer remains in play.",
        )
        research_item = ResearchItem(
            title="GDPNow Commentary",
            source="GDPNow Commentary",
            as_of="2026-04-09",
            summary="The GDPNow model estimate 1.3 percent on April 9, unchanged from April 7 after rounding.",
            url="https://example.com/gdpnow",
        )

        note = build_briefing_note(
            [article],
            PREMARKET,
            "2026-04-17",
            macro_metrics=static_macro_metrics(),
            research_items=[research_item],
        )

        self.assertIn("2.61%", note.scenario_analysis[0])
        self.assertIn("3.84% / 4.31%", note.scenario_analysis[0])
        self.assertIn("1.3%", note.scenario_analysis[0])
        self.assertIn("4.3%", note.scenario_analysis[0])
        self.assertIn("stay on hold", note.scenario_analysis[0])

    def test_parse_rss_items_extracts_articles(self) -> None:
        from fin_inform_push.sources import FeedSource, parse_rss_items

        feed = FeedSource(
            name="Federal Reserve",
            url="https://example.com/fed.xml",
            category="macro",
        )
        xml_text = """
        <rss version="2.0">
          <channel>
            <title>Federal Reserve News</title>
            <item>
              <title>Fed official says policy can stay patient</title>
              <link>https://example.com/fed/patient</link>
              <pubDate>Fri, 17 Apr 2026 12:30:00 GMT</pubDate>
              <description><![CDATA[Officials signaled limited urgency to tighten.]]></description>
            </item>
          </channel>
        </rss>
        """

        articles = parse_rss_items(feed, xml_text)

        self.assertEqual(1, len(articles))
        self.assertEqual("Fed official says policy can stay patient", articles[0].title)
        self.assertEqual("Federal Reserve", articles[0].source)
        self.assertEqual("macro", articles[0].category)
        self.assertIn("Officials signaled limited urgency", articles[0].summary)

    def test_deduplicate_articles_removes_repeated_links(self) -> None:
        from fin_inform_push.sources import deduplicate_articles

        first = Article(
            title="Treasury yields slip after data",
            source="Macro One",
            url="https://example.com/yields",
            published_at=datetime(2026, 4, 17, 7, 0),
            category="macro",
            summary="The 10-year yield moved lower after CPI.",
            market_impact="Growth stocks caught a bid.",
            thesis="Falling yields help long-duration sectors.",
        )
        duplicate = Article(
            title="Treasury yields slip after data update",
            source="Macro Two",
            url="https://example.com/yields",
            published_at=datetime(2026, 4, 17, 7, 5),
            category="macro",
            summary="Same link with a slightly different title.",
            market_impact="No extra impact.",
            thesis="Duplicate item should be filtered.",
        )

        deduped = deduplicate_articles([first, duplicate])

        self.assertEqual([first], deduped)

    def test_parse_rss_items_converts_gmt_into_local_briefing_time(self) -> None:
        from fin_inform_push.sources import FeedSource, parse_rss_items

        feed = FeedSource(
            name="MarketWatch Top Stories",
            url="https://example.com/mw.xml",
            category="market",
        )
        xml_text = """
        <rss version="2.0">
          <channel>
            <item>
              <title>Futures rise after soft inflation print</title>
              <link>https://example.com/futures</link>
              <pubDate>Fri, 17 Apr 2026 14:30:00 GMT</pubDate>
              <description>Stocks gained before the open.</description>
            </item>
          </channel>
        </rss>
        """

        articles = parse_rss_items(feed, xml_text)

        self.assertEqual(1, len(articles))
        self.assertEqual(7, articles[0].published_at.hour)

    def test_parse_rss_items_accepts_iso_like_pubdate(self) -> None:
        from fin_inform_push.sources import FeedSource, parse_rss_items

        feed = FeedSource(
            name="Investing.com Markets",
            url="https://example.com/investing.xml",
            category="market",
        )
        xml_text = """
        <rss version="2.0">
          <channel>
            <item>
              <title>Stocks drift higher into the close</title>
              <link>https://example.com/close</link>
              <pubDate>2026-04-17 20:36:56</pubDate>
              <description>Risk appetite stayed firm into late trading.</description>
            </item>
          </channel>
        </rss>
        """

        articles = parse_rss_items(feed, xml_text)

        self.assertEqual(1, len(articles))
        self.assertEqual("Stocks drift higher into the close", articles[0].title)

    def test_parse_fred_series_latest_extracts_latest_value(self) -> None:
        from fin_inform_push.macro_fetch import parse_fred_series_latest

        text = """
DATE  VALUE
2026-03-19  2.61
2026-03-20  2.59
2026-03-23  2.63
"""

        latest = parse_fred_series_latest(text)

        self.assertEqual(("2026-03-23", "2.63"), latest)

    def test_parse_gdpnow_page_extracts_estimate(self) -> None:
        from fin_inform_push.macro_fetch import parse_gdpnow_latest

        html = """
        <html><body>
        Latest estimate: 1.3 percent — April 9, 2026
        The GDPNow model estimate for real GDP growth (seasonally adjusted annual rate)
        in the first quarter of 2026 is 1.3 percent on April 9.
        </body></html>
        """

        latest = parse_gdpnow_latest(html)

        self.assertEqual(("2026-04-09", "1.3%"), latest)

    def test_parse_bls_employment_release_extracts_payrolls_and_unemployment(self) -> None:
        from fin_inform_push.macro_fetch import parse_bls_employment_metrics

        html = """
        THE EMPLOYMENT SITUATION -- March 2026
        Total nonfarm payroll employment increased by 178,000 in March, and the unemployment rate
        changed little at 4.3 percent, the U.S. Bureau of Labor Statistics reported today.
        """

        latest = parse_bls_employment_metrics(html)

        self.assertEqual(("2026-03", "+178k / 4.3%"), latest)

    def test_parse_gdpnow_commentary_extracts_latest_note(self) -> None:
        from fin_inform_push.research_fetch import parse_gdpnow_commentary

        html = """
        <html><body>
        <h2>April 09, 2026</h2>
        <p>The GDPNow model estimate for real GDP growth (seasonally adjusted annual rate) in the first quarter of 2026 is 1.3 percent on April 9, unchanged from April 7 after rounding.</p>
        </body></html>
        """

        item = parse_gdpnow_commentary(html)

        self.assertEqual("GDPNow Commentary", item.source)
        self.assertIn("1.3 percent", item.summary)
        self.assertEqual("2026-04-09", item.as_of)

    def test_parse_research_rss_extracts_items(self) -> None:
        from fin_inform_push.research_fetch import parse_research_rss_items

        xml_text = """
        <rss version="2.0">
          <channel>
            <item>
              <title>Waller, One Transitory Shock After Another</title>
              <link>https://example.com/fed/waller</link>
              <pubDate>Thu, 16 Apr 2026 14:00:00 GMT</pubDate>
              <description><![CDATA[Remarks on inflation shocks and policy patience.]]></description>
            </item>
          </channel>
        </rss>
        """

        items = parse_research_rss_items("Fed Speeches", xml_text)

        self.assertEqual(1, len(items))
        self.assertEqual("Fed Speeches", items[0].source)
        self.assertEqual("Waller, One Transitory Shock After Another", items[0].title)


if __name__ == "__main__":
    unittest.main()
