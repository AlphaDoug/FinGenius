#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术指标计算工具
支持 RSI、MACD、KDJ、布林带
"""

import argparse
import json
import sys

import numpy as np
import pandas as pd

# 复用K线数据获取
from kline_data import get_kline_data


def calc_rsi(closes, periods=(6, 12, 24)):
    """计算RSI指标"""
    result = {}
    for period in periods:
        delta = pd.Series(closes).diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        result[f"RSI_{period}"] = round(rsi.iloc[-1], 2) if len(rsi) > 0 else None
    return result


def calc_macd(closes, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    s = pd.Series(closes)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = 2 * (dif - dea)
    return {
        "DIF": round(dif.iloc[-1], 4),
        "DEA": round(dea.iloc[-1], 4),
        "MACD柱": round(macd_hist.iloc[-1], 4),
    }


def calc_kdj(highs, lows, closes, period=9, k_smooth=3, d_smooth=3):
    """计算KDJ指标"""
    h = pd.Series(highs)
    l = pd.Series(lows)
    c = pd.Series(closes)
    low_min = l.rolling(window=period, min_periods=1).min()
    high_max = h.rolling(window=period, min_periods=1).max()
    rsv = (c - low_min) / (high_max - low_min).replace(0, np.inf) * 100
    k = rsv.ewm(com=k_smooth - 1, adjust=False).mean()
    d = k.ewm(com=d_smooth - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return {
        "K": round(k.iloc[-1], 2),
        "D": round(d.iloc[-1], 2),
        "J": round(j.iloc[-1], 2),
    }


def calc_bollinger(closes, period=20, num_std=2):
    """计算布林带"""
    s = pd.Series(closes)
    mid = s.rolling(window=period, min_periods=1).mean()
    std = s.rolling(window=period, min_periods=1).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return {
        "上轨": round(upper.iloc[-1], 2),
        "中轨": round(mid.iloc[-1], 2),
        "下轨": round(lower.iloc[-1], 2),
        "带宽": round((upper.iloc[-1] - lower.iloc[-1]) / mid.iloc[-1] * 100, 2) if mid.iloc[-1] != 0 else 0,
    }


def calculate_all_indicators(stock_code, count=60):
    """计算所有技术指标"""
    kline = get_kline_data(stock_code, klt=101, count=count)
    if not kline:
        return {"error": "无法获取K线数据"}

    df = pd.DataFrame(kline)

    # 自适应列名
    close_col = next((c for c in df.columns if c in ["收盘", "close", "Close"]), None)
    high_col = next((c for c in df.columns if c in ["最高", "high", "High"]), None)
    low_col = next((c for c in df.columns if c in ["最低", "low", "Low"]), None)

    if not close_col:
        return {"error": "K线数据缺少收盘价列"}

    closes = pd.to_numeric(df[close_col], errors="coerce").dropna().tolist()
    highs = pd.to_numeric(df[high_col], errors="coerce").dropna().tolist() if high_col else closes
    lows = pd.to_numeric(df[low_col], errors="coerce").dropna().tolist() if low_col else closes

    return {
        "stock_code": stock_code,
        "data_count": len(closes),
        "latest_close": closes[-1] if closes else None,
        "RSI": calc_rsi(closes),
        "MACD": calc_macd(closes),
        "KDJ": calc_kdj(highs, lows, closes),
        "BOLL": calc_bollinger(closes),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="计算技术指标")
    parser.add_argument("stock_code", type=str, help="股票代码")
    parser.add_argument("--count", type=int, default=60, help="K线数据条数")
    args = parser.parse_args()

    result = calculate_all_indicators(args.stock_code, args.count)
    print(json.dumps(result, ensure_ascii=False, indent=2))
