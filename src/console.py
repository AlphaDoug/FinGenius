import io
import sys
import json
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.box import ROUNDED, DOUBLE, HEAVY
from rich.rule import Rule
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.markdown import Markdown
import time

# Windows GBK 控制台无法显示 emoji，强制使用 UTF-8 输出
if sys.platform == "win32":
    _utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console = Console(file=_utf8_stdout, force_terminal=True)
else:
    console = Console()

class FinGeniusVisualizer:
    """Enhanced visualizer for FinGenius analysis process"""
    
    def __init__(self):
        self.progress_stats = {
            "tool_calls": 0,
            "llm_calls": 0,
            "agents_active": 0
        }
        
        # Agent ID to friendly name mapping
        self.agent_name_mapping = {
            "sentiment_agent": "🧠 市场情绪分析师",
            "risk_control_agent": "🛡️ 风险控制专家", 
            "hot_money_agent": "💰 游资分析师",
            "technical_analysis_agent": "📈 技术分析师",
            "chip_analysis_agent": "🔍 筹码分析师",
            "big_deal_analysis_agent": "💹 大单分析师",
            "report_agent": "📊 报告生成专家",
            "System": "🤖 系统"
        }
    
    def _get_friendly_agent_name(self, agent_name: str) -> str:
        """Get friendly display name for agent"""
        return self.agent_name_mapping.get(agent_name, f"🤖 {agent_name}")

    def show_logo(self):
        """Display the FinGenius ASCII logo"""
        # Use simple ASCII characters for better compatibility
        logo = """
================================================================================
                                                                                
    ███████ ██ ███   ██  ██████  ███████ ███   ██ ██ ██   ██ ███████           
    ██      ██ ████  ██ ██       ██      ████  ██ ██ ██   ██ ██                
    █████   ██ ██ ██ ██ ██   ███ █████   ██ ██ ██ ██ ██   ██ ███████           
    ██      ██ ██  ████ ██    ██ ██      ██  ████ ██ ██   ██      ██           
    ██      ██ ██   ███  ██████  ███████ ██   ███ ██  █████  ███████           
                                                                                
                          🤖 FinGenius 📈                                      
                   AI-Powered Financial Analysis System                        
                                                                                
================================================================================
        """
        console.print(logo, style="bold cyan")
        console.print()

    def show_tool_call(self, tool_name: str, parameters: Dict[str, Any], agent_name: str = "System"):
        """Display tool call in a beautiful frame"""
        # Get friendly agent name
        friendly_name = self._get_friendly_agent_name(agent_name)
        
        # Create parameter display
        param_text = ""
        if parameters:
            for key, value in parameters.items():
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                param_text += f"  • {key}: {value}\n"
        
        content = f"🤖 **专家**: {friendly_name}\n🔧 **工具**: {tool_name}"
        if param_text:
            content += f"\n📋 **参数**:\n{param_text.rstrip()}"
        
        panel = Panel(
            content,
            title="🛠️ 工具调用",
            title_align="left",
            border_style="blue",
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)
        self.progress_stats["tool_calls"] += 1

    def show_tool_result(self, result: Any, success: bool = True):
        """Display tool result with beautiful formatting"""
        if success:
            title = "✅ Tool Result"
            style = "green"
            emoji = "📊"
        else:
            title = "❌ Tool Error"
            style = "red"
            emoji = "⚠️"
        
        # Format result based on type
        if isinstance(result, dict):
            if len(str(result)) > 200:
                content = f"{emoji} Result data received (JSON format)\n📏 Size: {len(str(result))} characters"
            else:
                content = f"{emoji} **Result**:\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
        elif isinstance(result, str):
            if len(result) > 200:
                content = f"{emoji} {result[:197]}..."
            else:
                content = f"{emoji} {result}"
        else:
            content = f"{emoji} {str(result)}"
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            border_style=style,
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)

    def show_agent_thought(self, agent_name: str, thought: str, thought_type: str = "analysis"):
        """Display agent's thinking process"""
        # Get friendly agent name
        friendly_name = self._get_friendly_agent_name(agent_name)
        
        emoji_map = {
            "analysis": "🧠",
            "planning": "📋",
            "decision": "🎯",
            "reflection": "🤔"
        }
        
        emoji = emoji_map.get(thought_type, "💭")
        
        content = f"{emoji} **{friendly_name}** 正在思考...\n\n{thought}"
        
        panel = Panel(
            content,
            title=f"💭 专家思考 ({thought_type.title()})",
            title_align="left",
            border_style="yellow",
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)

    def show_analysis_result(self, stock_code: str, analysis: Dict[str, Any]):
        """Display comprehensive analysis results"""
        # Main header
        header = f"📊 {stock_code} 投资分析结果"
        
        # Create main content
        content_parts = []
        
        # Summary section
        if "summary" in analysis:
            content_parts.append(f"📋 **分析摘要**:\n{analysis['summary']}\n")
        
        # Recommendation
        if "recommendation" in analysis:
            rec = analysis["recommendation"]
            rec_emoji = "📈" if "买入" in rec or "看涨" in rec else "📉" if "卖出" in rec or "看跌" in rec else "➡️"
            content_parts.append(f"{rec_emoji} **投资建议**: {rec}\n")
        
        # Target price
        if "target_price" in analysis:
            content_parts.append(f"🎯 **目标价格**: ¥{analysis['target_price']}\n")
        
        # Risk and value scores
        scores_text = ""
        if "risk_score" in analysis:
            risk_emoji = "🟢" if analysis["risk_score"] <= 3 else "🟡" if analysis["risk_score"] <= 6 else "🔴"
            scores_text += f"{risk_emoji} **风险评分**: {analysis['risk_score']}/10  "
        
        if "value_score" in analysis:
            value_emoji = "⭐" * min(int(analysis["value_score"]), 5)
            scores_text += f"{value_emoji} **价值评分**: {analysis['value_score']}/10"
        
        if scores_text:
            content_parts.append(scores_text + "\n")
        
        content = "\n".join(content_parts)
        
        panel = Panel(
            content,
            title=header,
            title_align="center",
            border_style="cyan",
            box=DOUBLE,
            padding=(1, 2)
        )
        console.print(panel)

    def show_debate_message(self, agent_name: str, message: str, message_type: str = "speak"):
        """Display debate messages with different styles"""
        # Get friendly agent name
        friendly_name = self._get_friendly_agent_name(agent_name)
        
        if message_type == "speak":
            emoji = "🗣️"
            style = "white"
            title = f"💬 {friendly_name} 发言"
        elif message_type == "vote":
            emoji = "🗳️"
            style = "green" if "bullish" in message.lower() else "red"
            title = f"🗳️ {friendly_name} 投票"
        else:
            emoji = "📢"
            style = "blue"
            title = f"📢 {friendly_name}"
        
        content = f"{emoji} {message}"
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            border_style=style,
            box=ROUNDED,
            padding=(0, 1)
        )
        console.print(panel)

    def show_debate_summary(self, debate_results: Dict[str, Any]):
        """Display debate summary with voting results"""
        content_parts = []
        
        # Voting results
        if "vote_results" in debate_results:
            votes = debate_results["vote_results"]
            total_votes = sum(votes.values())
            
            content_parts.append("🗳️ **投票结果**:")
            for option, count in votes.items():
                percentage = (count / total_votes * 100) if total_votes > 0 else 0
                emoji = "📈" if option == "bullish" else "📉"
                content_parts.append(f"  {emoji} {option.title()}: {count} 票 ({percentage:.1f}%)")
            content_parts.append("")
        
        # Key highlights
        if "battle_highlights" in debate_results and debate_results["battle_highlights"]:
            content_parts.append("💡 **关键观点**:")
            for highlight in debate_results["battle_highlights"][:3]:  # Show top 3
                content_parts.append(f"  • {highlight.get('agent', 'Agent')}: {highlight.get('point', '')[:100]}...")
            content_parts.append("")
        
        # Statistics
        if "tool_calls" in debate_results and "llm_calls" in debate_results:
            content_parts.append(f"📊 **统计信息**: {debate_results['tool_calls']} 工具调用, {debate_results['llm_calls']} LLM调用")
        
        content = "\n".join(content_parts)
        
        panel = Panel(
            content,
            title="🏆 辩论总结",
            title_align="center",
            border_style="magenta",
            box=DOUBLE,
            padding=(1, 2)
        )
        console.print(panel)

    def show_progress_update(self, stage: str, details: str = ""):
        """Show progress updates during analysis"""
        self.progress_stats["llm_calls"] += 1
        
        progress_text = f"🔄 **{stage}**"
        if details:
            progress_text += f"\n{details}"
        
        progress_text += f"\n📈 进度: {self.progress_stats['tool_calls']} 工具调用 | {self.progress_stats['llm_calls']} LLM调用"
        
        panel = Panel(
            progress_text,
            title="⏳ 分析进度",
            title_align="left",
            border_style="blue",
            box=ROUNDED,
            padding=(0, 1)
        )
        console.print(panel)

    def show_agent_starting(self, agent_name: str, current: int, total: int):
        """Display which agent is starting analysis"""
        friendly_name = self._get_friendly_agent_name(agent_name)
        
        content = f"🚀 **正在启动专家分析**\n\n专家: {friendly_name}\n进度: {current}/{total}"
        
        panel = Panel(
            content,
            title=f"🔄 专家分析 ({current}/{total})",
            title_align="left",
            border_style="green",
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)
        
    def show_agent_completed(self, agent_name: str, current: int, total: int):
        """Display when agent completes analysis"""
        friendly_name = self._get_friendly_agent_name(agent_name)
        
        content = f"✅ **专家分析完成**\n\n专家: {friendly_name}\n进度: {current}/{total}"
        
        panel = Panel(
            content,
            title=f"✅ 分析完成 ({current}/{total})",
            title_align="left",
            border_style="green",
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)
        
    def show_waiting_next_agent(self, seconds: int = 3):
        """Display waiting message between agents"""
        content = f"⏳ **等待下一个专家**\n\n等待时间: {seconds} 秒\n目的: 降低资源消耗"
        
        panel = Panel(
            content,
            title="⏸️ 间隔等待",
            title_align="left",
            border_style="yellow",
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)
        console.print()

    def show_section_header(self, title: str, emoji: str = "📊"):
        """Show section headers"""
        console.print()
        console.print(Rule(f"{emoji} {title}", style="bold blue"))
        console.print()

    def show_error(self, error_msg: str, context: str = ""):
        """Display errors in a formatted way"""
        content = f"❌ **错误**: {error_msg}"
        if context:
            content += f"\n🔍 **上下文**: {context}"
        
        panel = Panel(
            content,
            title="⚠️ 错误信息",
            title_align="left",
            border_style="red",
            box=HEAVY,
            padding=(1, 2)
        )
        console.print(panel)

    def show_completion(self, total_time: float):
        """Show completion message"""
        content = f"🎉 **分析完成!**\n⏱️ 总用时: {total_time:.2f} 秒\n📊 总工具调用: {self.progress_stats['tool_calls']}\n🤖 总LLM调用: {self.progress_stats['llm_calls']}"
        
        panel = Panel(
            content,
            title="✅ 任务完成",
            title_align="center",
            border_style="green",
            box=DOUBLE,
            padding=(1, 2)
        )
        console.print(panel)

    def show_agent_analysis_result(self, agent_name: str, analysis_content: str, analysis_type: str = "综合分析"):
        """Display individual agent analysis results"""
        # Get friendly agent name
        friendly_name = self._get_friendly_agent_name(agent_name)
        
        # Truncate very long content for display
        if len(analysis_content) > 1000:
            display_content = analysis_content[:997] + "..."
            full_content_note = f"\n\n📝 **注**: 完整分析内容共 {len(analysis_content)} 字符"
        else:
            display_content = analysis_content
            full_content_note = ""
        
        content = f"📋 **分析类型**: {analysis_type}\n\n{display_content}{full_content_note}"
        
        panel = Panel(
            content,
            title=f"📊 {friendly_name} 分析结果",
            title_align="left",
            border_style="green",
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(panel)

    def show_research_summary(self, research_results: Dict[str, Any]):
        """Display comprehensive research summary from all agents"""
        if not research_results:
            return
            
        console.print()
        console.print(Rule("📊 研究阶段完整分析结果", style="bold green"))
        console.print()
        
        # Show each agent's analysis
        agent_results = {
            "sentiment": ("🧠 市场情绪分析师", research_results.get("sentiment", "")),
            "risk": ("🛡️ 风险控制专家", research_results.get("risk", "")),
            "hot_money": ("💰 游资分析师", research_results.get("hot_money", "")),
            "technical": ("📈 技术分析师", research_results.get("technical", "")),
            "chip_analysis": ("🔍 筹码分析师", research_results.get("chip_analysis", "")),
            "big_deal": ("💹 大单分析师", research_results.get("big_deal", ""))
        }
        
        for analysis_key, (agent_name, analysis_content) in agent_results.items():
            if analysis_content and analysis_content.strip():
                self.show_agent_analysis_result(
                    analysis_key + "_agent", 
                    analysis_content, 
                    analysis_key.replace("_", " ").title()
                )
                console.print()
        
        # Show summary metrics if available
        if any(key in research_results for key in ["risk_score", "value_score", "recommendation"]):
            self._show_research_metrics(research_results)

    def _show_research_metrics(self, research_results: Dict[str, Any]):
        """Show research metrics summary"""
        metrics_content = []
        
        if "recommendation" in research_results:
            rec = research_results["recommendation"]
            rec_emoji = "📈" if any(word in rec.lower() for word in ['买入', '看涨', 'buy', 'bullish']) else "📉" if any(word in rec.lower() for word in ['卖出', '看跌', 'sell', 'bearish']) else "➡️"
            metrics_content.append(f"{rec_emoji} **综合建议**: {rec}")
        
        if "risk_score" in research_results:
            risk_score = research_results["risk_score"]
            risk_emoji = "🟢" if risk_score <= 3 else "🟡" if risk_score <= 6 else "🔴"
            metrics_content.append(f"{risk_emoji} **风险评分**: {risk_score}/10")
        
        if "value_score" in research_results:
            value_score = research_results["value_score"]
            value_stars = "⭐" * min(int(value_score), 5)
            metrics_content.append(f"{value_stars} **价值评分**: {value_score}/10")
        
        if "target_price_range" in research_results:
            metrics_content.append(f"🎯 **目标价格区间**: {research_results['target_price_range']}")
        
        if "reasonable_price_range" in research_results:
            metrics_content.append(f"💰 **合理价格区间**: ¥{research_results['reasonable_price_range']}")
        
        if metrics_content:
            content = "\n".join(metrics_content)
            panel = Panel(
                content,
                title="📊 综合评估指标",
                title_align="center",
                border_style="cyan",
                box=DOUBLE,
                padding=(1, 2)
            )
            console.print(panel)

# Global visualizer instance
visualizer = FinGeniusVisualizer()

# Export functions for backward compatibility
def show_logo():
    visualizer.show_logo()

def show_header(stock_code: str):
    header = f"📊 {stock_code} (获取中...) 投资分析与交易建议"
    panel = Panel(
        "",
        title=header,
        title_align="center",
        border_style="yellow",
        box=DOUBLE,
        height=3
    )
    console.print(panel)

def show_analysis_results(results: Dict[str, Any]):
    """Display final analysis results"""
    if not results:
        return
    
    stock_code = results.get('stock_code', 'Unknown')
    
    # Show recommendation
    if 'recommendation' in results:
        recommendation = results['recommendation']
        rec_emoji = "📈" if any(word in recommendation.lower() for word in ['买入', '看涨', 'buy']) else "📉"
        
        content = f"{rec_emoji} **投资建议**: {recommendation}\n"
        
        if 'target_price_range' in results:
            content += f"🎯 **目标价格区间**: {results['target_price_range']}\n"
        
        if 'risk_score' in results and 'value_score' in results:
            risk_emoji = "🟢" if results['risk_score'] <= 3 else "🟡" if results['risk_score'] <= 6 else "🔴"
            value_stars = "⭐" * min(int(results.get('value_score', 0)), 5)
            content += f"{risk_emoji} **风险评分**: {results['risk_score']}/10  {value_stars} **价值评分**: {results['value_score']}/10"
        
        panel = Panel(
            content,
            title=f"📊 {stock_code} 最终分析结果",
            title_align="center",
            border_style="cyan",
            box=DOUBLE,
            padding=(1, 2)
        )
        console.print(panel)

def show_debate_results(results: Dict[str, Any]):
    """Display debate results"""
    visualizer.show_debate_summary(results)

def show_progress_stats(tool_calls: int, llm_calls: int):
    """Show progress statistics"""
    visualizer.progress_stats["tool_calls"] = tool_calls
    visualizer.progress_stats["llm_calls"] = llm_calls
    
    stats_text = f"📊 统计信息: {tool_calls} 工具调用 | {llm_calls} LLM调用"
    console.print(stats_text, style="dim")
    console.print()

def clear_screen():
    """Clear the screen"""
    console.clear()

def print_separator():
    """Print a separator line"""
    console.print(Rule(style="dim")) 