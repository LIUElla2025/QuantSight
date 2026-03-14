# ML Trading Signal Combination & Position Sizing Research

## 1. Gradient Boosting for Alpha Factor Combination: LightGBM vs XGBoost

### Head-to-Head Comparison

| Dimension | LightGBM | XGBoost |
|-----------|----------|---------|
| Tree growth | Leaf-wise (best-first) | Level-wise (depth-first) |
| Speed (100K rows) | ~3-5 seconds | ~15-30 seconds |
| Memory | Lower (histogram-based) | Higher |
| Missing values | Native handling | Native handling |
| Categorical features | Native support | Requires encoding |
| Overfitting risk | Higher (leaf-wise) | Lower (level-wise) |
| Cumulative return (S&P 500 test) | 10.74% / 19.73% annualized | 11.31% / 20.81% annualized |

**Verdict**: LightGBM for speed in alpha research iteration; XGBoost for marginally better returns. In practice, use both as base learners in an ensemble.

### Recommended LightGBM Parameters for Alpha Combination

```python
# Configuration A: Conservative (daily signals, smaller universe)
lgbm_conservative = {
    "objective": "binary",       # or "lambdarank" for ranking
    "metric": "auc",
    "n_estimators": 300,         # range: 200-500
    "max_depth": 6,              # range: 5-8
    "learning_rate": 0.05,       # range: 0.01-0.1
    "num_leaves": 31,            # range: 20-63
    "min_child_samples": 30,     # range: 20-50
    "subsample": 0.8,            # range: 0.7-0.9
    "colsample_bytree": 0.8,     # range: 0.6-0.9
    "reg_alpha": 0.1,            # L1: range 0.01-10
    "reg_lambda": 1.0,           # L2: range 0.1-100
    "random_state": 42,
    "verbose": -1,
    "n_jobs": -1,
}

# Configuration B: Qlib-style (cross-sectional prediction, larger universe)
# From Microsoft Qlib production configs
lgbm_qlib = {
    "objective": "mse",          # regression for return prediction
    "learning_rate": 0.2,        # higher LR, fewer trees
    "max_depth": 8,
    "num_leaves": 210,           # much more leaves for cross-sectional
    "colsample_bytree": 0.8879,
    "subsample": 0.8789,
    "reg_alpha": 205.70,         # very heavy L1 for feature sparsity
    "reg_lambda": 580.98,        # very heavy L2 for smoothness
    "n_jobs": 20,
    "loss": "mse",
}
```

### Recommended XGBoost Parameters

```python
xgb_params = {
    "objective": "binary:logistic",  # or "reg:squarederror"
    "eval_metric": "auc",
    "n_estimators": 500,          # range: 300-3000
    "max_depth": 6,               # range: 4-8
    "learning_rate": 0.05,        # range: 0.01-0.1
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,        # range: 1-10
    "gamma": 0.1,                 # range: 0-0.5
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "tree_method": "hist",        # histogram-based for speed
    "random_state": 42,
    "n_jobs": -1,
}
```

### When to Use Which

- **LightGBM preferred**: Large universe (>500 stocks), frequent retraining, real-time scoring, categorical features (sector, exchange)
- **XGBoost preferred**: Smaller universe, max accuracy matters more than speed, already established pipeline
- **Both as ensemble**: Best approach - use as base learners in stacking (see Section 5)

---

## 2. Neural Networks for Signal Combination

### Architecture Comparison for Trading

| Architecture | Best For | Practical AUC Range | Training Time | Overfitting Risk |
|-------------|----------|-------------------|---------------|-----------------|
| LSTM (1-2 layers) | Sequential patterns, momentum | 0.52-0.58 | Minutes | Medium |
| Bi-LSTM | Pattern detection in both directions | 0.53-0.59 | Minutes | Medium-High |
| Transformer | Cross-asset relationships, attention | 0.54-0.60 | Hours | High |
| CNN-LSTM hybrid | Chart patterns + temporal | 0.53-0.58 | Minutes | Medium |
| Simple MLP | Tabular alpha factor combination | 0.52-0.56 | Seconds | Low |

### When Gradient Boosting Beats Neural Networks

From multiple perspectives:

**Gradient boosting wins when:**
- Tabular/structured features (alpha factors, technical indicators)
- Limited training data (<50K samples)
- Need for feature importance/interpretability
- Frequent retraining required (daily/weekly)
- CPU-only infrastructure

**Neural networks win when:**
- Sequential/temporal patterns matter (order book, tick data)
- Cross-asset relationships (attention mechanisms)
- Very large datasets (>1M samples)
- Alternative data (text, images)
- GPU infrastructure available

**Stress-test conclusion**: For your existing 11 alpha factors on HK stocks with daily data, gradient boosting (LightGBM/XGBoost ensemble) will almost certainly outperform neural networks. Neural nets shine when you move to intraday tick-level data or incorporate NLP sentiment.

### Practical LSTM for Signal Enhancement (if needed)

```python
import numpy as np

# LSTM architecture for alpha factor time series
# Input: (batch, sequence_length=60, n_features=11_alpha_factors + 40_engineered)
lstm_config = {
    "input_dim": 51,           # your 11 factors + ~40 engineered features
    "hidden_dim": 64,          # range: 32-128
    "num_layers": 2,           # range: 1-3
    "dropout": 0.3,            # range: 0.2-0.5
    "sequence_length": 60,     # trading days lookback
    "output_dim": 1,           # probability of profitable trade
    "learning_rate": 0.001,    # range: 0.0001-0.01
    "batch_size": 64,          # range: 32-128
    "epochs": 50,              # with early stopping patience=10
}

# PyTorch pattern
"""
class AlphaLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                           batch_first=True, dropout=dropout)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])  # last timestep
"""
```

---

## 3. Feature Engineering: What Actually Has Predictive Power

### Tier 1: Strongest Predictive Features (consistently significant in backtests)

| Feature | Category | Typical IC | Why It Works |
|---------|----------|-----------|-------------|
| Short-term reversal (1-5d return) | Price | 0.02-0.05 | Mean reversion in liquid stocks |
| 12-1 month momentum | Price | 0.03-0.06 | AQR's core factor, skip recent month |
| Volatility-adjusted momentum | Price | 0.03-0.07 | Citadel method, higher Sharpe |
| Volume ratio (current/avg) | Volume | 0.01-0.03 | Institutional activity signal |
| RSI extreme zones (<20, >80) | Technical | 0.02-0.04 | Oversold/overbought edges |
| Price position in N-day range | Technical | 0.02-0.04 | Mean reversion signal |
| VWAP deviation | Microstructure | 0.02-0.05 | Intraday most effective signal |
| Earnings surprise | Fundamental | 0.03-0.08 | Post-earnings drift (PEAD) |
| Book-to-market ratio | Fundamental | 0.02-0.04 | Value factor, Fama-French |

### Tier 2: Useful Supporting Features

| Feature | Category | Typical IC | Notes |
|---------|----------|-----------|-------|
| OBV slope (normalized) | Volume | 0.01-0.02 | Smart money flow |
| Bollinger band width | Technical | 0.01-0.02 | Volatility squeeze predictor |
| ADX (trend strength) | Technical | 0.01-0.02 | Regime indicator |
| Skewness of returns (20d) | Statistical | 0.01-0.02 | Tail risk signal |
| Day-of-week effect | Calendar | 0.005-0.015 | Monday weakness, Friday strength |
| Month-end effect | Calendar | 0.005-0.01 | Window dressing flows |
| 52-week high proximity | Anchoring | 0.01-0.03 | Momentum breakout signal |

### Tier 3: Features that look good but are dangerous

| Feature | Risk | Mitigation |
|---------|------|-----------|
| Raw price levels | Non-stationary, spurious correlation | Always use returns or normalized ratios |
| Exact volume values | Scale-dependent across stocks | Use ratios (volume/avg_volume) |
| Calendar features (raw) | Overfitting to specific dates | Use sin/cos encoding |
| Cross-sectional rank (static) | Survivorship bias | Recalculate on point-in-time universe |

### Feature Selection Methods That Prevent Overfitting

```python
# Method 1: Purged K-Fold Cross-Validation Feature Importance
# Prevents information leakage between train/test folds
def purged_feature_importance(X, y, model, n_splits=5, embargo_pct=0.01):
    """
    Uses TimeSeriesSplit with embargo period to prevent leakage.
    Features that are important across ALL folds are robust.
    """
    from sklearn.model_selection import TimeSeriesSplit
    importances = []
    tscv = TimeSeriesSplit(n_splits=n_splits)

    for train_idx, test_idx in tscv.split(X):
        # Add embargo: remove samples near the boundary
        embargo_size = int(len(X) * embargo_pct)
        train_idx = train_idx[:-embargo_size]

        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        importances.append(model.feature_importances_)

    mean_imp = np.mean(importances, axis=0)
    std_imp = np.std(importances, axis=0)

    # Only keep features where mean > 2*std (consistently important)
    robust_features = X.columns[mean_imp > 2 * std_imp]
    return robust_features


# Method 2: Sequential Feature Elimination with Walk-Forward
# Remove features one at a time, keep those that hurt performance when removed
def walk_forward_feature_selection(X, y, model, n_windows=5):
    """
    For each feature, measure performance WITH and WITHOUT it
    across multiple walk-forward windows. Keep only features
    that consistently improve out-of-sample performance.
    """
    window_size = len(X) // (n_windows + 1)
    base_scores = []
    feature_deltas = {col: [] for col in X.columns}

    for i in range(n_windows):
        train_end = window_size * (i + 1)
        test_end = train_end + window_size
        X_train, X_test = X.iloc[:train_end], X.iloc[train_end:test_end]
        y_train, y_test = y.iloc[:train_end], y.iloc[train_end:test_end]

        # Base score with all features
        model.fit(X_train, y_train)
        base_score = model.score(X_test, y_test)
        base_scores.append(base_score)

        # Score without each feature
        for col in X.columns:
            X_train_drop = X_train.drop(columns=[col])
            X_test_drop = X_test.drop(columns=[col])
            model.fit(X_train_drop, y_train)
            score = model.score(X_test_drop, y_test)
            feature_deltas[col].append(base_score - score)

    # Keep features where removal consistently hurts performance
    robust = [col for col, deltas in feature_deltas.items()
              if np.mean(deltas) > 0 and np.mean(deltas) > np.std(deltas)]
    return robust
```

### Recommended Feature Engineering for Your Codebase

Your existing `ml_signal_enhancer.py` already has excellent coverage. Suggested additions:

```python
def compute_cross_asset_features(df, market_df):
    """
    Cross-asset features that add alpha beyond single-stock technicals.
    Requires a market/index DataFrame for relative analysis.
    """
    features = pd.DataFrame(index=df.index)

    # Beta to market (rolling 60d)
    stock_ret = df["close"].pct_change()
    market_ret = market_df["close"].pct_change()
    features["beta_60d"] = stock_ret.rolling(60).cov(market_ret) / \
                           market_ret.rolling(60).var()

    # Relative strength vs market
    features["rel_strength_20d"] = (
        df["close"].pct_change(20) - market_df["close"].pct_change(20)
    )

    # Idiosyncratic volatility (residual vol after removing market factor)
    features["idio_vol_20d"] = (stock_ret - features["beta_60d"] * market_ret) \
                                .rolling(20).std() * np.sqrt(252)

    # Correlation with market (regime indicator)
    features["market_corr_60d"] = stock_ret.rolling(60).corr(market_ret)

    return features


def compute_microstructure_features(df):
    """
    Microstructure features from OHLCV data (no tick data needed).
    These capture institutional activity patterns.
    """
    features = pd.DataFrame(index=df.index)

    # Amihud illiquidity ratio (price impact per unit volume)
    daily_ret = df["close"].pct_change().abs()
    dollar_vol = df["close"] * df["volume"]
    features["amihud_20d"] = (daily_ret / dollar_vol.replace(0, np.nan)) \
                              .rolling(20).mean()

    # High-low spread estimator (Corwin-Schultz)
    # Estimates bid-ask spread from daily high-low prices
    beta = (np.log(df["high"] / df["low"])) ** 2
    gamma = (np.log(
        df["high"].rolling(2).max() / df["low"].rolling(2).min()
    )) ** 2
    alpha_cs = (np.sqrt(2 * beta) - np.sqrt(beta)) / \
               (3 - 2 * np.sqrt(2)) - np.sqrt(gamma / (3 - 2 * np.sqrt(2)))
    features["spread_estimate"] = 2 * (np.exp(alpha_cs) - 1) / \
                                  (1 + np.exp(alpha_cs))
    features["spread_estimate"] = features["spread_estimate"].clip(0, 0.1)

    # Kyle's lambda proxy (price impact)
    features["kyle_lambda_20d"] = (
        daily_ret.rolling(20).sum() /
        df["volume"].rolling(20).sum().replace(0, np.nan)
    )

    return features
```

---

## 4. Dynamic Position Sizing Algorithms

### 4A. Kelly Criterion with Practical Modifications

```python
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.integrate import quad
from scipy.stats import norm


class KellySizer:
    """
    Kelly Criterion position sizer with practical modifications.

    Full Kelly maximizes geometric growth but creates extreme drawdowns.
    Professional traders use fractional Kelly:
    - Full Kelly: max growth, ~50% drawdown risk
    - Half Kelly: ~75% of growth, ~25% drawdown risk (RECOMMENDED)
    - Quarter Kelly: ~50% of growth, ~12% drawdown risk (conservative)
    """

    def __init__(self, kelly_fraction: float = 0.5):
        """
        kelly_fraction: 0.25 (conservative) to 1.0 (full Kelly)
        Most practitioners: 0.25-0.5
        """
        self.kelly_fraction = kelly_fraction

    def kelly_from_winrate(self, win_rate: float, avg_win: float,
                           avg_loss: float) -> float:
        """
        Classic Kelly for discrete outcomes.
        f* = (p * b - q) / b
        where p=win_rate, q=1-p, b=avg_win/avg_loss
        """
        if avg_loss == 0:
            return 0.0
        b = abs(avg_win / avg_loss)
        q = 1 - win_rate
        f_star = (win_rate * b - q) / b
        return max(0, f_star * self.kelly_fraction)

    def kelly_continuous(self, returns: np.ndarray) -> float:
        """
        Kelly for continuous returns (more realistic for trading).
        Numerically optimizes expected log growth.
        """
        mean_ret = np.mean(returns)
        std_ret = np.std(returns)

        if std_ret == 0:
            return 0.0

        def neg_growth(f):
            val, _ = quad(
                lambda s: np.log(1 + f * s) * norm.pdf(s, mean_ret, std_ret),
                mean_ret - 3 * std_ret,
                mean_ret + 3 * std_ret,
            )
            return -val

        result = minimize_scalar(neg_growth, bounds=[0, 2], method="bounded")
        return result.x * self.kelly_fraction

    def position_size(self, capital: float, signal_confidence: float,
                      returns_history: np.ndarray,
                      max_position_pct: float = 0.20) -> float:
        """
        Practical position sizing combining Kelly with signal confidence.

        Parameters:
        - capital: current portfolio value
        - signal_confidence: ML model confidence (0-1)
        - returns_history: array of historical returns for this asset
        - max_position_pct: hard cap (default 20% of portfolio)
        """
        kelly_frac = self.kelly_continuous(returns_history)

        # Scale by signal confidence (higher confidence = larger position)
        adjusted_frac = kelly_frac * signal_confidence

        # Apply hard cap
        position_pct = min(adjusted_frac, max_position_pct)

        return capital * position_pct
```

### 4B. Volatility Targeting Position Sizing

```python
class VolatilityTargetSizer:
    """
    Maintains consistent portfolio volatility by adjusting position sizes
    inversely to each asset's realized volatility.

    Target vol of 10-15% annualized is common for:
    - Trend following: 10-12%
    - Mean reversion: 8-10%
    - Multi-strategy: 10-15%
    """

    def __init__(self, target_vol: float = 0.10, vol_lookback: int = 20,
                 vol_floor: float = 0.05, vol_cap: float = 0.50,
                 max_leverage: float = 2.0):
        """
        target_vol: annualized target volatility (e.g., 0.10 = 10%)
        vol_lookback: days for realized vol calculation
        vol_floor: minimum vol estimate (prevents division by very small vol)
        vol_cap: maximum vol estimate (prevents over-shrinking in crisis)
        max_leverage: maximum total portfolio leverage
        """
        self.target_vol = target_vol
        self.vol_lookback = vol_lookback
        self.vol_floor = vol_floor
        self.vol_cap = vol_cap
        self.max_leverage = max_leverage

    def estimate_volatility(self, returns: np.ndarray) -> float:
        """
        Exponentially weighted volatility (more responsive than simple).
        EWMA with span=vol_lookback gives ~5% weight to oldest observation.
        """
        import pandas as pd
        ret_series = pd.Series(returns)
        ewm_vol = ret_series.ewm(span=self.vol_lookback).std().iloc[-1]
        annual_vol = ewm_vol * np.sqrt(252)
        return np.clip(annual_vol, self.vol_floor, self.vol_cap)

    def position_weight(self, returns: np.ndarray) -> float:
        """
        Calculate position weight for a single asset.
        weight = target_vol / asset_vol
        """
        asset_vol = self.estimate_volatility(returns)
        weight = self.target_vol / asset_vol
        return min(weight, self.max_leverage)

    def portfolio_weights(self, returns_dict: dict,
                          signal_scores: dict) -> dict:
        """
        Calculate weights for multiple assets with signal integration.

        Parameters:
        - returns_dict: {"AAPL": np.array([...]), "GOOG": np.array([...])}
        - signal_scores: {"AAPL": 0.7, "GOOG": -0.3}  # from alpha model

        Returns: {"AAPL": 0.15, "GOOG": -0.08}  # signed weights
        """
        raw_weights = {}
        for asset, returns in returns_dict.items():
            vol_weight = self.position_weight(returns)
            signal = signal_scores.get(asset, 0)
            raw_weights[asset] = vol_weight * signal

        # Scale if total leverage exceeds cap
        total_leverage = sum(abs(w) for w in raw_weights.values())
        if total_leverage > self.max_leverage:
            scale = self.max_leverage / total_leverage
            raw_weights = {k: v * scale for k, v in raw_weights.items()}

        return raw_weights
```

### 4C. Risk Parity Position Sizing

```python
class RiskParitySizer:
    """
    Equal risk contribution: each position contributes equally to
    total portfolio risk.

    Used by Bridgewater (All Weather), AQR, and most risk parity funds.

    For N assets, each should contribute 1/N of total portfolio variance.
    """

    def __init__(self, lookback: int = 60, target_vol: float = 0.10):
        self.lookback = lookback
        self.target_vol = target_vol

    def calculate_weights(self, returns_df: "pd.DataFrame") -> np.ndarray:
        """
        Inverse-volatility risk parity (simplified but effective).

        For full risk parity with correlations, use scipy optimization.
        This inverse-vol version is a good approximation when correlations
        are moderate.

        Parameters:
        - returns_df: DataFrame with columns = assets, rows = daily returns
        """
        # Annualized volatility per asset
        vols = returns_df.tail(self.lookback).std() * np.sqrt(252)
        vols = vols.clip(lower=0.05)  # floor

        # Inverse volatility weights
        inv_vol = 1.0 / vols
        weights = inv_vol / inv_vol.sum()

        # Scale to target volatility
        port_vol = np.sqrt(
            weights @ returns_df.tail(self.lookback).cov() * 252 @ weights
        )
        if port_vol > 0:
            weights = weights * (self.target_vol / port_vol)

        return weights

    def calculate_weights_full(self, returns_df: "pd.DataFrame") -> np.ndarray:
        """
        Full risk parity with correlation structure (scipy optimization).
        Each asset's marginal risk contribution = 1/N of total risk.
        """
        from scipy.optimize import minimize

        cov = returns_df.tail(self.lookback).cov().values * 252
        n = len(cov)
        target_risk = 1.0 / n

        def risk_budget_objective(weights):
            port_var = weights @ cov @ weights
            port_vol = np.sqrt(port_var)
            # Marginal risk contributions
            mrc = cov @ weights / port_vol
            # Risk contributions
            rc = weights * mrc
            rc_pct = rc / port_vol
            # Minimize deviation from equal risk contribution
            return np.sum((rc_pct - target_risk) ** 2)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        bounds = [(0.01, 0.50)] * n
        x0 = np.ones(n) / n

        result = minimize(risk_budget_objective, x0,
                         method="SLSQP", bounds=bounds,
                         constraints=constraints)

        weights = result.x

        # Scale to target vol
        port_vol = np.sqrt(weights @ cov @ weights)
        if port_vol > 0:
            weights = weights * (self.target_vol / port_vol)

        return weights
```

---

## 5. Walk-Forward Optimization & Regime-Aware Adaptation

### 5A. Walk-Forward Optimization Framework

```python
class WalkForwardOptimizer:
    """
    Walk-forward optimization prevents overfitting by continuously
    re-optimizing on expanding/sliding windows and testing on unseen data.

    Two modes:
    - Expanding window: train on all data up to split point (more data)
    - Sliding window: train on fixed-size recent window (more adaptive)

    Expanding is better for regime-stable markets.
    Sliding is better for regime-changing markets (recommended for HK stocks).
    """

    def __init__(self, train_window: int = 252, test_window: int = 63,
                 step_size: int = 21, mode: str = "sliding"):
        """
        train_window: training period in trading days (252 = 1 year)
        test_window: out-of-sample test period (63 = 1 quarter)
        step_size: how far to advance between iterations (21 = 1 month)
        mode: "expanding" or "sliding"
        """
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size
        self.mode = mode

    def generate_windows(self, n_samples: int):
        """Generate train/test index pairs for walk-forward."""
        windows = []
        start = 0
        while start + self.train_window + self.test_window <= n_samples:
            if self.mode == "expanding":
                train_start = 0
            else:
                train_start = start

            train_end = start + self.train_window
            test_start = train_end
            test_end = test_start + self.test_window

            windows.append({
                "train": (train_start, train_end),
                "test": (test_start, min(test_end, n_samples)),
            })
            start += self.step_size

        return windows

    def run(self, X, y, model_factory, scorer):
        """
        Execute walk-forward optimization.

        Parameters:
        - X: feature matrix (DataFrame)
        - y: labels (Series)
        - model_factory: callable that returns a fresh model instance
        - scorer: callable(model, X_test, y_test) -> float

        Returns: list of {window, score, model, predictions}
        """
        windows = self.generate_windows(len(X))
        results = []

        for w in windows:
            train_start, train_end = w["train"]
            test_start, test_end = w["test"]

            X_train = X.iloc[train_start:train_end]
            y_train = y.iloc[train_start:train_end]
            X_test = X.iloc[test_start:test_end]
            y_test = y.iloc[test_start:test_end]

            model = model_factory()
            model.fit(X_train, y_train)

            score = scorer(model, X_test, y_test)
            preds = model.predict(X_test)

            results.append({
                "window": w,
                "score": score,
                "predictions": preds,
                "actual": y_test.values,
                "model": model,
            })

        return results
```

### Expanding vs Sliding Window Tradeoffs

| Aspect | Expanding Window | Sliding Window |
|--------|-----------------|----------------|
| Data efficiency | Uses all available history | Fixed recent window |
| Regime adaptation | Slow (diluted by old data) | Fast (drops old regimes) |
| Stability | More stable estimates | More volatile estimates |
| Best for | Stable markets, more data | Regime-switching, HK stocks |
| Typical train size | All history up to split | 252-504 days (1-2 years) |
| Typical test size | 63 days (1 quarter) | 21-63 days (1 month to quarter) |
| Retraining frequency | Monthly | Monthly |

### 5B. Regime Detection with Hidden Markov Models

```python
class RegimeDetector:
    """
    Hidden Markov Model for market regime detection.

    Identifies 3 regimes:
    - Bull (low vol, positive drift): trending strategies work
    - Bear (high vol, negative drift): defensive/reversal strategies work
    - Sideways (moderate vol, no drift): mean reversion works

    Features for HMM:
    - Log returns (drift)
    - Volatility of log returns (regime vol signature)
    """

    def __init__(self, n_regimes: int = 3, lookback: int = 252):
        self.n_regimes = n_regimes
        self.lookback = lookback
        self.model = None
        self.regime_map = {}  # maps HMM state -> human label

    def fit(self, prices: "pd.Series"):
        """
        Train HMM on price series.
        Uses log returns and rolling volatility as observations.
        """
        from hmmlearn.hmm import GaussianHMM

        log_ret = np.log(prices / prices.shift(1)).dropna()
        vol = log_ret.rolling(20).std().dropna()

        # Align
        common_idx = log_ret.index.intersection(vol.index)
        observations = np.column_stack([
            log_ret.loc[common_idx].values,
            vol.loc[common_idx].values,
        ])

        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=200,
            random_state=42,
        )
        self.model.fit(observations)

        # Label regimes by mean return
        means = self.model.means_[:, 0]  # mean log return per state
        sorted_states = np.argsort(means)
        regime_labels = ["bear", "sideways", "bull"]

        # Handle 2-state case
        if self.n_regimes == 2:
            regime_labels = ["bear", "bull"]

        self.regime_map = {
            sorted_states[i]: regime_labels[i]
            for i in range(self.n_regimes)
        }

        return self

    def predict_regime(self, prices: "pd.Series") -> str:
        """Predict current regime from recent prices."""
        log_ret = np.log(prices / prices.shift(1)).dropna()
        vol = log_ret.rolling(20).std().dropna()

        common_idx = log_ret.index.intersection(vol.index)
        obs = np.column_stack([
            log_ret.loc[common_idx].values,
            vol.loc[common_idx].values,
        ])

        states = self.model.predict(obs)
        current_state = states[-1]
        return self.regime_map.get(current_state, "unknown")

    def get_regime_params(self, regime: str) -> dict:
        """
        Return regime-specific strategy parameters.
        This is where you adapt your alpha weights and position sizing.
        """
        params = {
            "bull": {
                "momentum_weight": 1.8,
                "reversal_weight": 0.5,
                "position_size_multiplier": 1.2,
                "stop_loss_pct": 0.05,
                "vol_target": 0.12,
            },
            "bear": {
                "momentum_weight": 0.4,
                "reversal_weight": 1.5,
                "position_size_multiplier": 0.6,
                "stop_loss_pct": 0.03,
                "vol_target": 0.06,
            },
            "sideways": {
                "momentum_weight": 0.8,
                "reversal_weight": 1.2,
                "position_size_multiplier": 1.0,
                "stop_loss_pct": 0.04,
                "vol_target": 0.10,
            },
        }
        return params.get(regime, params["sideways"])
```

### 5C. Regime-Aware Walk-Forward Integration

```python
class RegimeAwareWalkForward:
    """
    Combines regime detection with walk-forward optimization.

    At each walk-forward step:
    1. Detect current regime (HMM)
    2. Select regime-specific model or parameters
    3. Train on regime-filtered data
    4. Predict with regime-appropriate model
    """

    def __init__(self, regime_detector, walk_forward_optimizer):
        self.regime_detector = regime_detector
        self.wfo = walk_forward_optimizer
        self.regime_models = {}  # {regime: model}

    def run(self, X, y, prices, model_factory):
        """
        Execute regime-aware walk-forward.

        Strategy: Train separate models per regime, use the model
        matching the current detected regime for prediction.
        """
        windows = self.wfo.generate_windows(len(X))
        results = []

        for w in windows:
            train_start, train_end = w["train"]
            test_start, test_end = w["test"]

            # Detect regime for test period
            train_prices = prices.iloc[train_start:train_end]
            self.regime_detector.fit(train_prices)
            current_regime = self.regime_detector.predict_regime(train_prices)

            # Get regime-specific parameters
            regime_params = self.regime_detector.get_regime_params(
                current_regime
            )

            # Train model (could use regime-filtered data or full data)
            X_train = X.iloc[train_start:train_end]
            y_train = y.iloc[train_start:train_end]
            X_test = X.iloc[test_start:test_end]

            model = model_factory(regime_params)
            model.fit(X_train, y_train)

            preds = model.predict(X_test)
            results.append({
                "regime": current_regime,
                "regime_params": regime_params,
                "predictions": preds,
                "window": w,
            })

        return results
```

---

## 6. Ensemble Methods for Signal Combination

### 6A. Stacking Architecture (What Top Quant Funds Use)

The dominant pattern at quantitative funds (Two Sigma, Citadel, DE Shaw, AQR):

```
Level 0 (Base Learners - diverse model types):
  - LightGBM (gradient boosting, leaf-wise)
  - XGBoost (gradient boosting, level-wise)
  - Random Forest (bagging)
  - Ridge/Lasso Regression (linear)
  - LSTM/GRU (sequential, optional)

Level 1 (Meta-Learner - combines base predictions):
  - Ridge Regression (most common, prevents overfitting)
  - OR Logistic Regression with regularization
  - OR simple weighted average with learned weights

Level 2 (optional - risk overlay):
  - Position sizing based on meta-learner confidence
  - Regime-aware weight adjustment
```

### 6B. Implementation Pattern

```python
from sklearn.model_selection import TimeSeriesSplit
import numpy as np
import pandas as pd


class TradingStackedEnsemble:
    """
    Stacked ensemble for trading signal combination.

    Key principles:
    1. Base learners must be DIVERSE (different algorithms, not just hyperparams)
    2. Meta-learner should be SIMPLE (Ridge/Logistic) to prevent overfitting
    3. Use TIME-SERIES cross-validation (no random splits!)
    4. Out-of-fold predictions prevent information leakage
    """

    def __init__(self, base_learners: dict, meta_learner=None,
                 n_folds: int = 5, embargo_days: int = 5):
        """
        base_learners: {"lgbm": lgbm_model, "xgb": xgb_model, ...}
        meta_learner: sklearn-compatible model (default: Ridge)
        n_folds: number of time-series folds
        embargo_days: gap between train and test to prevent leakage
        """
        self.base_learners = base_learners
        self.n_folds = n_folds
        self.embargo_days = embargo_days

        if meta_learner is None:
            from sklearn.linear_model import RidgeCV
            self.meta_learner = RidgeCV(alphas=[0.01, 0.1, 1, 10, 100])
        else:
            self.meta_learner = meta_learner

        self.trained_bases = {}

    def _generate_oof_predictions(self, X, y):
        """
        Generate out-of-fold predictions for meta-learner training.
        This is the KEY step that prevents information leakage.
        """
        oof_preds = {name: np.zeros(len(X)) for name in self.base_learners}
        tscv = TimeSeriesSplit(n_splits=self.n_folds)

        for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X)):
            # Apply embargo
            if len(train_idx) > self.embargo_days:
                train_idx = train_idx[:-self.embargo_days]

            X_train = X.iloc[train_idx]
            y_train = y.iloc[train_idx]
            X_test = X.iloc[test_idx]

            for name, learner in self.base_learners.items():
                import copy
                model = copy.deepcopy(learner)
                model.fit(X_train, y_train)

                if hasattr(model, "predict_proba"):
                    preds = model.predict_proba(X_test)[:, 1]
                else:
                    preds = model.predict(X_test)

                oof_preds[name][test_idx] = preds

        return pd.DataFrame(oof_preds)

    def fit(self, X, y):
        """
        Two-stage fitting:
        1. Generate out-of-fold predictions from base learners
        2. Train meta-learner on those predictions
        """
        # Stage 1: OOF predictions
        oof_df = self._generate_oof_predictions(X, y)

        # Only use rows with non-zero predictions (from test folds)
        valid_mask = oof_df.abs().sum(axis=1) > 0
        meta_X = oof_df.loc[valid_mask]
        meta_y = y.loc[valid_mask]

        # Stage 2: Train meta-learner
        self.meta_learner.fit(meta_X, meta_y)

        # Stage 3: Retrain all base learners on full data
        for name, learner in self.base_learners.items():
            learner.fit(X, y)
            self.trained_bases[name] = learner

        return self

    def predict(self, X):
        """Predict using the full ensemble."""
        base_preds = {}
        for name, model in self.trained_bases.items():
            if hasattr(model, "predict_proba"):
                base_preds[name] = model.predict_proba(X)[:, 1]
            else:
                base_preds[name] = model.predict(X)

        meta_X = pd.DataFrame(base_preds)
        return self.meta_learner.predict(meta_X)

    def predict_with_confidence(self, X):
        """
        Predict with confidence scoring.
        Agreement among base learners = higher confidence.
        """
        base_preds = {}
        for name, model in self.trained_bases.items():
            if hasattr(model, "predict_proba"):
                base_preds[name] = model.predict_proba(X)[:, 1]
            else:
                base_preds[name] = model.predict(X)

        meta_X = pd.DataFrame(base_preds)
        ensemble_pred = self.meta_learner.predict(meta_X)

        # Confidence = 1 - disagreement among base learners
        disagreement = meta_X.std(axis=1).values
        max_disagreement = 0.5  # normalize
        confidence = 1 - (disagreement / max_disagreement).clip(0, 1)

        return ensemble_pred, confidence
```

### 6C. Model Diversity Requirements

For effective ensembles, base learners MUST be diverse. Diversity sources:

| Diversity Type | Example | Impact |
|---------------|---------|--------|
| Algorithm diversity | LightGBM + RF + Ridge | High |
| Feature subset diversity | Each model sees 70% of features | Medium |
| Training data diversity | Bootstrap samples, time windows | Medium |
| Hyperparameter diversity | 3 LightGBMs with different depths | Low |
| Target diversity | One predicts return, one predicts direction | High |

**Minimum viable ensemble for trading:**
1. LightGBM (gradient boosting - captures non-linear interactions)
2. Random Forest (bagging - robust to noise)
3. Ridge Regression (linear - captures linear relationships, regularized)
4. Meta-learner: Ridge or Logistic Regression

### 6D. Anti-Overfitting Measures (Critical for Trading ML)

```python
# Checklist for preventing overfitting in ML trading models:

ANTI_OVERFIT_CHECKLIST = {
    # Data handling
    "time_series_split": "NEVER use random train/test splits",
    "embargo_period": "5-10 day gap between train and test folds",
    "purged_cv": "Remove overlapping labels near fold boundaries",
    "no_future_leakage": "Features must use only past data (rolling windows)",

    # Model constraints
    "regularization": "L1 + L2 (reg_alpha=0.1, reg_lambda=1.0 minimum)",
    "early_stopping": "patience=50 rounds on validation set",
    "max_depth": "Keep <= 8 for daily data, <= 5 for weekly",
    "min_samples": "min_child_samples >= 20 (prefer 30-50)",
    "subsample": "0.7-0.9 (never 1.0)",
    "colsample": "0.6-0.9 (never 1.0)",

    # Validation
    "walk_forward": "Always validate with walk-forward, not single split",
    "multiple_periods": "Test across different market regimes",
    "out_of_sample_sharpe": "Must be > 0.5 out-of-sample to be tradeable",
    "decay_analysis": "Check if alpha decays over time (IC half-life)",

    # Feature engineering
    "feature_count": "< 100 features for daily data (prefer 30-60)",
    "feature_stability": "Features important across all folds",
    "economic_rationale": "Every feature must have a story",
}
```

---

## 7. Integration Points with Existing QuantSight Codebase

### Current State Assessment

Your codebase already has solid foundations:

| Component | File | Status | Suggested Upgrade |
|-----------|------|--------|-------------------|
| Alpha factors (11) | `alpha_factors.py` | Good, regime-aware | Add cross-asset features |
| Feature engineering | `ml_signal_enhancer.py` | Good, ~40-50 features | Add microstructure features |
| LightGBM signal confirmation | `ml_signal_enhancer.py` | Working | Upgrade to stacked ensemble |
| Random Forest confirmation | `ml_signal_enhancer.py` | Working | Include as base learner |
| Ensemble (LGB+RF average) | `ml_signal_enhancer.py` | Basic | Upgrade to proper stacking |
| Regime-aware weights | `alpha_factors.py` | Basic (4 regimes) | Add HMM regime detection |
| Position sizing | Not implemented | Missing | Add Kelly + Vol targeting |
| Walk-forward validation | Not implemented | Missing | Add WFO framework |

### Recommended Integration Order

1. **Immediate (high impact, low effort)**: Replace simple LGB+RF average in `EnsembleSignalConfirmer` with proper stacking using `TradingStackedEnsemble`
2. **Week 1**: Add `VolatilityTargetSizer` to position sizing pipeline
3. **Week 2**: Add `RegimeDetector` (HMM) to replace rule-based regime detection in `compute_alpha_score`
4. **Week 3**: Implement `WalkForwardOptimizer` for model validation
5. **Week 4**: Add cross-asset and microstructure features from Section 3

### Specific Code Changes

**File: `ml_signal_enhancer.py`** - Replace `EnsembleSignalConfirmer.confirm_signal`:
- Current: Simple average of LGB and RF probabilities
- Upgrade: Use `TradingStackedEnsemble` with Ridge meta-learner
- Expected improvement: 0.5-1.5% AUC uplift

**File: `alpha_factors.py`** - Replace rule-based regime weights in `compute_alpha_score`:
- Current: Manual `if regime == "trend"` weight adjustments
- Upgrade: HMM-detected regimes with learned weight profiles
- Expected improvement: Better regime transition handling

**New file: `position_sizer.py`**:
- Implement `KellySizer` (half-Kelly) + `VolatilityTargetSizer`
- Integrate with signal confidence from ensemble
- Expected improvement: Smoother equity curve, reduced drawdowns

---

## Sources

- [Machine Learning Enhanced Multi-Factor Quantitative Trading](https://arxiv.org/html/2507.07107)
- [Qlib AI Quant Workflow with LightGBM](https://vadim.blog/qlib-ai-quant-workflow-lightgbm)
- [Feature Engineering: The Unsung Hero of Deep Learning in Equity Prediction](https://www.uncorrelatedalts.com/articles/feature-engineering-the-unsung-hero-of-deep-learning-in-equity-prediction)
- [Stock Prediction with ML: Feature Engineering - The Alpha Scientist](https://alphascientist.com/feature_engineering.html)
- [Ensemble Learning in Investment - CFA Institute (2025)](https://rpc.cfainstitute.org/research/foundation/2025/chapter-4-ensemble-learning-investment)
- [Kelly Criterion for Optimal Position Sizing - PyQuant News](https://www.pyquantnews.com/the-pyquant-newsletter/use-kelly-criterion-optimal-position-sizing)
- [Walk-Forward Optimization with XGBoost - QuantInsti](https://blog.quantinsti.com/walk-forward-optimization-python-xgboost-stock-prediction/)
- [Regime-Adaptive Trading with HMM - QuantInsti](https://blog.quantinsti.com/regime-adaptive-trading-python/)
- [Stacking Ensembles: XGBoost, LightGBM, CatBoost](https://medium.com/@stevechesa/stacking-ensembles-combining-xgboost-lightgbm-and-catboost-to-improve-model-performance-d4247d092c2e)
- [Volatility-Based Position Sizing](https://medium.com/@deepml1818/volatility-based-position-sizing-with-python-how-to-adjust-your-trades-1f88efc8b228)
- [An Introduction to Volatility Targeting - QuantPedia](https://quantpedia.com/an-introduction-to-volatility-targeting/)
- [Market Regime Detection using Hidden Markov Models](https://www.pyquantlab.com/articles/Market%20Regime%20Detection%20using%20Hidden%20Markov%20Models.html)
- [Advanced Stock Market Prediction Using LSTM Networks](https://arxiv.org/html/2505.05325v1)
- [Data-driven stock forecasting models: A review](https://www.sciencedirect.com/science/article/pii/S1566253524003944)
- [MSIF-OEM: Multi-Source Information Fusion for Alpha Factors](https://www.sciencedirect.com/science/article/abs/pii/S095741742504151X)
- [Stock Price Prediction Using Stacked Heterogeneous Ensemble](https://www.mdpi.com/2227-7072/13/4/201)
- [Walk-Forward Optimization Introduction - QuantInsti](https://blog.quantinsti.com/walk-forward-optimization-introduction/)
- [Position Sizing in Trading - QuantInsti](https://blog.quantinsti.com/position-sizing/)
