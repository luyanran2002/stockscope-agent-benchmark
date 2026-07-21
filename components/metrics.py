"""Reusable Streamlit metric and research panels."""

import math
import pandas as pd
import streamlit as st


def _money(value: object) -> str:
    if not isinstance(value, (int, float)) or not math.isfinite(value): return "—"
    for amount, suffix in [(1e12, "T"), (1e9, "B"), (1e6, "M")]:
        if abs(value) >= amount: return f"${value / amount:.2f}{suffix}"
    return f"${value:,.0f}"


def _number(value: object, digits: int = 2) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) and math.isfinite(value) else "—"


def render_market_metrics(data: pd.DataFrame, profile: dict) -> None:
    latest, previous = data.iloc[-1], data.iloc[-2] if len(data) > 1 else data.iloc[-1]
    change = (latest.Close / previous.Close - 1) * 100 if previous.Close else 0
    high_52 = profile.get("fiftyTwoWeekHigh") or data.High.tail(252).max()
    low_52 = profile.get("fiftyTwoWeekLow") or data.Low.tail(252).min()
    average_volume = profile.get("averageVolume") or data.Volume.tail(20).mean()
    columns = st.columns(5)
    columns[0].metric("最新收盘价", f"${latest.Close:,.2f}", f"{change:+.2f}%")
    columns[1].metric("当日成交量", f"{latest.Volume:,.0f}", f"20 日均量 {average_volume:,.0f}")
    columns[2].metric("区间高 / 低", f"${_number(high_52)} / ${_number(low_52)}")
    columns[3].metric("市值", _money(profile.get("marketCap")))
    columns[4].metric("市盈率 (TTM)", _number(profile.get("trailingPE")))


def render_signal_panel(summary: dict) -> None:
    mood = {"偏向做多": "🟢", "耐心观望": "🟡", "偏向做空": "🔴"}[summary["label"]]
    tone = {"偏向做多": "#1d9d68", "耐心观望": "#d58512", "偏向做空": "#df4d5c"}[summary["label"]]
    st.markdown("#### StockScope Signal")
    st.markdown(
        f'''<div style="padding:18px;border:1px solid {tone}33;border-left:4px solid {tone};border-radius:12px;background:#ffffff;">
        <div style="font-size:12px;color:#64748b;letter-spacing:.08em;text-transform:uppercase">趋势置信度</div>
        <div style="font-size:31px;font-weight:750;color:{tone};margin:3px 0">{summary['score']}<span style="font-size:14px"> / 100</span></div>
        <div style="font-size:18px;font-weight:700">{mood} {summary['label']}</div></div>''',
        unsafe_allow_html=True,
    )
    st.caption("均线、动能、量能与相对强弱的规则化结果")
    for reason in summary["reasons"]:
        st.write(f"• {reason}")
    st.write(f"• {summary['rsi_label']}")
    st.caption("这不是买卖指令；请结合财报、仓位和风险承受能力。")


def render_trade_radar(summary: dict) -> None:
    """A compact, actionable analysis card—not a personalised trade recommendation."""
    relative = summary.get("relative_return")
    relative_text = f"{relative:+.1%}" if relative is not None else "—"
    plan = {
        "偏向做多": ("等待回踩支撑后企稳，或放量突破阻力再关注", f"失效参考：跌破 ${summary['support'] - summary['atr']:.2f}"),
        "耐心观望": ("等待价格突破阻力，或回测支撑出现止跌信号", f"观察区间：${summary['support']:.2f} – ${summary['resistance']:.2f}"),
        "偏向做空": ("弱势中避免追多；关注反弹至阻力后的失败确认", f"风险参考：重回 ${summary['resistance']:.2f} 上方"),
    }[summary["label"]]
    st.markdown("#### 决策雷达")
    a, b, c = st.columns(3)
    a.metric("20 日支撑", f"${summary['support']:.2f}")
    b.metric("20 日阻力", f"${summary['resistance']:.2f}")
    c.metric("相对 SPY", relative_text)
    st.markdown("##### 观察计划")
    st.write(plan[0])
    st.caption(plan[1])
    st.markdown(f"**波动风险：** {summary['risk']}　·　**量能：** {summary['volume_ratio']:.1f}× 20 日均量")


def render_company_snapshot(profile: dict) -> None:
    left, right = st.columns([1, 2], gap="large")
    with left:
        st.markdown("#### 基本面")
        for label, key, formatter in [
            ("行业", "sector", str), ("细分领域", "industry", str), ("Beta", "beta", _number),
            ("远期市盈率", "forwardPE", _number), ("市净率", "priceToBook", _number),
            ("股息率", "dividendYield", lambda x: f"{x * 100:.2f}%" if x else "—"),
        ]:
            st.write(f"**{label}**：{formatter(profile.get(key)) if profile.get(key) is not None else '—'}")
        if profile.get("website"):
            st.link_button("访问公司网站", profile["website"])
    with right:
        st.markdown("#### 公司简介")
        st.write(profile.get("longBusinessSummary") or "暂未获得公司简介。")


def render_pe_explainer(profile: dict) -> None:
    pe = profile.get("trailingPE")
    with st.expander("PE（市盈率）怎么看？", expanded=False):
        if pe is not None:
            st.markdown(f"**当前 TTM PE：{_number(pe)} 倍。** 它表示市场愿意为公司过去 12 个月每 1 美元利润支付约 {float(pe):.1f} 美元。")
        else:
            st.markdown("**当前未取得 TTM PE。** 可在 Streamlit Secrets 配置 `ALPHAVANTAGE_API_KEY` 以获取实时估值数据。")
        st.write("PE 较高不等于必然高估：高增长企业的预期利润可能更快增长；PE 较低也不等于便宜，可能反映盈利下滑或周期风险。应与同行、历史区间、利润增长和现金流一起比较。")
