#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取东方财富个股资金流向数据
API: https://push2.eastmoney.com/api/qt/clist/get
"""

import argparse
import json
import os as _os
import re
import time
import traceback
from datetime import datetime

import requests

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

STOCK_CAPITAL_FLOW_URL = "https://push2.eastmoney.com/api/qt/clist/get?fid=f62&po=1&pz=50&pn=1&np=1&fltt=2&invt=2&ut=8dec03ba335b81bf4ebdf7b29ec27d15&fs=m%3A0%2Bt%3A6%2Bf%3A!2%2Cm%3A0%2Bt%3A13%2Bf%3A!2%2Cm%3A0%2Bt%3A80%2Bf%3A!2%2Cm%3A1%2Bt%3A2%2Bf%3A!2%2Cm%3A1%2Bt%3A23%2Bf%3A!2%2Cm%3A0%2Bt%3A7%2Bf%3A!2%2Cm%3A1%2Bt%3A3%2Bf%3A!2&fields=f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184%2Cf66%2Cf69%2Cf72%2Cf75%2Cf78%2Cf81%2Cf84%2Cf87%2Cf204%2Cf205%2Cf124%2Cf1%2Cf13"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def parse_jsonp(jsonp_str):
    """解析JSONP响应"""
    try:
        match = re.search(r"jQuery[0-9_]+\((.*)\)", jsonp_str)
        if match:
            return json.loads(match.group(1))
        return json.loads(jsonp_str)
    except Exception:
        return None


def fetch_stock_list_capital_flow(page_size=50, page_num=1, max_retries=3, retry_delay=2):
    """获取股票列表资金流向（按主力净流入排序）"""
    url = STOCK_CAPITAL_FLOW_URL.replace("pz=50", f"pz={page_size}").replace("pn=1", f"pn={page_num}")
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

            stock_list = data.get("data", {}).get("diff", [])
            if not stock_list:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

            return process_stock_list_data(stock_list, data.get("data", {}).get("total", 0))
        except Exception as e:
            print(f"获取个股资金流向失败: {e} (第{attempt}次)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None


def fetch_single_stock_capital_flow(stock_code, max_retries=3, retry_delay=2):
    """获取单个股票资金流向"""
    for page in range(1, 10):
        stock_list = fetch_stock_list_capital_flow(50, page)
        if not stock_list:
            break
        for stock in stock_list.get("股票列表", []):
            if stock.get("股票代码") == stock_code:
                return {"success": True, "message": f"成功获取{stock.get('股票名称')}({stock_code})资金流向", "last_updated": datetime.now().isoformat(), "data": stock}
    return {"success": False, "message": f"未找到股票{stock_code}的资金流向数据", "data": {}}


def process_stock_list_data(stock_list, total_count):
    """处理股票列表资金流向数据"""
    field_mapping = {
        "f12": "股票代码", "f14": "股票名称", "f2": "最新价", "f3": "涨跌幅",
        "f62": "主力净流入", "f184": "主力净占比", "f66": "超大单净流入", "f69": "超大单净占比",
        "f72": "大单净流入", "f75": "大单净占比", "f78": "中单净流入", "f81": "中单净占比",
        "f84": "小单净流入", "f87": "小单净占比", "f124": "更新时间", "f1": "市场代码", "f13": "市场类型",
    }
    market_map = {0: "SZ", 1: "SH"}

    result = {"股票列表": [], "总数": total_count, "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    for stock_item in stock_list:
        stock_data = {}
        for api_field, result_field in field_mapping.items():
            if api_field in stock_item:
                value = stock_item.get(api_field)
                if api_field == "f124":
                    try:
                        stock_data[result_field] = datetime.fromtimestamp(int(value) / 1000).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        stock_data[result_field] = "-"
                elif api_field in ["f62", "f66", "f72", "f78", "f84"]:
                    stock_data[result_field] = round(float(value) / 10000, 2) if value else 0
                elif api_field in ["f3", "f184", "f69", "f75", "f81", "f87"]:
                    stock_data[result_field] = round(float(value), 2) if value else 0
                elif api_field == "f13":
                    stock_data[result_field] = market_map.get(value, str(value))
                else:
                    stock_data[result_field] = value
        if "股票代码" in stock_data and "市场类型" in stock_data:
            stock_data["完整代码"] = f"{stock_data['市场类型']}.{stock_data['股票代码']}"
        result["股票列表"].append(stock_data)

    return result


def _to_ts_code(stock_code: str) -> str:
    """将纯数字股票代码转为tushare格式"""
    if "." in stock_code:
        return stock_code
    if stock_code.startswith("6"):
        return f"{stock_code}.SH"
    elif stock_code.startswith(("0", "3")):
        return f"{stock_code}.SZ"
    elif stock_code.startswith(("4", "8")):
        return f"{stock_code}.BJ"
    return stock_code


def _tushare_moneyflow_fallback(stock_code=None):
    """tushare moneyflow保底（2000积分）"""
    try:
        if _pro is None:
            _init_tushare()
        if _pro is None:
            return None
        pro = _pro
        if stock_code:
            ts_code = _to_ts_code(stock_code)
            df = pro.moneyflow(ts_code=ts_code)
            if isinstance(df, pd.DataFrame) and not df.empty:
                row = df.iloc[0]
                buy_lg = float(row.get("buy_lg_amount", 0) or 0) + float(row.get("buy_elg_amount", 0) or 0)
                sell_lg = float(row.get("sell_lg_amount", 0) or 0) + float(row.get("sell_elg_amount", 0) or 0)
                return {
                    "success": True, "message": f"tushare获取{stock_code}资金流向成功",
                    "last_updated": datetime.now().isoformat(),
                    "data": {
                        "股票代码": stock_code, "交易日期": str(row.get("trade_date", "")),
                        "主力净流入": round((buy_lg - sell_lg) / 10000, 2),
                        "超大单净流入": round((float(row.get("buy_elg_amount", 0) or 0) - float(row.get("sell_elg_amount", 0) or 0)) / 10000, 2),
                        "大单净流入": round((float(row.get("buy_lg_amount", 0) or 0) - float(row.get("sell_lg_amount", 0) or 0)) / 10000, 2),
                        "中单净流入": round((float(row.get("buy_md_amount", 0) or 0) - float(row.get("sell_md_amount", 0) or 0)) / 10000, 2),
                        "小单净流入": round((float(row.get("buy_sm_amount", 0) or 0) - float(row.get("sell_sm_amount", 0) or 0)) / 10000, 2),
                        "数据来源": "tushare",
                    },
                }
        else:
            trade_date = datetime.now().strftime("%Y%m%d")
            df = pro.moneyflow(trade_date=trade_date)
            if isinstance(df, pd.DataFrame) and not df.empty:
                records = []
                for _, row in df.head(50).iterrows():
                    code = str(row.get("ts_code", "")).split(".")[0]
                    buy_lg = float(row.get("buy_lg_amount", 0) or 0) + float(row.get("buy_elg_amount", 0) or 0)
                    sell_lg = float(row.get("sell_lg_amount", 0) or 0) + float(row.get("sell_elg_amount", 0) or 0)
                    records.append({"股票代码": code, "主力净流入": round((buy_lg - sell_lg) / 10000, 2)})
                records.sort(key=lambda x: x["主力净流入"], reverse=True)
                return {
                    "success": True, "message": f"tushare获取资金流向成功",
                    "last_updated": datetime.now().isoformat(),
                    "data": {"股票列表": records, "总数": len(records), "数据来源": "tushare"},
                }
    except Exception as e:
        print(f"tushare moneyflow保底失败: {e}")
    return None


def get_stock_capital_flow(page_size=50, page_num=1, stock_code=None):
    """获取股票资金流向数据"""
    try:
        if stock_code:
            result = fetch_single_stock_capital_flow(stock_code)
            if result and result.get("success"):
                return result
        else:
            flow_data = fetch_stock_list_capital_flow(page_size, page_num)
            if flow_data:
                return {"success": True, "message": f"成功获取数据，共{flow_data.get('总数', 0)}条", "last_updated": datetime.now().isoformat(), "data": flow_data}
    except Exception as e:
        print(f"东方财富资金流向失败: {e}")

    # 保底路径：tushare moneyflow
    fallback = _tushare_moneyflow_fallback(stock_code)
    if fallback:
        return fallback

    return {"success": False, "message": "获取股票资金流向数据失败", "data": {}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="获取股票资金流向")
    parser.add_argument("--code", type=str, help="股票代码")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--size", type=int, default=50)
    args = parser.parse_args()

    if args.code:
        result = get_stock_capital_flow(stock_code=args.code)
    else:
        result = get_stock_capital_flow(page_size=args.size, page_num=args.page)
    print(json.dumps(result, ensure_ascii=False, indent=2))
