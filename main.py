# !/usr/bin/env python3
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.environment.battle import BattleEnvironment
from src.environment.research import ResearchEnvironment
from src.logger import logger
from src.schema import AgentState
from src.tool.tts_tool import TTSTool

from src.utils.report_manager import report_manager
from src.console import visualizer, clear_screen
from rich.console import Console
import io

if sys.platform == "win32":
    _utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console = Console(file=_utf8_stdout, force_terminal=True)
else:
    console = Console()


def _extract_analysis_conclusion(agent_result: str) -> str:
    """从 agent 返回结果中提取 LLM 的分析结论文本。

    修改后的 ToolCallAgent.step() 会将 LLM 分析文本和工具输出合并返回，
    格式为: "[LLM分析文本]\n\nObserved output of cmd `terminate` executed:\n..."
    本函数从最后一个 step 中提取 LLM 的分析结论，排除工具执行日志。
    """
    if not agent_result:
        return ""

    # 按 step 分割
    import re
    steps = re.split(r'(?=Step \d+:)', agent_result.strip())
    steps = [s.strip() for s in steps if s.strip()]

    if not steps:
        return ""

    # 取最后一个 step 的内容
    last_step = steps[-1]

    # 移除 "Step N: " 前缀
    last_step = re.sub(r'^Step \d+:\s*', '', last_step)

    # 查找 "Observed output of cmd `terminate`" 的位置
    terminate_marker = "Observed output of cmd `terminate`"
    terminate_idx = last_step.find(terminate_marker)

    if terminate_idx > 0:
        # terminate 标记前面的内容就是 LLM 分析结论
        conclusion = last_step[:terminate_idx].strip()
        if conclusion:
            return conclusion

    # 如果最后一个 step 不包含 terminate，尝试查找任何非工具输出的文本
    # 检查是否以 "Observed output of cmd" 开头（纯工具输出，没有分析结论）
    if last_step.startswith("Observed output of cmd"):
        return ""

    # 如果有内容且不是纯工具输出，可能整段都是分析结论
    return last_step


class EnhancedFinGeniusAnalyzer:
    """Enhanced FinGenius analyzer with beautiful visualization"""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_tool_calls = 0
        self.total_llm_calls = 0

    async def analyze_stock(self, stock_code: str, max_steps: int = 3, debate_rounds: int = 2) -> Dict[str, Any]:
        """Run complete stock analysis with enhanced visualization"""
        try:
            # Clear screen and show logo
            clear_screen()
            visualizer.show_logo()
            
            # Show analysis start
            visualizer.show_section_header("开始股票分析", "🚀")
            visualizer.show_progress_update("初始化分析环境", f"目标股票: {stock_code}")
            
            # Research phase
            visualizer.show_section_header("研究阶段", "🔍")
            research_results = await self._run_research_phase(stock_code, max_steps)
            
            if not research_results:
                visualizer.show_error("研究阶段失败", "无法获取足够的分析数据")
                return {"error": "Research failed", "stock_code": stock_code}
            
            # Show research results
            visualizer.show_research_summary(research_results)
            
            # Battle phase
            visualizer.show_section_header("专家辩论阶段", "⚔️")
            battle_results = await self._run_battle_phase(research_results, max_steps, debate_rounds)
            
            if battle_results:
                visualizer.show_debate_summary(battle_results)
            
            # Generate reports
            await self._generate_reports(stock_code, research_results, battle_results)
            
            # Final results
            final_results = self._prepare_final_results(stock_code, research_results, battle_results)
            
            # Show completion
            total_time = time.time() - self.start_time
            visualizer.show_completion(total_time)
            
            return final_results
            
        except Exception as e:
            visualizer.show_error(str(e), "股票分析过程中出现错误")
            logger.error(f"Analysis failed: {str(e)}")
            return {"error": str(e), "stock_code": stock_code}

    async def _run_research_phase(self, stock_code: str, max_steps: int) -> Dict[str, Any]:
        """Run research phase with enhanced visualization"""
        try:
            # Create research environment
            visualizer.show_progress_update("创建研究环境")
            research_env = await ResearchEnvironment.create(max_steps=max_steps)
            
            # Show registered agents
            agent_names = [
                "sentiment_agent",
                "risk_control_agent", 
                "hot_money_agent",
                "technical_analysis_agent",
                "chip_analysis_agent",
                "big_deal_analysis_agent",
            ]
            
            for name in agent_names:
                agent = research_env.get_agent(name)
                if agent:
                    visualizer.show_progress_update(f"注册研究员", f"专家: {agent.name}")
            
            # Run research with tool call visualization
            visualizer.show_progress_update("开始深度研究", "多专家顺序分析中（每3秒一个）...")
            
            # Enhance agents with visualization
            self._enhance_agents_with_visualization(research_env)
            
            results = await research_env.run(stock_code)
            
            # Update counters
            if hasattr(research_env, 'tool_calls'):
                self.total_tool_calls += research_env.tool_calls
            if hasattr(research_env, 'llm_calls'):
                self.total_llm_calls += research_env.llm_calls
            
            await research_env.cleanup()
            return results
            
        except Exception as e:
            visualizer.show_error(f"研究阶段错误: {str(e)}")
            return {}

    async def _run_battle_phase(self, research_results: Dict[str, Any], max_steps: int, debate_rounds: int) -> Dict[str, Any]:
        """Run battle phase with enhanced visualization"""
        try:
            # Create battle environment
            visualizer.show_progress_update("创建辩论环境")
            battle_env = await BattleEnvironment.create(max_steps=max_steps, debate_rounds=debate_rounds)
            
            # Register agents for battle
            research_env = await ResearchEnvironment.create(max_steps=max_steps)
            agent_names = [
                "sentiment_agent",
                "risk_control_agent",
                "hot_money_agent", 
                "technical_analysis_agent",
                "chip_analysis_agent",
                "big_deal_analysis_agent",
            ]
            
            for name in agent_names:
                agent = research_env.get_agent(name)
                if agent:
                    agent.current_step = 0
                    agent.state = AgentState.IDLE
                    battle_env.register_agent(agent)
                    visualizer.show_progress_update(f"注册辩论专家", f"专家: {agent.name}")
            
            # Enhance agents with visualization for battle
            self._enhance_battle_agents_with_visualization(battle_env)
            
            # Run battle
            visualizer.show_progress_update("开始专家辩论", "多轮辩论与投票中...")
            results = await battle_env.run(research_results)
            
            # Update counters
            if hasattr(battle_env, 'tool_calls'):
                self.total_tool_calls += battle_env.tool_calls
            if hasattr(battle_env, 'llm_calls'):
                self.total_llm_calls += battle_env.llm_calls
            
            await research_env.cleanup()
            await battle_env.cleanup()
            return results
            
        except Exception as e:
            visualizer.show_error(f"辩论阶段错误: {str(e)}")
            return {}

    def _enhance_agents_with_visualization(self, environment):
        """Simple visualization enhancement without breaking functionality"""
        # Don't override methods - just store agent names for later use
        pass

    def _enhance_battle_agents_with_visualization(self, battle_env):
        """Enhance battle agents with visualization for debate messages"""
        # Instead of overriding methods, we'll enhance the broadcast message method
        if hasattr(battle_env, '_broadcast_message'):
            original_broadcast = battle_env._broadcast_message
            
            async def enhanced_broadcast(sender_id: str, content: str, event_type: str):
                # Show the debate message before broadcasting
                agent_name = battle_env.state.active_agents.get(sender_id, sender_id)
                
                if event_type == "speak":
                    visualizer.show_debate_message(agent_name, content, "speak")
                elif event_type == "vote":
                    visualizer.show_debate_message(agent_name, f"投票 {content}", "vote")
                
                # Call original broadcast
                return await original_broadcast(sender_id, content, event_type)
            
            battle_env._broadcast_message = enhanced_broadcast

    async def _generate_reports(self, stock_code: str, research_result: Dict[str, Any], battle_result: Dict[str, Any]):
        """Generate analysis reports with AI expert summaries"""
        try:
            visualizer.show_progress_update("生成分析报告", "创建专家总结和JSON数据...")
            
            # 导入新的报告生成器
            from src.utils.analysis_report_generator import AnalysisReportGenerator
            from src.llm import LLM
            
            # 获取LLM客户端
            llm_client = LLM()
            
            # 创建报告生成器
            report_generator = AnalysisReportGenerator(llm_client)
            
            # 生成完整的分析报告
            visualizer.show_progress_update("AI专家总结", "正在总结各专家观点...")
            analysis_report = await report_generator.generate_complete_report(
                stock_code=stock_code,
                research_results=research_result,
                battle_results=battle_result,
                start_time=self.start_time
            )
            
            # 获取原始股票数据（用于分离存储）
            visualizer.show_progress_update("获取股票数据", "收集原始股票信息...")
            raw_stock_data = await self._get_raw_stock_data(stock_code)
            
            # 保存分析报告
            visualizer.show_progress_update("保存分析报告", "写入文件系统...")
            file_paths = report_manager.save_analysis_report(
                stock_code=stock_code,
                analysis_report=analysis_report,
                raw_stock_data=raw_stock_data
            )
            
            # 显示保存结果
            folder_path = file_paths["folder_path"]
            self._report_dir = folder_path
            visualizer.show_progress_update("报告生成完成", f"文件夹: {folder_path}")
            
            logger.info(f"分析报告生成完成: {folder_path}")
            logger.info(f"- 主报告: {file_paths['main_report']}")
            if file_paths['raw_data']:
                logger.info(f"- 原始数据: {file_paths['raw_data']}")
            logger.info(f"- 元数据: {file_paths['metadata']}")
            
        except Exception as e:
            visualizer.show_error(f"生成报告失败: {str(e)}")
            logger.error(f"生成报告失败: {str(e)}")
    
    async def _get_raw_stock_data(self, stock_code: str) -> Dict[str, Any]:
        """获取原始股票数据"""
        try:
            from src.tool.stock_info_request import StockInfoRequest
            
            stock_info_tool = StockInfoRequest()
            raw_data = await stock_info_tool.execute(stock_code=stock_code)
            
            # 将 Pydantic model 转为 dict
            if hasattr(raw_data, 'model_dump'):
                raw_data = raw_data.model_dump()
            elif hasattr(raw_data, 'dict'):
                raw_data = raw_data.dict()
            
            # 添加获取时间戳
            raw_data_with_timestamp = {
                "stock_code": stock_code,
                "fetch_timestamp": datetime.now().isoformat(),
                "data": raw_data
            }
            
            return raw_data_with_timestamp
            
        except Exception as e:
            logger.error(f"获取原始股票数据失败 {stock_code}: {str(e)}")
            return {
                "stock_code": stock_code,
                "fetch_timestamp": datetime.now().isoformat(),
                "data": {"error": f"获取失败: {str(e)}"}
            }

    def _prepare_final_results(self, stock_code: str, research_results: Dict[str, Any], battle_results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare final analysis results"""
        final_results = {
            "stock_code": stock_code,
            "analysis_time": time.time() - self.start_time,
            "total_tool_calls": self.total_tool_calls,
            "total_llm_calls": self.total_llm_calls
        }
        
        # 添加报告目录路径
        if hasattr(self, "_report_dir") and self._report_dir:
            final_results["report_dir"] = self._report_dir
        
        # Merge research results
        if research_results:
            final_results.update(research_results)
        
        # Add battle insights
        if battle_results and "vote_count" in battle_results:
            votes = battle_results["vote_count"]
            total_votes = sum(votes.values())
            if total_votes > 0:
                bullish_pct = (votes.get("bullish", 0) / total_votes) * 100
                final_results["expert_consensus"] = f"{bullish_pct:.1f}% 看涨"
                final_results["battle_result"] = battle_results
        
        return final_results


async def announce_result_with_tts(results: Dict[str, Any]):
    """使用TTS工具播报最终的博弈结果"""
    try:
        battle_result = results.get("battle_result", {})
        final_decision = battle_result.get("final_decision", "Unknown")
        vote_count = battle_result.get("vote_count", {})
        stock_code = results.get("stock_code", "未知股票")

        if final_decision == "Unknown":
            tts_text = f"对{stock_code}的分析结果不明确，无法给出明确的建议。"
        else:
            bullish_count = vote_count.get("bullish", 0)
            bearish_count = vote_count.get("bearish", 0)

            if final_decision == "bullish":
                decision_text = "看涨"
            else:
                decision_text = "看跌"

            tts_text = f"股票{stock_code}的最终预测结果是{decision_text}。看涨票数{bullish_count}，看跌票数{bearish_count}。"

            # 添加一些关键战斗点
            if battle_result.get("battle_highlights"):
                tts_text += "关键分析点包括："
                for i, highlight in enumerate(
                    battle_result["battle_highlights"][:3]
                ):  # 只取前3个要点
                    agent = highlight.get("agent", "")
                    point = highlight.get("point", "")
                    tts_text += f"{agent}认为{point}。"

        # 初始化TTS工具并播报结果
        tts_tool = TTSTool()
        output_file = f"results/{stock_code}_result.mp3"

        # 执行TTS转换并播放
        await tts_tool.execute(text=tts_text, output_file=output_file)

        logger.info(f"结果语音播报已保存至: {output_file}")

    except Exception as e:
        logger.error(f"语音播报失败: {str(e)}")


def display_results(results: Dict[str, Any], output_format: str = "text", output_file: str | None = None):
    """Display or save research results."""
    # Handle JSON output
    if output_format == "json":
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    # For text output, results are already beautifully displayed during analysis
    # Just log completion
    if not output_file:
        return
    
    # Save to file if requested
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Stock Analysis Results for {results.get('stock_code', 'Unknown')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(json.dumps(results, indent=2, ensure_ascii=False))
    
    logger.info(f"Results saved to {output_file}")


async def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="FinGenius Stock Research")
    parser.add_argument("stock_code", help="Stock code to research (e.g., AAPL, MSFT)")
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("-o", "--output", help="Save results to file")
    parser.add_argument(
        "--tts", action="store_true", help="Enable text-to-speech for the final result"
    )
    parser.add_argument(
        "--max-steps", 
        type=int, 
        default=3, 
        help="Maximum number of steps for each agent (default: 3)"
    )
    parser.add_argument(
        "--debate-rounds", 
        type=int, 
        default=2, 
        help="Number of debate rounds in battle (default: 2)"
    )

    args = parser.parse_args()
    analyzer = None

    try:
        # Create enhanced analyzer
        analyzer = EnhancedFinGeniusAnalyzer()
        
        # Run analysis with beautiful visualization
        results = await analyzer.analyze_stock(args.stock_code, args.max_steps, args.debate_rounds)
        
        # Display results
        display_results(results, args.format, args.output)

        # TTS announcement if requested
        if args.tts:
            import os
            os.makedirs("results", exist_ok=True)
            await announce_result_with_tts(results)

    except KeyboardInterrupt:
        visualizer.show_error("分析被用户中断", "Ctrl+C")
        return 1
    except Exception as e:
        visualizer.show_error(f"分析过程中发生错误: {str(e)}")
        logger.error(f"Error during research: {str(e)}")
        return 1
    finally:
        # Clean up resources to prevent warnings
        if analyzer:
            try:
                # Force cleanup of any remaining async resources
                import gc
                gc.collect()
                
                # Give time for cleanup
                await asyncio.sleep(0.1)
            except:
                pass

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
