"""
专家总结相关的数据模型
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ExpertSummary(BaseModel):
    """专家观点总结模型"""
    
    expert_name: str = Field(description="专家名称")
    expert_type: str = Field(description="专家类型")
    analysis_conclusion: str = Field(description="分析结论，专家对该股票的整体判断和投资建议")
    one_sentence_summary: str = Field(description="一句话总结，用一句话概括专家的核心观点")
    key_arguments: List[str] = Field(description="关键论点，支撑专家结论的主要论据")
    key_tags: List[str] = Field(description="关键标签，反映专家观点特征的标签")
    data_sources: List[str] = Field(description="数据来源，专家分析所依据的主要数据来源和指标")


class DebateSpeech(BaseModel):
    """单条辩论发言"""
    
    speaker: str = Field(description="发言者名称")
    agent_id: str = Field(description="发言者ID")
    content: str = Field(description="发言内容")
    timestamp: str = Field(default="", description="发言时间")


class DebateRound(BaseModel):
    """单轮辩论记录"""
    
    round_number: int = Field(description="轮次编号")
    speeches: List[DebateSpeech] = Field(default_factory=list, description="该轮次所有专家的发言")


class StockBasicInfo(BaseModel):
    """股票基本信息模型"""
    
    stock_code: str = Field(description="股票代码")
    stock_name: str = Field(description="股票名称")
    industry: str = Field(description="所属行业")
    market_cap: str = Field(description="总市值")
    pe_ratio: str = Field(description="市盈率")
    pb_ratio: str = Field(description="市净率")
    roe: str = Field(description="净资产收益率")
    gross_margin: str = Field(description="毛利率")


class VotingResults(BaseModel):
    """投票结果模型"""
    
    final_decision: str = Field(description="最终决策：bullish或bearish")
    bullish_count: int = Field(description="看涨票数")
    bearish_count: int = Field(description="看跌票数")
    bullish_percentage: float = Field(description="看涨票数百分比")
    bearish_percentage: float = Field(description="看跌票数百分比")
    total_votes: int = Field(description="总票数")


class DebateSummary(BaseModel):
    """辩论总结模型"""
    
    total_rounds: int = Field(description="辩论轮数")
    total_speeches: int = Field(description="总发言次数")
    rounds_detail: List[DebateRound] = Field(default_factory=list, description="每轮辩论的详细发言记录")
    key_debate_points: List[str] = Field(description="关键辩论要点")
    consensus_points: List[str] = Field(description="共识观点")
    divergent_points: List[str] = Field(description="分歧观点")


class AnalysisReport(BaseModel):
    """完整分析报告模型"""
    
    stock_info: StockBasicInfo = Field(description="股票基本信息")
    expert_summaries: dict[str, ExpertSummary] = Field(description="专家总结，key为专家类型")
    voting_results: VotingResults = Field(description="投票结果")
    debate_summary: DebateSummary = Field(description="辩论总结")
    timestamp: str = Field(description="分析时间戳")
    analysis_duration: float = Field(description="分析耗时（秒）")