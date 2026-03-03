---
name: big-deal-analysis
description: 大单异动分析技能包，提供市场大单数据和个股资金排行
---

# 大单异动分析技能包

## 脚本清单

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/big_deal_data.py` | 大单资金流向分析 | `python scripts/big_deal_data.py [--code <code>] [--top_n 10] [--rank_symbol 即时]` |

排行窗口：`即时`/`3日排行`/`5日排行`/`10日排行`/`20日排行`。数据源：akshare → tushare保底。
