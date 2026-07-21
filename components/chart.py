"""Plotly chart builders."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_price_chart(data: pd.DataFrame, symbol: str) -> go.Figure:
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.76, 0.24])
    figure.add_trace(go.Candlestick(x=data.index, open=data.Open, high=data.High, low=data.Low, close=data.Close, name="K线"), row=1, col=1)
    for column, color, name in [("SMA20", "#f59e0b", "20日均线"), ("SMA50", "#2563eb", "50日均线"), ("SMA200", "#7c3aed", "200日均线")]:
        figure.add_trace(go.Scatter(x=data.index, y=data[column], name=name, line={"width": 1.5, "color": color}), row=1, col=1)
    colors = ["#16a34a" if c >= o else "#dc2626" for c, o in zip(data.Close, data.Open)]
    figure.add_trace(go.Bar(x=data.index, y=data.Volume, name="成交量", marker_color=colors, opacity=0.65), row=2, col=1)
    figure.update_layout(height=570, margin={"l": 8, "r": 8, "t": 35, "b": 0}, title=f"{symbol} 价格走势", xaxis_rangeslider_visible=False, legend={"orientation": "h", "y": 1.04}, hovermode="x unified", plot_bgcolor="white", paper_bgcolor="white", font={"color": "#334155"})
    figure.update_yaxes(gridcolor="#edf0f2", tickprefix="$", row=1)
    figure.update_yaxes(gridcolor="#edf0f2", tickformat="~s", row=2)
    return figure


def build_rsi_chart(data: pd.DataFrame, symbol: str) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=data.index, y=data.RSI, name="RSI (14)", line={"color": "#7c3aed", "width": 2}))
    figure.add_hrect(y0=70, y1=100, fillcolor="#ef4444", opacity=0.10, line_width=0)
    figure.add_hrect(y0=0, y1=30, fillcolor="#22c55e", opacity=0.10, line_width=0)
    figure.add_hline(y=70, line_dash="dot", line_color="#ef4444")
    figure.add_hline(y=30, line_dash="dot", line_color="#22c55e")
    figure.update_layout(title=f"{symbol} 相对强弱指标", height=310, margin={"l": 8, "r": 8, "t": 38, "b": 0}, yaxis={"range": [0, 100], "gridcolor": "#edf0f2"}, xaxis={"showgrid": False}, plot_bgcolor="white", paper_bgcolor="white", showlegend=False, font={"color": "#334155"})
    return figure
