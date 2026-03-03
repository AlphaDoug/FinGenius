#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取东方财富指数资金流向数据
数据源降级：东方财富API → tushare(moneyflow_hsgt+index_daily, 2000积分)
API: https://push2.eastmoney.com/api/qt/stock/get
"""

import json
import re
import sys
import time
import traceback
from datetime import datetime

import pandas as pd
import requests

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

INDEX_CAPITAL_FLOW_URL = "https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=1&fields=f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149&secid=1.000001&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=|0|0|0|web&dect=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

INDEX_CODE_NAME_MAP = {
    "000001": "上证指数", "399001": "深证成指", "399006": "创业板指",
    "000300": "沪深300", "000905": "中证500", "000016": "上证50",
    "000852": "中证1000", "000688": "科创50", "399673": "创业板50",
}


def parse_jsonp(jsonp_str):
    """解析JSONP响应"""
    try:
        match = re.search(r"jQuery[0-9_]+\((.*)\)", jsonp_str)
        if match:
            return json.loads(match.group(1))
        return json.loads(jsonp_str)
    except Exception as e:
        print(f"解析JSONP失败: {e}")
        return None


def fetch_index_capital_flow(index_code="000001", max_retries=3, retry_delay=2):
    """获取指数资金流向原始数据"""
    market = "1"
    if index_code.startswith("39") or index_code.startswith("1"):
        market = "0"

    url = INDEX_CAPITAL_FLOW_URL.replace("secid=1.000001", f"secid={market}.{index_code}")
    timestamp = int(time.time() * 1000)
    url += f"&_={timestamp}"

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = parse_jsonp(resp.text)
            if not data:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

            flow_data = data.get("data", {})
            if not flow_data:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

            return process_flow_data(flow_data, index_code)
        except Exception as e:
            print(f"获取指数资金流向数据失败: {e} (第{attempt}次尝试)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None


def process_flow_data(data, index_code):
    """处理资金流向数据，金额除以1亿转换为亿元"""
    field_mapping = {
        "f135": "今日主力净流入", "f136": "今日主力流入", "f137": "今日主力流出",
        "f138": "今日超大单净流入", "f139": "今日超大单流入", "f140": "今日超大单流出",
        "f141": "今日大单净流入", "f142": "今日大单流入", "f143": "今日大单流出",
        "f144": "今日中单净流入", "f145": "今日中单流入", "f146": "今日中单流出",
        "f147": "今日小单净流入", "f148": "今日小单流入", "f149": "今日小单流出",
    }

    index_name = INDEX_CODE_NAME_MAP.get(index_code, f"指数{index_code}")
    result = {
        "指数代码": index_code,
        "指数名称": index_name,
        "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    for field, label in field_mapping.items():
        if field in data:
            value = data.get(field, 0)
            result[label] = round(float(value) / 1e8, 2) if value else 0

    return result


def _tushare_index_capital_fallback(index_code):
    """tushare保底：用moneyflow_hsgt(沪深港通资金流向) + index_daily(指数行情)"""
    if _pro is None:
        _init_tushare()
    if _pro is None:
        return None
    index_name = INDEX_CODE_NAME_MAP.get(index_code, f"指数{index_code}")
    result = {"指数代码": index_code, "指数名称": index_name, "数据来源": "tushare"}

    # 北向资金流向（间接反映大盘资金流向）
    try:
        df = _pro.moneyflow_hsgt(trade_date=datetime.now().strftime("%Y%m%d"))
        if isinstance(df, pd.DataFrame) and not df.empty:
            row = df.iloc[0]
            result["北向资金(百万)"] = float(row.get("north_money", 0) or 0)
            result["沪股通(百万)"] = float(row.get("hgt", 0) or 0)
            result["深股通(百万)"] = float(row.get("sgt", 0) or 0)
    except Exception as e:
        print(f"tushare moneyflow_hsgt失败: {e}")

    # 指数行情
    try:
        ts_code_map = {
            "000001": "000001.SH", "399001": "399001.SZ", "399006": "399006.SZ",
            "000300": "000300.SH", "000905": "000905.SH", "000016": "000016.SH",
        }
        ts_code = ts_code_map.get(index_code, f"{index_code}.SH")
        df = _pro.index_daily(ts_code=ts_code)
        if isinstance(df, pd.DataFrame) and not df.empty:
            row = df.iloc[0]
            result["收盘点位"] = float(row.get("close", 0) or 0)
            result["涨跌幅"] = float(row.get("pct_chg", 0) or 0)
            result["成交额(千元)"] = float(row.get("amount", 0) or 0)
    except Exception as e:
        print(f"tushare index_daily失败: {e}")

    result["更新时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return result if len(result) > 4 else None


def get_index_capital_flow(index_code="000001"):
    """获取指数资金流向数据（公开接口）"""
    try:
        flow_data = fetch_index_capital_flow(index_code)
        if flow_data:
            index_name = flow_data.get("指数名称", INDEX_CODE_NAME_MAP.get(index_code, f"指数{index_code}"))
            return {
                "success": True,
                "message": f"成功获取{index_name}({index_code})资金流向数据",
                "last_updated": datetime.now().isoformat(),
                "data": flow_data,
            }
    except Exception as e:
        print(f"东方财富获取指数资金流向失败: {e}")

    # 保底路径：tushare
    fallback = _tushare_index_capital_fallback(index_code)
    if fallback:
        return {
            "success": True,
            "message": f"tushare获取{fallback.get('指数名称', index_code)}资金流向数据",
            "last_updated": datetime.now().isoformat(),
            "data": fallback,
        }

    return {"success": False, "message": f"获取指数{index_code}资金流向数据失败", "data": {}}


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "000001"
    result = get_index_capital_flow(index_code=code)
    print(json.dumps(result, ensure_ascii=False, indent=2))
