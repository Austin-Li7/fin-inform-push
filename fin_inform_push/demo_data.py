from __future__ import annotations

from datetime import datetime

from fin_inform_push.models import Article, BriefingWindow


BRIEFING_WINDOWS = [
    BriefingWindow(
        slug="premarket",
        title="开盘前简报",
        start_hour=4,
        end_hour=9,
        strategy_prompt="开盘前关注隔夜宏观数据、利率预期与股指期货方向。",
    ),
    BriefingWindow(
        slug="midday",
        title="午盘简报",
        start_hour=9,
        end_hour=13,
        strategy_prompt="午盘关注资金是否确认早盘方向，以及行业轮动是否扩散。",
    ),
    BriefingWindow(
        slug="postclose",
        title="收盘后简报",
        start_hour=13,
        end_hour=21,
        strategy_prompt="收盘后关注尾盘风险偏好、财报更新与次日交易准备。",
    ),
]


def build_demo_articles() -> list[Article]:
    return [
        Article(
            title="美国核心通胀低于预期，利率担忧缓和",
            source="Macro Wire",
            url="https://example.com/macro/cpi-cools",
            published_at=datetime(2026, 4, 17, 6, 20),
            category="macro",
            summary="最新通胀数据弱于市场预期，交易员下调年内紧缩定价。",
            market_impact="纳指期货上行，美债收益率回落，美元走弱。",
            thesis="成长股估值压力短线缓解，开盘前风险偏好改善。",
        ),
        Article(
            title="纽约联储制造业调查回暖但分项分化",
            source="Rates Desk",
            url="https://example.com/macro/nyfed-survey",
            published_at=datetime(2026, 4, 17, 8, 10),
            category="macro",
            summary="总指数改善，但就业与新订单扩散并不均衡。",
            market_impact="市场对增长回升持谨慎态度，周期股相对受益。",
            thesis="若风险偏好延续，可关注顺周期板块而非盲目追指数。",
        ),
        Article(
            title="午盘前美债拍卖需求平稳，指数震荡上移",
            source="Market Pulse",
            url="https://example.com/markets/auction",
            published_at=datetime(2026, 4, 17, 11, 5),
            category="market",
            summary="债券拍卖结果未引发新的利率冲击，市场延续早盘修复。",
            market_impact="大型科技维持强势，防御板块涨幅落后。",
            thesis="若午后成交继续放大，短线趋势资金可能进一步回流成长。",
        ),
        Article(
            title="收盘后多家策略机构上调二季度盈利预期",
            source="Street Research",
            url="https://example.com/research/q2-earnings",
            published_at=datetime(2026, 4, 17, 16, 40),
            category="research",
            summary="机构普遍认为盈利下修告一段落，但估值扩张空间有限。",
            market_impact="有利于稳住市场中期预期，但不会自动转成全面牛市。",
            thesis="更适合择强布局，而不是忽略估值和利率约束全面加仓。",
        ),
    ]
