# StockScope

一个可用于研究美股走势的 Streamlit 仪表盘。输入股票代码后，应用会从公开市场数据源获取日线行情，并显示价格、成交量、基本面和技术指标。

## 已实现功能

- 支持任意 Yahoo Finance 美股代码（例如 `AAPL`、`NVDA`、`SPY`），并提供常用标的快捷选择
- 1 个月至 5 年历史行情、K 线、成交量和 20/50/200 日均线
- RSI 与 MACD 技术指标，以及透明的规则化趋势摘要
- 趋势置信度、偏向做多／观望／做空的辅助信号、20 日支撑阻力、波动风险与相对 SPY 强弱
- 可筛选的 S&P 500 全部成分股目录、PE 解释卡片，以及可选的 X 官方 API 近期讨论面板
- 最新收盘价、日涨跌、52 周区间、市值、估值、行业和公司简介
- 行情缓存：价格数据每 5 分钟刷新，公司概览每小时刷新

## 本地运行

需要 Python 3.10 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开终端显示的本地地址即可使用。日线优先使用 Nasdaq 的公开接口，以避免云端部署环境遭遇 Yahoo Finance 共享 IP 限流；Yahoo Finance 用作回退行情源及公司资料来源。公开数据有时会延迟或临时不可用；本项目展示的是研究工具，不构成任何投资建议。

## 可选数据密钥

复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml` 后填入密钥（不要提交这个文件）：

- `ALPHAVANTAGE_API_KEY`：补充 TTM PE、远期 PE、PB、Beta 等估值基本面。
- `X_BEARER_TOKEN`：通过 X 官方 API 展示股票最近公开讨论。X 的 API 权限与套餐由账户决定；应用不会无授权抓取 X 内容。
