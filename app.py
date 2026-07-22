"""StockScope — a practical US equity research dashboard."""

import pandas as pd
import streamlit as st

from components.chart import build_price_chart, build_rsi_chart
from components.metrics import render_company_snapshot, render_market_metrics, render_pe_explainer, render_signal_panel, render_trade_radar
from services.indicators import add_indicators, build_signal_summary
from services.market import fetch_company_profile, fetch_price_history, fetch_us_symbol_directory, fetch_x_sentiment, normalise_ticker


st.set_page_config(page_title="StockScope | 美股分析", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
      .block-container {max-width: 1450px; padding-top: 1.4rem; padding-bottom: 2.5rem;}
      [data-testid="stAppViewContainer"] {background:linear-gradient(145deg,#e9f0f8 0%,#f4f7fb 48%,#e7eef8 100%);}
      [data-testid="stMain"], [data-testid="stMain"] p, [data-testid="stMain"] label,
      [data-testid="stMain"] span, [data-testid="stMain"] h1, [data-testid="stMain"] h2,
      [data-testid="stMain"] h3, [data-testid="stMain"] li {color:#172033 !important;}
      [data-testid="stMetric"] {background:#fff; border:1px solid #dce4ee; border-radius:12px; padding:13px 15px; box-shadow:0 2px 10px #0f172a08;}
      [data-testid="stMetricLabel"] {color:#64748b !important;}
      [data-testid="stMetricValue"] {color:#172033 !important; font-size:1.4rem; letter-spacing:-.03em;}
      [data-testid="stMetricDelta"] {color:#15803d !important;}
      [data-testid="stSidebar"] {background:#101827;}
      .sidebar-brand {
        margin:-1rem -1rem .7rem; padding:2.25rem 1.25rem 2rem; text-align:center;
        background:#101827;
      }
      .sidebar-brand .brand-name {font-size:30px; font-weight:800; letter-spacing:-.055em; color:#fff !important;}
      .sidebar-brand .brand-subtitle {margin-top:9px; font-size:14px; letter-spacing:.08em; color:#b9cae1 !important;}
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
      /* Company quick-access cards: distinctive backgrounds with accessible white text. */
      [data-testid="stSidebar"] [class*="st-key-quick_"] button {
        min-height:3.15rem; border:0 !important; border-radius:10px !important;
        font-weight:700 !important; box-shadow:none !important;
      }
      [data-testid="stSidebar"] [class*="st-key-quick_"] button,
      [data-testid="stSidebar"] [class*="st-key-quick_"] button * {
        color:#ffffff !important; -webkit-text-fill-color:#ffffff !important;
      }
      [data-testid="stSidebar"] .st-key-quick_AAPL button {background:#202a3a !important;}
      [data-testid="stSidebar"] .st-key-quick_MSFT button {background:#0078d4 !important;}
      [data-testid="stSidebar"] .st-key-quick_NVDA button {background:#5d9200 !important;}
      [data-testid="stSidebar"] .st-key-quick_AMZN button {background:#b45309 !important;}
      [data-testid="stSidebar"] .st-key-quick_GOOGL button {background:#2563eb !important;}
      [data-testid="stSidebar"] .st-key-quick_META button {background:#0866ff !important;}
      [data-testid="stSidebar"] .st-key-quick_TSLA button {background:#cc0000 !important;}
      [data-testid="stSidebar"] .st-key-quick_MU button {background:#1269b0 !important;}
      [data-testid="stSidebar"] .st-key-quick_SNDK button {background:#c81e1e !important;}
      [data-testid="stSidebar"] .st-key-quick_WDC button {background:#005195 !important;}
      [data-testid="stSidebar"] .st-key-quick_STX button {background:#6b2a8b !important;}
      .landing {
        min-height:590px; padding:48px; border-radius:24px; overflow:hidden; position:relative;
        background:radial-gradient(circle at 82% 20%, #365a9e 0%, transparent 29%), radial-gradient(circle at 12% 92%, #17465d 0%, transparent 30%), linear-gradient(135deg,#101b35 0%,#162b50 55%,#18284a 100%);
        box-shadow:0 24px 55px rgba(15,30,60,.20); color:#fff;
      }
      .landing, .landing p, .landing span, .landing h1, .landing h2, .landing h3, .landing h4, .landing div {color:#fff !important;}
      .landing-kicker {font-size:12px; letter-spacing:.14em; font-weight:800; color:#9cc2ff !important;}
      .landing-title {max-width:620px; margin:18px 0 14px; font-size:52px; line-height:1.04; letter-spacing:-.06em; font-weight:800;}
      .landing-copy {max-width:590px; color:#c8d5e9 !important; font-size:18px; line-height:1.65;}
      .landing-grid {display:grid; grid-template-columns:1.2fr .8fr; gap:22px; margin-top:40px;}
      .landing-cards {display:grid; grid-template-columns:repeat(3,1fr); gap:12px;}
      .landing-card, .signal-board {background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.16); border-radius:16px; backdrop-filter:blur(8px);}
      .landing-card {padding:18px 16px; min-height:112px;}
      .landing-card .icon {font-size:24px;}
      .landing-card h4 {margin:10px 0 5px; font-size:15px;}
      .landing-card p {margin:0; color:#bfd0e8 !important; font-size:12px; line-height:1.45;}
      .signal-board {padding:20px;}
      .signal-head {display:flex; justify-content:space-between; margin-bottom:18px; font-size:13px; color:#c7d6ee !important;}
      .signal-row {display:flex; align-items:center; gap:10px; margin:12px 0; font-size:13px;}
      .signal-track {height:7px; flex:1; border-radius:999px; background:rgba(255,255,255,.16); overflow:hidden;}
      .signal-fill {height:100%; border-radius:999px; background:linear-gradient(90deg,#66d9a3,#65a8ff);}
      @media (max-width: 850px) {.landing {padding:30px 22px; min-height:auto}.landing-title{font-size:38px}.landing-grid{grid-template-columns:1fr}.landing-cards{grid-template-columns:1fr}}
      h1 {letter-spacing:-.055em; font-weight:760;}
      h2,h3 {letter-spacing:-.025em;}
      .eyebrow {color:#5361e8; font-weight:700; letter-spacing:.11em; font-size:.72rem; text-transform:uppercase;}
    </style>
    """,
    unsafe_allow_html=True,
)

MEG7 = {"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet", "META": "Meta", "TSLA": "Tesla"}
STORAGE = {"MU": "Micron", "SNDK": "SanDisk", "WDC": "Western Digital", "STX": "Seagate"}
PERIODS = {"1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y", "2年": "2y", "5年": "5y"}


def load_data(symbol: str, period: str) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Fetch and calculate in one place so every chart uses the same observations."""
    history = fetch_price_history(symbol, period)
    try:
        benchmark = history if symbol == "SPY" else fetch_price_history("SPY", period)
    except Exception:
        benchmark = pd.DataFrame()
    return add_indicators(history), fetch_company_profile(symbol), add_indicators(benchmark) if not benchmark.empty else benchmark


def _choose_symbol(symbol: str) -> None:
    st.session_state["ticker_search_v2"] = symbol


with st.sidebar:
    st.markdown("<div class='sidebar-brand'><div class='brand-name'>StockScope</div><div class='brand-subtitle'>美股分析助手</div></div>", unsafe_allow_html=True)
    st.divider()
    try:
        directory = fetch_us_symbol_directory()
    except Exception:
        directory = [{"symbol": symbol, "name": name} for symbol, name in {**MEG7, **STORAGE}.items()]
    labels = {item["symbol"]: item.get("name", "") for item in directory}
    ticker_options = sorted(labels)
    ticker_input = st.selectbox(
        "股票代码搜索", ticker_options, key="ticker_search_v2", index=None,
        placeholder="输入代码或公司名搜索全部美股…",
        format_func=lambda ticker: f"{ticker} · {labels.get(ticker, '')}",
        help="点击后可输入代码或公司名筛选。目录优先覆盖美国上市股票，包含 S&P 500 成分股。",
    )
    st.caption("支持代码或公司名检索；例如 MU、SNDK、NVDA、Microsoft。")
    st.markdown("##### 热门快捷入口")
    st.caption("Meg 7")
    meg_columns = st.columns(2)
    for index, (ticker, name) in enumerate(MEG7.items()):
        meg_columns[index % 2].button(f"{ticker} · {name}", key=f"quick_{ticker}", on_click=_choose_symbol, args=(ticker,), use_container_width=True)
    st.caption("存储与半导体")
    storage_columns = st.columns(2)
    for index, (ticker, name) in enumerate(STORAGE.items()):
        storage_columns[index % 2].button(f"{ticker} · {name}", key=f"quick_{ticker}", on_click=_choose_symbol, args=(ticker,), use_container_width=True)
    period_label = st.select_slider("观察区间", options=list(PERIODS), value="1年")
    st.divider()
    st.caption("数据来源：Nasdaq / Yahoo Finance。日线数据可能有延迟，仅供研究。")

symbol = normalise_ticker(ticker_input or "")
period = PERIODS[period_label]

st.markdown("<div class='eyebrow'>US EQUITY RESEARCH TERMINAL</div>", unsafe_allow_html=True)
st.title("StockScope")
st.caption("将价格结构、市场相对强弱与风险控制合在一张研究界面。")

if not symbol:
    st.markdown(
        """
        <section class="landing">
          <div class="landing-kicker">STOCKSCOPE · US EQUITY RESEARCH</div>
          <div class="landing-title">研究一只股票，<br>从一个清晰的信号开始。</div>
          <div class="landing-copy">在左侧搜索任意美国股票代码或公司名。StockScope 会把趋势、动能、相对大盘强弱与风险控制整合为一份可读的研究快照。</div>
          <div class="landing-grid">
            <div class="landing-cards">
              <div class="landing-card"><div class="icon">◌</div><h4>6,755 个美股代码</h4><p>搜索代码或公司名，快速进入研究。</p></div>
              <div class="landing-card"><div class="icon">⌁</div><h4>多因子信号</h4><p>趋势、MACD、RSI 与成交量共同判断。</p></div>
              <div class="landing-card"><div class="icon">◈</div><h4>风险先于观点</h4><p>支撑、阻力、ATR 与相对 SPY 强弱。</p></div>
            </div>
            <div class="signal-board">
              <div class="signal-head"><span>RESEARCH FRAMEWORK</span><span>01 → 04</span></div>
              <div class="signal-row"><span>趋势结构</span><div class="signal-track"><div class="signal-fill" style="width:86%"></div></div></div>
              <div class="signal-row"><span>动能确认</span><div class="signal-track"><div class="signal-fill" style="width:68%"></div></div></div>
              <div class="signal-row"><span>市场相对强弱</span><div class="signal-track"><div class="signal-fill" style="width:74%"></div></div></div>
              <div class="signal-row"><span>风险边界</span><div class="signal-track"><div class="signal-fill" style="width:57%"></div></div></div>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
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
