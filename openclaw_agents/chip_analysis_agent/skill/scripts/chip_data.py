#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
筹码分布数据获取工具
数据源降级：akshare stock_cyq_em → 历史行情估算 → tushare(daily/daily_basic, 2000积分) → 默认值
"""

import argparse
import json
from datetime import datetime, timedelta

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


def get_chip_distribution(stock_code: str, adjust: str = "") -> dict:
    """
    获取筹码分布数据（三级降级）

    Args:
        stock_code: 股票代码
        adjust: 复权类型 ''/'qfq'/'hfq'

    Returns:
        dict: 筹码分布数据
    """
    clean_code = stock_code.lstrip("shsz")

    # 方法1: akshare stock_cyq_em
    if ak is not None:
        try:
            df = ak.stock_cyq_em(symbol=clean_code, adjust=adjust)
            if df is not None and not df.empty:
                recent_df = df.tail(5)
                return {
                    "date": recent_df.index.strftime("%Y-%m-%d").tolist() if hasattr(recent_df.index, 'strftime') else [],
                    "chip_distribution": recent_df.to_dict('records'),
                    "data_source": "stock_cyq_em",
                }
        except Exception as e:
            print(f"stock_cyq_em失败({clean_code}): {e}")

    # 方法2: 历史行情估算
    if ak is not None:
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=15)).strftime("%Y%m%d")
            hist_df = ak.stock_zh_a_hist(symbol=clean_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            if hist_df is not None and not hist_df.empty:
                recent = hist_df.tail(5)
                chip_dist = []
                for _, row in recent.iterrows():
                    chip_dist.append({
                        "日期": str(row.get("日期", "")),
                        "价格": row.get("收盘", 0),
                        "成交量": row.get("成交量", 0),
                        "成交额": row.get("成交额", 0),
                        "筹码比例": min(row.get("换手率", 1.0) * 0.1, 10.0),
                    })
                return {
                    "date": [d["日期"] for d in chip_dist],
                    "chip_distribution": chip_dist,
                    "data_source": "estimated_from_hist",
                }
        except Exception as e:
            print(f"历史行情估算失败({clean_code}): {e}")

    # 方法3: tushare保底
    tushare_result = _tushare_chip_fallback(clean_code)
    if tushare_result:
        return tushare_result

    # 方法4: 默认值
    return {
        "date": [datetime.now().strftime("%Y-%m-%d")],
        "chip_distribution": [{"日期": datetime.now().strftime("%Y-%m-%d"), "价格": 0, "成交量": 0, "成交额": 0, "筹码比例": 0, "说明": "数据获取失败"}],
        "data_source": "default_fallback",
    }


def _tushare_chip_fallback(stock_code):
    """tushare保底：用daily(日线行情) + daily_basic(每日指标)估算筹码分布"""
    if _pro is None:
        _init_tushare()
    if _pro is None:
        return None
    ts_code = _to_ts_code(stock_code)

    try:
        # 获取最近15天日线
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        df_daily = _pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df_daily is None or df_daily.empty:
            return None

        # 获取每日指标（含换手率）
        try:
            df_basic = _pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if isinstance(df_basic, pd.DataFrame) and not df_basic.empty:
                df_daily = df_daily.merge(df_basic[["trade_date", "turnover_rate", "pe", "pb", "total_mv"]],
                                          on="trade_date", how="left")
        except Exception:
            pass

        recent = df_daily.head(5)
        chip_dist = []
        for _, row in recent.iterrows():
            turnover = float(row.get("turnover_rate", 0) or 0)
            chip_dist.append({
                "日期": str(row.get("trade_date", "")),
                "价格": float(row.get("close", 0) or 0),
                "成交量": float(row.get("vol", 0) or 0),
                "成交额(千元)": float(row.get("amount", 0) or 0),
                "换手率": turnover,
                "筹码比例": min(turnover * 0.1, 10.0),
            })

        return {
            "date": [d["日期"] for d in chip_dist],
            "chip_distribution": chip_dist,
            "data_source": "tushare_daily",
        }
    except Exception as e:
        print(f"tushare筹码估算失败: {e}")
        return None


def get_stock_spot_info(stock_code: str) -> dict:
    """获取股票实时信息（akshare → tushare保底）"""
    clean_code = stock_code.lstrip("shsz")

    # 方法1: akshare
    if ak is not None:
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                stock_row = df[df['代码'] == clean_code]
                if not stock_row.empty:
                    d = stock_row.iloc[0]
                    return {
                        "name": d.get('名称', ''), "current_price": d.get('最新价', 0),
                        "change_percent": d.get('涨跌幅', 0), "volume": d.get('成交量', 0),
                        "turnover": d.get('成交额', 0), "market_cap": d.get('总市值', 0),
                        "pe_ratio": d.get('市盈率-动态', 0), "data_source": "spot_em",
                    }
        except Exception:
            pass

    # 方法2: tushare保底
    if _pro is None:
        _init_tushare()
    if _pro is not None:
        try:
            ts_code = _to_ts_code(clean_code)
            df = _pro.daily_basic(ts_code=ts_code)
            if isinstance(df, pd.DataFrame) and not df.empty:
                row = df.iloc[0]
                return {
                    "name": f"股票{clean_code}", "current_price": float(row.get("close", 0) or 0),
                    "change_percent": float(row.get("pct_chg", 0) or 0),
                    "volume": 0, "turnover": float(row.get("turnover_rate", 0) or 0),
                    "market_cap": float(row.get("total_mv", 0) or 0),
                    "pe_ratio": float(row.get("pe", 0) or 0),
                    "data_source": "tushare_daily_basic",
                }
        except Exception as e:
            print(f"tushare daily_basic失败: {e}")

    return {"name": f"股票{clean_code}", "current_price": 0, "data_source": "default"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取筹码分布数据")
    parser.add_argument("stock_code", type=str, help="股票代码")
    parser.add_argument("--adjust", type=str, default="", help="复权类型")
    args = parser.parse_args()

    result = get_chip_distribution(args.stock_code, args.adjust)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
