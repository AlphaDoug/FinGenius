#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
K线数据获取工具
数据源降级：efinance → tushare(日线) → akshare东财分时 → akshare新浪分时
"""

import argparse
import json
import sys

import pandas as pd

try:
    import efinance as ef
except ImportError:
    ef = None

import os as _os

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

try:
    import akshare as ak
except ImportError:
    ak = None

_KLT_TO_PERIOD = {1: "1", 5: "5", 15: "15", 30: "30", 60: "60"}


def _to_ts_code(stock_code: str) -> str:
    if "." in stock_code:
        return stock_code
    if stock_code.startswith("6"):
        return f"{stock_code}.SH"
    elif stock_code.startswith(("0", "3")):
        return f"{stock_code}.SZ"
    elif stock_code.startswith(("4", "8")):
        return f"{stock_code}.BJ"
    return stock_code


def _to_sina_symbol(stock_code: str) -> str:
    code = stock_code.lstrip("shsz")
    if code.startswith("6"):
        return f"sh{code}"
    elif code.startswith(("0", "3")):
        return f"sz{code}"
    return stock_code


def _to_dict(data) -> list:
    if isinstance(data, pd.DataFrame) and not data.empty:
        return data.to_dict(orient="records")
    return []


def get_kline_data(stock_code: str, klt: int = 101, count: int = 30) -> list:
    """
    获取K线数据

    Args:
        stock_code: 股票代码
        klt: K线类型，1=分钟, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟, 101=日线
        count: 返回数据条数

    Returns:
        list: K线数据列表
    """
    # 主路径：efinance
    if ef is not None:
        try:
            kline_df = ef.stock.get_quote_history(stock_code, klt=klt)
            if isinstance(kline_df, pd.DataFrame) and not kline_df.empty:
                data = _to_dict(kline_df)
                if data:
                    return data[-count:] if len(data) > count else data
        except Exception as e:
            print(f"efinance获取K线失败({stock_code}, klt={klt}): {e}")

    # 保底A：tushare日线（仅klt=101）
    _init_tushare()
    if klt == 101 and _pro is not None:
        try:
            ts_code = _to_ts_code(stock_code)
            df = _pro.daily(ts_code=ts_code)
            if isinstance(df, pd.DataFrame) and not df.empty:
                df = df.sort_values("trade_date").reset_index(drop=True)
                data = _to_dict(df)
                if data:
                    return data[-count:] if len(data) > count else data
        except Exception as e:
            print(f"tushare日线失败({stock_code}): {e}")

    # 保底B：akshare分钟线
    period = _KLT_TO_PERIOD.get(klt)
    if period is not None and ak is not None:
        # B-1：东财分时
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=stock_code, period=period, adjust="")
            if isinstance(df, pd.DataFrame) and not df.empty:
                data = _to_dict(df)
                if data:
                    return data[-count:] if len(data) > count else data
        except Exception as e:
            print(f"akshare东财分时失败({stock_code}): {e}")

        # B-2：新浪分时
        try:
            sina_symbol = _to_sina_symbol(stock_code)
            df = ak.stock_zh_a_minute(symbol=sina_symbol, period=period, adjust="")
            if isinstance(df, pd.DataFrame) and not df.empty:
                data = _to_dict(df)
                if data:
                    return data[-count:] if len(data) > count else data
        except Exception as e:
            print(f"akshare新浪分时失败({stock_code}): {e}")

    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取K线数据")
    parser.add_argument("stock_code", type=str, help="股票代码")
    parser.add_argument("--klt", type=int, default=101, help="K线类型: 1/5/15/30/60/101")
    parser.add_argument("--count", type=int, default=30, help="数据条数")
    args = parser.parse_args()

    result = get_kline_data(args.stock_code, args.klt, args.count)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
