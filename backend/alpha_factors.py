"""
高级Alpha因子库 v2.0
基于顶级量化基金公开论文和AQR/WorldQuant研究实现
每个因子返回 -1.0 到 +1.0 的分数：正=看多，负=看空

v2.0 改进：
- 修复 RSI 计算：使用 Wilder EWM 法（vs 原 rolling().mean() 有偏差）
- 新增 VWAP 偏离因子（日内最有效信号之一）
- 新增 52周高点接近度因子（动量锚点效应）
- 新增市场趋势因子（均线斜率感知大市）
- 权重优化：基于 WorldQuant/AQR 实证研究
"""
import numpy as np
import pandas as pd


def _wilder_rsi(prices: pd.Series, period: int) -> float:
    """Wilder平滑法RSI（标准实现，修正了原rolling().mean()偏差）"""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    return float(val) if not np.isnan(val) else 50.0


def factor_price_reversal(df: pd.DataFrame, lookback: int = 5) -> float:
    """
    短期价格反转因子（WorldQuant Alpha #1）
    过去N天跌幅越大 → 未来反弹概率越高
    港股散户占比高，过度反应明显，反转因子特别有效
    """
    if len(df) < lookback + 1:
        return 0.0
    ret = (df["close"].iloc[-1] - df["close"].iloc[-lookback - 1]) / df["close"].iloc[-lookback - 1]
    return float(np.clip(-ret / 0.05, -1, 1))


def factor_momentum(df: pd.DataFrame, lookback: int = 20, skip: int = 5) -> float:
    """
    中期动量因子（AQR核心因子）
    过去20天涨幅（跳过最近5天避免短期反转噪音）
    """
    if len(df) < lookback + skip + 1:
        return 0.0
    past_price = df["close"].iloc[-lookback - skip]
    recent_price = df["close"].iloc[-skip]
    ret = (recent_price - past_price) / past_price
    return float(np.clip(ret / 0.10, -1, 1))


def factor_volatility_adjusted_momentum(df: pd.DataFrame, period: int = 20) -> float:
    """
    波动率调整动量（Citadel方法）
    动量信号除以波动率 → 低波动时期的动量信号权重更大
    """
    if len(df) < period + 5:
        return 0.0
    ret = (df["close"].iloc[-1] - df["close"].iloc[-period]) / df["close"].iloc[-period]
    vol = df["close"].pct_change().tail(period).std()
    if vol == 0:
        return 0.0
    vol_adj = ret / vol
    return float(np.clip(vol_adj / 3.0, -1, 1))


def factor_volume_price_divergence(df: pd.DataFrame, period: int = 10) -> float:
    """
    量价背离因子
    价格上涨但成交量萎缩 → 上涨动力不足（看空）
    价格下跌但成交量萎缩 → 抛压减弱（看多）
    """
    if len(df) < period + 1 or "volume" not in df.columns:
        return 0.0
    price_change = (df["close"].iloc[-1] - df["close"].iloc[-period]) / df["close"].iloc[-period]
    vol_change = (df["volume"].tail(period // 2).mean() - df["volume"].tail(period).head(period // 2).mean())
    if df["volume"].tail(period).mean() == 0:
        return 0.0
    vol_ratio = vol_change / df["volume"].tail(period).mean()

    if price_change > 0 and vol_ratio < -0.1:
        return float(np.clip(-price_change / 0.03, -1, 0))
    elif price_change < 0 and vol_ratio < -0.1:
        return float(np.clip(-price_change / 0.03, 0, 1))
    return 0.0


def factor_rsi_extreme(df: pd.DataFrame, period: int = 14) -> float:
    """
    RSI极端值因子（v2.0修复：Wilder EWM法，原rolling().mean()有偏差）
    RSI < 20 → 极度超卖（强烈看多）
    RSI > 80 → 极度超买（强烈看空）
    """
    if len(df) < period + 1:
        return 0.0

    rsi = _wilder_rsi(df["close"], period)

    if rsi < 20:
        return 1.0
    elif rsi < 30:
        return 0.5
    elif rsi > 80:
        return -1.0
    elif rsi > 70:
        return -0.5
    return 0.0


def factor_bollinger_squeeze(df: pd.DataFrame, period: int = 20) -> float:
    """
    布林带挤压因子（波动率收缩→即将突破）
    当布林带宽度处于历史低位时，预示大行情即将到来
    """
    if len(df) < period * 2:
        return 0.0
    sma = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    bandwidth = (2 * std / sma).dropna()

    if len(bandwidth) < period:
        return 0.0

    current_bw = float(bandwidth.iloc[-1])
    avg_bw = float(bandwidth.tail(period * 2).mean())
    price = df["close"].iloc[-1]
    mid = float(sma.iloc[-1])

    if current_bw < avg_bw * 0.6:
        direction = 1.0 if price > mid else -1.0
        squeeze_strength = np.clip((avg_bw * 0.6 - current_bw) / (avg_bw * 0.3), 0, 1)
        return float(direction * squeeze_strength)
    return 0.0


def factor_gap_reversal(df: pd.DataFrame) -> float:
    """
    跳空回补因子（港股日内特别有效）
    开盘跳空高开 → 当日倾向回落（看空）
    开盘跳空低开 → 当日倾向回补（看多）
    """
    if len(df) < 2 or "open" not in df.columns:
        return 0.0
    prev_close = df["close"].iloc[-2]
    curr_open = df["open"].iloc[-1]
    gap = (curr_open - prev_close) / prev_close

    if abs(gap) < 0.005:
        return 0.0
    return float(np.clip(-gap / 0.03, -1, 1))


def factor_smart_money(df: pd.DataFrame, period: int = 20) -> float:
    """
    聪明钱流向因子（Chaikin Money Flow）
    机构建仓/出货的量价特征识别
    """
    if len(df) < period + 1 or "volume" not in df.columns:
        return 0.0
    if "high" not in df.columns or "low" not in df.columns:
        return 0.0

    high = df["high"].tail(period)
    low = df["low"].tail(period)
    close = df["close"].tail(period)
    volume = df["volume"].tail(period)

    hl_range = (high - low).replace(0, 1)
    mfm = ((close - low) - (high - close)) / hl_range
    mfv = mfm * volume

    cmf = float(mfv.sum() / volume.sum()) if volume.sum() > 0 else 0
    return float(np.clip(cmf * 2, -1, 1))


# ─── 新增因子 v2.0 ───────────────────────────────────

def factor_vwap_deviation(df: pd.DataFrame, period: int = 20) -> float:
    """
    VWAP偏离度因子（Volume Weighted Average Price）

    价格相对VWAP的偏离程度是日内交易最有效的信号之一：
    - 价格远低于VWAP（超卖）→ 看多（向VWAP回归）
    - 价格远高于VWAP（超买）→ 看空

    日K线使用典型价格×成交量近似VWAP（rolling N日）
    典型价格 = (High + Low + Close) / 3
    """
    if len(df) < period + 1 or "volume" not in df.columns:
        return 0.0
    if "high" not in df.columns or "low" not in df.columns:
        return 0.0

    try:
        tail = df.tail(period).copy()
        typical_price = (tail["high"] + tail["low"] + tail["close"]) / 3.0
        vol_sum = tail["volume"].sum()
        if vol_sum == 0:
            return 0.0
        vwap = (typical_price * tail["volume"]).sum() / vol_sum
        deviation = (df["close"].iloc[-1] - vwap) / vwap
        # 偏离3%以上有信号；超跌看多，超涨看空
        return float(np.clip(-deviation / 0.03, -1, 1))
    except Exception:
        return 0.0


def factor_52week_high(df: pd.DataFrame) -> float:
    """
    52周高点接近度因子（动量锚点效应）

    研究发现（George & Hwang 2004）：
    - 价格刚刚突破52周高点 → 最强烈的看多信号（动量延续）
    - 价格接近52周高点（95-98%）→ 待突破看多
    - 价格远低于52周高点（跌幅>40%）→ 恐慌超卖，反转机会
    """
    if len(df) < 20:
        return 0.0

    try:
        lookback = min(len(df), 252)
        high_col = df["high"] if "high" in df.columns else df["close"]
        period_high = float(high_col.tail(lookback).max())
        price = float(df["close"].iloc[-1])

        if period_high == 0:
            return 0.0

        proximity = price / period_high

        if proximity > 1.0:    # 突破新高
            return 0.9
        elif proximity > 0.98: # 极近高点
            return 0.7
        elif proximity > 0.93: # 接近高点
            return 0.3
        elif proximity < 0.55: # 远离高点，超卖反弹
            return float(np.clip((0.60 - proximity) / 0.30, 0, 0.7))
        return 0.0
    except Exception:
        return 0.0


def factor_market_trend(df: pd.DataFrame, period: int = 20) -> float:
    """
    市场趋势因子（中期均线斜率）

    通过股票自身的中期均线斜率来判断趋势方向：
    - 上升趋势（斜率>2%/月）→ 看多加持
    - 下降趋势（斜率<-2%/月）→ 看空压力
    """
    if len(df) < period * 2:
        return 0.0

    try:
        sma = df["close"].rolling(period).mean()
        recent_sma = float(sma.iloc[-1])
        old_sma = float(sma.iloc[-period // 2])
        if old_sma == 0:
            return 0.0
        slope = (recent_sma - old_sma) / old_sma
        return float(np.clip(slope / 0.02, -1, 1))
    except Exception:
        return 0.0


# ─── 新增因子 v3.0（幻方/九坤/明汯研究启发）───────────

def factor_multi_horizon_momentum(df: pd.DataFrame) -> float:
    """
    多时间窗口动量因子（幻方量化核心方法）

    幻方使用5/10/20/60日多窗口动量的非线性融合。
    不同周期的动量方向一致时，信号最强（趋势共振）。
    方向不一致时信号衰减（趋势分歧，风险升高）。
    """
    if len(df) < 65:
        return 0.0

    close = df["close"]
    price = float(close.iloc[-1])

    horizons = {
        5:  0.15,   # 短期动量（1周）
        10: 0.25,   # 中短期（2周）
        20: 0.35,   # 中期（1月）- 最重要
        60: 0.25,   # 长期（3月）
    }

    mom_scores = {}
    for period, weight in horizons.items():
        past = float(close.iloc[-period - 1])
        if past == 0:
            continue
        ret = (price - past) / past
        mom_scores[period] = np.clip(ret / 0.08, -1, 1)

    if not mom_scores:
        return 0.0

    # 趋势共振检测：所有周期方向一致时加成
    signs = [1 if v > 0.05 else (-1 if v < -0.05 else 0) for v in mom_scores.values()]
    non_zero = [s for s in signs if s != 0]
    if non_zero and all(s == non_zero[0] for s in non_zero):
        resonance_boost = 1.3  # 共振加成30%
    else:
        resonance_boost = 0.8  # 分歧衰减20%

    weighted_mom = sum(mom_scores[p] * horizons[p] for p in mom_scores) / sum(horizons[p] for p in mom_scores)
    return float(np.clip(weighted_mom * resonance_boost, -1, 1))


def factor_turnover_rate(df: pd.DataFrame, period: int = 20) -> float:
    """
    换手率异动因子（九坤300特征之一）

    换手率突然放大通常预示重大变动：
    - 底部放量 → 资金进场（看多）
    - 顶部放量 → 资金出逃（看空）
    结合价格位置判断方向。
    """
    if len(df) < period + 5 or "volume" not in df.columns:
        return 0.0

    vol = df["volume"]
    avg_vol = float(vol.iloc[-(period + 1):-1].mean())
    if avg_vol == 0:
        return 0.0

    curr_vol = float(vol.iloc[-1])
    vol_ratio = curr_vol / avg_vol

    # 判断价格位置（相对20日高低点）
    close = df["close"]
    high_20 = float(close.iloc[-period:].max())
    low_20 = float(close.iloc[-period:].min())
    price = float(close.iloc[-1])

    if high_20 == low_20:
        return 0.0

    price_position = (price - low_20) / (high_20 - low_20)  # 0=最低, 1=最高

    if vol_ratio > 2.0:
        if price_position < 0.3:
            return float(np.clip((vol_ratio - 2.0) / 3.0, 0, 1))    # 底部放量看多
        elif price_position > 0.7:
            return float(np.clip(-(vol_ratio - 2.0) / 3.0, -1, 0))  # 顶部放量看空
    return 0.0


def factor_price_acceleration(df: pd.DataFrame) -> float:
    """
    价格加速度因子（明汯统计套利信号之一）

    不只看动量（一阶导），还看动量的变化率（二阶导）。
    动量正在加速 → 趋势增强，看多
    动量正在减速 → 趋势衰弱，看空
    """
    if len(df) < 25:
        return 0.0

    close = df["close"]
    # 5日动量序列
    mom_5 = close.pct_change(5)
    if len(mom_5.dropna()) < 10:
        return 0.0

    # 动量的变化（加速度）
    curr_mom = float(mom_5.iloc[-1])
    prev_mom = float(mom_5.iloc[-5])

    if np.isnan(curr_mom) or np.isnan(prev_mom):
        return 0.0

    acceleration = curr_mom - prev_mom

    return float(np.clip(acceleration / 0.04, -1, 1))


# ─── 综合评分器 v2.0 ─────────────────────────────────

def compute_alpha_score(df: pd.DataFrame, regime: str = "normal") -> dict:
    """
    计算所有Alpha因子的综合评分 v3.0

    v3.0 改进（基于幻方/九坤/明汯研究）：
    - 新增3个因子：多时间窗口动量(幻方)、换手率异动(九坤)、价格加速度(明汯)
    - 非线性因子融合：sigmoid加权（模拟九坤DNN+LightGBM的非线性组合）
    - Regime-aware权重调整（v2.1延续）
    - 因子一致性检测：多数因子方向一致时增强信号（幻方趋势共振思路）

    参数:
    - df: OHLCV K线数据
    - regime: 市场状态 "trend" / "crisis" / "normal" / "mean_revert"

    返回: {score: -1~+1, factors: {name: value}, signal: BUY/SELL/HOLD}
    """
    factors = {
        "价格反转":       factor_price_reversal(df),
        "中期动量":       factor_momentum(df),
        "波动率调整动量": factor_volatility_adjusted_momentum(df),
        "量价背离":       factor_volume_price_divergence(df),
        "RSI极端":        factor_rsi_extreme(df),
        "布林挤压":       factor_bollinger_squeeze(df),
        "跳空回补":       factor_gap_reversal(df),
        "聪明钱流向":     factor_smart_money(df),
        "VWAP偏离":       factor_vwap_deviation(df),
        "52周高点":       factor_52week_high(df),
        "市场趋势":       factor_market_trend(df),
        # v3.0 新增因子（幻方/九坤/明汯研究启发）
        "多窗口动量":     factor_multi_horizon_momentum(df),
        "换手率异动":     factor_turnover_rate(df),
        "价格加速度":     factor_price_acceleration(df),
    }

    # 基础权重（v3.1: 港股/A股市场校准）
    # 关键研究发现（CAIA/Wharton/PanAgora）：
    # - 中国/港股市场纯动量因子效果差（散户集体行为导致）
    # - 反转因子特别有效（散户占80%交易量，过度反应显著）
    # - 情绪/量价因子强（聪明钱流向、换手率异动）
    # - VWAP偏离在港股日内特别有效
    # 权重合计=1.0
    weights = {
        "价格反转":       0.12,   # 港股反转因子最强，提升权重
        "中期动量":       0.05,   # 纯动量在中国市场弱，降权
        "波动率调整动量": 0.06,   # 波动率调整后的动量略好于纯动量
        "量价背离":       0.07,   # 量价信号在散户市场有效
        "RSI极端":        0.08,   # 超买超卖信号强
        "布林挤压":       0.05,   # 波动率压缩信号
        "跳空回补":       0.06,   # 港股跳空回补效果好
        "聪明钱流向":     0.10,   # 机构资金流向信号强，提升
        "VWAP偏离":       0.08,   # VWAP回归在港股特别有效
        "52周高点":       0.05,   # 历史高点锚定
        "市场趋势":       0.04,   # 大市方向参考
        # 新因子（幻方/九坤/明汯研究）
        "多窗口动量":     0.10,   # 幻方核心：多窗口共振比纯动量有效得多
        "换手率异动":     0.08,   # 九坤：散户市场换手率异动是强信号
        "价格加速度":     0.06,   # 明汯：二阶导信号
    }

    # Regime-aware因子权重调整
    if regime == "trend":
        weights["中期动量"]       *= 1.8
        weights["波动率调整动量"] *= 1.8
        weights["多窗口动量"]     *= 1.6   # 趋势中多窗口动量极重要
        weights["52周高点"]       *= 1.5
        weights["市场趋势"]       *= 1.5
        weights["价格加速度"]     *= 1.5   # 趋势加速信号
        weights["价格反转"]       *= 0.5
        weights["跳空回补"]       *= 0.5
    elif regime == "crisis":
        weights["RSI极端"]        *= 1.5
        weights["VWAP偏离"]       *= 1.5
        weights["价格反转"]       *= 1.3
        weights["换手率异动"]     *= 1.3   # 危机中异常换手有信号价值
        weights["中期动量"]       *= 0.4
        weights["波动率调整动量"] *= 0.4
        weights["多窗口动量"]     *= 0.5   # 危机中动量不可信
        weights["52周高点"]       *= 0.3
        weights["价格加速度"]     *= 0.5

    # 权重归一化
    total_w = sum(weights.values())
    weights = {k: v / total_w for k, v in weights.items()}

    # 线性加权评分
    linear_score = sum(factors[k] * weights[k] for k in factors)

    # v3.0: 非线性融合（sigmoid压缩 + 因子一致性加成）
    # 模拟九坤DNN+LightGBM的非线性效应：极端值信号增强，中性信号压缩
    def _sigmoid_enhance(x, steepness=5.0):
        """sigmoid增强：中性值压缩，极端值放大"""
        return 2.0 / (1.0 + np.exp(-steepness * x)) - 1.0

    # 因子一致性检测（幻方趋势共振思路）
    active_factors = {k: v for k, v in factors.items() if abs(v) > 0.1}
    if active_factors:
        bullish = sum(1 for v in active_factors.values() if v > 0)
        bearish = sum(1 for v in active_factors.values() if v < 0)
        total_active = len(active_factors)
        # 超过70%因子方向一致 → 信号增强20%
        consensus_ratio = max(bullish, bearish) / total_active
        consensus_boost = 1.2 if consensus_ratio > 0.7 else 1.0
    else:
        consensus_boost = 1.0

    # 最终评分：sigmoid压缩后乘以一致性系数
    final_score = _sigmoid_enhance(linear_score, steepness=4.0) * consensus_boost
    final_score = float(np.clip(final_score, -1.0, 1.0))

    if final_score > 0.12:
        signal = "BUY"
    elif final_score < -0.12:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "score": round(final_score, 4),
        "signal": signal,
        "factors": {k: round(v, 4) for k, v in factors.items()},
    }
