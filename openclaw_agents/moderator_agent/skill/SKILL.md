---
name: debate-moderator
description: 辩论主持人技能包，提供辩论生命周期管理、发言顺序控制、投票统计、结果交接、tushare token验证
---

# 辩论主持人技能包

## 脚本

| 脚本 | 功能 |
|------|------|
| `scripts/moderator_controller.py` | 主持人流程控制器 + token验证 |

## API

### validate_tushare_token(token) — 验证并激活 tushare

```python
from moderator_controller import validate_tushare_token

result = validate_tushare_token("用户输入的token")
# -> {"valid": True/False, "message": "...", "points": 2000}
```

验证通过后自动设置环境变量 `TUSHARE_TOKEN`，所有 agent skill 脚本会自动使用。

### ModeratorController

```python
mc = ModeratorController(max_rounds=2)

# 开场
mc.start_debate("600519", "贵州茅台")

# 辩论循环
while not mc.is_debate_complete():
    while not mc.is_round_complete():
        speaker = mc.get_next_speaker()  # -> {agent_id, name, order} 或 None
        mc.record_speech(speaker["agent_id"], "bullish", "发言内容")
    mc.advance_round()  # -> {status: "next_round"} 或 {status: "voting_phase"}

# 投票
for agent_id in mc.expert_ids:
    mc.record_vote(agent_id, "bullish", "理由")

# 结果
tally = mc.get_vote_tally()      # 票数/百分比/最终判定
package = mc.generate_handoff_package()  # 交接数据包
```

## 交接数据包结构

`generate_handoff_package()` 返回：
- `stock_code` / `stock_name` — 标的
- `transcript` — 完整发言记录
- `vote_tally` — 投票统计
- `timeline` — 时间线
