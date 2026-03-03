#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
辩论主持人流程控制器
负责辩论生命周期管理、发言顺序控制、投票统计、结果交接。
"""

import json
import os
from datetime import datetime
from enum import Enum


def validate_tushare_token(token: str) -> dict:
    """
    验证 tushare token 是否有效，并设置到环境变量。

    Args:
        token: 用户提供的 tushare token

    Returns:
        dict: {"valid": bool, "message": str, "points": int}
    """
    if not token or not token.strip():
        return {"valid": False, "message": "token不能为空", "points": 0}

    token = token.strip()
    try:
        import tushare as ts
        ts.set_token(token)
        pro = ts.pro_api()
        # 用一个轻量接口验证 token 有效性
        df = pro.trade_cal(exchange='SSE', start_date='20260101', end_date='20260103')
        if df is not None and not df.empty:
            os.environ["TUSHARE_TOKEN"] = token
            return {"valid": True, "message": "tushare token验证通过", "points": 2000}
        else:
            os.environ["TUSHARE_TOKEN"] = token
            return {"valid": True, "message": "tushare token已设置（无法确认积分）", "points": -1}
    except ImportError:
        return {"valid": False, "message": "未安装tushare库，请先 pip install tushare", "points": 0}
    except Exception as e:
        err_msg = str(e).lower()
        if "token" in err_msg or "auth" in err_msg or "401" in err_msg or "抄送" in err_msg:
            return {"valid": False, "message": f"token无效: {e}", "points": 0}
        # 网络等其他错误，token 可能有效但暂时不可用
        os.environ["TUSHARE_TOKEN"] = token
        return {"valid": True, "message": f"token已设置，但验证时遇到错误: {e}", "points": -1}


class DebatePhase(str, Enum):
    OPENING = "opening"
    DEBATING = "debating"
    VOTING = "voting"
    CONCLUDED = "concluded"


class ModeratorController:
    """辩论主持人控制器"""

    EXPERT_ORDER = [
        ("sentiment_agent", "舆情分析师"),
        ("risk_control_agent", "风控专家"),
        ("hot_money_agent", "游资分析师"),
        ("technical_analysis_agent", "技术分析师"),
        ("chip_analysis_agent", "筹码分析师"),
        ("big_deal_analysis_agent", "大单分析师"),
    ]

    def __init__(self, max_rounds=2):
        self.max_rounds = max_rounds
        self.current_round = 0
        self.phase = DebatePhase.OPENING
        self.stock_code = ""
        self.stock_name = ""

        self.expert_ids = [eid for eid, _ in self.EXPERT_ORDER]
        self.expert_names = {eid: name for eid, name in self.EXPERT_ORDER}

        # 发言记录: [{round, agent_id, speaker, stance, content, timestamp}]
        self.transcript = []
        # 投票记录: {agent_id: {vote, reason, timestamp}}
        self.votes = {}
        # 每轮已发言的专家索引
        self._round_speaker_index = 0

        self.start_time = None
        self.end_time = None

    def start_debate(self, stock_code, stock_name=""):
        """
        开启辩论

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
        """
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.current_round = 1
        self.phase = DebatePhase.DEBATING
        self._round_speaker_index = 0
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "status": "debate_started",
            "stock_code": stock_code,
            "stock_name": stock_name,
            "max_rounds": self.max_rounds,
            "experts": [
                {"id": eid, "name": name} for eid, name in self.EXPERT_ORDER
            ],
        }

    def get_next_speaker(self):
        """
        获取当前轮次的下一位发言者

        Returns:
            dict: {"agent_id": str, "name": str, "order": int} 或 None（轮次已完成）
        """
        if self._round_speaker_index >= len(self.expert_ids):
            return None
        eid = self.expert_ids[self._round_speaker_index]
        return {
            "agent_id": eid,
            "name": self.expert_names[eid],
            "order": self._round_speaker_index + 1,
        }

    def record_speech(self, agent_id, stance, content):
        """
        记录专家发言

        Args:
            agent_id: 专家ID
            stance: 立场 (bullish/bearish/neutral)
            content: 发言内容

        Returns:
            dict: 发言记录
        """
        if agent_id not in self.expert_ids:
            raise ValueError(f"未知专家ID: {agent_id}")

        speech = {
            "round": self.current_round,
            "agent_id": agent_id,
            "speaker": self.expert_names.get(agent_id, agent_id),
            "stance": stance,
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.transcript.append(speech)
        self._round_speaker_index += 1
        return speech

    def record_vote(self, agent_id, vote, reason=""):
        """
        记录投票

        Args:
            agent_id: 专家ID
            vote: 'bullish' 或 'bearish'
            reason: 投票理由
        """
        if vote.lower() not in ("bullish", "bearish"):
            raise ValueError(f"投票必须是 'bullish' 或 'bearish'，收到: {vote}")
        if agent_id not in self.expert_ids:
            raise ValueError(f"未知专家ID: {agent_id}")

        self.votes[agent_id] = {
            "vote": vote.lower(),
            "reason": reason,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def advance_round(self):
        """推进到下一轮"""
        if self.current_round < self.max_rounds:
            self.current_round += 1
            self._round_speaker_index = 0
            return {"status": "next_round", "round": self.current_round}
        else:
            self.phase = DebatePhase.VOTING
            return {"status": "voting_phase", "message": "辩论轮次结束，进入投票阶段"}

    def is_round_complete(self):
        """当前轮次是否所有专家已发言"""
        return self._round_speaker_index >= len(self.expert_ids)

    def is_debate_complete(self):
        """辩论是否已完成所有轮次"""
        return (
            self.current_round >= self.max_rounds
            and self.is_round_complete()
        )

    def get_vote_tally(self):
        """
        获取投票统计

        Returns:
            dict: 票数、百分比、最终判定
        """
        bullish = sum(1 for v in self.votes.values() if v["vote"] == "bullish")
        bearish = sum(1 for v in self.votes.values() if v["vote"] == "bearish")
        total = bullish + bearish
        abstain = len(self.expert_ids) - total

        if total == 0:
            final = "无有效投票"
        elif bullish > bearish:
            final = "bullish"
        elif bearish > bullish:
            final = "bearish"
        else:
            final = "neutral"

        return {
            "bullish": bullish,
            "bearish": bearish,
            "abstain": abstain,
            "total_valid": total,
            "bullish_percentage": round(bullish / total * 100, 1) if total > 0 else 0,
            "bearish_percentage": round(bearish / total * 100, 1) if total > 0 else 0,
            "final_decision": final,
            "votes_detail": {
                aid: {
                    "name": self.expert_names[aid],
                    "vote": v["vote"],
                    "reason": v["reason"],
                }
                for aid, v in self.votes.items()
            },
        }

    def get_round_summary(self, round_num):
        """
        获取指定轮次的发言摘要

        Args:
            round_num: 轮次号（从1开始）
        """
        speeches = [s for s in self.transcript if s["round"] == round_num]
        bullish_count = sum(1 for s in speeches if s["stance"] == "bullish")
        bearish_count = sum(1 for s in speeches if s["stance"] == "bearish")

        return {
            "round": round_num,
            "speeches": speeches,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": len(speeches) - bullish_count - bearish_count,
        }

    def get_full_transcript(self):
        """获取完整辩论记录"""
        rounds = []
        for r in range(1, self.current_round + 1):
            rounds.append(self.get_round_summary(r))
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "total_rounds": self.current_round,
            "rounds": rounds,
        }

    def generate_handoff_package(self):
        """
        生成交接给 report_agent 的完整数据包

        Returns:
            dict: 包含标的信息、辩论记录、投票统计、时间线
        """
        self.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.phase = DebatePhase.CONCLUDED

        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "debate_rounds": self.max_rounds,
            "transcript": self.get_full_transcript(),
            "vote_tally": self.get_vote_tally(),
            "timeline": {
                "start_time": self.start_time,
                "end_time": self.end_time,
            },
            "phase": self.phase.value,
        }



