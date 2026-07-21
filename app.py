"""StockScope — a practical US equity research dashboard."""

import pandas as pd
import streamlit as st

from components.chart import build_price_chart, build_rsi_chart
from components.metrics import render_company_snapshot, render_market_metrics, render_pe_explainer, render_signal_panel, render_trade_radar
from services.indicators import add_indicators, build_signal_summary
from services.market import fetch_company_profile, fetch_price_history, fetch_sp500_constituents, fetch_x_sentiment, normalise_ticker


st.set_page_config(page_title="StockScope | 美股分析", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
      .block-container {max-width: 1450px; padding-top: 1.4rem; padding-bottom: 2.5rem;}
      [data-testid="stAppViewContainer"] {background:linear-gradient(145deg,#f8fafc 0%,#ffffff 45%,#f2f7ff 100%);}
      [data-testid="stMain"], [data-testid="stMain"] p, [data-testid="stMain"] label,
      [data-testid="stMain"] span, [data-testid="stMain"] h1, [data-testid="stMain"] h2,
      [data-testid="stMain"] h3, [data-testid="stMain"] li {color:#172033 !important;}
      [data-testid="stMetric"] {background:#fff; border:1px solid #dce4ee; border-radius:12px; padding:13px 15px; box-shadow:0 2px 10px #0f172a08;}
      [data-testid="stMetricLabel"] {color:#64748b !important;}
      [data-testid="stMetricValue"] {color:#172033 !important; font-size:1.4rem; letter-spacing:-.03em;}
      [data-testid="stMetricDelta"] {color:#15803d !important;}
      [data-testid="stSidebar"] {background:#101827;}
      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span,
      [data-testid="stSidebar"] div {color:#e5e7eb;}
      /* Inputs are intentionally light surfaces inside the dark sidebar. */
      [data-testid="stSidebar"] input {
        background:#ffffff !important; color:#172033 !important;
        -webkit-text-fill-color:#172033 !important; border-color:#cbd5e1 !important;
      }
      [data-testid="stSidebar"] input::placeholder {
        color:#64748b !important; -webkit-text-fill-color:#64748b !important; opacity:1;
      }
      [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background:#ffffff !important; border-color:#cbd5e1 !important;
      }
      [data-testid="stSidebar"] [data-baseweb="select"] div,
      [data-testid="stSidebar"] [data-baseweb="select"] span,
      [data-testid="stSidebar"] [data-baseweb="select"] svg {
        color:#172033 !important; fill:#172033 !important;
      }
      h1 {letter-spacing:-.055em; font-weight:760;}
      h2,h3 {letter-spacing:-.025em;}
      .eyebrow {color:#5361e8; font-weight:700; letter-spacing:.11em; font-size:.72rem; text-transform:uppercase;}
    </style>
    """,
    unsafe_allow_html=True,
)

WATCHLIST = {
    "Apple": "AAPL", "NVIDIA": "NVDA", "Microsoft": "MSFT", "Amazon": "AMZN",
    "Tesla": "TSLA", "Meta": "META", "Alphabet": "GOOGL", "S&P 500 ETF": "SPY",
}
PERIODS = {"1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y", "2年": "2y", "5年": "5y"}


def load_data(symbol: str, period: str) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Fetch and calculate in one place so every chart uses the same observations."""
    history = fetch_price_history(symbol, period)
    try:
        benchmark = history if symbol == "SPY" else fetch_price_history("SPY", period)
    except Exception:
        benchmark = pd.DataFrame()
    return add_indicators(history), fetch_company_profile(symbol), add_indicators(benchmark) if not benchmark.empty else benchmark


with st.sidebar:
    st.title("StockScope")
    st.caption("美股行情与技术分析")
    st.divider()
    selected_name = st.selectbox("热门标的", ["自定义代码", *WATCHLIST])
    default_symbol = WATCHLIST.get(selected_name, "AAPL")
    use_sp500 = st.checkbox("浏览 S&P 500 全部成分股")
    universe_symbol = None
    if use_sp500:
        try:
            constituents = fetch_sp500_constituents()
            matches = st.text_input("筛选 S&P 500", placeholder="代码、公司名或行业").lower()
            filtered = [row for row in constituents if not matches or matches in f"{row['symbol']} {row['name']} {row['sector']}".lower()]
            options = {f"{row['symbol']} · {row['name']}": row["symbol"] for row in filtered}
            if options:
                universe_symbol = st.selectbox("S&P 500 成分股", list(options))
                universe_symbol = options[universe_symbol]
            else:
                st.caption("没有匹配的成分股。")
        except Exception:
            st.caption("成分股目录暂不可用，仍可直接输入股票代码。")
    ticker_input = st.text_input("股票代码", value=universe_symbol or default_symbol, placeholder="例如 AAPL、BRK-B")
    period_label = st.select_slider("观察区间", options=list(PERIODS), value="1年")
    st.divider()
    st.caption("数据来源：Nasdaq / Yahoo Finance。日线数据可能有延迟，仅供研究。")

symbol = normalise_ticker(ticker_input)
period = PERIODS[period_label]

st.markdown("<div class='eyebrow'>US EQUITY RESEARCH TERMINAL</div>", unsafe_allow_html=True)
st.title("StockScope")
st.caption("将价格结构、市场相对强弱与风险控制合在一张研究界面。")

if not symbol:
    st.info("在左侧输入美股代码开始分析，例如 `AAPL`、`NVDA` 或 `SPY`。")
    st.stop()

try:
    with st.spinner(f"正在获取 {symbol} 的市场数据…"):
        prices, profile, benchmark = load_data(symbol, period)
except Exception as exc:
    st.error(f"暂时无法获取 {symbol} 的行情：{exc}")
    st.info("请确认代码正确，并稍后重试。美股代码示例：AAPL、MSFT、NVDA、SPY。")
    st.stop()

if prices.empty:
    st.warning(f"没有找到 {symbol} 的可用历史行情。请检查股票代码或切换时间区间。")
    st.stop()

company_name = profile.get("longName") or profile.get("shortName") or symbol
exchange = profile.get("exchange") or "US Market"
last_updated = prices.index[-1].strftime("%Y-%m-%d")
st.subheader(f"{company_name} · {symbol}")
st.caption(f"{exchange} · 最近交易日 {last_updated} · 行情源：{prices.attrs.get('source', '公开数据源')}")

render_market_metrics(prices, profile)
render_pe_explainer(profile)
summary = build_signal_summary(prices, benchmark)

left, right = st.columns([3, 1], gap="large")
with left:
    st.plotly_chart(build_price_chart(prices, symbol), use_container_width=True, config={"displaylogo": False})
with right:
    render_signal_panel(summary)

radar_tab, indicator_tab, company_tab, sentiment_tab, data_tab = st.tabs(["决策雷达", "技术指标", "公司概览", "X 舆情", "历史数据"])
with radar_tab:
    render_trade_radar(summary)
    st.caption("支撑/阻力取近 20 个交易日的低点/高点；失效参考以 ATR（平均真实波幅）估算，适用于制定观察条件而非自动下单。")
with indicator_tab:
    st.plotly_chart(build_rsi_chart(prices, symbol), use_container_width=True, config={"displaylogo": False})
    st.caption("RSI（14）：高于 70 通常表示偏热，低于 30 通常表示偏冷；指标应结合趋势和基本面使用。")
with company_tab:
    render_company_snapshot(profile)
with sentiment_tab:
    posts = fetch_x_sentiment(symbol)
    st.markdown("#### X 最近讨论")
    if posts is None:
        st.info("配置 `X_BEARER_TOKEN` 后，可通过 X 官方 API 显示最近公开讨论；不会抓取未经授权的内容。")
    elif not posts:
        st.caption("当前没有可展示的近期公开帖子，或 X API 暂不可用。")
    else:
        for post in posts:
            st.markdown(f"**{post.get('created_at', '')} · {post.get('lang', '').upper()}**")
            st.write(post.get("text", ""))
            st.divider()
with data_tab:
    display_columns = [c for c in ["Open", "High", "Low", "Close", "Volume", "SMA20", "SMA50", "RSI"] if c in prices]
    table = prices[display_columns].tail(90).sort_index(ascending=False).copy()
    st.dataframe(table.style.format({c: "{:.2f}" for c in table.columns if c != "Volume"}).format({"Volume": "{:,.0f}"}), use_container_width=True, height=420)

st.divider()
st.caption("免责声明：StockScope 提供的是公开市场数据和规则化技术指标，并非个性化投资建议。投资有风险，决策前请自行核实信息。")
