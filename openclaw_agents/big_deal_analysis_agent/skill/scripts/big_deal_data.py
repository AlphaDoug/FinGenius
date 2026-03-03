#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大单资金流向分析工具
数据源降级：akshare → tushare(moneyflow/block_trade/daily, 2000积分)
"""

import argparse
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None

import os as _os

# tushare保底
try:
    import tushare as ts
except ImportError:
    ts = None

_pro = None

def _init_tushare(token=None):
    """初始化tushare，token优先级：参数 > 环境变量"""
    global _pro
    t = token or _os.environ.get("TUSHARE_TOKEN", "")
    if t and ts is not None:
        ts.set_token(t)
        _pro = ts.pro_api()
    return _pro is not None


def _to_ts_code(stock_code):
    """将6位股票代码转为tushare格式"""
    c = stock_code.lstrip("shsz")
    return f"{c}.SH" if c.startswith("6") else f"{c}.SZ"


def _safe_fetch(func, *args, max_retry=3, sleep_seconds=1, **kwargs):
    """带重试的安全数据获取"""
    for attempt in range(1, max_retry + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt >= max_retry:
                print(f"{func.__name__}失败: {e}")
                return None
            time.sleep(sleep_seconds)


def _to_float(series):
    """清洗字符串格式的数值列"""
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("亿", "e8").str.replace("万", "e4")
        .str.extract(r"([\d\.-eE]+)")[0]
        .astype(float)
    )


def get_big_deal_analysis(stock_code: str = "", top_n: int = 10,
                          rank_symbol: str = "即时", max_retry: int = 3) -> Dict[str, Any]:
    """
    大单资金流向分析

    Args:
        stock_code: 股票代码，空则仅全市场分析
        top_n: 排行前N名
        rank_symbol: 排行窗口 '即时'|'3日排行'|'5日排行'|'10日排行'|'20日排行'
        max_retry: 最大重试次数

    Returns:
        dict: 分析结果
    """
    if ak is None:
        return {"error": "未安装akshare库"}

    result = {}

    # 1. 市场逐笔大单
    df_bd = _safe_fetch(ak.stock_fund_flow_big_deal, max_retry=max_retry)
    if df_bd is not None and not df_bd.empty:
        if df_bd["成交额"].dtype == "O":
            df_bd["成交额"] = _to_float(df_bd["成交额"])

        inflow = df_bd[df_bd["大单性质"] == "买盘"]["成交额"].sum()
        outflow = df_bd[df_bd["大单性质"] == "卖盘"]["成交额"].sum()
        result["market_summary"] = {
            "total_inflow_wan": round(inflow, 2),
            "total_outflow_wan": round(outflow, 2),
            "net_inflow_wan": round(inflow - outflow, 2),
        }

        grouped = df_bd.groupby(["股票代码", "股票简称", "大单性质"])["成交额"].sum().reset_index()
        buy_df = grouped[grouped["大单性质"] == "买盘"].sort_values("成交额", ascending=False)
        sell_df = grouped[grouped["大单性质"] == "卖盘"].sort_values("成交额", ascending=False)
        result["top_inflow"] = buy_df.head(top_n).to_dict(orient="records")
        result["top_outflow"] = sell_df.head(top_n).to_dict(orient="records")
        result["market_big_deal_samples"] = df_bd.head(top_n).to_dict(orient="records")
    else:
        result["market_big_deal_samples"] = []

    # 2. 个股资金排行
    individual_rank = _safe_fetch(ak.stock_fund_flow_individual, symbol=rank_symbol, max_retry=max_retry)
    result["individual_rank_top"] = (
        individual_rank.head(top_n).to_dict(orient="records")
        if individual_rank is not None else []
    )

    if stock_code and individual_rank is not None:
        filtered = individual_rank[individual_rank["股票代码"].astype(str) == stock_code]
        result["individual_rank_stock"] = filtered.to_dict(orient="records") if not filtered.empty else []

    # 3. 个股专项分析
    if stock_code:
        # 资金流趋势
        flow = _safe_fetch(ak.stock_individual_fund_flow, stock=stock_code, market="sh" if stock_code.startswith("6") else "sz", max_retry=max_retry)
        result["stock_fund_flow"] = flow.to_dict(orient="records") if flow is not None else []

        # 历史行情
        hist = _safe_fetch(ak.stock_zh_a_hist, symbol=stock_code, period="daily", max_retry=max_retry)
        if hist is not None:
            result["stock_price_hist"] = hist.tail(120).to_dict(orient="records")
        else:
            result["stock_price_hist"] = []

        # 个股大单明细
        if df_bd is not None and not df_bd.empty:
            stk_df = df_bd[df_bd["股票代码"] == stock_code]
            if not stk_df.empty:
                inflow = stk_df[stk_df["大单性质"] == "买盘"]["成交额"].sum()
                outflow = stk_df[stk_df["大单性质"] == "卖盘"]["成交额"].sum()
                result["stock_big_deal_summary"] = {
                    "inflow_wan": round(inflow, 2), "outflow_wan": round(outflow, 2),
                    "net_inflow_wan": round(inflow - outflow, 2), "trade_count": len(stk_df),
                }
                result["stock_big_deal_samples"] = stk_df.head(top_n).to_dict(orient="records")
            else:
                result["stock_big_deal_summary"] = {}
                result["stock_big_deal_samples"] = []

    return result


def _tushare_big_deal_fallback(stock_code="", top_n=10):
    """tushare保底：用moneyflow(个股资金流向) + block_trade(大宗交易)"""
    if _pro is None:
        _init_tushare()
    if _pro is None:
        return None
    result = {"数据来源": "tushare"}
    today = datetime.now().strftime("%Y%m%d")

    # 1. 个股资金流向 moneyflow
    if stock_code:
        try:
            ts_code = _to_ts_code(stock_code)
            df = _pro.moneyflow(ts_code=ts_code)
            if isinstance(df, pd.DataFrame) and not df.empty:
                recent = df.head(5)
                row = recent.iloc[0]
                result["stock_fund_flow"] = recent.to_dict(orient="records")
                result["stock_big_deal_summary"] = {
                    "buy_lg_amount(万)": float(row.get("buy_lg_amount", 0) or 0),
                    "sell_lg_amount(万)": float(row.get("sell_lg_amount", 0) or 0),
                    "net_mf_amount(万)": float(row.get("net_mf_amount", 0) or 0),
                }
        except Exception as e:
            print(f"tushare moneyflow失败: {e}")

    # 2. 大宗交易 block_trade
    try:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        if stock_code:
            ts_code = _to_ts_code(stock_code)
            df = _pro.block_trade(ts_code=ts_code, start_date=start_date, end_date=today)
        else:
            df = _pro.block_trade(start_date=start_date, end_date=today)
        if isinstance(df, pd.DataFrame) and not df.empty:
            result["block_trade_top"] = df.head(top_n).to_dict(orient="records")
    except Exception as e:
        print(f"tushare block_trade失败: {e}")

    # 3. 全市场资金流向排行（用daily获取近期涨幅代替）
    if not stock_code:
        try:
            df = _pro.moneyflow(trade_date=today)
            if isinstance(df, pd.DataFrame) and not df.empty:
                df["net_amount"] = df["buy_lg_amount"].fillna(0) - df["sell_lg_amount"].fillna(0)
                top_in = df.nlargest(top_n, "net_amount")
                top_out = df.nsmallest(top_n, "net_amount")
                result["top_inflow"] = top_in.to_dict(orient="records")
                result["top_outflow"] = top_out.to_dict(orient="records")
        except Exception as e:
            print(f"tushare全市场moneyflow失败: {e}")

    return result if len(result) > 1 else None


def get_big_deal_analysis_with_fallback(stock_code="", top_n=10,
                                        rank_symbol="即时", max_retry=3):
    """大单资金分析（akshare → tushare保底）"""
    result = get_big_deal_analysis(stock_code, top_n, rank_symbol, max_retry)

    # 检查akshare是否获取到有效数据
    has_data = (result.get("market_big_deal_samples") or
                result.get("individual_rank_top") or
                result.get("stock_fund_flow"))
    if has_data and "error" not in result:
        return result

    # tushare保底
    fallback = _tushare_big_deal_fallback(stock_code, top_n)
    if fallback:
        return fallback

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="大单资金分析")
    parser.add_argument("--code", type=str, default="", help="股票代码")
    parser.add_argument("--top_n", type=int, default=10, help="排行前N名")
    parser.add_argument("--rank_symbol", type=str, default="即时", help="排行窗口")
    args = parser.parse_args()

    result = get_big_deal_analysis_with_fallback(args.code, args.top_n, args.rank_symbol)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
