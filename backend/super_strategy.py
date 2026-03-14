"""
超级融合策略 — 终极Alpha引擎
融合8个alpha因子 + 市场状态检测 + DeepSeek情绪分析
这是所有策略的集大成者，综合了Renaissance/AQR/Citadel/D.E.Shaw的精华
"""
import numpy as np
import pandas as pd
import logging
from strategies import BaseStrategy, Signal, TradeSignal
from alpha_factors import compute_alpha_score

logger = logging.getLogger(__name__)


class SuperAlphaStrategy(BaseStrategy):
    """
    超级Alpha融合策略

    架构设计（模仿顶级量化基金的多层决策框架）：

    第1层：市场状态检测（趋势 vs 震荡 vs 危机）
    - ADX判断趋势强度
    - 波动率判断风险水平
    - 赫斯特指数判断延续性

    第2层：8个Alpha因子综合评分
    - 价格反转、动量、波动率调整动量、量价背离
    - RSI极端、布林挤压、跳空回补、聪明钱流向

    第3层：仓位管理
    - 信号强度决定仓位大小（不是全进全出）
    - 波动率缩放（高波动减仓，低波动加仓）

    第4层：风险控制
    - ATR动态止损
    - 追踪止盈
    - 最大持仓天数限制

    可选第5层：DeepSeek情绪分析（如果配置了API）
    """

    name = "超级Alpha融合策略"
    description = "8因子综合评分+状态检测+波动率仓位+动态风控，顶级量化基金方法论"

    def __init__(self, params: dict = None):
        defaults = {
            # 因子参数
            "alpha_buy_threshold": 0.25,     # Alpha综合分>0.25买入
            "alpha_sell_threshold": -0.20,   # Alpha综合分<-0.20卖出

            # 状态检测
            "adx_period": 14,
            "adx_trend_threshold": 25,

            # 仓位管理
            "base_quantity": 100,
            "max_quantity": 500,
            "volatility_scale": True,        # 波动率缩放仓位

            # 风控
            "atr_period": 14,
            "atr_stop_mult": 2.0,
            "atr_profit_mult": 3.5,
            "max_holding_bars": 60,          # 最大持仓K线数

            # 动量过滤（防止动量崩溃）
            "momentum_crash_filter": True,   # AQR改进
            "short_term_reversal_cap": 0.05, # 5日涨幅超5%不追
        }
        super().__init__({**defaults, **(params or {})})
        self._entry_bar = 0
        self._entry_price = 0.0

    def _calc_adx(self, df: pd.DataFrame, period: int) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1)
        adx = dx.rolling(period).mean()
        val = adx.iloc[-1]
        return float(val) if not np.isnan(val) else 0

    def _calc_atr(self, df: pd.DataFrame, period: int) -> float:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        val = tr.rolling(period).mean().iloc[-1]
        return float(val) if not np.isnan(val) else 0

    def _detect_regime(self, df: pd.DataFrame) -> str:
        """
        检测市场状态: trend / mean_revert / crisis / low_vol_trend
        v3.0（幻方MoE思路）：增加低波动趋势状态，这是幻方最赚钱的环境。
        四种状态对应不同的因子权重组合（类似MoE的专家路由）。
        """
        adx = self._calc_adx(df, self.params["adx_period"])
        vol = df["close"].pct_change().tail(20).std()

        if vol > 0.04:  # 日波动>4% → 危机模式
            return "crisis"
        elif adx > self.params["adx_trend_threshold"]:
            if vol < 0.015:
                return "low_vol_trend"  # 低波动趋势 = 最佳环境，加大仓位
            return "trend"
        else:
            return "mean_revert"

    def _calc_position_size(self, df: pd.DataFrame, alpha_score: float, regime: str = "normal") -> int:
        """
        根据信号强度、波动率和市场状态计算仓位大小
        v3.0: 低波动趋势环境下允许更大仓位（幻方研究表明这是收益最高的环境）
        """
        base = self.params["base_quantity"]
        max_qty = self.params["max_quantity"]

        # 信号强度缩放: alpha分越高，仓位越大
        signal_scale = min(abs(alpha_score) / 0.5, 1.0)

        if self.params["volatility_scale"]:
            vol = df["close"].pct_change().tail(20).std()
            target_vol = 0.02
            vol_scale = target_vol / max(vol, 0.005) if vol > 0 else 1.0
            vol_scale = np.clip(vol_scale, 0.3, 2.0)
        else:
            vol_scale = 1.0

        # 状态加成（幻方MoE思路：最优环境给最大仓位）
        regime_scale = 1.0
        if regime == "low_vol_trend":
            regime_scale = 1.5   # 低波动趋势：加仓50%
        elif regime == "crisis":
            regime_scale = 0.5   # 危机模式：减仓50%

        qty = int(base * signal_scale * vol_scale * regime_scale)
        return min(max(qty, 1), max_qty)

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        p = self.params
        price = df["close"].iloc[-1]

        if len(df) < 60:
            return TradeSignal(Signal.HOLD, symbol, price, 0, "数据不足(需60根K线)")

        # ── 第1层：市场状态 ──
        regime = self._detect_regime(df)

        # ── 第2层：Alpha因子综合评分（ISC-42: 传入regime做权重调整）──
        # alpha_factors模块只认识 trend/crisis/normal/mean_revert
        alpha_regime = "trend" if regime == "low_vol_trend" else regime
        alpha = compute_alpha_score(df, regime=alpha_regime)
        alpha_score = alpha["score"]
        top_factors = sorted(alpha["factors"].items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        factor_desc = ", ".join(f"{k}={v:+.2f}" for k, v in top_factors)

        # ── 状态调整阈值 ──
        buy_thresh = p["alpha_buy_threshold"]
        sell_thresh = p["alpha_sell_threshold"]

        if regime == "crisis":
            # 危机模式：大幅收紧买入条件，放宽卖出条件
            buy_thresh = 0.50
            sell_thresh = -0.10
        elif regime == "low_vol_trend":
            # 低波动趋势（幻方最赚钱环境）：最宽松的买入门槛，加大仓位
            buy_thresh = 0.15
            sell_thresh = -0.25
        elif regime == "trend":
            # 趋势模式：略微降低买入门槛
            buy_thresh = 0.20
        # 震荡模式用默认阈值

        # ── 动量崩溃过滤（AQR改进） ──
        if p["momentum_crash_filter"] and position_qty == 0:
            short_ret = (price - df["close"].iloc[-5]) / df["close"].iloc[-5]
            if short_ret > p["short_term_reversal_cap"]:
                return TradeSignal(
                    Signal.HOLD, symbol, price, 0,
                    f"[{regime}]Alpha={alpha_score:+.3f}但5日涨{short_ret*100:.1f}%过热，"
                    f"动量崩溃过滤,等待回调"
                )

        atr = self._calc_atr(df, p["atr_period"])

        # ── 买入决策 ──
        if alpha_score > buy_thresh and position_qty == 0:
            qty = self._calc_position_size(df, alpha_score, regime=regime)
            stop_loss = price - atr * p["atr_stop_mult"]
            take_profit = price + atr * p["atr_profit_mult"]

            self._entry_bar = len(df)
            self._entry_price = price

            return TradeSignal(
                Signal.BUY, symbol, price, qty,
                f"[{regime}]Alpha={alpha_score:+.3f}>{buy_thresh}, "
                f"主要因子: {factor_desc}, "
                f"仓位{qty}股, 止损{stop_loss:.2f}, 止盈{take_profit:.2f}",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        # ── 卖出决策 ──
        if position_qty > 0:
            holding_bars = len(df) - self._entry_bar if self._entry_bar > 0 else 0
            profit_pct = (price - self._entry_price) / self._entry_price if self._entry_price > 0 else 0

            # Alpha转空
            if alpha_score < sell_thresh:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"[{regime}]Alpha={alpha_score:+.3f}<{sell_thresh}转空, "
                    f"主要因子: {factor_desc}, 盈利{profit_pct*100:.1f}%"
                )

            # 持仓超时
            if holding_bars >= p["max_holding_bars"]:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"持仓{holding_bars}根K线超过上限{p['max_holding_bars']},"
                    f"强制平仓,盈利{profit_pct*100:.1f}%"
                )

            # 危机模式强制减仓
            if regime == "crisis" and profit_pct < 0:
                return TradeSignal(
                    Signal.SELL, symbol, price, position_qty,
                    f"[危机模式]浮亏{profit_pct*100:.1f}%+高波动，风控减仓"
                )

        return TradeSignal(
            Signal.HOLD, symbol, price, 0,
            f"[{regime}]Alpha={alpha_score:+.3f}, {factor_desc}, "
            f"阈值买>{buy_thresh}/卖<{sell_thresh}"
        )
