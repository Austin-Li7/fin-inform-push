from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from urllib.request import Request, urlopen

from fin_inform_push.macro_snapshot import static_macro_metrics
from fin_inform_push.models import MacroMetric


FRED_SERIES_URLS = {
    "t5yie": "https://fred.stlouisfed.org/data/T5YIE",
    "dgs2": "https://fred.stlouisfed.org/data/DGS2",
    "dgs10": "https://fred.stlouisfed.org/data/DGS10",
    "dtwexbgs": "https://fred.stlouisfed.org/data/DTWEXBGS",
    "dcoilwtico": "https://fred.stlouisfed.org/data/DCOILWTICO",
}
GDPNOW_URL = "https://www.atlantafed.org/cqer/research/gdpnow"
BLS_EMPLOYMENT_URL = "https://www.bls.gov/news.release/empsit.nr0.htm"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (fin-inform-push macro-fetch)"}


def latest_macro_metrics(live: bool = False, timeout: float = 15.0) -> list[MacroMetric]:
    if not live:
        return static_macro_metrics()
    try:
        return fetch_live_macro_metrics(timeout=timeout)
    except Exception:
        return static_macro_metrics()


def fetch_live_macro_metrics(timeout: float = 15.0) -> list[MacroMetric]:
    t5yie_date, t5yie_value = parse_fred_series_latest(fetch_text(FRED_SERIES_URLS["t5yie"], timeout))
    dgs2_date, dgs2_value = parse_fred_series_latest(fetch_text(FRED_SERIES_URLS["dgs2"], timeout))
    dgs10_date, dgs10_value = parse_fred_series_latest(fetch_text(FRED_SERIES_URLS["dgs10"], timeout))
    dollar_date, dollar_value = parse_fred_series_latest(fetch_text(FRED_SERIES_URLS["dtwexbgs"], timeout))
    oil_date, oil_value = parse_fred_series_latest(fetch_text(FRED_SERIES_URLS["dcoilwtico"], timeout))
    gdp_date, gdp_value = parse_gdpnow_latest(fetch_text(GDPNOW_URL, timeout))
    jobs_date, jobs_value = parse_bls_employment_metrics(fetch_text(BLS_EMPLOYMENT_URL, timeout))

    return [
        MacroMetric(
            name="通胀预期（5Y Breakeven）",
            value=f"{t5yie_value}%",
            as_of=t5yie_date,
            interpretation="市场对未来 5 年平均通胀的定价，能直接反映“更久高利率”担忧是否升温。",
            focus="若继续上行，成长股和长久期资产更容易承压。",
            source="FRED / T5YIE",
        ),
        MacroMetric(
            name="增长预期（GDPNow）",
            value=f"Q1 实际 GDP 年化 {gdp_value}",
            as_of=gdp_date,
            interpretation="Atlanta Fed 对当前季度增长的实时 nowcast，适合跟踪增长动能是上修还是下修。",
            focus="若继续下修，市场风格更容易从进攻转向防守。",
            source="Atlanta Fed GDPNow",
        ),
        MacroMetric(
            name="美债收益率（2Y / 10Y）",
            value=f"{dgs2_value}% / {dgs10_value}%",
            as_of=f"{dgs2_date} / {dgs10_date}",
            interpretation="2Y 更贴政策路径，10Y 更贴增长和通胀溢价，两者一起看最有用。",
            focus="盘前优先盯 2Y 和 10Y 是否继续上行来判断估值压力。",
            source="FRED / DGS2, DGS10",
        ),
        MacroMetric(
            name="美元（广义美元指数）",
            value=dollar_value,
            as_of=dollar_date,
            interpretation="美元偏强通常意味着全球风险偏好和金融条件还不算宽松。",
            focus="若美元继续走强，要提防美股风险偏好回落。",
            source="FRED / DTWEXBGS",
        ),
        MacroMetric(
            name="油价（WTI）",
            value=f"${oil_value}/桶",
            as_of=oil_date,
            interpretation="油价会直接影响通胀预期和地缘风险交易，是最近最敏感的外生变量之一。",
            focus="若再上冲，市场会重新交易输入型通胀和更久高利率。",
            source="EIA via FRED / DCOILWTICO",
        ),
        MacroMetric(
            name="就业数据（最新非农 / 失业率）",
            value=jobs_value,
            as_of=jobs_date,
            interpretation="非农和失业率一起看，能判断劳动力市场是在降温、企稳，还是重新走强。",
            focus="若后续非农转弱或失业率抬升，降息预期会明显升温。",
            source="BLS Employment Situation",
        ),
    ]


def fetch_text(url: str, timeout: float = 15.0) -> str:
    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_fred_series_latest(text: str) -> tuple[str, str]:
    matches = re.findall(r"(\d{4}-\d{2}-\d{2})\s+([0-9.]+)", text)
    if not matches:
        raise ValueError("No FRED observations found")
    return matches[-1]


def parse_gdpnow_latest(html: str) -> tuple[str, str]:
    clean = " ".join(unescape(html).split())
    match = re.search(r"Latest estimate:\s*([0-9.]+)\s*percent\s*[—-]\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", clean)
    if not match:
        match = re.search(
            r"is\s+([0-9.]+)\s*percent\s+on\s+([A-Za-z]+\s+\d{1,2})",
            clean,
        )
        if not match:
            raise ValueError("No GDPNow estimate found")
        value = f"{match.group(1)}%"
        return datetime.now().strftime("%Y-%m-%d"), value
    value = f"{match.group(1)}%"
    date_label = datetime.strptime(match.group(2), "%B %d, %Y").strftime("%Y-%m-%d")
    return date_label, value


def parse_bls_employment_metrics(html: str) -> tuple[str, str]:
    clean = " ".join(unescape(html).split())
    month_match = re.search(r"THE EMPLOYMENT SITUATION -- ([A-Za-z]+)\s+(\d{4})", clean)
    payroll_match = re.search(r"Total nonfarm payroll employment (?:increased|rose|changed little|edged down|decreased) by ([0-9,]+)", clean)
    unemployment_match = re.search(r"unemployment rate .*? at ([0-9.]+)\s+percent", clean)
    if not (month_match and payroll_match and unemployment_match):
        raise ValueError("Employment release parsing failed")
    month_num = datetime.strptime(month_match.group(1), "%B").month
    as_of = f"{month_match.group(2)}-{month_num:02d}"
    payroll_value = f"+{int(payroll_match.group(1).replace(',', '')) // 1000}k"
    unemployment_value = f"{unemployment_match.group(1)}%"
    return as_of, f"{payroll_value} / {unemployment_value}"
