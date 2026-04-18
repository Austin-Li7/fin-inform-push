from __future__ import annotations

from fin_inform_push.models import MacroMetric


def static_macro_metrics() -> list[MacroMetric]:
    return [
        MacroMetric(
            name="通胀预期（5Y Breakeven）",
            value="2.61%",
            as_of="2026-03-13",
            interpretation="市场仍预期未来 5 年通胀高于 2%，说明“更久高利率”担忧没有完全退去。",
            focus="若继续上行，成长股和长久期资产更容易承压。",
            source="FRED / T5YIE",
        ),
        MacroMetric(
            name="增长预期（GDPNow）",
            value="Q1 实际 GDP 年化 1.3%",
            as_of="2026-04-09",
            interpretation="增长预期偏温和，不是衰退读数，但已经不算强劲。",
            focus="若继续下修，市场风格更容易从进攻转向防守。",
            source="Atlanta Fed GDPNow",
        ),
        MacroMetric(
            name="美债收益率（2Y / 10Y）",
            value="3.84% / 4.31%",
            as_of="2026-03-25 / 2026-04-02",
            interpretation="短端仍处高位，说明政策利率下行空间并未被市场充分计入。",
            focus="盘前优先盯 2Y 和 10Y 是否继续上行来判断估值压力。",
            source="FRED / DGS2, DGS10",
        ),
        MacroMetric(
            name="美元（广义美元指数）",
            value="120.8851",
            as_of="2026-03-27",
            interpretation="美元仍然偏强，通常意味着全球风险偏好和流动性环境不算宽松。",
            focus="若美元继续走强，要提防美股风险偏好回落。",
            source="FRED / DTWEXBGS",
        ),
        MacroMetric(
            name="油价（WTI）",
            value="$93.39/桶",
            as_of="2026-03-16",
            interpretation="油价处在偏高区间，容易反复抬升通胀与地缘风险交易。",
            focus="若再上冲，市场会重新交易输入型通胀和更久高利率。",
            source="EIA via FRED / DCOILWTICO",
        ),
        MacroMetric(
            name="就业数据（3月非农 / 失业率）",
            value="+178k / 4.3%",
            as_of="2026-04-03",
            interpretation="就业仍有增量，但失业率不低，说明劳动力市场在降温而非失速。",
            focus="若后续非农转弱或失业率抬升，降息预期会明显升温。",
            source="BLS Employment Situation",
        ),
    ]
