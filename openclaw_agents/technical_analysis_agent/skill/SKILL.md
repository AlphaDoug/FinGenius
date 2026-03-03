---
name: technical-analysis
description: 技术分析技能包，提供K线数据、实时行情和技术指标计算
---

# 技术分析技能包

## 脚本清单

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/realtime_quotes.py` | 实时行情 | `python scripts/realtime_quotes.py <stock_code>` |
| `scripts/kline_data.py` | K线数据(日线klt=101/分钟klt=1) | `python scripts/kline_data.py <stock_code> [--klt 101] [--count 30]` |
| `scripts/technical_indicators.py` | RSI/MACD/KDJ/布林带 | `python scripts/technical_indicators.py <stock_code>` |

数据源降级：efinance → tushare → akshare。所有脚本返回 JSON。
