"""
飞书消息卡片构建器
将 FinGenius 分析结果构建为飞书 Interactive Card JSON，
尽量还原 HTML 报告中的信息和排版。
"""

from typing import Any, Dict, List
from src.feishu.bot import get_agent_display_name


def _md_section(content: str) -> dict:
    """一个 Markdown 富文本块"""
    return {"tag": "div", "text": {"tag": "lark_md", "content": content}}


def _hr() -> dict:
    return {"tag": "hr"}


def _header(title: str, template: str = "blue") -> dict:
    return {
        "title": {"tag": "plain_text", "content": title},
        "template": template,
    }


# ─── 公开 API ───────────────────────────────────────────────


def build_progress_card(stock_code: str, stage: str, detail: str = "") -> dict:
    """构建进度通知卡片"""
    elements = [
        _md_section(f"**股票代码：** {stock_code}"),
        _md_section(f"**当前阶段：** {stage}"),
    ]
    if detail:
        elements.append(_md_section(detail))

    return {
        "header": _header(f"⏳ FinGenius 分析进行中", "orange"),
        "elements": elements,
    }


def build_result_card(
    stock_code: str,
    research_results: Dict[str, Any],
    battle_results: Dict[str, Any],
    analysis_time: float = 0,
) -> List[dict]:
    """
    构建完整分析结果卡片。
    由于飞书单张卡片有字数限制(~30000字符)，拆分为多张卡片：
      1. 概览 + 投票结果
      2. 各维度分析结论
      3. 辩论过程（可能拆为多张）
    返回卡片列表。
    """
    cards: List[dict] = []

    # ────── 卡片 1：概览 + 投票 ──────
    vote_count = battle_results.get("vote_count", {})
    bull = vote_count.get("bullish", 0)
    bear = vote_count.get("bearish", 0)
    total = bull + bear
    bull_pct = round(bull / total * 100, 1) if total else 0
    bear_pct = round(bear / total * 100, 1) if total else 0
    decision = battle_results.get("final_decision", "unknown")
    decision_text = "📈 看涨" if decision == "bullish" else "📉 看跌" if decision == "bearish" else "❓ 未定"
    decision_color = "green" if decision == "bullish" else "red" if decision == "bearish" else "grey"

    overview_elements = [
        _md_section(f"**股票代码：** {stock_code}"),
        _hr(),
        _md_section(f"## 🗳️ 投票结果\n\n"
                    f"**最终结论：{decision_text}**\n\n"
                    f"- 📈 看涨：**{bull}** 票 ({bull_pct}%)\n"
                    f"- 📉 看跌：**{bear}** 票 ({bear_pct}%)\n"
                    f"- 参与专家：**{total}** 位"),
    ]

    if analysis_time > 0:
        minutes = int(analysis_time // 60)
        seconds = int(analysis_time % 60)
        overview_elements.append(
            _md_section(f"⏱️ 分析耗时：{minutes}分{seconds}秒")
        )

    header_tpl = "green" if decision == "bullish" else "red" if decision == "bearish" else "blue"
    cards.append({
        "header": _header(f"FinGenius 股票分析报告 - {stock_code}", header_tpl),
        "elements": overview_elements,
    })

    # ────── 卡片 2：各维度分析 ──────
    analysis_map = {
        "sentiment": ("🧠", "市场情绪分析"),
        "risk": ("🛡️", "风险控制分析"),
        "hot_money": ("💰", "游资动向分析"),
        "technical": ("📈", "技术面分析"),
        "chip_analysis": ("🔍", "筹码分析"),
        "big_deal": ("💹", "大单异动分析"),
    }

    analysis_elements = []
    for key, (icon, title) in analysis_map.items():
        content = research_results.get(key, "")
        if not content:
            continue
        # 截断过长内容（飞书卡片单块上限）
        text = str(content)
        if len(text) > 1500:
            text = text[:1500] + "\n\n... (内容过长，已截断)"
        analysis_elements.append(_md_section(f"## {icon} {title}\n\n{text}"))
        analysis_elements.append(_hr())

    if analysis_elements:
        # 移除最后的分隔线
        analysis_elements.pop()
        cards.append({
            "header": _header(f"📊 分析详情 - {stock_code}", "blue"),
            "elements": analysis_elements,
        })

    # ────── 卡片 3+：辩论过程 ──────
    debate_history = battle_results.get("debate_history", [])
    if not debate_history:
        # 尝试嵌套路径
        debate_history = battle_results.get("battle_results", {}).get("debate_history", [])

    if debate_history:
        debate_cards = _build_debate_cards(stock_code, debate_history)
        cards.extend(debate_cards)

    # ────── 免责声明 ──────
    cards.append({
        "header": _header("⚠️ 免责声明", "grey"),
        "elements": [
            _md_section(
                "本报告由 **FinGenius AI 多智能体系统**自动生成，仅供参考，不构成任何投资建议。"
                "投资有风险，入市需谨慎。请结合自身情况和专业顾问意见做出投资决策。"
            ),
        ],
    })

    return cards


def _build_debate_cards(stock_code: str, debate_history: list) -> List[dict]:
    """将辩论历史拆分为多张卡片（每轮一张）"""
    cards = []

    # 按轮次分组
    rounds: Dict[int, list] = {}
    for item in debate_history:
        r = item.get("round", 1)
        rounds.setdefault(r, []).append(item)

    for round_num in sorted(rounds.keys()):
        items = rounds[round_num]
        elements = []

        for item in items:
            speaker = get_agent_display_name(item.get("speaker", "未知"))
            content = item.get("content", "无内容")
            timestamp = item.get("timestamp", "")

            # 截断过长发言
            if len(content) > 1000:
                content = content[:1000] + "\n\n... (发言过长，已截断)"

            block = (
                f"**🎤 {speaker}**"
                f"{'　　⏰ ' + timestamp if timestamp else ''}\n\n"
                f"{content}"
            )
            elements.append(_md_section(block))
            elements.append(_hr())

        if elements:
            elements.pop()  # 移除末尾分隔线

        cards.append({
            "header": _header(f"⚔️ 辩论过程 - 第{round_num}轮 ({stock_code})", "purple"),
            "elements": elements,
        })

    return cards


def build_report_cards(report_data: dict) -> List[dict]:
    """
    从 analysis_report.json 格式构建飞书卡片列表。
    返回三张卡片：
      1. 股票详细信息 + 投票结果
      2. 六位专家最终结论
      3+. 两轮辩论流程（每轮一张）
    """
    cards: List[dict] = []
    stock_info = report_data.get("stock_info", {})
    stock_code = stock_info.get("stock_code", "未知")
    stock_name = stock_info.get("stock_name", "未知")
    voting = report_data.get("voting_results", {})
    debate = report_data.get("debate_summary", {})
    expert_summaries = report_data.get("expert_summaries", {})
    duration = report_data.get("analysis_duration", 0)

    # ────── 卡片 1：股票详细信息 + 投票结果 ──────
    decision = voting.get("final_decision", "unknown")
    decision_text = "📈 看涨" if decision == "bullish" else "📉 看跌" if decision == "bearish" else "❓ 未定"
    header_tpl = "green" if decision == "bullish" else "red" if decision == "bearish" else "blue"
    bull = voting.get("bullish_count", 0)
    bear = voting.get("bearish_count", 0)
    total = voting.get("total_votes", 0)
    bull_pct = voting.get("bullish_percentage", 0)
    bear_pct = voting.get("bearish_percentage", 0)

    # 格式化市值
    market_cap_raw = stock_info.get("market_cap", "未知")
    try:
        mc = float(market_cap_raw)
        if mc >= 1e12:
            market_cap_str = f"{mc / 1e12:.2f} 万亿"
        elif mc >= 1e8:
            market_cap_str = f"{mc / 1e8:.2f} 亿"
        else:
            market_cap_str = f"{mc:.0f}"
    except (ValueError, TypeError):
        market_cap_str = str(market_cap_raw)

    # 格式化毛利率
    gm_raw = stock_info.get("gross_margin", "未知")
    try:
        gm_str = f"{float(gm_raw):.2f}%"
    except (ValueError, TypeError):
        gm_str = str(gm_raw)

    stock_detail_md = (
        f"## 📋 股票基本信息\n\n"
        f"| 指标 | 数值 |\n"
        f"|:---|:---|\n"
        f"| **股票代码** | {stock_code} |\n"
        f"| **股票名称** | {stock_name} |\n"
        f"| **所属行业** | {stock_info.get('industry', '未知')} |\n"
        f"| **总市值** | {market_cap_str} |\n"
        f"| **市盈率(PE)** | {stock_info.get('pe_ratio', '未知')} |\n"
        f"| **市净率(PB)** | {stock_info.get('pb_ratio', '未知')} |\n"
        f"| **ROE** | {stock_info.get('roe', '未知')}% |\n"
        f"| **毛利率** | {gm_str} |"
    )

    vote_md = (
        f"## 🗳️ 投票结果\n\n"
        f"**最终结论：{decision_text}**\n\n"
        f"- 📈 看涨：**{bull}** 票 ({bull_pct}%)\n"
        f"- 📉 看跌：**{bear}** 票 ({bear_pct}%)\n"
        f"- 参与专家：**{total}** 位"
    )

    info_elements = [_md_section(stock_detail_md), _hr(), _md_section(vote_md)]
    if duration > 0:
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        info_elements.append(_md_section(f"⏱️ 分析耗时：{minutes}分{seconds}秒"))

    cards.append({
        "header": _header(f"FinGenius 分析报告 - {stock_name}({stock_code})", header_tpl),
        "elements": info_elements,
    })

    # ────── 卡片 2：六位专家最终结论 ──────
    expert_order = ["sentiment", "risk", "hot_money", "technical", "chip_analysis", "big_deal"]
    expert_icons = {
        "sentiment": "🧠", "risk": "🛡️", "hot_money": "💰",
        "technical": "📈", "chip_analysis": "🔍", "big_deal": "💹",
    }

    expert_elements = []
    for etype in expert_order:
        summary = expert_summaries.get(etype)
        if not summary:
            continue
        icon = expert_icons.get(etype, "📌")
        name = summary.get("expert_name", etype)
        one_line = summary.get("one_sentence_summary", "")
        conclusion = summary.get("analysis_conclusion", "")
        tags = summary.get("key_tags", [])
        arguments = summary.get("key_arguments", [])

        tags_str = "  ".join([f"`{t}`" for t in tags]) if tags else ""

        args_str = ""
        if arguments:
            args_str = "\n".join([f"  - {a}" for a in arguments])

        block = f"## {icon} {name}\n\n"
        if one_line:
            block += f"**💡 {one_line}**\n\n"
        if tags_str:
            block += f"{tags_str}\n\n"
        if args_str:
            block += f"**核心论据：**\n{args_str}\n\n"
        # 完整结论截断
        if conclusion:
            if len(conclusion) > 800:
                conclusion = conclusion[:800] + "..."
            block += f"**详细结论：**\n{conclusion}"

        expert_elements.append(_md_section(block))
        expert_elements.append(_hr())

    if expert_elements:
        expert_elements.pop()
    cards.append({
        "header": _header(f"🎓 六位专家结论 - {stock_name}({stock_code})", "blue"),
        "elements": expert_elements,
    })

    # ────── 卡片 3+：辩论流程（按轮次） ──────
    rounds_detail = debate.get("rounds_detail", [])
    if rounds_detail:
        for round_info in rounds_detail:
            round_num = round_info.get("round_number", 0)
            speeches = round_info.get("speeches", [])
            elements = []
            for sp in speeches:
                speaker = get_agent_display_name(sp.get("speaker", "") or sp.get("agent_id", "未知"))
                content = sp.get("content", "无内容")
                timestamp = sp.get("timestamp", "")

                if len(content) > 1000:
                    content = content[:1000] + "\n\n... (发言过长，已截断)"

                block = (
                    f"**🎤 {speaker}**"
                    f"{'　　⏰ ' + timestamp if timestamp else ''}\n\n"
                    f"{content}"
                )
                elements.append(_md_section(block))
                elements.append(_hr())

            if elements:
                elements.pop()

            cards.append({
                "header": _header(f"⚔️ 辩论过程 - 第{round_num}轮 ({stock_name})", "purple"),
                "elements": elements,
            })
    else:
        # fallback: 用 key_debate_points
        key_points = debate.get("key_debate_points", [])
        if key_points:
            elements = []
            for i, point in enumerate(key_points, 1):
                text = point if len(point) <= 1000 else point[:1000] + "\n\n... (已截断)"
                elements.append(_md_section(f"**发言 {i}：**\n\n{text}"))
                elements.append(_hr())
            if elements:
                elements.pop()
            cards.append({
                "header": _header(f"⚔️ 辩论要点 ({stock_name})", "purple"),
                "elements": elements,
            })

    # ────── 共识与分歧 ──────
    consensus = debate.get("consensus_points", [])
    divergent = debate.get("divergent_points", [])
    if consensus or divergent:
        summary_elements = []
        if consensus:
            consensus_md = "## ✅ 共识观点\n\n" + "\n".join([f"- {c}" for c in consensus])
            summary_elements.append(_md_section(consensus_md))
        if divergent:
            divergent_md = "## ⚡ 分歧观点\n\n" + "\n".join([f"- {d}" for d in divergent])
            summary_elements.append(_md_section(divergent_md))
        cards.append({
            "header": _header(f"📝 辩论总结 - {stock_name}({stock_code})", "indigo"),
            "elements": summary_elements,
        })

    # ────── 免责声明 ──────
    cards.append({
        "header": _header("⚠️ 免责声明", "grey"),
        "elements": [
            _md_section(
                "本报告由 **FinGenius AI 多智能体系统**自动生成，仅供参考，不构成任何投资建议。"
                "投资有风险，入市需谨慎。请结合自身情况和专业顾问意见做出投资决策。"
            ),
        ],
    })

    return cards


def build_error_card(stock_code: str, error_msg: str) -> dict:
    """构建错误通知卡片"""
    return {
        "header": _header("❌ 分析失败", "red"),
        "elements": [
            _md_section(f"**股票代码：** {stock_code}"),
            _md_section(f"**错误信息：** {error_msg}"),
            _md_section("请检查股票代码是否正确，或稍后重试。"),
        ],
    }


def build_help_card() -> dict:
    """构建帮助信息卡片"""
    return {
        "header": _header("📖 FinGenius 使用帮助", "blue"),
        "elements": [
            _md_section(
                "发送 **6位股票代码** 即可开始分析，例如：\n\n"
                "- `600519` — 贵州茅台\n"
                "- `300624` — 万兴科技\n"
                "- `000001` — 平安银行\n\n"
                "**其他命令：**\n"
                "- `帮助` / `help` — 显示本帮助\n"
            ),
        ],
    }
