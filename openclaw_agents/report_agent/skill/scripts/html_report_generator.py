#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML 分析报告生成器
将 analysis_report.json 渲染为美观的单文件 HTML 页面。
包含：股票详细信息、辩论流程、投票结果、每位分析师的最终结论。
"""

import json
import os
import sys
from datetime import datetime

# ── 专家类型 → 图标 / 颜色 映射 ──────────────────────────────
EXPERT_META = {
    "sentiment":     {"icon": "💬", "color": "#6366f1", "label": "市场情感分析师"},
    "risk":          {"icon": "🛡️", "color": "#ef4444", "label": "风险控制专家"},
    "hot_money":     {"icon": "🔥", "color": "#f97316", "label": "游资分析师"},
    "technical":     {"icon": "📈", "color": "#0ea5e9", "label": "技术分析师"},
    "chip_analysis": {"icon": "🧩", "color": "#8b5cf6", "label": "筹码分析师"},
    "big_deal":      {"icon": "🐋", "color": "#14b8a6", "label": "大单分析师"},
}


def _safe(text):
    """HTML 转义"""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "<br>")
    )


def _pct_bar(bullish_pct, bearish_pct):
    """生成投票占比条 HTML"""
    return f"""
    <div class="vote-bar-container">
        <div class="vote-bar-bullish" style="width:{bullish_pct}%">
            {bullish_pct}%
        </div>
        <div class="vote-bar-bearish" style="width:{bearish_pct}%">
            {bearish_pct}%
        </div>
    </div>"""


def generate_html(report_data):
    """
    根据报告 JSON 数据生成完整 HTML 字符串。

    Args:
        report_data: dict，与 AnalysisReport schema 一致的报告数据

    Returns:
        str: 完整 HTML 文本
    """
    # ── 提取数据 ──────────────────────────────────────────────
    stock = report_data.get("stock_info", {})
    experts = report_data.get("expert_summaries", {})
    voting = report_data.get("voting_results", {})
    debate = report_data.get("debate_summary", {})
    timestamp = report_data.get("timestamp", "")
    duration = report_data.get("analysis_duration", 0)

    stock_code = stock.get("stock_code", "未知")
    stock_name = stock.get("stock_name", "未知")
    industry = stock.get("industry", "未知")
    market_cap = stock.get("market_cap", "未知")
    pe = stock.get("pe_ratio", "未知")
    pb = stock.get("pb_ratio", "未知")
    roe = stock.get("roe", "未知")
    gm = stock.get("gross_margin", "未知")

    final_decision = voting.get("final_decision", "unknown")
    bullish_count = voting.get("bullish_count", 0)
    bearish_count = voting.get("bearish_count", 0)
    bullish_pct = voting.get("bullish_percentage", 0)
    bearish_pct = voting.get("bearish_percentage", 0)
    total_votes = voting.get("total_votes", 0)

    decision_cn = "看涨 (Bullish)" if final_decision == "bullish" else "看跌 (Bearish)" if final_decision == "bearish" else "未决"
    decision_class = "bullish" if final_decision == "bullish" else "bearish"

    # ── 格式化时间 ────────────────────────────────────────────
    try:
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        display_time = timestamp or "未知"

    duration_min = round(duration / 60, 1) if duration else "未知"

    # ── 辩论轮次 HTML ─────────────────────────────────────────
    rounds_html = ""
    rounds_detail = debate.get("rounds_detail", [])
    for rd in rounds_detail:
        round_num = rd.get("round_number", "?")
        speeches = rd.get("speeches", [])
        speeches_html = ""
        for sp in speeches:
            speaker = sp.get("speaker", "未知")
            agent_id = sp.get("agent_id", "")
            content = sp.get("content", "")
            # 找到对应的专家元信息
            meta = None
            for et, em in EXPERT_META.items():
                if et in agent_id:
                    meta = em
                    break
            icon = meta["icon"] if meta else "🗣️"
            color = meta["color"] if meta else "#64748b"
            speeches_html += f"""
            <div class="speech-card" style="border-left-color:{color}">
                <div class="speech-header">
                    <span class="speech-icon">{icon}</span>
                    <span class="speech-speaker" style="color:{color}">{_safe(speaker)}</span>
                </div>
                <div class="speech-content">{_safe(content)}</div>
            </div>"""
        rounds_html += f"""
        <div class="debate-round">
            <div class="round-badge">第 {round_num} 轮</div>
            {speeches_html}
        </div>"""

    # ── 共识与分歧 ────────────────────────────────────────────
    consensus = debate.get("consensus_points", [])
    divergent = debate.get("divergent_points", [])
    key_points = debate.get("key_debate_points", [])

    consensus_html = "".join(f'<li>{_safe(p)}</li>' for p in consensus) if consensus else "<li>暂无数据</li>"
    divergent_html = "".join(f'<li>{_safe(p)}</li>' for p in divergent) if divergent else "<li>暂无数据</li>"
    key_points_html = "".join(f'<li>{_safe(p)}</li>' for p in key_points) if key_points else "<li>暂无数据</li>"

    # ── 专家总结卡片 ──────────────────────────────────────────
    expert_cards_html = ""
    for expert_type, summary in experts.items():
        meta = EXPERT_META.get(expert_type, {"icon": "📊", "color": "#64748b", "label": expert_type})
        name = summary.get("expert_name", meta["label"])
        conclusion = summary.get("analysis_conclusion", "暂无结论")
        one_line = summary.get("one_sentence_summary", "")
        args_list = summary.get("key_arguments", [])
        tags = summary.get("key_tags", [])
        sources = summary.get("data_sources", [])

        args_html = "".join(f'<li>{_safe(a)}</li>' for a in args_list)
        tags_html = "".join(f'<span class="tag" style="background:{meta["color"]}22;color:{meta["color"]};border:1px solid {meta["color"]}44">{_safe(t)}</span>' for t in tags)
        sources_html = "".join(f'<span class="source-badge">{_safe(s)}</span>' for s in sources)

        expert_cards_html += f"""
        <div class="expert-card">
            <div class="expert-card-header" style="background:linear-gradient(135deg,{meta['color']}15,{meta['color']}05)">
                <div class="expert-avatar" style="background:{meta['color']}">{meta['icon']}</div>
                <div class="expert-title">
                    <h3>{_safe(name)}</h3>
                    <p class="expert-one-line">{_safe(one_line)}</p>
                </div>
            </div>
            <div class="expert-card-body">
                <div class="conclusion-section">
                    <h4>📋 分析结论</h4>
                    <p>{_safe(conclusion)}</p>
                </div>
                <div class="arguments-section">
                    <h4>🎯 关键论点</h4>
                    <ul>{args_html}</ul>
                </div>
                <div class="tags-row">
                    {tags_html}
                </div>
                <div class="sources-row">
                    <span class="sources-label">数据来源：</span>{sources_html}
                </div>
            </div>
        </div>"""

    # ── 最终 HTML ─────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_safe(stock_name)}({_safe(stock_code)}) - FinGenius 智能分析报告</title>
<style>
:root {{
    --bg: #0f172a;
    --bg-card: #1e293b;
    --bg-card-hover: #273548;
    --text: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #334155;
    --accent: #6366f1;
    --bullish: #22c55e;
    --bearish: #ef4444;
    --radius: 12px;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    min-height: 100vh;
}}

/* ── Header ── */
.header {{
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
    padding: 48px 0 36px;
    text-align: center;
    border-bottom: 1px solid var(--border);
    position: relative;
    overflow: hidden;
}}
.header::before {{
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(99,102,241,0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 50%, rgba(14,165,233,0.06) 0%, transparent 50%);
    animation: headerGlow 8s ease-in-out infinite alternate;
}}
@keyframes headerGlow {{
    0% {{ transform: translate(0, 0); }}
    100% {{ transform: translate(-5%, 5%); }}
}}
.header-content {{ position: relative; z-index: 1; }}
.header h1 {{
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 8px;
    background: linear-gradient(90deg, #c7d2fe, #e0e7ff, #a5b4fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.header .subtitle {{
    color: var(--text-secondary);
    font-size: 0.95rem;
}}
.header .meta-row {{
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 16px;
    flex-wrap: wrap;
}}
.header .meta-item {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 0.85rem;
    color: var(--text-secondary);
    backdrop-filter: blur(8px);
}}

/* ── Container ── */
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 24px;
}}

/* ── Section ── */
.section {{
    margin-bottom: 40px;
}}
.section-title {{
    font-size: 1.3rem;
    font-weight: 600;
    margin-bottom: 20px;
    padding-left: 14px;
    border-left: 4px solid var(--accent);
    display: flex;
    align-items: center;
    gap: 8px;
}}

/* ── Stock Info Grid ── */
.stock-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
}}
.stock-metric {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    transition: all 0.2s ease;
}}
.stock-metric:hover {{
    background: var(--bg-card-hover);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}}
.stock-metric .metric-label {{
    font-size: 0.8rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}}
.stock-metric .metric-value {{
    font-size: 1.5rem;
    font-weight: 700;
    color: #e0e7ff;
}}

/* ── Vote ── */
.vote-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 32px;
    text-align: center;
}}
.vote-decision {{
    font-size: 2rem;
    font-weight: 800;
    margin: 12px 0 24px;
    letter-spacing: 1px;
}}
.vote-decision.bullish {{ color: var(--bullish); }}
.vote-decision.bearish {{ color: var(--bearish); }}

.vote-stats {{
    display: flex;
    justify-content: center;
    gap: 48px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}}
.vote-stat {{
    text-align: center;
}}
.vote-stat .num {{
    font-size: 2.5rem;
    font-weight: 800;
    line-height: 1;
}}
.vote-stat .num.bullish {{ color: var(--bullish); }}
.vote-stat .num.bearish {{ color: var(--bearish); }}
.vote-stat .lbl {{
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-top: 4px;
}}

.vote-bar-container {{
    display: flex;
    width: 100%;
    height: 36px;
    border-radius: 18px;
    overflow: hidden;
    font-size: 0.85rem;
    font-weight: 600;
}}
.vote-bar-bullish {{
    background: linear-gradient(90deg, #16a34a, #22c55e);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    transition: width 0.8s ease;
}}
.vote-bar-bearish {{
    background: linear-gradient(90deg, #ef4444, #dc2626);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    transition: width 0.8s ease;
}}

/* ── Debate ── */
.debate-round {{
    margin-bottom: 28px;
}}
.round-badge {{
    display: inline-block;
    background: var(--accent);
    color: #fff;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 16px;
}}
.speech-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: background 0.2s;
}}
.speech-card:hover {{ background: var(--bg-card-hover); }}
.speech-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}}
.speech-icon {{ font-size: 1.3rem; }}
.speech-speaker {{
    font-weight: 600;
    font-size: 0.95rem;
}}
.speech-content {{
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.8;
}}

/* ── Insights ── */
.insights-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
}}
.insight-box {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
}}
.insight-box h4 {{
    font-size: 0.95rem;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.insight-box ul {{
    list-style: none;
    padding: 0;
}}
.insight-box li {{
    position: relative;
    padding-left: 18px;
    margin-bottom: 8px;
    font-size: 0.88rem;
    color: var(--text-secondary);
    line-height: 1.6;
}}
.insight-box li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 10px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
}}

/* ── Expert Cards ── */
.expert-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
    gap: 20px;
}}
.expert-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    transition: all 0.2s ease;
}}
.expert-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.3);
}}
.expert-card-header {{
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 14px;
}}
.expert-avatar {{
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    flex-shrink: 0;
}}
.expert-title h3 {{
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 2px;
}}
.expert-one-line {{
    font-size: 0.82rem;
    color: var(--text-muted);
}}
.expert-card-body {{
    padding: 0 20px 20px;
}}
.expert-card-body h4 {{
    font-size: 0.88rem;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--text);
}}
.conclusion-section {{
    margin-bottom: 16px;
}}
.conclusion-section p {{
    font-size: 0.88rem;
    color: var(--text-secondary);
    line-height: 1.8;
}}
.arguments-section {{
    margin-bottom: 14px;
}}
.arguments-section ul {{
    list-style: none;
    padding: 0;
}}
.arguments-section li {{
    position: relative;
    padding-left: 16px;
    margin-bottom: 6px;
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.6;
}}
.arguments-section li::before {{
    content: '▸';
    position: absolute;
    left: 0;
    color: var(--accent);
}}
.tags-row {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}}
.tag {{
    font-size: 0.75rem;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 500;
}}
.sources-row {{
    font-size: 0.78rem;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}}
.sources-label {{ font-weight: 500; }}
.source-badge {{
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
}}

/* ── Footer ── */
.footer {{
    text-align: center;
    padding: 32px;
    color: var(--text-muted);
    font-size: 0.8rem;
    border-top: 1px solid var(--border);
    margin-top: 48px;
}}
.footer a {{
    color: var(--accent);
    text-decoration: none;
}}

/* ── Responsive ── */
@media (max-width: 640px) {{
    .header h1 {{ font-size: 1.5rem; }}
    .expert-grid {{ grid-template-columns: 1fr; }}
    .insights-grid {{ grid-template-columns: 1fr; }}
    .vote-stats {{ gap: 24px; }}
    .stock-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* ── Collapse / Expand for debate rounds ── */
.debate-toggle {{
    background: none;
    border: 1px solid var(--border);
    color: var(--text-secondary);
    padding: 8px 18px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
    margin-bottom: 16px;
}}
.debate-toggle:hover {{
    background: var(--bg-card);
    color: var(--text);
}}
.debate-body {{ max-height: 0; overflow: hidden; transition: max-height 0.5s ease; }}
.debate-body.open {{ max-height: 100000px; }}
</style>
</head>
<body>

<!-- Header -->
<header class="header">
    <div class="header-content">
        <h1>📊 {_safe(stock_name)} ({_safe(stock_code)})</h1>
        <p class="subtitle">FinGenius 多智能体深度分析报告</p>
        <div class="meta-row">
            <span class="meta-item">🏭 行业：{_safe(industry)}</span>
            <span class="meta-item">🕐 分析时间：{_safe(display_time)}</span>
            <span class="meta-item">⏱️ 耗时：{duration_min} 分钟</span>
        </div>
    </div>
</header>

<div class="container">

    <!-- 股票基本面 -->
    <div class="section">
        <h2 class="section-title">📋 基本面数据</h2>
        <div class="stock-grid">
            <div class="stock-metric">
                <div class="metric-label">总市值</div>
                <div class="metric-value">{_safe(market_cap)}</div>
            </div>
            <div class="stock-metric">
                <div class="metric-label">市盈率 (PE)</div>
                <div class="metric-value">{_safe(pe)}</div>
            </div>
            <div class="stock-metric">
                <div class="metric-label">市净率 (PB)</div>
                <div class="metric-value">{_safe(pb)}</div>
            </div>
            <div class="stock-metric">
                <div class="metric-label">净资产收益率 (ROE)</div>
                <div class="metric-value">{_safe(roe)}</div>
            </div>
            <div class="stock-metric">
                <div class="metric-label">毛利率</div>
                <div class="metric-value">{_safe(gm)}</div>
            </div>
        </div>
    </div>

    <!-- 投票结果 -->
    <div class="section">
        <h2 class="section-title">🗳️ 投票结果</h2>
        <div class="vote-card">
            <p style="color:var(--text-muted);font-size:0.9rem;">最终决策</p>
            <div class="vote-decision {decision_class}">{decision_cn}</div>
            <div class="vote-stats">
                <div class="vote-stat">
                    <div class="num bullish">{bullish_count}</div>
                    <div class="lbl">看涨票数</div>
                </div>
                <div class="vote-stat">
                    <div class="num" style="color:var(--text);font-size:1.2rem;">/ {total_votes}</div>
                    <div class="lbl">总票数</div>
                </div>
                <div class="vote-stat">
                    <div class="num bearish">{bearish_count}</div>
                    <div class="lbl">看跌票数</div>
                </div>
            </div>
            {_pct_bar(bullish_pct, bearish_pct)}
        </div>
    </div>

    <!-- 专家分析结论 -->
    <div class="section">
        <h2 class="section-title">🧠 专家分析结论</h2>
        <div class="expert-grid">
            {expert_cards_html}
        </div>
    </div>

    <!-- 辩论流程 -->
    <div class="section">
        <h2 class="section-title">⚔️ 辩论流程</h2>
        <p style="color:var(--text-secondary);margin-bottom:12px;font-size:0.9rem;">
            共 {debate.get('total_rounds', 0)} 轮辩论，{debate.get('total_speeches', 0)} 次发言
        </p>
        <button class="debate-toggle" onclick="toggleDebate()">展开 / 收起辩论记录</button>
        <div class="debate-body" id="debateBody">
            {rounds_html if rounds_html else '<p style="color:var(--text-muted)">暂无辩论记录</p>'}
        </div>
    </div>

    <!-- 辩论洞察 -->
    <div class="section">
        <h2 class="section-title">💡 辩论洞察</h2>
        <div class="insights-grid">
            <div class="insight-box">
                <h4>✅ 共识观点</h4>
                <ul>{consensus_html}</ul>
            </div>
            <div class="insight-box">
                <h4>⚡ 分歧观点</h4>
                <ul>{divergent_html}</ul>
            </div>
            <div class="insight-box">
                <h4>🔑 关键辩论要点</h4>
                <ul>{key_points_html}</ul>
            </div>
        </div>
    </div>

</div>

<footer class="footer">
    <p>Powered by <strong>FinGenius</strong> 多智能体金融分析系统</p>
    <p style="margin-top:4px;">报告自动生成于 {_safe(display_time)} · 仅供参考，不构成投资建议</p>
</footer>

<script>
function toggleDebate() {{
    const body = document.getElementById('debateBody');
    body.classList.toggle('open');
}}
// 默认展开辩论记录
document.addEventListener('DOMContentLoaded', function() {{
    document.getElementById('debateBody').classList.add('open');
}});
</script>

</body>
</html>"""
    return html


def generate_html_report(report_data, output_path=None):
    """
    生成 HTML 报告文件。

    Args:
        report_data: dict，分析报告数据
        output_path: 可选输出路径，不指定则自动生成

    Returns:
        str: 输出文件路径
    """
    html = generate_html(report_data)

    if output_path is None:
        stock_code = report_data.get("stock_info", {}).get("stock_code", "unknown")
        timestamp = report_data.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs("report/html", exist_ok=True)
        output_path = f"report/html/report_{stock_code}_{timestamp}.html"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


# ── CLI ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="将 analysis_report.json 渲染为 HTML")
    parser.add_argument("report_json", help="分析报告 JSON 文件路径")
    parser.add_argument("-o", "--output", help="输出 HTML 文件路径（默认自动生成）")
    args = parser.parse_args()

    with open(args.report_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    path = generate_html_report(data, args.output)
    print(f"HTML 报告已生成: {path}")
