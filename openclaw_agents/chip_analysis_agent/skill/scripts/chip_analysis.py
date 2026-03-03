#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
筹码分析完整工具
6维度分析 + 交易信号生成
"""

import argparse
import json

import pandas as pd

from chip_data import get_chip_distribution, get_stock_spot_info


def _evaluate_control_level(concentration):
    if concentration < 10: return "低度控盘"
    elif concentration < 20: return "中度控盘"
    elif concentration < 30: return "高度控盘"
    else: return "极度控盘"


def _evaluate_trapped_depth(trapped_ratio):
    if trapped_ratio < 20: return "轻度套牢"
    elif trapped_ratio < 40: return "中度套牢"
    elif trapped_ratio < 60: return "重度套牢"
    else: return "深度套牢"


def _evaluate_selling_pressure(trapped_ratio):
    if trapped_ratio < 30: return "抛压较小"
    elif trapped_ratio < 60: return "抛压中等"
    else: return "抛压较大"


def basic_chip_analysis(df, current_price):
    """基础筹码分析"""
    avg_cost = current_price * 0.95 if current_price > 0 else 10.0
    profit_ratio = 50.0

    if isinstance(df, pd.DataFrame) and not df.empty:
        if '平均成本' in df.columns:
            avg_cost = df['平均成本'].iloc[-1]
        elif '价格' in df.columns and '筹码比例' in df.columns:
            total = df['筹码比例'].sum()
            if total > 0:
                avg_cost = (df['价格'] * df['筹码比例']).sum() / total

        if '获利比例' in df.columns:
            profit_ratio = df['获利比例'].iloc[-1]
        elif '价格' in df.columns and current_price > 0 and '筹码比例' in df.columns:
            prof_vol = df[df['价格'] < current_price]['筹码比例'].sum()
            total_vol = df['筹码比例'].sum()
            profit_ratio = (prof_vol / total_vol * 100) if total_vol > 0 else 50

    deviation = round((current_price - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 else 0
    return {"average_cost": round(avg_cost, 2), "profit_ratio": round(profit_ratio, 2), "cost_deviation": deviation}


def main_cost_analysis(df, current_price):
    """主力成本分析"""
    basic = basic_chip_analysis(df, current_price)
    avg_cost = basic["average_cost"]
    deviation = basic["cost_deviation"]
    concentration = 80.0
    if isinstance(df, pd.DataFrame) and '90%成本集中度' in df.columns and not df.empty:
        concentration = df['90%成本集中度'].iloc[-1]
    control = _evaluate_control_level(concentration)
    return {"main_cost_area": avg_cost, "cost_deviation_percent": deviation, "control_level": control}


def trapped_area_analysis(df, current_price):
    """套牢区分析"""
    basic = basic_chip_analysis(df, current_price)
    trapped_ratio = 100 - basic["profit_ratio"]
    depth = _evaluate_trapped_depth(trapped_ratio)
    pressure = _evaluate_selling_pressure(trapped_ratio)
    return {"trapped_ratio": round(trapped_ratio, 2), "trapped_depth": depth, "selling_pressure": pressure}


def generate_trading_signals(basic, main_cost, trapped):
    """生成交易信号"""
    signals = {"buy_signals": [], "sell_signals": [], "risk_warnings": []}

    if basic.get("profit_ratio", 0) < 20:
        signals["buy_signals"].append("底部筹码密集，获利盘极少")
    if -10 < main_cost.get("cost_deviation_percent", 0) < 5:
        signals["buy_signals"].append("价格回踩主力成本线")

    if basic.get("profit_ratio", 0) > 80:
        signals["sell_signals"].append("高位获利盘过多")
    if trapped.get("trapped_ratio", 0) < 10:
        signals["sell_signals"].append("套牢盘极少，主力可能派发")

    if basic.get("profit_ratio", 0) > 90:
        signals["risk_warnings"].append("获利盘过多，回调风险大")

    return signals


def full_chip_analysis(stock_code, adjust="", analysis_days=5):
    """完整筹码分析"""
    chip_data = get_chip_distribution(stock_code, adjust)
    stock_info = get_stock_spot_info(stock_code)
    current_price = stock_info.get("current_price", 0)

    df = pd.DataFrame(chip_data.get("chip_distribution", []))

    basic = basic_chip_analysis(df, current_price)
    main_cost = main_cost_analysis(df, current_price)
    trapped = trapped_area_analysis(df, current_price)
    signals = generate_trading_signals(basic, main_cost, trapped)

    return {
        "stock_code": stock_code,
        "stock_info": stock_info,
        "chip_data_source": chip_data.get("data_source"),
        "analysis": {
            "basic_analysis": basic,
            "main_cost_analysis": main_cost,
            "trapped_analysis": trapped,
            "trading_signals": signals,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="筹码分析")
    parser.add_argument("stock_code", type=str, help="股票代码")
    parser.add_argument("--adjust", type=str, default="")
    args = parser.parse_args()

    result = full_chip_analysis(args.stock_code, args.adjust)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
