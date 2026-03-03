---
name: report-generation
description: 综合报告生成技能包，整合专家分析和辩论结果生成报告
---

# 综合报告生成技能包

## 脚本清单

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/stock_info.py` | 股票基本信息 | `python scripts/stock_info.py <stock_code>` |
| `scripts/report_generator.py` | 报告生成+持久化 | `python scripts/report_generator.py <stock_code> --battle-file FILE [--output-dir DIR] [--list] [--cleanup DAYS]` |

## 核心函数

- `get_stock_basic_info(code)` — 获取股票名称/行业/市值/PE/PB/ROE/毛利率
- `generate_analysis_report(code, research, battle, start_time)` — 生成完整报告
- `save_report(report)` / `load_report(path)` — 报告持久化
- `calculate_voting_results(battle)` — 投票统计
- `build_expert_summary_prompt()` — 构建专家总结提示词
