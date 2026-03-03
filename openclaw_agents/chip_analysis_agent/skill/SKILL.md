---
name: chip-analysis
description: 筹码分析技能包，提供筹码分布数据和6维度分析
---

# 筹码分析技能包

## 脚本清单

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/chip_data.py` | 筹码分布数据 | `python scripts/chip_data.py <stock_code>` |
| `scripts/chip_analysis.py` | 6维度筹码分析+交易信号 | `python scripts/chip_analysis.py <stock_code>` |

数据源降级：akshare → 历史行情估算 → tushare → 默认值。输出包含基础分析/主力成本/套牢区/集中度/趋势/A股特色6个维度。
