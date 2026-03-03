---
name: sentiment-analysis
description: 舆情分析技能包，提供板块数据、指数资金流向、多引擎网络搜索
---

# 舆情分析技能包

## 脚本清单

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/get_section_data.py` | 板块行情(hot/concept/industry/regional/all) | `python scripts/get_section_data.py [type]` |
| `scripts/index_capital.py` | 指数资金流向 | `python scripts/index_capital.py [index_code]` |
| `scripts/web_search.py` | 多引擎搜索+正文抓取 | `python scripts/web_search.py "关键词" [--fetch_content] [--num_results 5]` |

搜索引擎降级：Google → Baidu → DuckDuckGo → Bing。所有脚本返回 JSON。
