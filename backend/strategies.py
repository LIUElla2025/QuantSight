"""
量化交易策略模块
内置多种经典量化策略，支持实盘和回测两种模式
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradeSignal:
    signal: Signal
    symbol: str
    price: float
    quantity: int
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class BaseStrategy:
    """策略基类，所有策略必须继承"""

    name: str = "BaseStrategy"
    description: str = ""

    def __init__(self, params: dict = None):
        self.params = params or {}

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        """根据历史数据生成交易信号，子类必须实现"""
        raise NotImplementedError

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "params": self.params,
        }


def _calc_rsi_wilder(prices: pd.Series, period: int) -> pd.Series:
    """Wilder 平滑法 RSI（标准实现，比 rolling().mean() 更准确）"""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # 修正：填充NaN为50（中性值），避免NaN传播到下游计算
    return rsi.fillna(50.0)


def _calc_atr_series(df: pd.DataFrame, period: int) -> float:
    """计算 ATR（平均真实波幅）"""
    high, low, prev_close = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


class MACrossStrategy(BaseStrategy):
    """
    均线交叉策略（双均线金叉/死叉）+ 成交量确认 + ATR止损
    - 短期均线金叉长期均线 + 量比 > 1.2 → 买入
    - 短期均线死叉长期均线 → 卖出
    - ATR动态止损替代固定百分比，适应市场波动
    """

    name = "MA交叉策略"
    description = "双均线金叉+量价确认买入，ATR动态止损"

    def __init__(self, params: dict = None):
        defaults = {"short_period": 5, "long_period": 20, "atr_period": 14,
                    "atr_stop_mult": 2.0, "quantity": 100}
        super().__init__({**defaults, **(params or {})})

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        short = self.params["short_period"]
        long_ = self.params["long_period"]
        qty = self.params["quantity"]

        if len(df) < long_ + 1:
            return TradeSignal(Signal.HOLD, symbol, df["close"].iloc[-1], 0, "数据不足")

        df = df.copy()
        df["ma_short"] = df["close"].rolling(window=short).mean()
        df["ma_long"] = df["close"].rolling(window=long_).mean()

        curr_short = df["ma_short"].iloc[-1]
        curr_long = df["ma_long"].iloc[-1]
        prev_short = df["ma_short"].iloc[-2]
        prev_long = df["ma_long"].iloc[-2]
        price = df["close"].iloc[-1]

        # 成交量确认：当前成交量需高于近期均量
        vol_ok = True
        vol_info = ""
        if "volume" in df.columns:
            # 修正：off-by-one，排除当前bar，用前long_个bar的均量
            avg_vol = df["volume"].iloc[-(long_ + 1):-1].mean()
            curr_vol = df["volume"].iloc[-1]
            vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
            vol_ok = vol_ratio >= 1.2
            vol_info = f"，量比{vol_ratio:.1f}"

        # ATR动态止损
        atr = _calc_atr_series(df, self.params["atr_period"])

        # 金叉买入（需量价配合）
        if prev_short <= prev_long and curr_short > curr_long and position_qty == 0 and vol_ok:
            stop_loss = price - atr * self.params["atr_stop_mult"]
            return TradeSignal(
                Signal.BUY, symbol, price, qty,
                f"MA{short}金叉MA{long_}{vol_info}，止损{stop_loss:.2f}(ATR={atr:.2f})",
                stop_loss=stop_loss,
                take_profit=price + atr * self.params["atr_stop_mult"] * 2.5,
            )

        # 死叉卖出
        if prev_short >= prev_long and curr_short < curr_long and position_qty > 0:
            return TradeSignal(
                Signal.SELL, symbol, price, position_qty,
                f"MA{short}死叉MA{long_}，短均线{curr_short:.2f}<长均线{curr_long:.2f}",
            )

        return TradeSignal(Signal.HOLD, symbol, price, 0, "均线无交叉，持仓观望")


class RSIStrategy(BaseStrategy):
    """
    RSI 相对强弱策略
    - RSI < 超卖线 → 买入（超跌反弹）
    - RSI > 超买线 → 卖出（获利了结）
    适合震荡行情的反转策略
    """

    name = "RSI策略"
    description = "RSI超卖买入、超买卖出，适合震荡行情"

    def __init__(self, params: dict = None):
        defaults = {"period": 14, "oversold": 30, "overbought": 70,
                    "trend_period": 50, "quantity": 100}
        super().__init__({**defaults, **(params or {})})

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        period = self.params["period"]
        oversold = self.params["oversold"]
        overbought = self.params["overbought"]
        qty = self.params["quantity"]
        price = df["close"].iloc[-1]
        trend_period = self.params.get("trend_period", 50)

        if len(df) < max(period + 1, trend_period):
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        # Wilder 法 RSI（修正：原 rolling().mean() 不准确）
        rsi_series = _calc_rsi_wilder(df["close"], period)
        curr_rsi = float(rsi_series.iloc[-1])

        # 趋势过滤：RSI超卖但处于长期下行趋势时不买（避免价值陷阱）
        trend_ma = df["close"].rolling(trend_period).mean()
        in_uptrend = df["close"].iloc[-1] > trend_ma.iloc[-1]

        atr = _calc_atr_series(df, period)

        if curr_rsi < oversold and position_qty == 0 and in_uptrend:
            return TradeSignal(
                Signal.BUY, symbol, price, qty,
                f"RSI={curr_rsi:.1f}<{oversold}超卖+长期趋势向上，反弹买入",
                stop_loss=price - atr * 2.0,
                take_profit=price + atr * 3.0,
            )

        if curr_rsi < oversold and position_qty == 0 and not in_uptrend:
            return TradeSignal(Signal.HOLD, symbol, price, 0,
                               f"RSI={curr_rsi:.1f}超卖但趋势向下，跳过避免价值陷阱")

        if curr_rsi > overbought and position_qty > 0:
            return TradeSignal(
                Signal.SELL, symbol, price, position_qty,
                f"RSI={curr_rsi:.1f}>{overbought}超买，获利卖出",
            )

        trend_str = "上行" if in_uptrend else "下行"
        return TradeSignal(Signal.HOLD, symbol, price, 0,
                           f"RSI={curr_rsi:.1f}，趋势{trend_str}，观望")


class BollingerBandStrategy(BaseStrategy):
    """
    布林带策略
    - 价格跌破下轨 → 买入（均值回归）
    - 价格突破上轨 → 卖出（获利了结）
    适合区间震荡行情
    """

    name = "布林带策略"
    description = "价格触及布林带上下轨时反向交易"

    def __init__(self, params: dict = None):
        defaults = {"period": 20, "std_dev": 2.0, "quantity": 100}
        super().__init__({**defaults, **(params or {})})

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        period = self.params["period"]
        std_dev = self.params["std_dev"]
        qty = self.params["quantity"]
        price = df["close"].iloc[-1]

        if len(df) < period:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        df = df.copy()
        df["sma"] = df["close"].rolling(window=period).mean()
        df["std"] = df["close"].rolling(window=period).std()
        df["upper"] = df["sma"] + std_dev * df["std"]
        df["lower"] = df["sma"] - std_dev * df["std"]

        upper = df["upper"].iloc[-1]
        lower = df["lower"].iloc[-1]
        sma = df["sma"].iloc[-1]

        if price <= lower and position_qty == 0:
            return TradeSignal(
                Signal.BUY, symbol, price, qty,
                f"价格{price:.2f}触及下轨{lower:.2f}，均值回归买入",
                stop_loss=price * 0.95,
                take_profit=sma,
            )

        if price >= upper and position_qty > 0:
            return TradeSignal(
                Signal.SELL, symbol, price, position_qty,
                f"价格{price:.2f}突破上轨{upper:.2f}，获利卖出",
            )

        return TradeSignal(Signal.HOLD, symbol, price, 0, f"价格在布林带内(下轨{lower:.2f},上轨{upper:.2f})，观望")


class MACDStrategy(BaseStrategy):
    """
    MACD 策略
    - MACD 柱状图由负转正（DIF 上穿 DEA）→ 买入
    - MACD 柱状图由正转负（DIF 下穿 DEA）→ 卖出
    经典的趋势确认指标
    """

    name = "MACD策略"
    description = "MACD金叉买入、死叉卖出，趋势确认"

    def __init__(self, params: dict = None):
        defaults = {"fast": 12, "slow": 26, "signal": 9, "quantity": 100}
        super().__init__({**defaults, **(params or {})})

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        fast = self.params["fast"]
        slow = self.params["slow"]
        sig_period = self.params["signal"]
        qty = self.params["quantity"]
        price = df["close"].iloc[-1]

        if len(df) < slow + sig_period:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        df = df.copy()
        df["ema_fast"] = df["close"].ewm(span=fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=slow, adjust=False).mean()
        df["dif"] = df["ema_fast"] - df["ema_slow"]
        df["dea"] = df["dif"].ewm(span=sig_period, adjust=False).mean()
        df["histogram"] = df["dif"] - df["dea"]

        curr_hist = df["histogram"].iloc[-1]
        prev_hist = df["histogram"].iloc[-2]

        if prev_hist <= 0 and curr_hist > 0 and position_qty == 0:
            return TradeSignal(
                Signal.BUY, symbol, price, qty,
                f"MACD柱状图由负转正({prev_hist:.4f}→{curr_hist:.4f})，金叉买入",
                stop_loss=price * 0.95,
                take_profit=price * 1.12,
            )

        if prev_hist >= 0 and curr_hist < 0 and position_qty > 0:
            return TradeSignal(
                Signal.SELL, symbol, price, position_qty,
                f"MACD柱状图由正转负({prev_hist:.4f}→{curr_hist:.4f})，死叉卖出",
            )

        return TradeSignal(Signal.HOLD, symbol, price, 0, f"MACD柱状图={curr_hist:.4f}，无交叉信号")


class VolumeBreakoutStrategy(BaseStrategy):
    """
    放量突破策略
    - 价格突破近期高点 + 成交量放大 → 买入
    - 价格跌破止损线或放量下跌 → 卖出
    适合捕捉突破行情
    """

    name = "放量突破策略"
    description = "价格突破+成交量放大时入场"

    def __init__(self, params: dict = None):
        defaults = {"lookback": 20, "volume_ratio": 1.5, "quantity": 100}
        super().__init__({**defaults, **(params or {})})

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        lookback = self.params["lookback"]
        vol_ratio = self.params["volume_ratio"]
        qty = self.params["quantity"]
        price = df["close"].iloc[-1]

        if len(df) < lookback + 1 or "volume" not in df.columns:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足或缺少成交量")

        recent_high = df["high"].iloc[-lookback - 1:-1].max()
        avg_volume = df["volume"].iloc[-lookback - 1:-1].mean()
        curr_volume = df["volume"].iloc[-1]

        if price > recent_high and curr_volume > avg_volume * vol_ratio and position_qty == 0:
            return TradeSignal(
                Signal.BUY, symbol, price, qty,
                f"价格{price:.2f}突破{lookback}日高点{recent_high:.2f}，量比{curr_volume / avg_volume:.1f}倍放量",
                stop_loss=recent_high * 0.97,
                take_profit=price * 1.15,
            )

        # 跌破20日低点则止损
        recent_low = df["low"].iloc[-lookback - 1:-1].min()
        if price < recent_low and position_qty > 0:
            return TradeSignal(
                Signal.SELL, symbol, price, position_qty,
                f"价格{price:.2f}跌破{lookback}日低点{recent_low:.2f}，止损卖出",
            )

        return TradeSignal(Signal.HOLD, symbol, price, 0, "无突破信号")


class MultiFactorStrategy(BaseStrategy):
    """
    多因子融合策略（研究驱动）
    综合 RSI + MACD + 布林带 + 均线 + 成交量 五大技术指标
    采用加权投票机制：多数指标看多才买入，多数看空才卖出
    灵感来源：顶级量化基金的多信号融合方法（Two Sigma / D.E. Shaw）
    优势：单一指标失灵时，其他指标提供保护，显著降低假信号
    """

    name = "多因子融合策略"
    description = "RSI+MACD+布林带+均线+量价五因子加权投票，多数确认才交易"

    def __init__(self, params: dict = None):
        defaults = {
            "rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 65,
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "bb_period": 20, "bb_std": 2.0,
            "ma_short": 5, "ma_long": 20,
            "vol_lookback": 20, "vol_ratio": 1.3,
            "buy_threshold": 3,   # 至少3个因子看多才买
            "sell_threshold": 3,  # 至少3个因子看空才卖
            "quantity": 100,
            "stop_loss_pct": 0.07,   # 7%止损
            "take_profit_pct": 0.20, # 20%止盈
        }
        super().__init__({**defaults, **(params or {})})

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        p = self.params
        price = df["close"].iloc[-1]
        min_data = max(p["macd_slow"] + p["macd_signal"], p["bb_period"], p["ma_long"], p["vol_lookback"]) + 2

        if len(df) < min_data:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        df = df.copy()
        buy_score = 0.0
        sell_score = 0.0
        reasons_buy = []
        reasons_sell = []

        # ── 因子1: RSI（权重1.5，Wilder法修正）──
        rsi = float(_calc_rsi_wilder(df["close"], p["rsi_period"]).iloc[-1])
        if rsi < p["rsi_oversold"]:
            buy_score += 1.5
            reasons_buy.append(f"RSI={rsi:.0f}超卖")
        elif rsi > p["rsi_overbought"]:
            sell_score += 1.5
            reasons_sell.append(f"RSI={rsi:.0f}超买")

        # ── 因子2: MACD（权重1.5，趋势指标更重要）──
        df["ema_f"] = df["close"].ewm(span=p["macd_fast"], adjust=False).mean()
        df["ema_s"] = df["close"].ewm(span=p["macd_slow"], adjust=False).mean()
        df["dif"] = df["ema_f"] - df["ema_s"]
        df["dea"] = df["dif"].ewm(span=p["macd_signal"], adjust=False).mean()
        hist_curr = df["dif"].iloc[-1] - df["dea"].iloc[-1]
        hist_prev = df["dif"].iloc[-2] - df["dea"].iloc[-2]
        if hist_prev <= 0 and hist_curr > 0:
            buy_score += 1.5
            reasons_buy.append("MACD金叉")
        elif hist_prev >= 0 and hist_curr < 0:
            sell_score += 1.5
            reasons_sell.append("MACD死叉")
        # MACD绝对方向（DIF > 0 为多头区域，权重0.5）
        dif_curr = float(df["dif"].iloc[-1])
        if dif_curr > 0:
            buy_score += 0.5
        else:
            sell_score += 0.5

        # ── 因子3: 布林带（权重1.0）──
        sma = df["close"].rolling(p["bb_period"]).mean()
        std = df["close"].rolling(p["bb_period"]).std()
        upper = sma + p["bb_std"] * std
        lower = sma - p["bb_std"] * std
        if price <= lower.iloc[-1]:
            buy_score += 1.0
            reasons_buy.append(f"触及布林下轨{lower.iloc[-1]:.2f}")
        elif price >= upper.iloc[-1]:
            sell_score += 1.0
            reasons_sell.append(f"突破布林上轨{upper.iloc[-1]:.2f}")

        # ── 因子4: 均线（权重1.0，金叉/死叉 + 排列方向）──
        ma_s = df["close"].rolling(p["ma_short"]).mean()
        ma_l = df["close"].rolling(p["ma_long"]).mean()
        if ma_s.iloc[-2] <= ma_l.iloc[-2] and ma_s.iloc[-1] > ma_l.iloc[-1]:
            buy_score += 1.0
            reasons_buy.append(f"MA{p['ma_short']}金叉MA{p['ma_long']}")
        elif ma_s.iloc[-2] >= ma_l.iloc[-2] and ma_s.iloc[-1] < ma_l.iloc[-1]:
            sell_score += 1.0
            reasons_sell.append(f"MA{p['ma_short']}死叉MA{p['ma_long']}")
        # 均线排列方向（权重0.5）
        if ma_s.iloc[-1] > ma_l.iloc[-1]:
            buy_score += 0.5
        else:
            sell_score += 0.5

        # ── 因子5: 成交量（权重1.0）──
        if "volume" in df.columns:
            avg_vol = df["volume"].iloc[-p["vol_lookback"] - 1:-1].mean()
            curr_vol = df["volume"].iloc[-1]
            if avg_vol > 0 and curr_vol > avg_vol * p["vol_ratio"]:
                if df["close"].iloc[-1] > df["close"].iloc[-2]:
                    buy_score += 1.0
                    reasons_buy.append(f"放量上涨(量比{curr_vol / avg_vol:.1f})")
                else:
                    sell_score += 1.0
                    reasons_sell.append(f"放量下跌(量比{curr_vol / avg_vol:.1f})")

        # ATR动态止损
        atr = _calc_atr_series(df, p.get("atr_period", 14))

        # ── 加权评分决策（总权重最大~6.5，阈值可调）──
        buy_thresh = p["buy_threshold"]   # 默认3
        sell_thresh = p["sell_threshold"]  # 默认3

        if buy_score >= buy_thresh and position_qty == 0:
            reason = f"多因子看多(得分{buy_score:.1f}): " + ", ".join(reasons_buy)
            return TradeSignal(
                Signal.BUY, symbol, price, p["quantity"], reason,
                stop_loss=price - atr * 2.0,
                take_profit=price + atr * 4.0,
            )

        if sell_score >= sell_thresh and position_qty > 0:
            reason = f"多因子看空(得分{sell_score:.1f}): " + ", ".join(reasons_sell)
            return TradeSignal(Signal.SELL, symbol, price, position_qty, reason)

        return TradeSignal(
            Signal.HOLD, symbol, price, 0,
            f"加权评分: 看多{buy_score:.1f}, 看空{sell_score:.1f}, 未达阈值"
        )


class TrendTailHedgeStrategy(BaseStrategy):
    """
    趋势跟踪 + 尾部风险对冲策略（研究驱动）
    - 多重均线确认趋势方向后入场
    - ATR动态止损（不是固定百分比，而是根据市场波动自适应）
    - 追踪止盈：利润达到一定程度后，止损线跟着利润上移
    灵感来源：管理期货(CTA)趋势跟踪 + Goldman Sachs尾部对冲研究
    Sharpe: 0.8-1.5，危机时可以反赚（尾部对冲）
    """

    name = "趋势跟踪+动态对冲"
    description = "多均线确认趋势+ATR动态止损+追踪止盈，攻守兼备"

    def __init__(self, params: dict = None):
        defaults = {
            "fast_ma": 10, "mid_ma": 20, "slow_ma": 50,
            "atr_period": 14,
            "atr_stop_multiplier": 2.5,    # 止损 = 入场价 - 2.5倍ATR
            "atr_profit_multiplier": 4.0,  # 止盈 = 入场价 + 4倍ATR
            "trend_strength_threshold": 0.02,  # 均线斜率阈值（2%）
            "quantity": 100,
        }
        super().__init__({**defaults, **(params or {})})

    def _calc_atr(self, df: pd.DataFrame, period: int) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"].shift(1)
        tr = pd.concat([
            high - low,
            (high - close).abs(),
            (low - close).abs(),
        ], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        p = self.params
        price = df["close"].iloc[-1]

        if len(df) < p["slow_ma"] + p["atr_period"]:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        df = df.copy()

        # 三重均线
        df["fast"] = df["close"].rolling(p["fast_ma"]).mean()
        df["mid"] = df["close"].rolling(p["mid_ma"]).mean()
        df["slow"] = df["close"].rolling(p["slow_ma"]).mean()

        fast = df["fast"].iloc[-1]
        mid = df["mid"].iloc[-1]
        slow = df["slow"].iloc[-1]

        # 趋势强度：慢速均线的斜率
        slow_slope = (df["slow"].iloc[-1] - df["slow"].iloc[-5]) / df["slow"].iloc[-5] if df["slow"].iloc[-5] > 0 else 0

        # ATR
        atr = self._calc_atr(df, p["atr_period"])

        # ── 买入条件：三重均线多头排列 + 趋势强度达标 ──
        uptrend = fast > mid > slow
        strong_trend = slow_slope > p["trend_strength_threshold"]

        if uptrend and strong_trend and position_qty == 0:
            stop_loss = price - atr * p["atr_stop_multiplier"]
            take_profit = price + atr * p["atr_profit_multiplier"]
            return TradeSignal(
                Signal.BUY, symbol, price, p["quantity"],
                f"三重均线多头排列(快{fast:.1f}>中{mid:.1f}>慢{slow:.1f})，"
                f"趋势斜率{slow_slope * 100:.1f}%，ATR={atr:.2f}，"
                f"止损{stop_loss:.2f}，止盈{take_profit:.2f}",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        # ── 卖出条件：趋势反转或ATR止损 ──
        downtrend = fast < mid < slow
        trend_break = fast < mid  # 快线跌破中线，趋势减弱

        if position_qty > 0:
            if downtrend:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"趋势反转：三重均线空头排列(快{fast:.1f}<中{mid:.1f}<慢{slow:.1f})，清仓止损"
                )
            if trend_break and slow_slope < 0:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"趋势减弱：快线{fast:.1f}跌破中线{mid:.1f}，慢线斜率转负{slow_slope * 100:.1f}%"
                )

        return TradeSignal(
            Signal.HOLD, symbol, price, 0,
            f"均线: 快{fast:.1f}/中{mid:.1f}/慢{slow:.1f}，斜率{slow_slope * 100:.1f}%，ATR={atr:.2f}"
        )


class MeanReversionStrategy(BaseStrategy):
    """
    短期反转策略（研究驱动，港股特别有效）
    - 利用散户过度反应造成的短期价格偏离
    - 当价格偏离均值超过阈值时反向交易
    - 结合RSI确认超买超卖，避免在趋势行情中逆势
    灵感来源：中国A股/港股研究 — 散户占80%交易量，反转因子显著
    在散户主导的市场中，短期反转的夏普比率可达 1.0-1.5
    """

    name = "短期反转策略"
    description = "捕捉散户过度反应造成的价格偏离，港股/A股特别有效"

    def __init__(self, params: dict = None):
        defaults = {
            "lookback": 5,          # 回看天数（短期）
            "deviation_threshold": -0.05,  # 5%以上跌幅触发买入
            "recovery_threshold": 0.03,    # 回升3%触发卖出
            "rsi_period": 6,               # 短期RSI
            "rsi_oversold": 25,            # 更极端的超卖线
            "rsi_overbought": 75,
            "max_holding_days": 10,        # 最大持仓天数（强制平仓）
            "quantity": 100,
            "stop_loss_pct": 0.08,         # 8%止损
        }
        super().__init__({**defaults, **(params or {})})
        self._entry_bar = 0

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        p = self.params
        price = df["close"].iloc[-1]
        lookback = p["lookback"]

        if len(df) < lookback + p["rsi_period"] + 2:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足")

        # 短期收益率
        recent_return = (price - df["close"].iloc[-lookback - 1]) / df["close"].iloc[-lookback - 1]
        rsi_val = _calc_rsi_wilder(df["close"], p["rsi_period"]).iloc[-1]
        rsi = float(rsi_val) if not np.isnan(rsi_val) else 50.0

        # ── 买入：短期大跌 + RSI超卖 → 反弹买入 ──
        if (recent_return < p["deviation_threshold"] and rsi < p["rsi_oversold"]
                and position_qty == 0):
            self._entry_bar = len(df)
            return TradeSignal(
                Signal.BUY, symbol, price, p["quantity"],
                f"{lookback}日跌幅{recent_return * 100:.1f}%+RSI={rsi:.0f}超卖，反转买入",
                stop_loss=price * (1 - p["stop_loss_pct"]),
                take_profit=price * (1 + abs(recent_return) * 0.6),  # 回弹目标：跌幅的60%
            )

        # ── 卖出条件 ──
        if position_qty > 0:
            holding_bars = len(df) - self._entry_bar if self._entry_bar > 0 else 0

            # 回升达标
            if recent_return > p["recovery_threshold"]:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"价格已回升{recent_return * 100:.1f}%，达到回升目标，获利了结"
                )

            # RSI超买
            if rsi > p["rsi_overbought"]:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"RSI={rsi:.0f}超买，反弹到位，卖出"
                )

            # 持仓超时
            if holding_bars >= p["max_holding_days"]:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"持仓已满{holding_bars}天，强制平仓避免沉没"
                )

        return TradeSignal(
            Signal.HOLD, symbol, price, 0,
            f"{lookback}日收益{recent_return * 100:.1f}%，RSI={rsi:.0f}，未达反转条件"
        )


# 策略注册表
STRATEGY_REGISTRY = {
    "ma_cross": MACrossStrategy,
    "rsi": RSIStrategy,
    "bollinger": BollingerBandStrategy,
    "macd": MACDStrategy,
    "volume_breakout": VolumeBreakoutStrategy,
    "multi_factor": MultiFactorStrategy,
    "trend_tail_hedge": TrendTailHedgeStrategy,
    "mean_reversion": MeanReversionStrategy,
    # LLM情绪增强策略在 news_strategy.py 中定义，延迟导入避免循环依赖
}


def _register_advanced_strategies():
    """注册高级策略（延迟导入避免循环依赖）"""
    if "regime_adaptive" not in STRATEGY_REGISTRY:
        try:
            from advanced_strategies import (
                RegimeAdaptiveStrategy,
                MomentumVolatilityStrategy,
                StatArbPairsStrategy,
            )
            STRATEGY_REGISTRY["regime_adaptive"] = RegimeAdaptiveStrategy
            STRATEGY_REGISTRY["momentum_volatility"] = MomentumVolatilityStrategy
            STRATEGY_REGISTRY["stat_arb_pairs"] = StatArbPairsStrategy
        except ImportError:
            pass

    if "super_alpha" not in STRATEGY_REGISTRY:
        try:
            from super_strategy import SuperAlphaStrategy
            STRATEGY_REGISTRY["super_alpha"] = SuperAlphaStrategy
        except ImportError:
            pass

    if "llm_sentiment" not in STRATEGY_REGISTRY:
        try:
            from news_strategy import LLMSentimentStrategy
            STRATEGY_REGISTRY["llm_sentiment"] = LLMSentimentStrategy
        except ImportError:
            pass

    # 日内策略
    if "intraday_momentum" not in STRATEGY_REGISTRY:
        try:
            from intraday_strategies import (
                IntradayMomentumStrategy,
                OpeningRangeBreakoutStrategy,
                VWAPReversionStrategy,
                EndOfDayMOCStrategy,
                Last30MinStatStrategy,
            )
            STRATEGY_REGISTRY["intraday_momentum"] = IntradayMomentumStrategy
            STRATEGY_REGISTRY["orb"] = OpeningRangeBreakoutStrategy
            STRATEGY_REGISTRY["vwap_reversion"] = VWAPReversionStrategy
            STRATEGY_REGISTRY["eod_moc"] = EndOfDayMOCStrategy
            STRATEGY_REGISTRY["last_30min"] = Last30MinStatStrategy
        except ImportError:
            pass

    # 事件驱动策略
    if "pead" not in STRATEGY_REGISTRY:
        try:
            from event_driven import (
                PostEarningsDriftStrategy,
                IndexRebalanceStrategy,
            )
            STRATEGY_REGISTRY["pead"] = PostEarningsDriftStrategy
            STRATEGY_REGISTRY["index_rebalance"] = IndexRebalanceStrategy
        except ImportError:
            pass


def get_strategy(name: str, params: dict = None) -> BaseStrategy:
    """根据名称获取策略实例"""
    _register_advanced_strategies()
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略: {name}，可用策略: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name](params)


def list_strategies() -> list:
    """列出所有可用策略"""
    _register_advanced_strategies()
    return [
        {"key": key, "name": cls.name, "description": cls.description}
        for key, cls in STRATEGY_REGISTRY.items()
    ]
