"""
专家观点AI总结工具
基于CreateChatCompletion实现结构化的专家辩论内容总结功能
"""

import json
from typing import Any, Dict, List
from src.tool.create_chat_completion import CreateChatCompletion
from src.schema import Message, ToolChoice
from src.schema.expert_summary import ExpertSummary
from src.prompt.expert_summary import EXPERT_SUMMARY_SYSTEM_PROMPT, EXPERT_SUMMARY_PROMPT_TEMPLATE
from src.logger import logger


class ExpertSummaryTool(CreateChatCompletion):
    """专家观点AI总结工具"""
    
    name: str = "expert_summary"
    description: str = "对专家的辩论发言进行深度总结，提取核心观点、关键论据和数据来源"
    
    def __init__(self):
        """初始化专家总结工具"""
        super().__init__(response_type=ExpertSummary)
    
    async def summarize_expert_opinion(
        self,
        expert_name: str,
        expert_type: str,
        stock_code: str,
        expert_speeches: List[Dict[str, Any]],
        research_result: str,
        llm_client
    ) -> ExpertSummary:
        """
        总结专家观点
        
        Args:
            expert_name: 专家名称
            expert_type: 专家类型
            stock_code: 股票代码
            expert_speeches: 专家发言列表
            research_result: 专家的研究分析结果
            llm_client: LLM客户端
            
        Returns:
            ExpertSummary: 专家观点总结
        """
        try:
            # 整理专家发言内容
            speeches_text = self._format_expert_speeches(expert_speeches)
            
            # 构建提示词
            prompt = EXPERT_SUMMARY_PROMPT_TEMPLATE.format(
                expert_name=expert_name,
                expert_type=expert_type,
                stock_code=stock_code,
                expert_speeches=speeches_text,
                research_result=research_result
            )
            
            logger.info(f"开始总结专家观点: {expert_name}")
            
            # 构建工具定义（符合 OpenAI function calling 格式）
            tools = [self.to_param()]
            
            # 使用正确的 ask_tool 签名调用 LLM
            response = await llm_client.ask_tool(
                messages=[Message.user_message(prompt)],
                system_msgs=[Message.system_message(EXPERT_SUMMARY_SYSTEM_PROMPT)],
                tools=tools,
                tool_choice=ToolChoice.REQUIRED,
            )
            
            # 从 ChatCompletionMessage 中解析 tool_calls 的 function.arguments
            parsed_data = self._parse_tool_response(response)
            
            # 合并专家基础信息
            summary_data = {
                "expert_name": expert_name,
                "expert_type": expert_type,
                **parsed_data
            }
            
            expert_summary = ExpertSummary(**summary_data)
            logger.info(f"专家观点总结完成: {expert_name}")
            
            return expert_summary
            
        except Exception as e:
            logger.error(f"总结专家观点失败 {expert_name}: {str(e)}")
            # 返回基础总结作为降级策略
            return self._create_fallback_summary(
                expert_name, expert_type, expert_speeches, research_result
            )
    
    def _parse_tool_response(self, response) -> Dict[str, Any]:
        """从 LLM 的 tool_calls 响应中解析结构化数据"""
        if response and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function and tool_call.function.arguments:
                    try:
                        return json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析 tool_call arguments 失败: {e}")
        
        # 如果没有 tool_calls，尝试从 content 中解析
        if response and response.content:
            try:
                return json.loads(response.content)
            except (json.JSONDecodeError, TypeError):
                pass
        
        raise ValueError("LLM 响应中没有有效的结构化数据")
    
    def _format_expert_speeches(self, expert_speeches: List[Dict[str, Any]]) -> str:
        """格式化专家发言内容"""
        if not expert_speeches:
            return "该专家在辩论中未发言"
        
        formatted_speeches = []
        for i, speech in enumerate(expert_speeches, 1):
            content = speech.get('content', '')
            timestamp = speech.get('timestamp', '')
            round_num = speech.get('round', '')
            
            formatted_speech = f"第{i}次发言"
            if round_num:
                formatted_speech += f"（第{round_num}轮）"
            if timestamp:
                formatted_speech += f" [{timestamp}]"
            formatted_speech += f"：\n{content}\n"
            
            formatted_speeches.append(formatted_speech)
        
        return "\n".join(formatted_speeches)
    
    def _create_fallback_summary(
        self,
        expert_name: str,
        expert_type: str,
        expert_speeches: List[Dict[str, Any]],
        research_result: str
    ) -> ExpertSummary:
        """创建降级总结（当AI总结失败时使用）"""
        
        # 从研究结果中提取简单总结
        conclusion = research_result[:200] + "..." if len(research_result) > 200 else research_result
        
        # 基于专家类型生成默认标签
        type_tags = {
            "sentiment": ["市场情感", "投资者情绪"],
            "risk": ["风险控制", "风险评估"],
            "hot_money": ["游资分析", "资金流向"],
            "technical": ["技术分析", "图表分析"],
            "chip_analysis": ["筹码分析", "持仓结构"],
            "big_deal": ["大单分析", "主力资金"]
        }
        
        return ExpertSummary(
            expert_name=expert_name,
            expert_type=expert_type,
            analysis_conclusion=conclusion,
            one_sentence_summary=f"{expert_name}基于{expert_type}进行了深度分析",
            key_arguments=["基于历史数据分析", "结合市场环境判断", "考虑技术指标因素"],
            key_tags=type_tags.get(expert_type.split("_")[0], ["专业分析"]),
            data_sources=["市场数据", "技术指标", "历史走势"]
        )


# 专家类型映射
EXPERT_TYPE_MAPPING = {
    "sentiment_agent": {
        "name": "市场情感分析师",
        "type": "sentiment"
    },
    "risk_control_agent": {
        "name": "风险控制专家", 
        "type": "risk"
    },
    "hot_money_agent": {
        "name": "游资分析师",
        "type": "hot_money"
    },
    "technical_analysis_agent": {
        "name": "技术分析师",
        "type": "technical"
    },
    "chip_analysis_agent": {
        "name": "筹码分析师",
        "type": "chip_analysis"
    },
    "big_deal_analysis_agent": {
        "name": "大单分析师",
        "type": "big_deal"
    }
}