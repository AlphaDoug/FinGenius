#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取龙虎榜数据
数据源降级：efinance → tushare(top_list, 2000积分)
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


def get_daily_billboard(start_date: str, end_date: str = None) -> list:
    """
    获取龙虎榜数据

    Args:
        start_date: 开始日期，格式 'YYYY-MM-DD'
        end_date: 结束日期，格式 'YYYY-MM-DD'，默认与start_date相同

    Returns:
        list: 龙虎榜数据列表
    """
    end_date = end_date or start_date

    # 主路径：efinance
    if ef is not None:
        try:
            df = ef.stock.get_daily_billboard(start_date=start_date, end_date=end_date)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df.to_dict(orient="records")
        except Exception as e:
            print(f"efinance获取龙虎榜失败: {e}")

    # 保底路径：tushare top_list (2000积分)
    if _pro is None:
        _init_tushare()
    if _pro is not None:
        try:
            trade_date = start_date.replace("-", "")
            df = _pro.top_list(trade_date=trade_date)
            if isinstance(df, pd.DataFrame) and not df.empty:
                records = []
                for _, row in df.iterrows():
                    records.append({
                        "股票代码": row.get("ts_code", "").split(".")[0],
                        "股票名称": row.get("name", ""),
                        "收盘价": row.get("close", 0),
                        "涨跌幅": row.get("pct_change", 0),
                        "换手率": row.get("turnover_rate", 0),
                        "龙虎榜买入额": row.get("l_buy", 0),
                        "龙虎榜卖出额": row.get("l_sell", 0),
                        "龙虎榜净买入额": row.get("net_amount", 0),
                        "上榜理由": row.get("reason", ""),
                        "数据来源": "tushare",
                    })
                return records
        except Exception as e:
            print(f"tushare获取龙虎榜失败: {e}")

    return []


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else "2025-03-01"
    result = get_daily_billboard(start_date=date)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
