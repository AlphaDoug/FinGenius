"""
FinGenius 飞书机器人入口
支持两种运行模式：

模式一（推荐入门）：Webhook 模式
  - 在飞书群添加"自定义机器人"，获取 webhook 地址
  - 手动运行脚本触发分析，结果发送到群
  - 命令：python feishu_bot.py --mode webhook --stock 300624

模式二（推荐生产）：App 事件订阅模式
  - 在飞书开放平台创建企业应用，开启机器人能力
  - 使用长连接接收群消息，自动识别股票代码并分析
  - 命令：python feishu_bot.py --mode app

模式三：从缓存数据发送
  - 直接读取之前分析保存的 analysis_data JSON，无需重新分析
  - 命令：python feishu_bot.py --mode webhook --from-cache report/analysis_data/analysis_data_300624_20260214_121220.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
import threading
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.logger import logger
from src.config import config
from src.feishu.bot import FeishuWebhookBot, FeishuAppBot, parse_stock_code
from src.feishu.card_builder import (
    build_progress_card,
    build_result_card,
    build_report_cards,
    build_error_card,
    build_help_card,
)


# ─── 配置 ─────────────────────────────────────────────────────
# 优先使用 config.toml 中的配置，环境变量可覆盖

# Webhook 模式配置
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "") or config.feishu_config.webhook_url
FEISHU_WEBHOOK_SECRET = os.getenv("FEISHU_WEBHOOK_SECRET", "") or config.feishu_config.webhook_secret

# App 模式配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "") or config.feishu_config.app_id
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "") or config.feishu_config.app_secret

# 分析参数默认值
DEFAULT_MAX_STEPS = 3
DEFAULT_DEBATE_ROUNDS = 2


# ─── 分析任务管理 ──────────────────────────────────────────────

# 防止同一股票重复分析
_running_tasks: dict[str, bool] = {}


async def run_analysis(stock_code: str, max_steps: int = DEFAULT_MAX_STEPS,
                       debate_rounds: int = DEFAULT_DEBATE_ROUNDS) -> dict:
    """执行完整的股票分析流程，返回结果字典"""
    from main import EnhancedFinGeniusAnalyzer

    analyzer = EnhancedFinGeniusAnalyzer()
    result = await analyzer.analyze_stock(stock_code, max_steps, debate_rounds)
    return result


def load_analysis_from_cache(cache_path: str) -> dict:
    """从缓存的 JSON 文件加载分析数据
    
    支持：
    - 直接指定 JSON 文件路径
    - 指定分析结果目录（自动查找 analysis_report.json）
    """
    path = cache_path
    if os.path.isdir(path):
        report_file = os.path.join(path, "analysis_report.json")
        if os.path.exists(report_file):
            path = report_file
        else:
            raise FileNotFoundError(f"目录 {cache_path} 中未找到 analysis_report.json")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_cards_from_analysis_data(bot, analysis_data: dict, send_fn=None):
    """从 analysis_data 构建卡片并发送（通用，支持 Webhook 和 App 模式）
    
    自动识别两种数据格式：
    - 新格式(analysis_report.json): 包含 stock_info, expert_summaries, debate_summary 等
    - 旧格式(analysis_data.json): 包含 stock_code, research_results, battle_results 等
    """
    # 检测是否为 analysis_report.json 新格式
    if "stock_info" in analysis_data and "expert_summaries" in analysis_data:
        cards = build_report_cards(analysis_data)
    else:
        # 旧格式兼容
        stock_code = analysis_data.get("stock_code", "未知")
        research_results = analysis_data.get("research_results", {})
        battle_results = analysis_data.get("battle_results", {})

        conclusions = analysis_data.get("analysis_conclusions", {})
        if conclusions:
            for key, conclusion in conclusions.items():
                if conclusion and key in research_results:
                    research_results[key] = conclusion

        cards = build_result_card(stock_code, research_results, battle_results)

    for card in cards:
        if send_fn:
            send_fn(card)
        else:
            bot.send_interactive(card)
        time.sleep(0.5)


# ─── Webhook 模式 ──────────────────────────────────────────────

async def webhook_analyze_and_send(stock_code: str):
    """Webhook 模式：分析股票并将结果通过 webhook 发送到群"""
    bot = FeishuWebhookBot(FEISHU_WEBHOOK_URL, FEISHU_WEBHOOK_SECRET)

    # 发送开始分析通知
    progress_card = build_progress_card(stock_code, "🚀 开始分析", "正在启动多智能体研究...")
    bot.send_interactive(progress_card)

    try:
        start_time = time.time()

        # 发送研究阶段通知
        bot.send_interactive(
            build_progress_card(stock_code, "🔍 研究阶段", "6位专家正在独立研究分析...")
        )

        result = await run_analysis(stock_code)

        if "error" in result:
            bot.send_interactive(build_error_card(stock_code, result["error"]))
            return

        analysis_time = time.time() - start_time

        # 提取数据
        research_results = {}
        for key in ("sentiment", "risk", "hot_money", "technical", "chip_analysis", "big_deal"):
            if key in result:
                research_results[key] = result[key]

        battle_results = result.get("battle_result", {})

        # 构建并发送结果卡片
        cards = build_result_card(stock_code, research_results, battle_results, analysis_time)
        for card in cards:
            bot.send_interactive(card)
            time.sleep(0.5)  # 避免发送过快被限流

        logger.info(f"飞书 Webhook 发送完成: {stock_code}")

    except Exception as e:
        logger.error(f"分析失败: {e}")
        bot.send_interactive(build_error_card(stock_code, str(e)))


# ─── App 事件订阅模式 ──────────────────────────────────────────

def start_app_bot():
    """
    App 模式：使用 lark-oapi SDK 长连接接收群消息。
    需要安装: pip install lark-oapi
    
    飞书开放平台配置步骤：
    1. 创建企业应用 → 获取 App ID 和 App Secret
    2. 添加"机器人"能力
    3. 订阅事件：im.message.receive_v1
    4. 添加权限：im:message、im:message:send_as_bot
    5. 发布应用版本并审批通过
    6. 将机器人添加到目标群
    """
    try:
        import lark_oapi as lark
        from lark_oapi.api.im.v1 import P2ImMessageReceiveV1
    except ImportError:
        logger.error(
            "App 模式需要安装 lark-oapi: pip install lark-oapi\n"
            "如果你只需要发送消息，请使用 --mode webhook"
        )
        sys.exit(1)

    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        logger.error("请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量")
        sys.exit(1)

    app_bot = FeishuAppBot(FEISHU_APP_ID, FEISHU_APP_SECRET)

    def handle_message(data: P2ImMessageReceiveV1) -> None:
        """处理接收到的消息"""
        try:
            event = data.event
            msg = event.message
            msg_type = msg.message_type
            chat_id = msg.chat_id
            message_id = msg.message_id

            # 只处理文本消息
            if msg_type != "text":
                return

            content = json.loads(msg.content)
            text = content.get("text", "").strip()

            # 去掉 @机器人 的部分
            text = text.replace("@_user_1", "").strip()

            logger.info(f"收到飞书消息: [{chat_id}] {text}")

            # 帮助命令
            if text.lower() in ("帮助", "help", "?", "？"):
                app_bot.reply_interactive(message_id, build_help_card())
                return

            # 解析股票代码
            stock_code = parse_stock_code(text)
            if not stock_code:
                app_bot.reply_interactive(message_id, build_help_card())
                return

            # 检查是否已在分析
            if _running_tasks.get(stock_code):
                app_bot.send_text(chat_id, f"⏳ 股票 {stock_code} 正在分析中，请稍候...")
                return

            _running_tasks[stock_code] = True

            # 发送开始通知
            app_bot.send_interactive(
                chat_id,
                build_progress_card(stock_code, "🚀 开始分析", "正在启动多智能体研究...")
            )

            # 在后台线程中执行分析（因为分析是 async 且耗时较长）
            def background_analyze():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    start_time = time.time()

                    # 阶段通知
                    app_bot.send_interactive(
                        chat_id,
                        build_progress_card(stock_code, "🔍 研究阶段", "6位专家正在独立研究分析...")
                    )

                    result = loop.run_until_complete(run_analysis(stock_code))

                    if "error" in result:
                        app_bot.send_interactive(chat_id, build_error_card(stock_code, result["error"]))
                        return

                    # 尝试加载新格式的 analysis_report.json
                    report_dir = result.get("report_dir", "")
                    report_data = None
                    if report_dir:
                        report_file = os.path.join(report_dir, "analysis_report.json")
                        if os.path.exists(report_file):
                            try:
                                with open(report_file, "r", encoding="utf-8") as f:
                                    report_data = json.load(f)
                            except Exception as e:
                                logger.warning(f"加载 analysis_report.json 失败，回退旧格式: {e}")

                    if report_data:
                        # 新格式：使用 build_report_cards
                        cards = build_report_cards(report_data)
                    else:
                        # 旧格式兼容
                        analysis_time = time.time() - start_time
                        research_results = {}
                        for key in ("sentiment", "risk", "hot_money", "technical", "chip_analysis", "big_deal"):
                            if key in result:
                                research_results[key] = result[key]
                        battle_results = result.get("battle_result", {})
                        cards = build_result_card(stock_code, research_results, battle_results, analysis_time)

                    for card in cards:
                        app_bot.send_interactive(chat_id, card)
                        time.sleep(0.5)

                    logger.info(f"飞书 App 分析发送完成: {stock_code}")

                except Exception as e:
                    logger.error(f"后台分析失败: {e}")
                    app_bot.send_interactive(chat_id, build_error_card(stock_code, str(e)))
                finally:
                    _running_tasks.pop(stock_code, None)
                    loop.close()

            thread = threading.Thread(target=background_analyze, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"处理飞书消息异常: {e}")

    # 构建事件处理器
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(handle_message)
        .build()
    )

    # 使用长连接（WebSocket）模式 —— 无需公网地址
    cli = (
        lark.ws.Client(FEISHU_APP_ID, FEISHU_APP_SECRET,
                       event_handler=event_handler,
                       log_level=lark.LogLevel.INFO)
    )

    logger.info("飞书 App 机器人已启动（长连接模式），等待群消息...")
    cli.start()


# ─── CLI 入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FinGenius 飞书机器人",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # Webhook 模式 - 手动触发分析
  python feishu_bot.py --mode webhook --stock 300624

  # App 模式 - 自动监听群消息
  python feishu_bot.py --mode app

环境变量:
  FEISHU_WEBHOOK_URL     群自定义机器人 Webhook 地址
  FEISHU_WEBHOOK_SECRET  Webhook 签名密钥（可选）
  FEISHU_APP_ID          企业应用 App ID
  FEISHU_APP_SECRET      企业应用 App Secret
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["webhook", "app"],
        default="webhook",
        help="运行模式: webhook(仅发送) / app(收发消息，推荐) (默认: webhook)",
    )
    parser.add_argument(
        "--stock",
        type=str,
        default="",
        help="[webhook模式] 要分析的股票代码 (如 300624)",
    )
    parser.add_argument(
        "--from-cache",
        type=str,
        default="",
        help="[webhook模式] 从缓存的 JSON 文件发送，跳过分析。支持: analysis_report.json 文件路径 或 分析结果目录路径",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        help=f"每个 Agent 最大步数 (默认: {DEFAULT_MAX_STEPS})",
    )
    parser.add_argument(
        "--debate-rounds",
        type=int,
        default=DEFAULT_DEBATE_ROUNDS,
        help=f"辩论轮数 (默认: {DEFAULT_DEBATE_ROUNDS})",
    )

    args = parser.parse_args()

    if args.mode == "webhook":
        if not FEISHU_WEBHOOK_URL:
            print("错误: 飞书 Webhook URL 未配置")
            print("配置方式（二选一）：")
            print("  1. 在 config/config.toml 的 [feishu] 节中设置 webhook_url")
            print("  2. 设置环境变量 FEISHU_WEBHOOK_URL")
            print("获取方式: 飞书群 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人 → 复制 webhook 地址")
            sys.exit(1)

        if args.from_cache:
            # 从缓存文件直接发送
            bot = FeishuWebhookBot(FEISHU_WEBHOOK_URL, FEISHU_WEBHOOK_SECRET)
            analysis_data = load_analysis_from_cache(args.from_cache)
            send_cards_from_analysis_data(bot, analysis_data)
            print(f"已从缓存文件发送: {args.from_cache}")
        elif args.stock:
            asyncio.run(webhook_analyze_and_send(args.stock))
        else:
            print("错误: webhook 模式需要指定 --stock 或 --from-cache 参数")
            sys.exit(1)

    elif args.mode == "app":
        start_app_bot()


if __name__ == "__main__":
    main()
