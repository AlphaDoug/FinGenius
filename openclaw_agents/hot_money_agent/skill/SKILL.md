---
name: hot-money-analysis
description: 游资分析技能包，提供实时行情、龙虎榜、个股资金流向、板块行情、指数资金流向
---

# 游资分析技能包

## 脚本清单

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/realtime_quotes.py` | 实时行情 | `python scripts/realtime_quotes.py <stock_code>` |
| `scripts/daily_billboard.py` | 龙虎榜数据 | `python scripts/daily_billboard.py [stock_code]` |
| `scripts/stock_capital.py` | 个股资金流向 | `python scripts/stock_capital.py [stock_code]` |
| `scripts/get_section_data.py` | 板块行情(hot/concept/industry/regional/all) | `python scripts/get_section_data.py [type]` |
| `scripts/index_capital.py` | 指数资金流向 | `python scripts/index_capital.py [index_code]` |

所有脚本返回 JSON，金额单位：亿元。数据源降级：efinance/东方财富 → tushare。
