#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合报告生成器
整合专家总结、股票详情、投票结果生成完整的JSON分析报告并持久化存储。
对应原工程: src/utils/analysis_report_generator.py + src/tool/expert_summary.py
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime

# 导入同目录的股票信息模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_info import get_stock_basic_info


# ============================================================
# 专家类型映射（与原工程 src/tool/expert_summary.py 保持一致）
# ============================================================
EXPERT_TYPE_MAPPING = {
    "sentiment_agent": {"name": "市场情感分析师", "type": "sentiment"},
    "risk_control_agent": {"name": "风险控制专家", "type": "risk"},
    "hot_money_agent": {"name": "游资分析师", "type": "hot_money"},
    "technical_analysis_agent": {"name": "技术分析师", "type": "technical"},
    "chip_analysis_agent": {"name": "筹码分析师", "type": "chip_analysis"},
    "big_deal_analysis_agent": {"name": "大单分析师", "type": "big_deal"},
}


# ============================================================
# 专家观点总结相关
# ============================================================
def group_speeches_by_expert(debate_history):
    """
    按专家分组辩论发言

    Args:
        debate_history: [{agent_id, speaker, content, round, timestamp}, ...]

    Returns:
        dict: {agent_id: [speeches]}
    """
    groups = {}
    for speech in debate_history:
        agent_id = speech.get("agent_id") or speech.get("speaker")
        if agent_id:
            groups.setdefault(agent_id, []).append(speech)
    return groups


def format_expert_speeches(speeches):
    """格式化专家发言内容"""
    if not speeches:
        return "该专家在辩论中未发言"

    formatted = []
    for i, speech in enumerate(speeches, 1):
        content = speech.get("content", "")
        round_num = speech.get("round", "")
        timestamp = speech.get("timestamp", "")

        line = f"第{i}次发言"
        if round_num:
            line += f"（第{round_num}轮）"
        if timestamp:
            line += f" [{timestamp}]"
        line += f"：\n{content}\n"
        formatted.append(line)

    return "\n".join(formatted)


def build_expert_summary_prompt(expert_name, expert_type, stock_code, speeches, research_result):
    """
    构建专家总结的LLM提示词

    Args:
        expert_name: 专家名称
        expert_type: 专家类型
        stock_code: 股票代码
        speeches: 该专家的发言列表
        research_result: 该专家的研究报告

    Returns:
        str: 提示词文本（交给LLM生成总结）
    """
    speeches_text = format_expert_speeches(speeches)

    return f"""请为以下金融分析专家生成结构化总结：

专家：{expert_name}（{expert_type}）
分析标的：{stock_code}

【研究报告摘要】
{str(research_result)[:2000]}

【辩论发言记录】
{speeches_text}

请输出以下结构（JSON格式）：
1. analysis_conclusion: 分析结论（100-200字概述核心观点）
2. one_sentence_summary: 一句话总结（20-30字精炼结论）
3. key_arguments: 关键论点（3-5个要点，数组）
4. key_tags: 关键标签（3-5个标签词，数组）
5. data_sources: 数据来源列表（数组）"""


def create_fallback_summary(expert_name, expert_type, speeches, research_result):
    """
    创建降级总结（当AI总结不可用时使用）

    Args:
        expert_name: 专家名称
        expert_type: 专家类型
        speeches: 发言列表
        research_result: 研究报告

    Returns:
        dict: 专家总结结构
    """
    conclusion = str(research_result)[:200] + "..." if len(str(research_result)) > 200 else str(research_result)

    type_tags = {
        "sentiment": ["市场情感", "投资者情绪"],
        "risk": ["风险控制", "风险评估"],
        "hot_money": ["游资分析", "资金流向"],
        "technical": ["技术分析", "图表分析"],
        "chip_analysis": ["筹码分析", "持仓结构"],
        "big_deal": ["大单分析", "主力资金"],
    }

    return {
        "expert_name": expert_name,
        "expert_type": expert_type,
        "analysis_conclusion": conclusion,
        "one_sentence_summary": f"{expert_name}基于{expert_type}进行了深度分析",
        "key_arguments": ["基于历史数据分析", "结合市场环境判断", "考虑技术指标因素"],
        "key_tags": type_tags.get(expert_type.split("_")[0], ["专业分析"]),
        "data_sources": ["市场数据", "技术指标", "历史走势"],
    }


# ============================================================
# 投票结果统计
# ============================================================
def calculate_voting_results(battle_results):
    """
    计算投票结果

    Args:
        battle_results: 辩论控制器的 get_debate_summary() 返回值

    Returns:
        dict: {
            final_decision, bullish_count, bearish_count,
            bullish_percentage, bearish_percentage, total_votes
        }
    """
    vote_count = battle_results.get("vote_count", {})
    bullish = vote_count.get("bullish", 0)
    bearish = vote_count.get("bearish", 0)
    total = bullish + bearish

    return {
        "final_decision": battle_results.get("final_decision", "unknown"),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "bullish_percentage": round(bullish / total * 100, 1) if total > 0 else 0,
        "bearish_percentage": round(bearish / total * 100, 1) if total > 0 else 0,
        "total_votes": total,
    }


# ============================================================
# 辩论共识与分歧分析
# ============================================================
def build_consensus_analysis_prompt(debate_highlights):
    """
    构建共识/分歧分析的LLM提示词

    Args:
        debate_highlights: 辩论要点列表

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    debate_text = "\n\n".join([
        f"【发言{i + 1}】\n{point}" for i, point in enumerate(debate_highlights[:5])
    ])

    system_prompt = "你是一位专业的金融分析总结专家，负责从多位专家的辩论中提炼共识和分歧观点。请以JSON格式返回结果。"

    user_prompt = f"""请分析以下专家辩论内容，提炼出共识观点和分歧观点：

{debate_text}

请提取：
1. consensus_points: 所有或大多数专家都同意的观点（3-5条）
2. divergent_points: 专家之间存在明显分歧的观点（3-5条）

每条观点用简洁的一句话概括（20-40字）。

请返回JSON格式：
{{"consensus_points": ["..."], "divergent_points": ["..."]}}"""

    return system_prompt, user_prompt


# ============================================================
# 辩论记录结构化
# ============================================================
def build_rounds_detail(debate_history):
    """
    将 debate_history 按轮次结构化为轮次列表

    Args:
        debate_history: 辩论历史记录列表

    Returns:
        list[dict]: 按轮次组织的结构化辩论记录
    """
    if not debate_history:
        return []

    rounds_map = {}
    for entry in debate_history:
        round_num = entry.get("round", 1)
        rounds_map.setdefault(round_num, []).append(entry)

    rounds_detail = []
    for round_num in sorted(rounds_map.keys()):
        speeches = [
            {
                "speaker": s.get("speaker", "未知"),
                "agent_id": s.get("agent_id", ""),
                "content": s.get("content", ""),
                "timestamp": s.get("timestamp", ""),
            }
            for s in rounds_map[round_num]
        ]
        rounds_detail.append({
            "round_number": round_num,
            "speeches": speeches,
        })

    return rounds_detail


# ============================================================
# 综合报告生成
# ============================================================
def generate_analysis_report(stock_code, research_results, battle_results, start_time, expert_summaries=None):
    """
    生成完整的分析报告数据结构

    Args:
        stock_code: 股票代码
        research_results: {expert_type: analysis_data} 各专家研究结果
        battle_results: 辩论控制器的完整摘要
        start_time: 分析开始时间戳
        expert_summaries: 可选，AI生成的专家总结

    Returns:
        dict: 完整的报告JSON结构
    """
    stock_info = get_stock_basic_info(stock_code)
    voting = calculate_voting_results(battle_results)

    # 按轮次组织辩论记录
    debate_history = battle_results.get("debate_history", [])
    rounds_detail = build_rounds_detail(debate_history)

    # 如果没有提供专家总结，使用降级方案自动生成
    if expert_summaries is None:
        expert_summaries = {}
        expert_speeches = group_speeches_by_expert(debate_history)
        for agent_id, expert_info in EXPERT_TYPE_MAPPING.items():
            expert_name = expert_info["name"]
            expert_type = expert_info["type"]
            research_result = research_results.get(expert_type, "") or research_results.get(agent_id, "")
            if research_result:
                speeches = expert_speeches.get(agent_id, [])
                expert_summaries[expert_type] = create_fallback_summary(
                    expert_name, expert_type, speeches, research_result
                )

    # 提取辩论要点
    battle_highlights = battle_results.get("battle_highlights", [])
    key_points = []
    for highlight in battle_highlights[:5]:
        if isinstance(highlight, dict):
            point = highlight.get("point", "")
            if point:
                key_points.append(point)

    report = {
        "stock_info": stock_info,
        "expert_summaries": expert_summaries,
        "voting_results": voting,
        "debate_summary": {
            "total_rounds": battle_results.get("debate_rounds", 0),
            "total_speeches": len(debate_history),
            "rounds_detail": rounds_detail,
            "key_debate_points": key_points,
        },
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "analysis_duration": round(datetime.now().timestamp() - start_time, 2),
    }

    return report


# ============================================================
# 报告持久化存储
# ============================================================
def save_report(report, base_dir="analysis_reports"):
    """
    保存分析报告到文件

    Args:
        report: 报告字典
        base_dir: 报告存储根目录

    Returns:
        str: 报告保存路径
    """
    stock_code = report.get("stock_info", {}).get("stock_code", "unknown")
    timestamp = report.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))

    folder = os.path.join(base_dir, f"{stock_code}_{timestamp}")
    os.makedirs(folder, exist_ok=True)

    report_path = os.path.join(folder, "analysis_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 保存元数据
    metadata = {
        "stock_code": stock_code,
        "timestamp": timestamp,
        "report_file": "analysis_report.json",
        "created_at": datetime.now().isoformat(),
    }
    with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return report_path


def load_report(report_path):
    """加载已保存的报告"""
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_reports(base_dir="analysis_reports", stock_code=None):
    """
    列出所有已保存的报告

    Args:
        base_dir: 报告存储根目录
        stock_code: 可选，按股票代码筛选

    Returns:
        list[dict]: 报告元数据列表
    """
    if not os.path.exists(base_dir):
        return []

    reports = []
    for folder in sorted(os.listdir(base_dir), reverse=True):
        meta_path = os.path.join(base_dir, folder, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if stock_code is None or meta.get("stock_code") == stock_code:
                reports.append(meta)
    return reports


def cleanup_old_reports(base_dir="analysis_reports", max_age_days=30):
    """
    清理超过指定天数的旧报告

    Args:
        base_dir: 报告存储根目录
        max_age_days: 最大保留天数
    """
    if not os.path.exists(base_dir):
        return

    cutoff = datetime.now().timestamp() - max_age_days * 86400

    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path):
            meta_path = os.path.join(folder_path, "metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    created = datetime.fromisoformat(meta.get("created_at", "")).timestamp()
                    if created < cutoff:
                        shutil.rmtree(folder_path)
                except Exception:
                    pass


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="综合报告生成器")
    parser.add_argument("stock_code", help="6位股票代码，如 600519")
    parser.add_argument("--battle-file", help="辩论结果JSON文件路径")
    parser.add_argument("--output-dir", default="analysis_reports", help="报告输出目录（默认 analysis_reports）")
    parser.add_argument("--list", action="store_true", help="列出所有已保存的报告")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="清理N天前的旧报告")
    args = parser.parse_args()

    if args.list:
        reports = list_reports(base_dir=args.output_dir, stock_code=args.stock_code)
        print(json.dumps(reports, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.cleanup:
        cleanup_old_reports(base_dir=args.output_dir, max_age_days=args.cleanup)
        print(f"已清理 {args.cleanup} 天前的旧报告")
        sys.exit(0)

    if not args.battle_file:
        print("错误：请通过 --battle-file 提供辩论结果JSON文件")
        sys.exit(1)

    with open(args.battle_file, "r", encoding="utf-8") as f:
        battle_results = json.load(f)

    research_results = battle_results.get("research_results", {})
    start_time = battle_results.get("start_time", time.time())

    report = generate_analysis_report(args.stock_code, research_results, battle_results, start_time)
    path = save_report(report, base_dir=args.output_dir)
    print(f"报告已保存至: {path}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
