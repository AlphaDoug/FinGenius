#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
风控数据获取工具
获取公司公告（东方财富）和财务报表（akshare）
数据源降级：akshare → tushare(income/balancesheet/cashflow/fina_indicator, 2000积分)
"""

import argparse
import json
import time
import traceback
from datetime import datetime

import pandas as pd
import requests

# akshare
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


# ============ 公告相关 ============

def get_eastmoney_announcements(stock_code, page_size=50, page_index=1, max_retries=3, retry_delay=2):
    """获取东方财富公告列表"""
    api_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    params = {
        "sr": -1, "page_size": page_size, "page_index": page_index,
        "ann_type": "A", "client_source": "web", "stock_list": stock_code,
        "f_node": 0, "s_node": 0, "_": int(time.time() * 1000),
    }
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data or "data" not in data or "list" not in data["data"]:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return []
            return data["data"]["list"]
        except Exception as e:
            print(f"获取公告列表失败: {e} (第{attempt}次)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return []


def get_eastmoney_announcement_detail(art_code, max_retries=3, retry_delay=2):
    """获取公告详情正文"""
    detail_url = "https://np-cnotice-stock.eastmoney.com/api/content/ann"
    params = {"art_code": art_code, "client_source": "web", "page_index": 1}
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(detail_url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "data" in data:
                content = data["data"].get("content")
                return content if content else data["data"]
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            return None
        except Exception as e:
            print(f"公告详情失败 art_code={art_code}: {e} (第{attempt}次)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None


def get_announcements_with_detail(stock_code, max_count=10):
    """获取公告列表+正文（正文截断至1000字）"""
    max_count = min(max_count, 10)
    try:
        anns = get_eastmoney_announcements(stock_code, page_size=max_count)
        result = []
        for i, ann in enumerate(anns[:max_count]):
            art_code = ann.get("art_code")
            title = ann.get("title")
            notice_date = ann.get("notice_date", "").split("T")[0]
            content = ""
            if art_code:
                detail = get_eastmoney_announcement_detail(art_code)
                if isinstance(detail, str):
                    content = detail[:1000]
                elif isinstance(detail, dict):
                    raw = detail.get("content") or detail.get("notice_content") or ""
                    content = raw[:1000]
            result.append({"title": title, "date": notice_date, "content": content})
            time.sleep(0.3)
        return result
    except Exception as e:
        print(f"获取公告失败: {e}")
        return []


# ============ 财务报表相关 ============

def get_balance_sheet(stock_code, period="按年度"):
    """获取资产负债表"""
    if not HAS_AKSHARE:
        return pd.DataFrame()
    try:
        df = ak.stock_financial_debt_ths(symbol=stock_code, indicator=period)
        return df.head(5) if isinstance(df, pd.DataFrame) and not df.empty else pd.DataFrame()
    except Exception as e:
        print(f"获取资产负债表失败: {e}")
        return pd.DataFrame()


def get_income_statement(stock_code, period="按年度"):
    """获取利润表"""
    if not HAS_AKSHARE:
        return pd.DataFrame()
    try:
        df = ak.stock_financial_benefit_ths(symbol=stock_code, indicator=period)
        return df.head(5) if isinstance(df, pd.DataFrame) and not df.empty else pd.DataFrame()
    except Exception as e:
        print(f"获取利润表失败: {e}")
        return pd.DataFrame()


def get_cash_flow(stock_code, period="按年度"):
    """获取现金流量表"""
    if not HAS_AKSHARE:
        return pd.DataFrame()
    try:
        df = ak.stock_financial_cash_ths(symbol=stock_code, indicator=period)
        return df.head(5) if isinstance(df, pd.DataFrame) and not df.empty else pd.DataFrame()
    except Exception as e:
        print(f"获取现金流量表失败: {e}")
        return pd.DataFrame()


def _tushare_financial_fallback(stock_code):
    """tushare保底：用income/balancesheet/cashflow获取三大财务报表"""
    if _pro is None:
        _init_tushare()
    if _pro is None:
        return None
    ts_code = _to_ts_code(stock_code)

    balance_records, income_records, cashflow_records = [], [], []

    # 利润表
    try:
        df = _pro.income(ts_code=ts_code)
        if isinstance(df, pd.DataFrame) and not df.empty:
            income_records = df.head(5).to_dict(orient="records")
    except Exception as e:
        print(f"tushare income失败: {e}")

    # 资产负债表
    try:
        df = _pro.balancesheet(ts_code=ts_code)
        if isinstance(df, pd.DataFrame) and not df.empty:
            balance_records = df.head(5).to_dict(orient="records")
    except Exception as e:
        print(f"tushare balancesheet失败: {e}")

    # 现金流量表
    try:
        df = _pro.cashflow(ts_code=ts_code)
        if isinstance(df, pd.DataFrame) and not df.empty:
            cashflow_records = df.head(5).to_dict(orient="records")
    except Exception as e:
        print(f"tushare cashflow失败: {e}")

    if not balance_records and not income_records and not cashflow_records:
        return None

    return {
        "元数据": {
            "股票代码": stock_code, "数据周期": "tushare默认",
            "数据获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "数据来源": "tushare",
            "报表条目数": {
                "资产负债表": len(balance_records),
                "利润表": len(income_records),
                "现金流量表": len(cashflow_records),
            },
        },
        "资产负债表": balance_records,
        "利润表": income_records,
        "现金流量表": cashflow_records,
    }


def get_financial_reports(stock_code, period="按年度"):
    """获取三大财务报表（akshare → tushare保底）"""
    # 方法1: akshare
    if HAS_AKSHARE:
        try:
            balance = get_balance_sheet(stock_code, period)
            income = get_income_statement(stock_code, period)
            cashflow = get_cash_flow(stock_code, period)

            if not all(isinstance(df, pd.DataFrame) and df.empty for df in [balance, income, cashflow]):
                return {
                    "元数据": {
                        "股票代码": stock_code, "数据周期": period,
                        "数据获取时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "报表条目数": {
                            "资产负债表": len(balance), "利润表": len(income), "现金流量表": len(cashflow),
                        },
                    },
                    "资产负债表": balance.to_dict(orient="records") if not balance.empty else [],
                    "利润表": income.to_dict(orient="records") if not income.empty else [],
                    "现金流量表": cashflow.to_dict(orient="records") if not cashflow.empty else [],
                }
        except Exception as e:
            print(f"akshare获取财务报表失败: {e}")

    # 方法2: tushare保底
    fallback = _tushare_financial_fallback(stock_code)
    if fallback:
        return fallback

    return {"error": f"未获取到{stock_code}的任何财务数据"}


# ============ 一键风控数据 ============

def get_risk_control_data(stock_code, max_count=10, period="按年度",
                          include_announcements=True, include_financial=True,
                          max_retry=3, sleep_seconds=1):
    """
    获取完整风控数据（公告 + 财务）

    Args:
        stock_code: 股票代码
        max_count: 公告数量上限
        period: 财务数据周期
        include_announcements: 是否包含公告
        include_financial: 是否包含财务数据
        max_retry: 最大重试次数
        sleep_seconds: 重试间隔

    Returns:
        dict: {"legal": [...], "financial_meta": {...}}
    """
    for attempt in range(1, max_retry + 1):
        try:
            legal_data = get_announcements_with_detail(stock_code, max_count) if include_announcements else None
            financial_data = get_financial_reports(stock_code, period) if include_financial else None
            financial_meta = financial_data.get("元数据", {}) if isinstance(financial_data, dict) else {}
            return {"legal": legal_data, "financial_meta": financial_meta}
        except Exception as e:
            print(f"[第{attempt}次] 获取风控数据失败: {e}")
            if attempt < max_retry:
                time.sleep(sleep_seconds)
    return {"financial": None, "legal": None, "error": "获取风控数据失败"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="风控数据获取")
    parser.add_argument("--code", type=str, required=True, help="股票代码")
    parser.add_argument("--max_count", type=int, default=10, help="公告数量")
    parser.add_argument("--period", type=str, default="按年度", help="财务周期")
    parser.add_argument("--financial_only", action="store_true", help="仅获取财务数据")
    args = parser.parse_args()

    if args.financial_only:
        result = get_financial_reports(args.code, args.period)
    else:
        result = get_risk_control_data(args.code, args.max_count, args.period)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
