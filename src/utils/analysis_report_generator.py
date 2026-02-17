"""
分析报告生成器
整合专家总结、股票详情、投票结果生成完整的JSON分析报告
"""

import json
import asyncio
from typing import Any, Dict, List
from datetime import datetime

from src.tool.expert_summary import ExpertSummaryTool, EXPERT_TYPE_MAPPING
from src.tool.stock_info_request import StockInfoRequest
from src.schema import Message, ToolChoice
from src.schema.expert_summary import (
    AnalysisReport, StockBasicInfo, VotingResults, 
    DebateSummary, DebateRound, DebateSpeech, ExpertSummary
)
from src.logger import logger


class AnalysisReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, llm_client):
        """
        初始化报告生成器
        
        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
        self.expert_summary_tool = ExpertSummaryTool()
        self.stock_info_tool = StockInfoRequest()
    
    async def generate_complete_report(
        self,
        stock_code: str,
        research_results: Dict[str, Any],
        battle_results: Dict[str, Any],
        start_time: float
    ) -> AnalysisReport:
        """
        生成完整的分析报告
        
        Args:
            stock_code: 股票代码
            research_results: 研究阶段结果
            battle_results: 辩论阶段结果
            start_time: 分析开始时间
            
        Returns:
            AnalysisReport: 完整的分析报告
        """
        try:
            logger.info(f"开始生成完整分析报告: {stock_code}")
            
            # 并行执行多个任务
            tasks = [
                self._generate_expert_summaries(stock_code, research_results, battle_results),
                self._get_stock_basic_info(stock_code),
                self._generate_voting_results(battle_results),
                self._generate_debate_summary(battle_results)
            ]
            
            expert_summaries, stock_info, voting_results, debate_summary = await asyncio.gather(*tasks)
            
            # 计算分析耗时
            analysis_duration = datetime.now().timestamp() - start_time
            
            # 构建完整报告
            report = AnalysisReport(
                stock_info=stock_info,
                expert_summaries=expert_summaries,
                voting_results=voting_results,
                debate_summary=debate_summary,
                timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
                analysis_duration=round(analysis_duration, 2)
            )
            
            logger.info(f"分析报告生成完成: {stock_code}")
            return report
            
        except Exception as e:
            logger.error(f"生成分析报告失败 {stock_code}: {str(e)}")
            raise
    
    async def _generate_expert_summaries(
        self,
        stock_code: str,
        research_results: Dict[str, Any],
        battle_results: Dict[str, Any]
    ) -> Dict[str, ExpertSummary]:
        """生成专家观点总结"""
        
        expert_summaries = {}
        debate_history = battle_results.get("debate_history", [])
        
        # 按专家分组辩论发言
        expert_speeches = self._group_speeches_by_expert(debate_history)
        
        # 并行生成所有专家的总结
        summary_tasks = []
        for agent_id, expert_info in EXPERT_TYPE_MAPPING.items():
            expert_name = expert_info["name"]
            expert_type = expert_info["type"]
            
            # research_results 的 key 是 expert_type (如 "sentiment", "risk" 等)
            # 而不是 agent_id (如 "sentiment_agent" 等)
            research_result = research_results.get(expert_type, "")
            if not research_result:
                # 也尝试用 agent_id 匹配（兼容性）
                research_result = research_results.get(agent_id, "")
            
            if research_result:
                speeches = expert_speeches.get(agent_id, [])
                
                task = self.expert_summary_tool.summarize_expert_opinion(
                    expert_name=expert_name,
                    expert_type=expert_type,
                    stock_code=stock_code,
                    expert_speeches=speeches,
                    research_result=research_result if isinstance(research_result, str) else str(research_result),
                    llm_client=self.llm_client
                )
                summary_tasks.append((expert_type, task))
        
        # 等待所有总结完成
        for expert_type, task in summary_tasks:
            try:
                summary = await task
                expert_summaries[expert_type] = summary
            except Exception as e:
                logger.error(f"生成专家总结失败 {expert_type}: {str(e)}")
        
        return expert_summaries
    
    def _group_speeches_by_expert(self, debate_history: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按专家分组辩论发言"""
        expert_speeches = {}
        
        for speech in debate_history:
            # 兼容不同的字段名格式
            agent_id = speech.get('agent_id') or speech.get('speaker')
            if agent_id:
                if agent_id not in expert_speeches:
                    expert_speeches[agent_id] = []
                expert_speeches[agent_id].append(speech)
        
        return expert_speeches
    
    async def _get_stock_basic_info(self, stock_code: str) -> StockBasicInfo:
        """获取股票基本信息"""
        try:
            # 调用股票信息工具获取基本信息
            stock_data = await self.stock_info_tool.execute(stock_code=stock_code)
            
            # 将 Pydantic model 转为 dict
            if hasattr(stock_data, 'model_dump'):
                stock_data = stock_data.model_dump()
            elif hasattr(stock_data, 'dict'):
                stock_data = stock_data.dict()
            
            # 解析股票数据并构建StockBasicInfo
            if isinstance(stock_data, dict) and 'output' in stock_data:
                data = stock_data['output'].get('basic_info', {})
                return StockBasicInfo(
                    stock_code=stock_code,
                    stock_name=data.get('股票名称', '未知'),
                    industry=data.get('所处行业', data.get('所属行业', '未知')),
                    market_cap=str(data.get('总市值', '未知')),
                    pe_ratio=str(data.get('市盈率(动)', data.get('市盈率', '未知'))),
                    pb_ratio=str(data.get('市净率', '未知')),
                    roe=str(data.get('ROE', data.get('净资产收益率', '未知'))),
                    gross_margin=str(data.get('毛利率', '未知'))
                )
            elif isinstance(stock_data, dict) and 'data' in stock_data:
                data = stock_data['data']
                return StockBasicInfo(
                    stock_code=stock_code,
                    stock_name=data.get('股票名称', '未知'),
                    industry=data.get('所属行业', '未知'),
                    market_cap=str(data.get('总市值', '未知')),
                    pe_ratio=str(data.get('市盈率', '未知')),
                    pb_ratio=str(data.get('市净率', '未知')),
                    roe=str(data.get('净资产收益率', '未知')),
                    gross_margin=str(data.get('毛利率', '未知'))
                )
            else:
                # 降级处理：返回基础信息
                return StockBasicInfo(
                    stock_code=stock_code,
                    stock_name="未获取到股票名称",
                    industry="未知行业",
                    market_cap="未知",
                    pe_ratio="未知",
                    pb_ratio="未知",
                    roe="未知",
                    gross_margin="未知"
                )
                
        except Exception as e:
            logger.error(f"获取股票基本信息失败 {stock_code}: {str(e)}")
            # 返回基础信息作为降级策略
            return StockBasicInfo(
                stock_code=stock_code,
                stock_name="获取失败",
                industry="未知",
                market_cap="未知",
                pe_ratio="未知",
                pb_ratio="未知",
                roe="未知",
                gross_margin="未知"
            )
    
    async def _generate_voting_results(self, battle_results: Dict[str, Any]) -> VotingResults:
        """生成投票结果"""
        vote_count = battle_results.get("vote_count", {})
        bullish_count = vote_count.get("bullish", 0)
        bearish_count = vote_count.get("bearish", 0)
        total_votes = bullish_count + bearish_count
        
        bullish_pct = round(bullish_count / total_votes * 100, 1) if total_votes > 0 else 0
        bearish_pct = round(bearish_count / total_votes * 100, 1) if total_votes > 0 else 0
        
        return VotingResults(
            final_decision=battle_results.get("final_decision", "unknown"),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            bullish_percentage=bullish_pct,
            bearish_percentage=bearish_pct,
            total_votes=total_votes
        )
    
    async def _generate_debate_summary(self, battle_results: Dict[str, Any]) -> DebateSummary:
        """生成辩论总结"""
        debate_history = battle_results.get("debate_history", [])
        battle_highlights = battle_results.get("battle_highlights", [])
        
        # 提取关键辩论要点
        key_points = []
        for highlight in battle_highlights[:5]:  # 取前5个要点
            if isinstance(highlight, dict):
                point = highlight.get("point", "")
                if point:
                    key_points.append(point)
        
        # 按轮次组织详细发言记录
        rounds_detail = self._build_rounds_detail(debate_history)
        
        # 用 LLM 生成共识观点和分歧观点
        consensus_points, divergent_points = await self._analyze_debate_consensus(key_points)
        
        return DebateSummary(
            total_rounds=battle_results.get("debate_rounds", 0),
            total_speeches=len(debate_history),
            rounds_detail=rounds_detail,
            key_debate_points=key_points,
            consensus_points=consensus_points,
            divergent_points=divergent_points
        )
    
    def _build_rounds_detail(self, debate_history: List[Dict[str, Any]]) -> List[DebateRound]:
        """将 debate_history 按轮次结构化为 DebateRound 列表"""
        if not debate_history:
            return []
        
        # 按 round 字段分组
        rounds_map: Dict[int, List[Dict[str, Any]]] = {}
        for entry in debate_history:
            round_num = entry.get("round", 1)
            if round_num not in rounds_map:
                rounds_map[round_num] = []
            rounds_map[round_num].append(entry)
        
        # 构建结构化轮次列表
        rounds_detail = []
        for round_num in sorted(rounds_map.keys()):
            speeches = []
            for entry in rounds_map[round_num]:
                speech = DebateSpeech(
                    speaker=entry.get("speaker", "未知"),
                    agent_id=entry.get("agent_id", ""),
                    content=entry.get("content", ""),
                    timestamp=entry.get("timestamp", ""),
                )
                speeches.append(speech)
            rounds_detail.append(DebateRound(
                round_number=round_num,
                speeches=speeches
            ))
        
        return rounds_detail
    
    async def _analyze_debate_consensus(self, key_debate_points: List[str]) -> tuple:
        """用 LLM 分析辩论中的共识观点和分歧观点"""
        if not key_debate_points:
            return ["无辩论数据"], ["无辩论数据"]
        
        try:
            # 构建辩论内容摘要
            debate_text = "\n\n".join([f"【发言{i+1}】\n{point}" for i, point in enumerate(key_debate_points)])
            
            system_prompt = "你是一位专业的金融分析总结专家，负责从多位专家的辩论中提炼共识和分歧观点。请以JSON格式返回结果。"
            
            user_prompt = f"""请分析以下专家辩论内容，提炼出共识观点和分歧观点：

{debate_text}

请提取：
1. consensus_points: 所有或大多数专家都同意的观点（3-5条）
2. divergent_points: 专家之间存在明显分歧的观点（3-5条）

每条观点用简洁的一句话概括（20-40字）。"""
            
            # 定义工具参数
            tools = [{
                "type": "function",
                "function": {
                    "name": "debate_consensus_analysis",
                    "description": "分析辩论中的共识和分歧观点",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "consensus_points": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "所有或大多数专家都同意的共识观点列表"
                            },
                            "divergent_points": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "专家之间存在明显分歧的观点列表"
                            }
                        },
                        "required": ["consensus_points", "divergent_points"]
                    }
                }
            }]
            
            response = await self.llm_client.ask_tool(
                messages=[Message.user_message(user_prompt)],
                system_msgs=[Message.system_message(system_prompt)],
                tools=tools,
                tool_choice=ToolChoice.REQUIRED,
            )
            
            # 解析响应
            if response and response.tool_calls:
                for tool_call in response.tool_calls:
                    if tool_call.function and tool_call.function.arguments:
                        try:
                            data = json.loads(tool_call.function.arguments)
                            consensus = data.get("consensus_points", ["AI分析未返回共识"])
                            divergent = data.get("divergent_points", ["AI分析未返回分歧"])
                            return consensus, divergent
                        except json.JSONDecodeError:
                            pass
            
            return ["AI分析解析失败"], ["AI分析解析失败"]
            
        except Exception as e:
            logger.error(f"分析辩论共识失败: {str(e)}")
            return ["AI分析生成失败"], ["AI分析生成失败"]