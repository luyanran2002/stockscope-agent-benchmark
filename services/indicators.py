"""Small, transparent technical-analysis calculations."""

import pandas as pd
from typing import Optional


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    close = data["Close"]
    data["SMA20"] = close.rolling(20, min_periods=1).mean()
    data["SMA50"] = close.rolling(50, min_periods=1).mean()
    data["SMA200"] = close.rolling(200, min_periods=1).mean()
    delta = close.diff()
    gains, losses = delta.clip(lower=0), -delta.clip(upper=0)
    relative_strength = gains.ewm(alpha=1 / 14, adjust=False).mean() / losses.ewm(alpha=1 / 14, adjust=False).mean()
    data["RSI"] = 100 - (100 / (1 + relative_strength))
    data["EMA12"] = close.ewm(span=12, adjust=False).mean()
    data["EMA26"] = close.ewm(span=26, adjust=False).mean()
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["MACDSignal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    true_range = pd.concat([
        data["High"] - data["Low"],
        (data["High"] - close.shift()).abs(),
        (data["Low"] - close.shift()).abs(),
    ], axis=1).max(axis=1)
    data["ATR14"] = true_range.rolling(14, min_periods=1).mean()
    data["VolumeAvg20"] = data["Volume"].rolling(20, min_periods=1).mean()
    data["High20"] = data["High"].rolling(20, min_periods=1).max()
    data["Low20"] = data["Low"].rolling(20, min_periods=1).min()
    return data


def build_signal_summary(data: pd.DataFrame, benchmark: Optional[pd.DataFrame] = None) -> dict:
    latest = data.iloc[-1]
    score = 50
    reasons = []
    if latest.Close > latest.SMA20:
        score += 12; reasons.append("价格位于 20 日均线上方")
    else:
        score -= 12; reasons.append("价格位于 20 日均线下方")
    if latest.SMA20 > latest.SMA50:
        score += 10; reasons.append("短期均线高于中期均线")
    else:
        score -= 10; reasons.append("短期均线低于中期均线")
    if latest.SMA50 > latest.SMA200:
        score += 8; reasons.append("中期趋势仍在长期均线上方")
    else:
        score -= 8; reasons.append("中期趋势弱于长期均线")
    if latest.MACD > latest.MACDSignal:
        score += 10; reasons.append("MACD 动能偏强")
    else:
        score -= 10; reasons.append("MACD 动能偏弱")
    if latest.RSI >= 70:
        score -= 8; rsi_label = "RSI 偏热，留意回撤风险"
    elif latest.RSI <= 30:
        score -= 5; rsi_label = "RSI 偏冷，等待止跌确认"
    else:
        score += 4; rsi_label = "RSI 处于健康区间"
    volume_ratio = latest.Volume / latest.VolumeAvg20 if latest.VolumeAvg20 else 1
    if volume_ratio >= 1.2:
        score += 5; reasons.append("成交量高于 20 日均量，走势获得确认")
    relative_return = None
    if benchmark is not None and not benchmark.empty and len(data) > 21 and len(benchmark) > 21:
        stock_return = data.Close.iloc[-1] / data.Close.iloc[-21] - 1
        benchmark_return = benchmark.Close.iloc[-1] / benchmark.Close.iloc[-21] - 1
        relative_return = stock_return - benchmark_return
        if relative_return > 0:
            score += 5; reasons.append("近 20 日跑赢 S&P 500")
        else:
            score -= 5; reasons.append("近 20 日跑输 S&P 500")
    score = max(0, min(100, int(score)))
    label = "偏向做多" if score >= 68 else "偏向做空" if score <= 34 else "耐心观望"
    risk = "高" if latest.ATR14 / latest.Close >= 0.035 else "中" if latest.ATR14 / latest.Close >= 0.018 else "低"
    return {
        "label": label, "score": score, "reasons": reasons[:4], "rsi_label": rsi_label,
        "volume_ratio": volume_ratio, "risk": risk, "relative_return": relative_return,
        "support": float(data.Low.tail(20).min()), "resistance": float(data.High.tail(20).max()),
        "atr": float(latest.ATR14), "close": float(latest.Close),
    }
