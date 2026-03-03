---
name: battle-debate
description: 辩论博弈技能包，提供多轮结构化辩论流程控制、发言/投票管理、上下文累积传递功能
---

# 辩论博弈技能包

## 脚本

| 脚本 | 功能 |
|------|------|
| `scripts/battle_controller.py` | 辩论流程控制器 |

## BattleController API

```python
controller = BattleController(max_rounds=2)

# 发言+投票
battle_speak_and_vote(controller, "sentiment_agent", "我认为...", "bullish")

# 构建上下文（含研究报告摘要+本轮前序发言）
context = build_debate_context(controller, "sentiment_agent", research_reports)

# 下一轮
controller.next_round()

# 获取结果
summary = controller.get_debate_summary()
```

## 核心方法

- `handle_speak(agent_id, content)` — 记录发言
- `handle_vote(agent_id, vote)` — 记录投票(bullish/bearish)
- `get_context_for_agent(agent_id)` — 获取本轮上下文
- `get_voting_results()` — 投票统计
- `get_debate_summary()` — 完整辩论摘要
