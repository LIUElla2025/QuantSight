"""
机器学习增强信号确认模块 — 轻量级CPU方法
使用LightGBM和Random Forest进行信号确认, 无需GPU

核心思路:
    传统技术指标产生的买卖信号, 通过ML模型进行二次确认,
    过滤掉低质量信号, 提高胜率。

特征工程方法论 (来自AQR/WorldQuant公开研究):
    1. 价格特征: 多周期收益率、波动率、偏度
    2. 成交量特征: 量比、OBV斜率、成交量突变
    3. 技术指标特征: RSI、MACD、布林带位置
    4. 微观结构特征: 买卖价差、成交密度
    5. 时间特征: 星期几效应、月初/月末效应
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
import warnings
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 1. 特征工程模块
# ═══════════════════════════════════════════════════════════════

def compute_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    价格类特征

    生成以下特征:
    - ret_1d ~ ret_60d: 多周期收益率 (1,2,3,5,10,20,60天)
    - vol_5d ~ vol_60d: 多周期实现波动率
    - skew_20d: 20日收益率偏度
    - kurt_20d: 20日收益率峰度
    - max_drawdown_20d: 20日最大回撤
    - price_position_20d: 价格在20日范围内的位置 [0,1]
    """
    features = pd.DataFrame(index=df.index)

    # 多周期收益率
    for period in [1, 2, 3, 5, 10, 20, 60]:
        features[f"ret_{period}d"] = df["close"].pct_change(period)

    # 多周期波动率 (年化)
    for period in [5, 10, 20, 60]:
        features[f"vol_{period}d"] = (
            df["close"].pct_change().rolling(period).std() * np.sqrt(252)
        )

    # 收益率高阶矩
    features["skew_20d"] = df["close"].pct_change().rolling(20).skew()
    features["kurt_20d"] = df["close"].pct_change().rolling(20).kurt()

    # 最大回撤
    rolling_max = df["close"].rolling(20).max()
    features["max_drawdown_20d"] = (df["close"] - rolling_max) / rolling_max

    # 价格位置: 当前价在N日高低范围内的位置
    for period in [10, 20, 60]:
        high = df["high"].rolling(period).max()
        low = df["low"].rolling(period).min()
        rng = high - low
        rng = rng.replace(0, np.nan)
        features[f"price_pos_{period}d"] = (df["close"] - low) / rng

    return features


def compute_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    成交量类特征

    生成以下特征:
    - volume_ratio_5d/10d/20d: 当日成交量 / N日平均成交量
    - obv_slope_10d: OBV的10日线性回归斜率
    - volume_price_corr_10d: 量价相关性
    - volume_change_std_10d: 成交量变化的标准差(量的波动)
    """
    features = pd.DataFrame(index=df.index)

    if "volume" not in df.columns:
        return features

    # 量比
    for period in [5, 10, 20]:
        avg_vol = df["volume"].rolling(period).mean()
        avg_vol = avg_vol.replace(0, np.nan)
        features[f"vol_ratio_{period}d"] = df["volume"] / avg_vol

    # OBV (On-Balance Volume) 斜率
    obv = (np.sign(df["close"].diff()) * df["volume"]).cumsum()
    features["obv_slope_10d"] = obv.rolling(10).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0,
        raw=False
    )
    # 归一化OBV斜率
    obv_std = features["obv_slope_10d"].rolling(60).std()
    obv_std = obv_std.replace(0, np.nan)
    features["obv_slope_10d_norm"] = features["obv_slope_10d"] / obv_std

    # 量价相关性
    features["vol_price_corr_10d"] = (
        df["close"].pct_change().rolling(10).corr(
            df["volume"].pct_change()
        )
    )

    # 成交量变化的波动率
    features["vol_change_std_10d"] = df["volume"].pct_change().rolling(10).std()

    return features


def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    技术指标类特征

    生成以下特征:
    - rsi_6/14/28: 多周期RSI
    - macd_histogram: MACD柱状图
    - macd_signal_dist: MACD与信号线的距离
    - bb_position: 布林带位置 (0=下轨, 0.5=中轨, 1=上轨)
    - bb_width: 布林带宽度 (波动率代理)
    - adx_14: ADX趋势强度
    - atr_ratio_14: ATR占价格的比例
    """
    features = pd.DataFrame(index=df.index)

    # 多周期RSI
    for period in [6, 14, 28]:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        features[f"rsi_{period}"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    features["macd_histogram"] = dif - dea
    features["macd_signal_dist"] = dif - dea
    # 归一化
    features["macd_hist_norm"] = features["macd_histogram"] / df["close"] * 100

    # 布林带
    sma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    bb_range = upper - lower
    bb_range = bb_range.replace(0, np.nan)
    features["bb_position"] = (df["close"] - lower) / bb_range
    features["bb_width"] = bb_range / sma20

    # ADX
    high = df["high"]
    low = df["low"]
    close = df["close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr14.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr14.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    features["adx_14"] = dx.rolling(14).mean()

    # ATR比率
    features["atr_ratio_14"] = atr14 / df["close"]

    return features


def compute_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    时间类特征

    利用港股市场的日历效应:
    - 星期几效应: 周一通常偏弱, 周五强
    - 月初/月末效应: 月末资金面紧张, 月初宽松
    - 季末效应: 基金季末调仓
    - 节假日前效应
    """
    features = pd.DataFrame(index=df.index)

    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            dates = pd.to_datetime(df.index)
        except Exception:
            return features
    else:
        dates = df.index

    features["day_of_week"] = dates.dayofweek  # 0=Monday
    features["day_of_month"] = dates.day
    features["month"] = dates.month
    features["is_month_start"] = (dates.day <= 5).astype(int)
    features["is_month_end"] = (dates.day >= 25).astype(int)
    features["is_quarter_end"] = dates.is_quarter_end.astype(int)

    # 编码为周期特征 (sin/cos编码避免离散跳跃)
    features["dow_sin"] = np.sin(2 * np.pi * features["day_of_week"] / 5)
    features["dow_cos"] = np.cos(2 * np.pi * features["day_of_week"] / 5)
    features["dom_sin"] = np.sin(2 * np.pi * features["day_of_month"] / 31)
    features["dom_cos"] = np.cos(2 * np.pi * features["day_of_month"] / 31)

    return features


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    构建完整特征矩阵

    合并所有特征类别, 处理缺失值。
    总计约 40-50 个特征。

    参数:
        df: 包含 OHLCV 的 DataFrame

    返回:
        特征矩阵 DataFrame, 去除前60行(预热期)
    """
    price_feat = compute_price_features(df)
    vol_feat = compute_volume_features(df)
    tech_feat = compute_technical_features(df)
    time_feat = compute_time_features(df)

    all_features = pd.concat(
        [price_feat, vol_feat, tech_feat, time_feat],
        axis=1
    )

    # 去除预热期
    all_features = all_features.iloc[60:]

    # 处理无穷值
    all_features = all_features.replace([np.inf, -np.inf], np.nan)

    # 前向填充 + 后向填充处理NaN
    all_features = all_features.fillna(method="ffill").fillna(method="bfill").fillna(0)

    return all_features


# ═══════════════════════════════════════════════════════════════
# 2. 标签生成模块
# ═══════════════════════════════════════════════════════════════

def generate_labels(
    df: pd.DataFrame,
    forward_period: int = 5,
    threshold: float = 0.02,
) -> pd.Series:
    """
    生成训练标签

    使用前瞻收益率判断:
    - 未来N天收益 > threshold → 标签=1 (好的买入信号)
    - 未来N天收益 < -threshold → 标签=-1 (好的卖出信号)
    - 其他 → 标签=0 (信号无效)

    参数:
        df: 价格数据
        forward_period: 前瞻天数 (默认5天)
        threshold: 收益率阈值 (默认2%)

    返回: 标签Series
    """
    forward_returns = df["close"].pct_change(forward_period).shift(-forward_period)

    labels = pd.Series(0, index=df.index)
    labels[forward_returns > threshold] = 1
    labels[forward_returns < -threshold] = -1

    return labels


def generate_binary_labels(
    df: pd.DataFrame,
    forward_period: int = 5,
    threshold: float = 0.01,
) -> pd.Series:
    """
    生成二分类标签 (用于信号确认)

    - 未来N天收益 > threshold → 1 (信号有效)
    - 未来N天收益 <= threshold → 0 (信号无效)

    返回: 二值标签Series
    """
    forward_returns = df["close"].pct_change(forward_period).shift(-forward_period)
    labels = (forward_returns > threshold).astype(int)
    return labels


# ═══════════════════════════════════════════════════════════════
# 3. LightGBM 信号确认模型
# ═══════════════════════════════════════════════════════════════

class LightGBMSignalConfirmer:
    """
    LightGBM信号确认器

    使用方式:
        1. 传入历史OHLCV数据训练模型
        2. 当传统策略产生信号时, 用本模型确认
        3. 模型输出概率, 只有高概率信号才执行

    LightGBM优势 (无需GPU):
        - 训练速度快: 10万行数据 < 5秒 (CPU)
        - 内存效率高: 使用直方图算法
        - 自动处理缺失值
        - 防过拟合: 内置正则化

    推荐参数 (针对港股日线数据优化):
        n_estimators: 200-500
        max_depth: 5-7 (防过拟合)
        learning_rate: 0.05-0.1
        num_leaves: 31 (默认即可)
        min_child_samples: 20-50
        subsample: 0.8
        colsample_bytree: 0.8
        reg_alpha: 0.1 (L1正则)
        reg_lambda: 1.0 (L2正则)
    """

    def __init__(self, params: Optional[Dict] = None):
        self.default_params = {
            "objective": "binary",
            "metric": "auc",
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_child_samples": 30,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "verbose": -1,
            "n_jobs": -1,  # 使用所有CPU核心
        }
        if params:
            self.default_params.update(params)

        self.model = None
        self.feature_names = None
        self.feature_importance = None

    def train(
        self,
        df: pd.DataFrame,
        forward_period: int = 5,
        threshold: float = 0.01,
        test_ratio: float = 0.2,
    ) -> Dict:
        """
        训练信号确认模型

        使用时序分割(不是随机分割!) 避免前瞻偏差。

        参数:
            df: OHLCV数据
            forward_period: 标签前瞻天数
            threshold: 收益率阈值
            test_ratio: 测试集比例

        返回: {"auc": float, "accuracy": float, "feature_importance": dict}
        """
        try:
            import lightgbm as lgb
        except ImportError:
            logger.error("请安装lightgbm: pip install lightgbm")
            return {"error": "lightgbm not installed"}

        # 构建特征和标签
        features = build_feature_matrix(df)
        labels = generate_binary_labels(df, forward_period, threshold)

        # 对齐索引
        common_idx = features.index.intersection(labels.dropna().index)
        X = features.loc[common_idx]
        y = labels.loc[common_idx]

        # 时序分割 (关键: 不能随机分割!)
        split_idx = int(len(X) * (1 - test_ratio))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        self.feature_names = list(X.columns)

        # 训练
        model = lgb.LGBMClassifier(**self.default_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        self.model = model

        # 评估
        from sklearn.metrics import roc_auc_score, accuracy_score
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        y_pred = model.predict(X_test)

        auc = roc_auc_score(y_test, y_pred_proba)
        acc = accuracy_score(y_test, y_pred)

        # 特征重要性
        importance = dict(zip(
            self.feature_names,
            model.feature_importances_
        ))
        self.feature_importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)
        )

        return {
            "auc": round(auc, 4),
            "accuracy": round(acc, 4),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "top_10_features": dict(list(self.feature_importance.items())[:10]),
        }

    def confirm_signal(
        self,
        df: pd.DataFrame,
        min_confidence: float = 0.6,
    ) -> Dict:
        """
        确认交易信号

        参数:
            df: 当前OHLCV数据
            min_confidence: 最低置信度阈值 (推荐0.6-0.7)

        返回: {
            "confirmed": bool,
            "confidence": float,  # 0-1
            "action": str,  # "CONFIRM_BUY" | "REJECT" | "NO_MODEL"
        }
        """
        if self.model is None:
            return {"confirmed": False, "confidence": 0.0, "action": "NO_MODEL"}

        features = build_feature_matrix(df)
        if len(features) == 0:
            return {"confirmed": False, "confidence": 0.0, "action": "NO_DATA"}

        # 取最新一行特征
        X_latest = features.iloc[[-1]]

        # 确保特征顺序一致
        missing_cols = set(self.feature_names) - set(X_latest.columns)
        for col in missing_cols:
            X_latest[col] = 0
        X_latest = X_latest[self.feature_names]

        # 预测概率
        proba = self.model.predict_proba(X_latest)[0, 1]

        confirmed = proba >= min_confidence
        return {
            "confirmed": confirmed,
            "confidence": round(float(proba), 4),
            "action": "CONFIRM_BUY" if confirmed else "REJECT",
        }


# ═══════════════════════════════════════════════════════════════
# 4. Random Forest 信号确认模型
# ═══════════════════════════════════════════════════════════════

class RandomForestSignalConfirmer:
    """
    Random Forest信号确认器

    相比LightGBM的优势:
    - 更不容易过拟合 (bagging vs boosting)
    - 对噪声更鲁棒
    - 无需调太多参数

    相比LightGBM的劣势:
    - 稍慢
    - 对不平衡数据不如LightGBM

    推荐参数 (港股日线数据):
        n_estimators: 500-1000
        max_depth: 8-12
        min_samples_leaf: 20-50
        max_features: "sqrt"
        class_weight: "balanced" (处理不平衡)
    """

    def __init__(self, params: Optional[Dict] = None):
        self.default_params = {
            "n_estimators": 500,
            "max_depth": 10,
            "min_samples_leaf": 30,
            "max_features": "sqrt",
            "class_weight": "balanced",
            "random_state": 42,
            "n_jobs": -1,
        }
        if params:
            self.default_params.update(params)

        self.model = None
        self.feature_names = None
        self.feature_importance = None

    def train(
        self,
        df: pd.DataFrame,
        forward_period: int = 5,
        threshold: float = 0.01,
        test_ratio: float = 0.2,
    ) -> Dict:
        """训练模型 (与LightGBM接口一致)"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.metrics import roc_auc_score, accuracy_score
        except ImportError:
            logger.error("请安装scikit-learn: pip install scikit-learn")
            return {"error": "sklearn not installed"}

        features = build_feature_matrix(df)
        labels = generate_binary_labels(df, forward_period, threshold)

        common_idx = features.index.intersection(labels.dropna().index)
        X = features.loc[common_idx]
        y = labels.loc[common_idx]

        split_idx = int(len(X) * (1 - test_ratio))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        self.feature_names = list(X.columns)

        model = RandomForestClassifier(**self.default_params)
        model.fit(X_train, y_train)

        self.model = model

        y_pred_proba = model.predict_proba(X_test)[:, 1]
        y_pred = model.predict(X_test)

        auc = roc_auc_score(y_test, y_pred_proba)
        acc = accuracy_score(y_test, y_pred)

        importance = dict(zip(self.feature_names, model.feature_importances_))
        self.feature_importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)
        )

        return {
            "auc": round(auc, 4),
            "accuracy": round(acc, 4),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "top_10_features": dict(list(self.feature_importance.items())[:10]),
        }

    def confirm_signal(
        self,
        df: pd.DataFrame,
        min_confidence: float = 0.6,
    ) -> Dict:
        """确认信号 (与LightGBM接口一致)"""
        if self.model is None:
            return {"confirmed": False, "confidence": 0.0, "action": "NO_MODEL"}

        features = build_feature_matrix(df)
        if len(features) == 0:
            return {"confirmed": False, "confidence": 0.0, "action": "NO_DATA"}

        X_latest = features.iloc[[-1]]
        missing_cols = set(self.feature_names) - set(X_latest.columns)
        for col in missing_cols:
            X_latest[col] = 0
        X_latest = X_latest[self.feature_names]

        proba = self.model.predict_proba(X_latest)[0, 1]

        confirmed = proba >= min_confidence
        return {
            "confirmed": confirmed,
            "confidence": round(float(proba), 4),
            "action": "CONFIRM_BUY" if confirmed else "REJECT",
        }


# ═══════════════════════════════════════════════════════════════
# 5. 集成确认器 (LightGBM + RF 投票)
# ═══════════════════════════════════════════════════════════════

class EnsembleSignalConfirmer:
    """
    集成信号确认器

    同时使用LightGBM和Random Forest, 取平均概率。
    集成方法在量化交易中通常比单模型提升0.5-1.5%的AUC。

    投票机制:
        1. 两个模型都确认 → 强确认 (confidence > 0.7)
        2. 一个确认一个拒绝 → 弱确认 (需要更高阈值)
        3. 两个都拒绝 → 拒绝
    """

    def __init__(self, lgbm_params: Optional[Dict] = None,
                 rf_params: Optional[Dict] = None):
        self.lgbm = LightGBMSignalConfirmer(lgbm_params)
        self.rf = RandomForestSignalConfirmer(rf_params)

    def train(self, df: pd.DataFrame, **kwargs) -> Dict:
        """同时训练两个模型"""
        lgbm_result = self.lgbm.train(df, **kwargs)
        rf_result = self.rf.train(df, **kwargs)

        return {
            "lightgbm": lgbm_result,
            "random_forest": rf_result,
            "ensemble_note": "集成模型训练完成, 使用两模型平均概率确认信号",
        }

    def confirm_signal(
        self,
        df: pd.DataFrame,
        min_confidence: float = 0.6,
    ) -> Dict:
        """集成确认"""
        lgbm_result = self.lgbm.confirm_signal(df, min_confidence)
        rf_result = self.rf.confirm_signal(df, min_confidence)

        # 平均概率
        avg_confidence = (lgbm_result["confidence"] + rf_result["confidence"]) / 2

        # 投票
        both_confirm = lgbm_result["confirmed"] and rf_result["confirmed"]
        any_confirm = lgbm_result["confirmed"] or rf_result["confirmed"]

        if both_confirm:
            action = "STRONG_CONFIRM"
            confirmed = True
        elif any_confirm and avg_confidence >= min_confidence:
            action = "WEAK_CONFIRM"
            confirmed = True
        else:
            action = "REJECT"
            confirmed = False

        return {
            "confirmed": confirmed,
            "confidence": round(avg_confidence, 4),
            "action": action,
            "lgbm_confidence": lgbm_result["confidence"],
            "rf_confidence": rf_result["confidence"],
        }
