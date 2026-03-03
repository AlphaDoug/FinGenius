#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取股票实时行情数据
数据源降级：efinance → tushare
"""

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


def get_realtime_quotes(stock_code: str) -> dict:
    """获取股票实时行情，efinance → tushare降级"""
    if ef is not None:
        try:
            snapshot = ef.stock.get_quote_snapshot(stock_code)
            if snapshot is not None and len(snapshot) > 0:
                return {str(k): v for k, v in snapshot.to_dict().items()}
        except Exception as e:
            print(f"efinance快照失败({stock_code}), 尝试get_latest_quote...")
        try:
            df = ef.stock.get_latest_quote(stock_code)
            if isinstance(df, pd.DataFrame) and not df.empty:
                records = df.to_dict(orient="records")
                if records:
                    return {str(k): v for k, v in records[0].items()}
        except Exception as e:
            print(f"efinance失败({stock_code}): {e}")

    _init_tushare()
    if _pro is not None:
        try:
            ts_code = _to_ts_code(stock_code)
            df = ts.realtime_quote(ts_code=ts_code, src="dc")
            if isinstance(df, pd.DataFrame) and not df.empty:
                records = df.to_dict(orient="records")
                if records:
                    return {str(k): v for k, v in records[0].items()}
        except Exception as e:
            print(f"tushare失败({stock_code}): {e}")

    return {}


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "600519"
    print(json.dumps(get_realtime_quotes(code), ensure_ascii=False, indent=2, default=str))
