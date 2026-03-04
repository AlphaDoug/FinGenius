#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票基本信息获取
数据源降级链: efinance → akshare全市场快照 → tushare(stock_basic+daily_basic+fina_indicator) → 默认值
对应原工程: src/tool/stock_info_request.py + market_data_provider.get_base_info
"""

import argparse
import json
import sys

import pandas as pd

try:
    import efinance as ef
except ImportError:
    ef = None

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
    # 去掉可能的前缀 sh/sz，注意不能用 lstrip 因为它会逐字符剥离
    c = stock_code
    for prefix in ("sh", "sz", "SH", "SZ"):
        if c.startswith(prefix):
            c = c[len(prefix):]
            break
    return f"{c}.SH" if c.startswith("6") else f"{c}.SZ"


def get_stock_basic_info(stock_code):
    """
    获取股票基本信息

    Args:
        stock_code: 6位股票代码

    Returns:
        dict: {
            stock_code, stock_name, industry, market_cap,
            pe_ratio, pb_ratio, roe, gross_margin
        }
    """
    # 方法1：efinance基本信息
    if ef is not None:
        try:
            data = ef.stock.get_base_info(stock_code)
            if isinstance(data, pd.DataFrame) and not data.empty:
                info = data.to_dict(orient="records")[0] if isinstance(data.to_dict(orient="records"), list) else data.to_dict()
                return {
                    "stock_code": stock_code,
                    "stock_name": info.get("股票名称", "未知"),
                    "industry": info.get("所处行业", info.get("所属行业", "未知")),
                    "market_cap": str(info.get("总市值", "未知")),
                    "pe_ratio": str(info.get("市盈率(动)", info.get("市盈率", "未知"))),
                    "pb_ratio": str(info.get("市净率", "未知")),
                    "roe": str(info.get("ROE", info.get("净资产收益率", "未知"))),
                    "gross_margin": str(info.get("毛利率", "未知")),
                }
        except Exception as e:
            print(f"[efinance] 获取基本信息失败: {e}", file=sys.stderr)

    # 方法2：akshare全市场快照
    if ak is not None:
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                stock = df[df["代码"] == stock_code]
                if not stock.empty:
                    d = stock.iloc[0]
                    return {
                        "stock_code": stock_code,
                        "stock_name": d.get("名称", "未知"),
                        "industry": "未知",
                        "market_cap": str(d.get("总市值", "未知")),
                        "pe_ratio": str(d.get("市盈率-动态", "未知")),
                        "pb_ratio": str(d.get("市净率", "未知")),
                        "roe": "未知",
                        "gross_margin": "未知",
                    }
        except Exception as e:
            print(f"[akshare] 获取基本信息失败: {e}", file=sys.stderr)

    # 方法3: tushare保底
    if _pro is None:
        _init_tushare()
    if _pro is not None:
        try:
            ts_code = _to_ts_code(stock_code)

            # stock_basic 获取股票名称和行业（仅需120积分）
            stock_name = "未知"
            industry = "未知"
            try:
                df_stock = _pro.stock_basic(
                    ts_code=ts_code,
                    fields="ts_code,name,industry",
                )
                if isinstance(df_stock, pd.DataFrame) and not df_stock.empty:
                    row = df_stock.iloc[0]
                    stock_name = str(row.get("name", "未知"))
                    industry = str(row.get("industry", "未知"))
            except Exception as e:
                print(f"[tushare] stock_basic 失败: {e}", file=sys.stderr)

            # daily_basic 获取市值/PE/PB（需要2000积分）
            # 注意：ts_code 和 trade_date 是二选一参数，按 ts_code 查询可获取历史数据
            basic_info = {}
            try:
                df_basic = _pro.daily_basic(
                    ts_code=ts_code,
                    fields="ts_code,trade_date,pe,pe_ttm,pb,total_mv,circ_mv",
                )
                if isinstance(df_basic, pd.DataFrame) and not df_basic.empty:
                    row = df_basic.iloc[0]  # 最近一个交易日
                    total_mv = row.get("total_mv", 0) or 0
                    basic_info = {
                        "market_cap": str(round(float(total_mv) / 10000, 2)) + "亿",
                        "pe_ratio": str(row.get("pe_ttm") or row.get("pe") or "未知"),
                        "pb_ratio": str(row.get("pb", "未知")),
                    }
            except Exception as e:
                print(f"[tushare] daily_basic 失败: {e}", file=sys.stderr)

            # fina_indicator 获取ROE/毛利率（需要2000积分）
            fina_info = {}
            try:
                df_fina = _pro.fina_indicator(
                    ts_code=ts_code,
                    fields="ts_code,end_date,roe,grossprofit_margin",
                )
                if isinstance(df_fina, pd.DataFrame) and not df_fina.empty:
                    row = df_fina.iloc[0]  # 最新一期财报
                    fina_info = {
                        "roe": str(row.get("roe", "未知")),
                        "gross_margin": str(row.get("grossprofit_margin", "未知")),
                    }
            except Exception as e:
                print(f"[tushare] fina_indicator 失败: {e}", file=sys.stderr)

            # 只要有任何一个接口成功就返回
            if stock_name != "未知" or basic_info or fina_info:
                return {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "industry": industry,
                    "market_cap": basic_info.get("market_cap", "未知"),
                    "pe_ratio": basic_info.get("pe_ratio", "未知"),
                    "pb_ratio": basic_info.get("pb_ratio", "未知"),
                    "roe": fina_info.get("roe", "未知"),
                    "gross_margin": fina_info.get("gross_margin", "未知"),
                    "data_source": "tushare",
                }
        except Exception as e:
            print(f"[tushare] 获取基本信息失败: {e}", file=sys.stderr)

    # 兜底
    return {
        "stock_code": stock_code,
        "stock_name": "获取失败",
        "industry": "未知",
        "market_cap": "未知",
        "pe_ratio": "未知",
        "pb_ratio": "未知",
        "roe": "未知",
        "gross_margin": "未知",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取股票基本信息")
    parser.add_argument("stock_code", help="6位股票代码，如 600519")
    args = parser.parse_args()

    result = get_stock_basic_info(args.stock_code)
    print(json.dumps(result, ensure_ascii=False, indent=2))
