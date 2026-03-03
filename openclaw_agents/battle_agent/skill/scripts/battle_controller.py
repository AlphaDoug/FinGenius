#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
辩论博弈流程控制器
提供多轮结构化辩论流程管理、发言/投票、上下文累积传递功能。
对应原工程: src/tool/battle.py
"""

import json
from datetime import datetime


class BattleController:
    """辩论流程控制器"""

    def __init__(self, expert_ids=None, max_rounds=2):
        """
        Args:
            expert_ids: 参与辩论的专家ID列表
            max_rounds: 辩论轮次
        """
        self.expert_ids = expert_ids or [
            "sentiment_agent",           # 舆情分析师
            "risk_control_agent",        # 风控专家
            "hot_money_agent",           # 游资分析师
            "technical_analysis_agent",  # 技术分析师
            "chip_analysis_agent",       # 筹码分析师
            "big_deal_analysis_agent",   # 大单分析师
        ]
        self.max_rounds = max_rounds
        self.debate_history = []   # [{round, agent_id, speaker, content, timestamp}, ...]
        self.votes = {}            # {agent_id: "bullish"|"bearish"}
        self.current_round = 0

    def handle_speak(self, agent_id, content):
        """
        记录一条发言

        Args:
            agent_id: 专家ID
            content: 发言内容

        Returns:
            dict: 发言记录
        """
        speech = {
            "round": self.current_round + 1,
            "agent_id": agent_id,
            "speaker": self._get_speaker_name(agent_id),
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.debate_history.append(speech)
        return speech

    def handle_vote(self, agent_id, vote):
        """
        记录投票（动态投票，最后一次为准）

        Args:
            agent_id: 专家ID
            vote: 'bullish' 或 'bearish'
        """
        if vote.lower() not in ("bullish", "bearish"):
            raise ValueError(f"投票必须是 'bullish' 或 'bearish'，收到: {vote}")
        self.votes[agent_id] = vote.lower()

    def get_context_for_agent(self, agent_id):
        """
        获取当前轮次中该专家发言前的所有上下文

        Args:
            agent_id: 当前发言的专家ID

        Returns:
            list[dict]: 该专家发言前的所有发言记录
        """
        return [
            s for s in self.debate_history
            if s["round"] == self.current_round + 1
        ]

    def next_round(self):
        """进入下一轮"""
        self.current_round += 1

    def get_voting_results(self):
        """
        获取投票结果汇总

        Returns:
            dict: {
                votes: {agent_id: vote},
                vote_count: {bullish: N, bearish: N},
                final_decision: 'bullish'|'bearish',
                total_votes: N,
                bullish_percentage: float,
                bearish_percentage: float
            }
        """
        bullish = sum(1 for v in self.votes.values() if v == "bullish")
        bearish = sum(1 for v in self.votes.values() if v == "bearish")
        total = bullish + bearish

        return {
            "votes": self.votes,
            "vote_count": {"bullish": bullish, "bearish": bearish},
            "final_decision": "bullish" if bullish >= bearish else "bearish",
            "total_votes": total,
            "bullish_percentage": round(bullish / total * 100, 1) if total > 0 else 0,
            "bearish_percentage": round(bearish / total * 100, 1) if total > 0 else 0,
        }

    def get_debate_summary(self):
        """
        获取辩论完整摘要

        Returns:
            dict: 包含辩论历史、投票结果、轮次信息
        """
        return {
            "debate_rounds": self.max_rounds,
            "debate_history": self.debate_history,
            **self.get_voting_results(),
        }

    @staticmethod
    def _get_speaker_name(agent_id):
        name_map = {
            "sentiment_agent": "舆情分析师",
            "risk_control_agent": "风控专家",
            "hot_money_agent": "游资分析师",
            "technical_analysis_agent": "技术分析师",
            "chip_analysis_agent": "筹码分析师",
            "big_deal_analysis_agent": "大单分析师",
        }
        return name_map.get(agent_id, agent_id)


def battle_speak_and_vote(controller, agent_id, speak, vote):
    """
    专家发言并投票

    Args:
        controller: BattleController 实例
        agent_id: 专家ID，如 'sentiment_agent'
        speak: 发言内容（应引用具体数据和论据）
        vote: 投票 'bullish'(看涨) 或 'bearish'(看跌)

    Returns:
        str: 格式化的发言记录
    """
    if vote.lower() not in ("bullish", "bearish"):
        return f"错误：投票必须是 'bullish' 或 'bearish'"

    controller.handle_speak(agent_id, speak)
    controller.handle_vote(agent_id, vote)

    return f"{agent_id}[{vote}]: {speak}"


def build_debate_context(controller, current_agent_id, research_reports):
    """
    为当前发言专家构建完整上下文

    Args:
        controller: BattleController 实例
        current_agent_id: 当前发言的专家ID
        research_reports: dict，各专家的研究报告 {agent_id: report_text}

    Returns:
        str: 格式化的上下文文本，包含研究报告和前序发言
    """
    context_parts = []

    # 加入研究报告摘要
    context_parts.append("=== 研究阶段报告摘要 ===")
    for aid, report in research_reports.items():
        name = BattleController._get_speaker_name(aid)
        # 截取前500字作为摘要
        summary = str(report)[:500]
        context_parts.append(f"\n【{name}】{summary}")

    # 加入本轮前序发言
    prior_speeches = controller.get_context_for_agent(current_agent_id)
    if prior_speeches:
        context_parts.append("\n=== 本轮已有发言 ===")
        for s in prior_speeches:
            context_parts.append(f"\n【{s['speaker']}】{s['content']}")

    return "\n".join(context_parts)



