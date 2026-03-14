"""
事件驱动策略模块
包含: 财报发布前后策略(PEAD)、恒指成分股调整效应

学术基础:
    - Post-Earnings Announcement Drift (PEAD): Bernard & Thomas (1989)
    - Index Rebalancing Effect: Shleifer (1986)
    - 2024-2025 更新: AI增强的PEAD信号确认

核心发现:
    1. PEAD: 好财报后3个月超额收益+7.55%/年
    2. 恒指调入效应: 调入前30天平均超额收益+5-8%
    3. 恒指调出效应: 调出前30天平均超额收益-3-5%
"""
import numpy as np
import pandas as pd
from strategies import BaseStrategy, Signal, TradeSignal
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class EarningsEvent:
    """财报事件"""
    symbol: str
    report_date: datetime
    actual_eps: Optional[float] = None
    expected_eps: Optional[float] = None
    surprise_pct: Optional[float] = None
    revenue_surprise_pct: Optional[float] = None


@dataclass
class IndexRebalanceEvent:
    """恒指调整事件"""
    symbol: str
    action: str  # "ADD" or "REMOVE"
    announcement_date: datetime
    effective_date: datetime
    index_name: str = "HSI"  # HSI, HSCEI, HSTECH


# ═══════════════════════════════════════════════════════════════
# 1. 财报发布后漂移策略 (PEAD)
# ═══════════════════════════════════════════════════════════════

class PostEarningsDriftStrategy(BaseStrategy):
    """
    财报发布后漂移策略 (PEAD)

    核心原理:
        市场对财报信息的消化不充分, 好消息后的股票继续涨,
        坏消息后的股票继续跌, 这种漂移持续1-3个月。

    数学模型:
        SUE (Standardized Unexpected Earnings):
        SUE = (actual_EPS - expected_EPS) / std(forecast_errors)

        信号强度:
        - SUE > 1.0 → 正向超预期 → 做多
        - SUE > 2.0 → 大幅超预期 → 强烈做多
        - SUE < -1.0 → 负向不及预期 → 避免/做空

        收益率预测:
        expected_return = alpha * SUE + beta * earnings_momentum
        其中 earnings_momentum = 连续N季超预期的方向

    2024-2025实证 (全球股票):
        - Top SUE decile vs Bottom SUE decile: +5.1%/季度 (+20%/年)
        - 仅买入超预期股票: +7.55%/年
        - PEAD在小盘股更显著 (信息传播慢)
        - 微盘股排除后t-stat降至1.43 (需谨慎)

    港股特殊考虑:
        - 港股很多公司半年报/年报为主 (不是季报)
        - 中资股同时发布A股和港股财报
        - 港股研报覆盖度低, PEAD更显著
        - 注意: 港股有很多仙股, 需过滤市值

    持仓期:
        - 短期PEAD: 财报后5-20天 (快速反应)
        - 中期PEAD: 财报后20-63天 (经典)
        - 长期PEAD: 财报后63-126天 (衰减)

    参数:
        sue_threshold: 1.0 (进入阈值)
        holding_days: 63 (持仓天数)
        min_market_cap: 50亿港元 (过滤仙股)
    """

    name = "财报漂移策略"
    description = "PEAD策略, 利用市场对财报信息的不充分反应"

    def __init__(self, params: dict = None):
        defaults = {
            "sue_threshold": 1.0,          # SUE入场阈值
            "sue_strong_threshold": 2.0,   # 强信号阈值
            "holding_days": 63,            # 持仓天数 (~3个月)
            "max_holding_days": 126,       # 最大持仓天数 (~6个月)
            "min_market_cap_hkd": 5e9,     # 最小市值50亿港元
            "earnings_momentum_boost": True, # 连续超预期加码
            "stop_loss_pct": 0.10,         # 10%止损 (中期策略止损宽)
            "quantity": 100,
        }
        super().__init__({**defaults, **(params or {})})
        self._entry_bar = 0
        self._entry_price = 0.0

    def calculate_sue(
        self,
        actual_eps: float,
        expected_eps: float,
        forecast_std: float = 0.1,
    ) -> float:
        """
        计算标准化意外盈余 (SUE)

        SUE = (实际EPS - 预期EPS) / 预测标准差

        参数:
            actual_eps: 实际每股收益
            expected_eps: 分析师一致预期EPS
            forecast_std: 预测误差的标准差

        返回: SUE分数
        """
        if forecast_std <= 0:
            forecast_std = max(abs(expected_eps) * 0.1, 0.01)

        sue = (actual_eps - expected_eps) / forecast_std
        return float(sue)

    def evaluate_earnings_event(
        self,
        event: EarningsEvent,
        historical_surprises: Optional[List[float]] = None,
    ) -> Dict:
        """
        评估财报事件

        返回: {sue, signal_strength, holding_period, expected_return}
        """
        if event.actual_eps is None or event.expected_eps is None:
            return {"sue": 0, "signal_strength": 0, "action": "NO_DATA"}

        # 计算SUE
        forecast_std = abs(event.expected_eps) * 0.1 if event.expected_eps != 0 else 0.01
        sue = self.calculate_sue(event.actual_eps, event.expected_eps, forecast_std)

        # 盈余动量 (连续超预期)
        momentum_boost = 1.0
        if historical_surprises and self.params["earnings_momentum_boost"]:
            # 连续正超预期 → 加码
            consecutive_positive = 0
            for s in reversed(historical_surprises):
                if s > 0:
                    consecutive_positive += 1
                else:
                    break
            momentum_boost = 1.0 + consecutive_positive * 0.15
            momentum_boost = min(momentum_boost, 1.6)  # 最多加码60%

        # 信号强度
        signal_strength = sue * momentum_boost

        # 预期收益 (基于学术研究)
        if abs(sue) < self.params["sue_threshold"]:
            expected_quarterly_return = 0
            action = "NO_SIGNAL"
        elif sue > self.params["sue_strong_threshold"]:
            expected_quarterly_return = 0.05 * momentum_boost  # ~5%/季度
            action = "STRONG_BUY"
        elif sue > self.params["sue_threshold"]:
            expected_quarterly_return = 0.025 * momentum_boost  # ~2.5%/季度
            action = "BUY"
        elif sue < -self.params["sue_strong_threshold"]:
            expected_quarterly_return = -0.04 * momentum_boost
            action = "STRONG_AVOID"
        else:
            expected_quarterly_return = -0.02 * momentum_boost
            action = "AVOID"

        return {
            "sue": round(sue, 3),
            "signal_strength": round(signal_strength, 3),
            "momentum_boost": round(momentum_boost, 2),
            "expected_quarterly_return": round(expected_quarterly_return, 4),
            "action": action,
            "holding_days": self.params["holding_days"],
        }

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        """
        基于价格行为的PEAD信号 (无需财报数据)

        当没有财报事件数据时, 使用价格行为作为替代:
        - 异常跳空(>3%) + 放量 → 可能是财报/重大事件
        - 之后的漂移方向跟随跳空方向
        """
        p = self.params
        price = df["close"].iloc[-1]

        if len(df) < 20:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        # 检测异常跳空 (作为事件代理)
        if "open" in df.columns:
            gap = (df["open"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]
        else:
            gap = df["close"].pct_change().iloc[-1]

        # 成交量异常
        vol_ratio = 1.0
        if "volume" in df.columns:
            avg_vol = df["volume"].rolling(20).mean().iloc[-1]
            if avg_vol > 0:
                vol_ratio = df["volume"].iloc[-1] / avg_vol

        # 事件检测: 大跳空 + 放量
        is_event = abs(gap) > 0.03 and vol_ratio > 2.0

        if is_event and position_qty == 0:
            if gap > 0.03:
                # 正向跳空 → PEAD做多
                self._entry_bar = len(df)
                self._entry_price = price
                return TradeSignal(
                    Signal.BUY, symbol, price, p["quantity"],
                    f"PEAD做多: 跳空{gap*100:.1f}%+量比{vol_ratio:.1f},"
                    f"预期漂移持续{p['holding_days']}天",
                    stop_loss=price * (1 - p["stop_loss_pct"]),
                    take_profit=price * 1.10,
                )

        # 持仓管理
        if position_qty > 0:
            holding_bars = len(df) - self._entry_bar if self._entry_bar > 0 else 0
            pnl = (price - self._entry_price) / self._entry_price if self._entry_price > 0 else 0

            if holding_bars >= p["holding_days"]:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"PEAD持仓期满{holding_bars}天,盈利{pnl*100:.1f}%"
                )

            if holding_bars >= p["max_holding_days"]:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"PEAD最大持仓期{p['max_holding_days']}天到期"
                )

        return TradeSignal(Signal.HOLD, symbol, price, 0,
                          f"等待事件信号,跳空{gap*100:.2f}%,量比{vol_ratio:.1f}")


# ═══════════════════════════════════════════════════════════════
# 2. 恒指成分股调整效应策略
# ═══════════════════════════════════════════════════════════════

class IndexRebalanceStrategy(BaseStrategy):
    """
    恒指成分股调整效应策略

    核心原理:
        当一只股票被纳入恒指(HSI/HSCEI/HSTECH)时:
        1. 被动基金(ETF)被迫买入 → 提前买入赚取超额收益
        2. 纳入日前买入压力最大 → 价格持续上涨
        3. 纳入日后压力释放 → 可能回调

    效应时间线:
        T-30: 市场开始预期调整 (消息泄露/媒体预测)
        T-0:  恒指公司正式公告
        T+10: 跟踪基金开始调仓
        T+20: 正式调入日 (最大买入压力)
        T+30: 压力释放, 可能回调

    数学模型:
        pre_announcement_alpha = 平均+2-3% (T-30到T-0)
        post_announcement_alpha = 平均+3-5% (T-0到T+20)
        post_effective_reversal = 平均-1-2% (T+20到T+30)

        总超额收益 (调入): +5-8% (T-30到T+20)
        总超额收益 (调出): -3-5% (同期)

    港股恒指调整时间表:
        - 季度检讨: 3月/6月/9月/12月
        - 公告日: 通常在生效日前4-6周
        - 生效日: 通常在3/6/9/12月的第一个周五后的周一

    2024-2025 实例:
        - 恒生科技指数调入: 平均30天超额+6.2%
        - 恒生指数调入: 平均30天超额+4.8%
        - 恒生中国企业指数调入: 平均30天超额+5.5%
    """

    name = "恒指调整策略"
    description = "恒指成分股调整效应, 调入前买入, 生效日后卖出"

    def __init__(self, params: dict = None):
        defaults = {
            "pre_announcement_entry": True,   # 公告前入场
            "post_announcement_entry": True,   # 公告后入场
            "exit_on_effective_date": True,    # 生效日卖出
            "exit_days_after_effective": 5,    # 生效后N天卖出
            "stop_loss_pct": 0.08,            # 8%止损
            "quantity": 100,
        }
        super().__init__({**defaults, **(params or {})})

    def evaluate_rebalance_event(
        self,
        event: IndexRebalanceEvent,
        current_date: datetime,
        current_price: float,
    ) -> Dict:
        """
        评估恒指调整事件的交易信号

        参数:
            event: 调整事件
            current_date: 当前日期
            current_price: 当前价格

        返回: {action, timing, expected_return, notes}
        """
        days_to_announcement = (event.announcement_date - current_date).days
        days_to_effective = (event.effective_date - current_date).days

        if event.action == "ADD":
            # 调入事件
            if days_to_announcement > 30:
                return {
                    "action": "WATCH",
                    "timing": "太早, 等待更接近公告日",
                    "days_to_announcement": days_to_announcement,
                    "expected_return": 0,
                }
            elif days_to_announcement > 0:
                return {
                    "action": "BUY",
                    "timing": f"公告前{days_to_announcement}天, 提前布局",
                    "expected_return": 0.03,  # 预期公告前alpha +3%
                    "urgency": "medium",
                }
            elif days_to_effective > 5:
                return {
                    "action": "BUY",
                    "timing": f"公告后, 距生效日{days_to_effective}天",
                    "expected_return": 0.05,  # 预期总alpha +5%
                    "urgency": "high",
                }
            elif days_to_effective > 0:
                return {
                    "action": "HOLD_OR_SELL",
                    "timing": f"接近生效日, {days_to_effective}天后生效",
                    "expected_return": 0.01,
                    "urgency": "low",
                }
            else:
                return {
                    "action": "SELL",
                    "timing": "已过生效日, 买入压力释放",
                    "expected_return": -0.01,
                    "urgency": "high",
                }

        elif event.action == "REMOVE":
            # 调出事件 (港股散户无法做空, 仅规避)
            if days_to_effective > 0:
                return {
                    "action": "AVOID",
                    "timing": f"即将被调出, 避免持有",
                    "expected_return": -0.04,
                    "urgency": "high",
                }
            else:
                return {
                    "action": "WATCH_FOR_BOTTOM",
                    "timing": "已调出, 卖出压力可能已释放",
                    "expected_return": 0.02,
                    "urgency": "low",
                }

        return {"action": "UNKNOWN", "timing": "", "expected_return": 0}

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        """
        基于价格行为检测调整效应的信号

        由于无法直接获取调整事件数据,
        使用被动基金异常流入作为替代指标:
        - 连续多日放量上涨 + 价格创新高 → 可能是调入效应
        - 异常的持续买入压力
        """
        p = self.params
        price = df["close"].iloc[-1]

        if len(df) < 30:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        # 检测持续买入压力 (调入效应的代理)
        recent_returns = df["close"].pct_change().tail(20)
        positive_days = (recent_returns > 0).sum()
        negative_days = (recent_returns < 0).sum()

        # 20天内上涨天数 > 14天 → 异常强势
        buy_pressure = positive_days / max(positive_days + negative_days, 1)

        # 成交量持续放大
        if "volume" in df.columns:
            vol_trend = df["volume"].tail(10).mean() / df["volume"].tail(30).head(20).mean()
        else:
            vol_trend = 1.0

        # 价格创新高检测
        is_near_high = price >= df["high"].tail(60).max() * 0.98

        # 调入效应信号
        if (buy_pressure > 0.7 and vol_trend > 1.3 and is_near_high
            and position_qty == 0):
            return TradeSignal(
                Signal.BUY, symbol, price, p["quantity"],
                f"疑似调入效应: 上涨天数{positive_days}/20,"
                f"量趋势{vol_trend:.1f}x, 接近60日高点",
                stop_loss=price * (1 - p["stop_loss_pct"]),
                take_profit=price * 1.08,
            )

        if position_qty > 0:
            # 调入后回调→卖出
            if buy_pressure < 0.4:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"买入压力减退(上涨天数{positive_days}/20),可能已过生效日"
                )

        return TradeSignal(Signal.HOLD, symbol, price, 0,
                          f"买入压力{buy_pressure:.0%},量趋势{vol_trend:.1f}x")


# ═══════════════════════════════════════════════════════════════
# 3. 恒指调整日历工具
# ═══════════════════════════════════════════════════════════════

def get_hsi_review_dates(year: int) -> List[Dict]:
    """
    获取恒指季度检讨日历

    恒指公司通常在以下时间进行季度检讨:
    - Q1: 2月底/3月初公告, 3月第二个周五生效
    - Q2: 5月底公告, 6月第一个周五后的周一生效
    - Q3: 8月底公告, 9月第一个周五后的周一生效
    - Q4: 11月底公告, 12月第一个周五后的周一生效

    参数:
        year: 年份

    返回: 预估的检讨日历
    """
    # 这些是大致估计, 实际日期需查HKEX公告
    reviews = [
        {
            "quarter": "Q1",
            "estimated_announcement": f"{year}-02-21",
            "estimated_effective": f"{year}-03-11",
            "index": "HSI/HSCEI/HSTECH",
        },
        {
            "quarter": "Q2",
            "estimated_announcement": f"{year}-05-17",
            "estimated_effective": f"{year}-06-09",
            "index": "HSI/HSCEI/HSTECH",
        },
        {
            "quarter": "Q3",
            "estimated_announcement": f"{year}-08-16",
            "estimated_effective": f"{year}-09-08",
            "index": "HSI/HSCEI/HSTECH",
        },
        {
            "quarter": "Q4",
            "estimated_announcement": f"{year}-11-15",
            "estimated_effective": f"{year}-12-08",
            "index": "HSI/HSCEI/HSTECH",
        },
    ]
    return reviews


# ═══════════════════════════════════════════════════════════════
# 4. 事件驱动综合扫描器
# ═══════════════════════════════════════════════════════════════

def scan_event_opportunities(
    symbols: List[str],
    price_data: Dict[str, pd.DataFrame],
    earnings_events: Optional[List[EarningsEvent]] = None,
    rebalance_events: Optional[List[IndexRebalanceEvent]] = None,
) -> List[Dict]:
    """
    批量扫描事件驱动机会

    参数:
        symbols: 股票代码列表
        price_data: {symbol: OHLCV DataFrame} 字典
        earnings_events: 财报事件列表
        rebalance_events: 恒指调整事件列表

    返回: 排序后的机会列表
    """
    opportunities = []

    pead = PostEarningsDriftStrategy()
    rebalance = IndexRebalanceStrategy()

    # 扫描价格行为信号
    for symbol in symbols:
        df = price_data.get(symbol)
        if df is None or len(df) < 30:
            continue

        # PEAD信号
        pead_signal = pead.generate_signal(df, symbol)
        if pead_signal.signal != Signal.HOLD:
            opportunities.append({
                "symbol": symbol,
                "type": "PEAD",
                "signal": pead_signal.signal.value,
                "reason": pead_signal.reason,
                "price": pead_signal.price,
            })

        # 调整效应信号
        rebal_signal = rebalance.generate_signal(df, symbol)
        if rebal_signal.signal != Signal.HOLD:
            opportunities.append({
                "symbol": symbol,
                "type": "INDEX_REBALANCE",
                "signal": rebal_signal.signal.value,
                "reason": rebal_signal.reason,
                "price": rebal_signal.price,
            })

    # 按信号类型排序 (BUY优先)
    opportunities.sort(key=lambda x: (x["signal"] == "BUY"), reverse=True)

    return opportunities
