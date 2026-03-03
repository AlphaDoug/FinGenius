---
name: risk-control-analysis
description: 风控分析技能包，提供公司公告和三大财务报表数据
---

# 风控分析技能包

## 脚本清单

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/risk_control_data.py` | 公告+财务报表 | `python scripts/risk_control_data.py --code <code> [--max_count 10] [--period 按年度] [--financial_only]` |

数据源：公告(东方财富API)、财务报表(akshare → tushare保底)。周期可选：按年度/按报告期/按单季度。
