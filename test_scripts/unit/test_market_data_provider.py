"""
测试 MarketDataProvider 各接口 — 股票代码 600699（均胜电子）
运行方式: python test_scripts/unit/test_market_data_provider.py
"""

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from pprint import pformat

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.tool.market_data_provider import MarketDataProvider

STOCK_CODE = "600699"

# 收集结果
_passed: list = []
_failed: list = []


def _log(title: str, data, *, truncate: int = 3000):
    """格式化打印测试结果，超长内容截断。"""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)
    try:
        text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        text = pformat(data, width=120)
    if len(text) > truncate:
        text = text[:truncate] + f"\n... (已截断, 总长 {len(text)} 字符)"
    print(text)
    print()


def run_test(name: str, func):
    """运行单个测试，捕获异常并归类到 _passed / _failed。"""
    try:
        func()
        _passed.append(name)
    except Exception:
        err = traceback.format_exc()
        _log(f"{name} — 异常", err)
        _failed.append((name, err))


def main():
    provider = MarketDataProvider()

    print("\n" + "#" * 60)
    print(f"  MarketDataProvider 接口测试 — 股票: {STOCK_CODE}")
    print(f"  efinance 可用: {provider.efinance_available()}")
    print(f"  akshare  可用: {provider.akshare_available()}")
    print("#" * 60)

    today = datetime.now()

    # ------------------------------------------------------------------
    # 1. get_base_info
    # ------------------------------------------------------------------
    def test_get_base_info():
        result = provider.get_base_info(STOCK_CODE)
        _log("get_base_info", result)
        assert isinstance(result, dict), f"期望 dict，实际 {type(result)}"

    run_test("get_base_info", test_get_base_info)

    # ------------------------------------------------------------------
    # 2. get_realtime_quotes（含 tushare 保底）
    # ------------------------------------------------------------------
    def test_get_realtime_quotes():
        result = provider.get_realtime_quotes(STOCK_CODE)
        _log("get_realtime_quotes", result)
        assert isinstance(result, dict), f"期望 dict，实际 {type(result)}"

    run_test("get_realtime_quotes", test_get_realtime_quotes)

    # ------------------------------------------------------------------
    # 3. get_quote_history — 日线
    # ------------------------------------------------------------------
    def test_get_quote_history_daily():
        result = provider.get_quote_history(STOCK_CODE, klt=101)
        _log(f"get_quote_history(klt=101) 共 {len(result)} 条", result[-5:] if result else result)
        assert isinstance(result, list), f"期望 list，实际 {type(result)}"

    run_test("get_quote_history(日线klt=101)", test_get_quote_history_daily)

    # ------------------------------------------------------------------
    # 4. get_quote_history — 分钟线
    # ------------------------------------------------------------------
    def test_get_quote_history_minute():
        result = provider.get_quote_history(STOCK_CODE, klt=1)
        _log(f"get_quote_history(klt=1) 共 {len(result)} 条", result[-5:] if result else result)
        assert isinstance(result, list), f"期望 list，实际 {type(result)}"

    run_test("get_quote_history(分钟klt=1)", test_get_quote_history_minute)

    # ------------------------------------------------------------------
    # 5. get_daily_billboard — 龙虎榜
    # ------------------------------------------------------------------
    def test_get_daily_billboard():
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        result = provider.get_daily_billboard(start_date=start_date, end_date=end_date)
        _log(f"get_daily_billboard({start_date}~{end_date})", provider.to_dict(result) if result is not None else None)

    run_test("get_daily_billboard", test_get_daily_billboard)

    # ------------------------------------------------------------------
    # 6. get_stock_fund_flow_big_deal — 市场大单
    # ------------------------------------------------------------------
    def test_get_stock_fund_flow_big_deal():
        result = provider.get_stock_fund_flow_big_deal()
        _log("get_stock_fund_flow_big_deal", provider.to_dict(result) if result is not None else None)

    run_test("get_stock_fund_flow_big_deal", test_get_stock_fund_flow_big_deal)

    # ------------------------------------------------------------------
    # 7. get_stock_fund_flow_individual — 个股资金流排行
    # ------------------------------------------------------------------
    def test_get_stock_fund_flow_individual():
        result = provider.get_stock_fund_flow_individual(symbol="即时")
        _log("get_stock_fund_flow_individual", provider.to_dict(result) if result is not None else None)

    run_test("get_stock_fund_flow_individual", test_get_stock_fund_flow_individual)

    # ------------------------------------------------------------------
    # 8. get_stock_individual_fund_flow — 个股资金流向趋势
    # ------------------------------------------------------------------
    def test_get_stock_individual_fund_flow():
        result = provider.get_stock_individual_fund_flow(stock_code=STOCK_CODE, market="sh")
        _log("get_stock_individual_fund_flow", provider.to_dict(result) if result is not None else None)

    run_test("get_stock_individual_fund_flow", test_get_stock_individual_fund_flow)

    # ------------------------------------------------------------------
    # 9. get_stock_zh_a_hist — A 股历史行情
    # ------------------------------------------------------------------
    def test_get_stock_zh_a_hist():
        end_date = today.strftime("%Y%m%d")
        start_date = (today - timedelta(days=30)).strftime("%Y%m%d")
        result = provider.get_stock_zh_a_hist(
            stock_code=STOCK_CODE, period="daily",
            start_date=start_date, end_date=end_date,
        )
        _log(f"get_stock_zh_a_hist({start_date}~{end_date})", provider.to_dict(result) if result is not None else None)

    run_test("get_stock_zh_a_hist", test_get_stock_zh_a_hist)

    # ------------------------------------------------------------------
    # 10. get_stock_zh_a_spot_em — 全市场快照
    # ------------------------------------------------------------------
    def test_get_stock_zh_a_spot_em():
        result = provider.get_stock_zh_a_spot_em()
        data = provider.to_dict(result) if result is not None else None
        if isinstance(data, list) and len(data) > 5:
            _log(f"get_stock_zh_a_spot_em 共 {len(data)} 条（仅显示前5条）", data[:5])
        else:
            _log("get_stock_zh_a_spot_em", data)

    run_test("get_stock_zh_a_spot_em", test_get_stock_zh_a_spot_em)

    # ------------------------------------------------------------------
    # 11. get_stock_cyq_em — 筹码分布
    # ------------------------------------------------------------------
    def test_get_stock_cyq_em():
        result = provider.get_stock_cyq_em(stock_code=STOCK_CODE)
        data = provider.to_dict(result) if result is not None else None
        if isinstance(data, list) and len(data) > 5:
            _log(f"get_stock_cyq_em 共 {len(data)} 条（仅显示前5条）", data[:5])
        else:
            _log("get_stock_cyq_em", data)

    run_test("get_stock_cyq_em", test_get_stock_cyq_em)

    # ------------------------------------------------------------------
    # 12. get_stock_capital_flow — 个股资金流向（爬虫）
    # ------------------------------------------------------------------
    def test_get_stock_capital_flow():
        result = provider.get_stock_capital_flow(stock_code=STOCK_CODE)
        _log("get_stock_capital_flow", result)
        assert isinstance(result, dict), f"期望 dict，实际 {type(result)}"

    run_test("get_stock_capital_flow", test_get_stock_capital_flow)

    # ------------------------------------------------------------------
    # 13. get_index_capital_flow — 指数资金流向
    # ------------------------------------------------------------------
    def test_get_index_capital_flow():
        result = provider.get_index_capital_flow(index_code="000001")
        _log("get_index_capital_flow", result)
        assert isinstance(result, dict), f"期望 dict，实际 {type(result)}"

    run_test("get_index_capital_flow", test_get_index_capital_flow)

    # ------------------------------------------------------------------
    # 14. get_section_data — 板块行情
    # ------------------------------------------------------------------
    def test_get_section_data():
        result = provider.get_section_data(sector_types="all")
        _log("get_section_data(all)", result)
        assert isinstance(result, dict), f"期望 dict，实际 {type(result)}"

    run_test("get_section_data", test_get_section_data)

    # ------------------------------------------------------------------
    # 15. get_risk_control_data — 风控数据
    # ------------------------------------------------------------------
    def test_get_risk_control_data():
        result = provider.get_risk_control_data(stock_code=STOCK_CODE)
        _log("get_risk_control_data", result)
        assert isinstance(result, dict), f"期望 dict，实际 {type(result)}"

    run_test("get_risk_control_data", test_get_risk_control_data)

    # ------------------------------------------------------------------
    # 16. _to_ts_code — 代码转换
    # ------------------------------------------------------------------
    def test_to_ts_code():
        cases = {
            "600699": "600699.SH",
            "000001": "000001.SZ",
            "300750": "300750.SZ",
            "430047": "430047.BJ",
            "600699.SH": "600699.SH",
        }
        for code, expected in cases.items():
            result = MarketDataProvider._to_ts_code(code)
            status = "PASS" if result == expected else "FAIL"
            print(f"  _to_ts_code('{code}') => '{result}'  [{status}]")
            assert result == expected, f"_to_ts_code('{code}') 期望 '{expected}'，实际 '{result}'"

    run_test("_to_ts_code", test_to_ts_code)

    # ------------------------------------------------------------------
    # 17. to_dict — 数据格式转换
    # ------------------------------------------------------------------
    def test_to_dict():
        import pandas as pd
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        r = MarketDataProvider.to_dict(df)
        assert isinstance(r, list) and len(r) == 2, f"DataFrame 转换异常: {r}"
        r = MarketDataProvider.to_dict(pd.DataFrame())
        assert r == [], f"空 DataFrame 转换异常: {r}"
        r = MarketDataProvider.to_dict(pd.Series({"x": 10, "y": 20}))
        assert isinstance(r, dict), f"Series 转换异常: {r}"
        r = MarketDataProvider.to_dict(42)
        assert r == {"value": 42}, f"标量转换异常: {r}"
        _log("to_dict 全部通过", "OK")

    run_test("to_dict", test_to_dict)

    # ==================================================================
    # 汇总报告
    # ==================================================================
    print("\n" + "=" * 60)
    print("  测试汇总")
    print("=" * 60)
    total = len(_passed) + len(_failed)
    print(f"  总计: {total}  |  通过: {len(_passed)}  |  失败: {len(_failed)}")
    print()

    if _passed:
        print("  [通过的接口]")
        for name in _passed:
            print(f"    ✓ {name}")
        print()

    if _failed:
        print("  [失败的接口] <<<< 以下接口需要修改 >>>>")
        for name, err in _failed:
            # 只取最后一行异常信息作为摘要
            last_line = err.strip().splitlines()[-1] if err.strip() else "未知错误"
            print(f"    ✗ {name}")
            print(f"      原因: {last_line}")
        print()
    else:
        print("  所有接口全部通过！")
        print()

    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
