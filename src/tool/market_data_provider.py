"""
统一行情数据提供者 - 所有股票/市场数据的唯一入口。

所有工具模块（stock_info_request、technical_analysis、hot_money、big_deal_analysis、
chip_analysis、risk_control 等）统一通过本模块获取数据，不再直接导入 efinance / akshare。
如需更换数据源，只需修改本文件即可。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from src.logger import logger

# ---------------------------------------------------------------------------
# tushare 初始化（0 积分爬虫接口，需要 token 但不消耗积分）
# ---------------------------------------------------------------------------
try:
    import tushare as ts  # type: ignore[import-untyped,import-not-found]

    from src.config import config as _app_config
    _ts_token = os.environ.get("TUSHARE_TOKEN", "") or _app_config.tushare_config.token
    if _ts_token:
        ts.set_token(_ts_token)
except ImportError:  # pragma: no cover - 可选依赖
    ts = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 可选的第三方数据库
# ---------------------------------------------------------------------------
try:
    import efinance as ef  # type: ignore[import-untyped,import-not-found]
except ImportError:  # pragma: no cover - 可选依赖
    ef = None  # type: ignore[assignment]

try:
    import akshare as ak  # type: ignore[import-untyped,import-not-found]
except ImportError:  # pragma: no cover - 可选依赖
    ak = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 延迟导入内部爬虫模块（避免模块级循环引用）
# ---------------------------------------------------------------------------

def _get_stock_capital_flow_func():
    """获取个股资金流向函数"""
    from src.tool.financial_deep_search.stock_capital import get_stock_capital_flow
    return get_stock_capital_flow

def _get_index_capital_flow_func():
    """获取指数资金流向函数"""
    from src.tool.financial_deep_search.index_capital import get_index_capital_flow
    return get_index_capital_flow

def _get_section_data_func():
    """获取板块数据函数"""
    from src.tool.financial_deep_search.get_section_data import get_all_section
    return get_all_section

def _get_risk_control_data_func():
    """获取风控数据函数"""
    from src.tool.financial_deep_search.risk_control_data import get_risk_control_data
    return get_risk_control_data


# ===========================================================================
# MarketDataProvider - 统一行情数据提供者
# ===========================================================================

class MarketDataProvider:
    """统一数据门面，封装所有外部数据源。"""

    # ------ 工具方法 --------------------------------------------------------

    @staticmethod
    def to_dict(data: Any) -> Any:
        """将 pandas 对象或其他类型转换为可 JSON 序列化的字典/列表。"""
        if isinstance(data, pd.DataFrame):
            return data.to_dict(orient="records") if not data.empty else []
        if isinstance(data, pd.Series):
            return {str(k): v for k, v in data.to_dict().items()}
        if isinstance(data, dict):
            return data
        if isinstance(data, (int, float, str, bool)):
            return {"value": data}
        return {"value": str(data)}

    # ------ 可用性检查 -----------------------------------------------------

    @staticmethod
    def efinance_available() -> bool:
        """检查 efinance 库是否可用"""
        return ef is not None

    @staticmethod
    def akshare_available() -> bool:
        """检查 akshare 库是否可用"""
        return ak is not None

    # ==================================================================
    # efinance 接口封装
    # ==================================================================

    def get_base_info(self, stock_code: str) -> Dict[str, Any]:
        """通过 efinance 获取股票基础信息。"""
        if ef is None:
            return {}
        data = ef.stock.get_base_info(stock_code)
        result = self.to_dict(data)
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        if isinstance(result, dict):
            return result
        return {}

    def get_realtime_quotes(self, stock_code: str) -> Dict[str, Any]:
        """通过 efinance 获取单只股票的实时行情，失败时使用 tushare 爬虫接口保底。"""
        # ---------- 主路径：efinance ----------
        if ef is not None:
            try:
                # 根据股票代码添加市场前缀
                if stock_code.startswith("6"):
                    formatted_code = f"sh{stock_code}"
                elif stock_code.startswith(("0", "3")):
                    formatted_code = f"sz{stock_code}"
                else:
                    formatted_code = stock_code

                quotes_df = ef.stock.get_realtime_quotes(formatted_code)
                if isinstance(quotes_df, pd.DataFrame) and not quotes_df.empty:
                    records = quotes_df.to_dict(orient="records")
                    if records:
                        return {str(k): v for k, v in records[0].items()}
            except Exception as e:
                logger.warning(f"efinance 获取实时行情失败({stock_code})，尝试 tushare 保底: {e}")

        # ---------- 保底路径：tushare realtime_quote（0 积分爬虫接口）----------
        if ts is not None:
            try:
                ts_code = self._to_ts_code(stock_code)
                df = ts.realtime_quote(ts_code=ts_code, src="dc")  # type: ignore[union-attr]
                if isinstance(df, pd.DataFrame) and not df.empty:
                    records = df.to_dict(orient="records")
                    if records:
                        return {str(k): v for k, v in records[0].items()}
            except Exception as e:
                logger.warning(f"tushare 保底获取实时行情也失败({stock_code}): {e}")

        return {}

    @staticmethod
    def _to_ts_code(stock_code: str) -> str:
        """将纯数字股票代码转为 tushare 标准代码格式（如 600519 -> 600519.SH）。"""
        if "." in stock_code:
            return stock_code
        if stock_code.startswith("6"):
            return f"{stock_code}.SH"
        elif stock_code.startswith(("0", "3")):
            return f"{stock_code}.SZ"
        elif stock_code.startswith(("4", "8")):
            return f"{stock_code}.BJ"
        return stock_code

    # efinance klt 值与标准分钟周期的映射
    _KLT_TO_PERIOD: Dict[int, str] = {1: "1", 5: "5", 15: "15", 30: "30", 60: "60"}

    @staticmethod
    def _to_sina_symbol(stock_code: str) -> str:
        """将纯数字股票代码转为新浪格式（如 600519 -> sh600519）。"""
        code = stock_code.lstrip("shsz")
        if code.startswith("6"):
            return f"sh{code}"
        elif code.startswith(("0", "3")):
            return f"sz{code}"
        return stock_code

    def get_quote_history(self, stock_code: str, klt: int) -> List[Dict[str, Any]]:
        """通过 efinance 获取 K 线历史数据（klt: 1=分钟, 101=日线 等），失败时多级保底。"""
        # ---------- 主路径：efinance ----------
        if ef is not None:
            try:
                kline_df = ef.stock.get_quote_history(stock_code, klt=klt)
                if isinstance(kline_df, pd.DataFrame) and not kline_df.empty:
                    data = self.to_dict(kline_df)
                    if isinstance(data, list) and data:
                        return data
            except Exception as e:
                logger.warning(f"efinance 获取K线失败({stock_code}, klt={klt})，尝试保底方案: {e}")

        # ---------- 保底路径 A：tushare pro.daily()（仅日线 klt=101）----------
        if klt == 101 and ts is not None:
            try:
                pro = ts.pro_api()  # type: ignore[union-attr]
                ts_code = self._to_ts_code(stock_code)
                df = pro.daily(ts_code=ts_code)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df = df.sort_values("trade_date").reset_index(drop=True)
                    data = self.to_dict(df)
                    if isinstance(data, list) and data:
                        return data
            except Exception as e:
                logger.warning(f"tushare 保底获取日线也失败({stock_code}): {e}")

        # ---------- 保底路径 B：akshare 分钟线（klt 为分钟级别）----------
        period = self._KLT_TO_PERIOD.get(klt)
        if period is not None and ak is not None:
            # B-1: 东财分时 stock_zh_a_hist_min_em（优先，数据更丰富）
            try:
                df = ak.stock_zh_a_hist_min_em(  # type: ignore[union-attr]
                    symbol=stock_code,
                    period=period,
                    adjust="",
                )
                if isinstance(df, pd.DataFrame) and not df.empty:
                    data = self.to_dict(df)
                    if isinstance(data, list) and data:
                        return data
            except Exception as e:
                logger.warning(f"akshare 东财分时失败({stock_code}, period={period}): {e}")

            # B-2: 新浪分时 stock_zh_a_minute（兜底）
            try:
                sina_symbol = self._to_sina_symbol(stock_code)
                df = ak.stock_zh_a_minute(  # type: ignore[union-attr]
                    symbol=sina_symbol,
                    period=period,
                    adjust="",
                )
                if isinstance(df, pd.DataFrame) and not df.empty:
                    data = self.to_dict(df)
                    if isinstance(data, list) and data:
                        return data
            except Exception as e:
                logger.warning(f"akshare 新浪分时也失败({stock_code}, period={period}): {e}")

        return []

    def get_daily_billboard(self, start_date: str, end_date: str) -> Any:
        """通过 efinance 获取龙虎榜数据。"""
        if ef is None:
            return None
        return ef.stock.get_daily_billboard(start_date=start_date, end_date=end_date)

    # ==================================================================
    # akshare 接口封装
    # ==================================================================

    def get_stock_fund_flow_big_deal(self) -> Any:
        """获取市场逐笔大单资金流向数据。"""
        if ak is None:
            return None
        return ak.stock_fund_flow_big_deal()

    def get_stock_fund_flow_individual(self, symbol: str = "即时") -> Any:
        """获取个股资金流排行榜数据。"""
        if ak is None:
            return None
        return ak.stock_fund_flow_individual(symbol=symbol)

    def get_stock_individual_fund_flow(self, stock_code: str, market: str = "sh") -> Any:
        """获取单只股票的资金流向趋势数据。"""
        if ak is None:
            return None
        return ak.stock_individual_fund_flow(stock=stock_code, market=market)

    def get_stock_zh_a_hist(
        self,
        stock_code: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "",
    ) -> Optional[pd.DataFrame]:
        """获取 A 股历史行情数据（日/周/月级别），akshare 失败时用 tushare 保底。"""
        # ---------- 主路径：akshare ----------
        if ak is not None:
            try:
                kwargs: Dict[str, Any] = {
                    "symbol": stock_code,
                    "period": period,
                    "adjust": adjust,
                }
                if start_date is not None:
                    kwargs["start_date"] = start_date
                if end_date is not None:
                    kwargs["end_date"] = end_date
                df = ak.stock_zh_a_hist(**kwargs)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"akshare get_stock_zh_a_hist 失败({stock_code}, period={period})，尝试 tushare 保底: {e}")

        # ---------- 保底路径：tushare ----------
        if ts is None:
            return None
        try:
            pro = ts.pro_api()  # type: ignore[union-attr]
            ts_code = self._to_ts_code(stock_code)
            ts_kwargs: Dict[str, Any] = {"ts_code": ts_code}
            if start_date is not None:
                ts_kwargs["start_date"] = start_date
            if end_date is not None:
                ts_kwargs["end_date"] = end_date

            df: Optional[pd.DataFrame] = None

            if period == "daily":
                # 保底 1：tushare pro.daily()（120 积分，未复权日线）
                df = pro.daily(**ts_kwargs)
            elif period in ("weekly", "monthly"):
                # akshare period 映射到 tushare freq
                freq = "week" if period == "weekly" else "month"
                ts_kwargs["freq"] = freq

                if adjust in ("qfq", "hfq"):
                    # 保底 3：stk_week_month_adj（复权周/月线，每日更新，2000 积分）
                    df = pro.stk_week_month_adj(**ts_kwargs)
                else:
                    # 保底 2：stk_weekly_monthly（不复权周/月线，每日更新，2000 积分）
                    df = pro.stk_weekly_monthly(**ts_kwargs)

            if isinstance(df, pd.DataFrame) and not df.empty:
                df = df.sort_values("trade_date").reset_index(drop=True)
                return df
        except Exception as e:
            logger.warning(f"tushare 保底获取历史行情也失败({stock_code}, period={period}): {e}")

        return None

    def get_stock_zh_a_spot_em(self) -> Optional[pd.DataFrame]:
        """获取 A 股全市场实时行情快照（东方财富），akshare 失败时用 tushare realtime_list 保底。"""
        # ---------- 主路径：akshare ----------
        if ak is not None:
            try:
                df = ak.stock_zh_a_spot_em()
                if isinstance(df, pd.DataFrame) and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"akshare stock_zh_a_spot_em 失败，尝试 tushare 保底: {e}")

        # ---------- 保底路径：tushare realtime_list（0 积分，爬虫接口）----------
        if ts is not None:
            try:
                df = ts.realtime_list(src="dc")  # type: ignore[union-attr]
                if isinstance(df, pd.DataFrame) and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"tushare realtime_list(dc) 失败: {e}")
            # 东财源失败时再尝试新浪源
            try:
                df = ts.realtime_list(src="sina")  # type: ignore[union-attr]
                if isinstance(df, pd.DataFrame) and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"tushare realtime_list(sina) 也失败: {e}")

            # ---------- 最终保底：tushare daily_basic（当日全市场每日指标，2000 积分）----------
            try:
                pro = ts.pro_api()  # type: ignore[union-attr]
                from datetime import datetime, timedelta
                today = datetime.now()
                # daily_basic 在 15~17 点入库，当天可能尚无数据，最多回退 5 天
                for offset in range(6):
                    date_str = (today - timedelta(days=offset)).strftime("%Y%m%d")
                    df = pro.daily_basic(ts_code="", trade_date=date_str)
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        return df
            except Exception as e:
                logger.warning(f"tushare daily_basic 最终保底也失败: {e}")

        return None

    def get_stock_cyq_em(self, stock_code: str, adjust: str = "") -> Optional[pd.DataFrame]:
        """获取东方财富筹码分布数据。"""
        if ak is None:
            return None
        return ak.stock_cyq_em(symbol=stock_code, adjust=adjust)

    # ==================================================================
    # 东方财富内部爬虫接口（financial_deep_search）
    # ==================================================================

    def get_stock_capital_flow(self, stock_code: str = "", **kwargs: Any) -> Dict[str, Any]:
        """获取个股资金流向数据。"""
        fn = _get_stock_capital_flow_func()
        if stock_code:
            return fn(stock_code=stock_code, **kwargs)
        return fn(**kwargs)

    def get_index_capital_flow(self, index_code: str = "000001") -> Dict[str, Any]:
        """获取指数资金流向数据。"""
        fn = _get_index_capital_flow_func()
        return fn(index_code=index_code)

    def get_section_data(self, sector_types: Optional[str] = None) -> Dict[str, Any]:
        """获取板块行情数据（热门/概念/行业/地域）。"""
        fn = _get_section_data_func()
        return fn(sector_types=sector_types)

    def get_risk_control_data(self, **kwargs: Any) -> Dict[str, Any]:
        """获取风控数据（财务报表 + 法务公告）。"""
        fn = _get_risk_control_data_func()
        return fn(**kwargs)


# ---------------------------------------------------------------------------
# 模块级单例 - 在其他模块中直接 import market_data_provider 使用
# ---------------------------------------------------------------------------
market_data_provider = MarketDataProvider()
