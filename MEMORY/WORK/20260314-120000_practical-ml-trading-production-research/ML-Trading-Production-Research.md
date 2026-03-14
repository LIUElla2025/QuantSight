# Practical ML/AI for Trading: What Actually Works in Production

**Researcher**: Johannes (Contrarian Fact-Seeker)
**Date**: 2026-03-14
**Scope**: Production-tested ML approaches for trading signal generation

---

## The Contrarian Take Up Front

The popular narrative says "deep learning is revolutionizing trading." The data tells a different story. **The models that consistently work in live trading are boring**: gradient boosted trees (LightGBM, XGBoost), Hidden Markov Models for regime detection, and simple ensembles. Neural networks have a narrow window of superiority. Most ML trading failures come not from bad models, but from bad data handling and bad validation -- as Marcos Lopez de Prado puts it: "In finance, the hardest problem is not prediction. It's validation."

---

## 1. Which ML Models Have Proven Edge in Live Trading

### What the evidence actually shows

**Gradient Boosted Trees dominate production trading systems.** Recent multi-factor quantitative trading frameworks using gradient boosting have achieved annualized returns of approximately 20% with Sharpe ratios exceeding 2.0 during 2021-2024 (arxiv.org/html/2507.07107). These are described as "The Winning Trio" (XGBoost, LightGBM, CatBoost) that dominate tabular financial data processing.

**The contrarian finding**: Simpler models often beat complex ones in live trading. A 2025 comparative analysis of cryptocurrency prediction models found that Naive models consistently outperformed more complex ML and deep learning models in time-series analysis (Springer Nature). This is not an anomaly -- it reflects a fundamental truth: **signal-to-noise ratio in financial data is extremely low**, and complex models are better at memorizing noise.

**What actually works in production:**

| Model | Live Trading Evidence | Best Use Case |
|-------|----------------------|---------------|
| LightGBM/XGBoost | 20% annualized, Sharpe >2.0 in multi-factor frameworks | Cross-sectional stock selection, factor timing |
| Random Forest | Robust during regime changes, graceful degradation | Risk management signals, regime-specialist models |
| HMM (Hidden Markov) | Outperformed buy-and-hold 2006-2023 as regime filter | Market regime detection and strategy switching |
| LSTM/Transformers | Marginal improvement on specific time horizons | Only when you have >10 years of high-frequency data |
| Linear Models | Competitive on many tasks, much easier to maintain | Baseline that should always be compared against |

**Key insight from practitioners**: Ensemble methods (combining multiple "pretty good" models) consistently outperform individual models in live trading. They are more robust during regime changes and degrade gracefully when assumptions break. A combined XGBoost+LightGBM model outperformed both individual models and neural networks in stock prediction contexts.

---

## 2. Feature Importance: What Actually Predicts Stock Returns Out of Sample

### The popular narrative vs. the data

Most retail quants throw 200+ technical indicators at a model and let feature importance sort it out. **This is backwards.** The evidence shows:

**Top features by out-of-sample predictive power (from 166 asset pricing characteristics study using SHAP analysis):**

1. **Momentum features** -- consistently highest predictive power across model specifications
2. **Trading-based features** -- volume, turnover, liquidity measures
3. **Net equity expansion** -- corporate actions signal
4. **Return on assets** -- fundamental profitability
5. **Sales-to-price ratio** -- value signal
6. **Earnings volatility** -- risk/quality measure
7. **Sales-to-receivables** -- operational efficiency
8. **Technology industry classification** -- sector exposure

**The contrarian finding**: Most technical indicators add noise, not signal. The case study on overfitting prevention showed that cutting features from 50 to 10 improved live trading performance despite backtested accuracy dropping from 95% to 85%. **The 85% model made money; the 95% model lost money.**

**Feature engineering principles that survive regime changes:**

- **Volatility-adjusted returns** outperform raw returns as features
- **Event-based sampling** (sample on price moves >= X%, volatility spikes, volume surges) beats fixed time-interval sampling -- this is one of Lopez de Prado's most important contributions
- **Cross-asset correlation features** capture regime information that single-asset features miss
- **Market microstructure signals** (bid-ask spread dynamics, order flow imbalance) provide edge that is harder to arbitrage away
- **Fractionally differentiated features** preserve memory while maintaining stationarity -- a key technique from Advances in Financial Machine Learning

---

## 3. Overfitting Prevention: The Make-or-Break Discipline

### Why most ML trading strategies fail

**Overfitting is the DEFAULT outcome in financial ML.** The signal-to-noise ratio is so low that any sufficiently flexible model will find patterns that don't exist. Here are the techniques that actually prevent it:

### Technique 1: Feature Reduction (Most Important)
- Cut features aggressively. Real-world case: reducing from 50 indicators to 10 indicators that showed proven prediction accuracy
- Correlation analysis: remove features with >0.7 pairwise correlation
- Use SHAP values from an initial model to identify truly predictive features
- **Rule of thumb**: If you can't explain why a feature should predict returns economically, remove it

### Technique 2: Triple-Barrier Labeling (Lopez de Prado)
Instead of labeling data as "up/down after N days":
- Set a **profit-taking barrier** (e.g., +2%)
- Set a **stop-loss barrier** (e.g., -1%)
- Set a **time expiry barrier** (e.g., 5 days)
- Whichever barrier is hit first determines the label

This aligns ML labels with actual trading mechanics and dramatically reduces label noise.

### Technique 3: Statistical Corrections for Multiple Testing
- **Deflated Sharpe Ratio**: Adjusts Sharpe ratio for the number of strategies tested. A Sharpe of 2.0 after testing 1,000 strategies is meaningless -- the Deflated Sharpe tells you the probability it's real.
- **Probabilistic Sharpe Ratio**: Accounts for estimation error in Sharpe ratio calculation
- **Bonferroni correction**: Divide significance threshold by number of tests
- **Key insight**: "A high Sharpe ratio is meaningless unless you know how likely it is to be luck."

### Technique 4: Regularization
- L1 (Lasso) regularization to eliminate redundant parameters entirely
- L2 (Ridge) regularization to shrink coefficients
- Dropout in neural networks (randomly exclude neurons during training)
- Noise injection on training data to reduce sensitivity to minor patterns
- **For tree models**: Limit max_depth (start at 3-5), increase min_samples_leaf, use early stopping

### Technique 5: The GT-Score (2025 Innovation)
A composite objective function integrating:
- Performance metrics
- Statistical significance
- Consistency across time periods
- Downside risk measures

Optimizing for GT-Score instead of raw returns guides the optimizer to discard spurious patterns and favor robust solutions.

### Practical Thresholds
- Maximum features: 10-15 for daily trading models
- Train/validation/test split: 60/20/20 minimum
- If backtested Sharpe > 3.0, you are almost certainly overfit
- Require consistency across at least 3 independent time periods
- Performance should degrade <30% from backtest to paper trading

---

## 4. LightGBM vs XGBoost vs Neural Networks: Real-World Comparison

### The honest comparison

| Dimension | LightGBM | XGBoost | Neural Networks |
|-----------|----------|---------|-----------------|
| **Training Speed** | Fastest (histogram-based, leaf-wise growth) | Fast (level-wise growth) | Slowest (GPU recommended) |
| **Small Datasets (<10K samples)** | Good | Best | Poor (overfits) |
| **Large Datasets (>1M samples)** | Best | Good | Good with enough data |
| **Categorical Features** | Native support | Requires encoding | Requires encoding |
| **Interpretability** | High (SHAP, feature importance) | High | Low (black box) |
| **Missing Data** | Native handling | Native handling | Requires imputation |
| **Maintenance Burden** | Low | Low | High (architecture tuning) |
| **Out-of-Sample Accuracy** | 70-71% signal accuracy | 70-71% signal accuracy | Marginal improvement if any |
| **Regime Robustness** | Moderate | Moderate | Poor without retraining |
| **Production Deployment** | Simple | Simple | Complex (serving infrastructure) |

### When to use each

**LightGBM**: Default choice for production trading. Faster training enables more frequent model updates. Best for large feature sets and high-cardinality categoricals. Benchmarking studies show it is "the best and most consistent" across datasets.

**XGBoost**: Better for smaller datasets. Slightly more robust regularization. Use when you have <50K training samples or need maximum interpretability.

**Neural Networks (LSTM/Transformer)**: Only when:
1. You have >10 years of granular data (intraday or tick-level)
2. You are processing unstructured data (news, filings, order book sequences)
3. You have GPU infrastructure and ML engineering resources
4. An Autoformer with autocorrelation mechanism has shown ability to outperform simpler models at 1-, 3-, and 12-month horizons, but only with 920+ features

**The contrarian finding**: A combined XGBoost+LightGBM ensemble outperforms neural networks in most stock prediction tasks. The marginal accuracy improvement from deep learning rarely justifies the 10x increase in infrastructure complexity and maintenance burden.

---

## 5. Minimum Training Data Requirements

### The honest answer: it depends, but here are numbers

**General rule**: Training observations should be at least 10x the number of model parameters (degrees of freedom).

**Model-specific minimums for daily trading signals:**

| Model | Minimum Data | Recommended | Why |
|-------|-------------|-------------|-----|
| Linear/Ridge | 2-3 years | 5+ years | Few parameters, but need regime coverage |
| Random Forest | 3-5 years | 7+ years | Need enough data for tree diversity |
| XGBoost | 3-5 years (500-1000+ samples) | 5-10 years | Better with less data than LightGBM |
| LightGBM | 5+ years (1000+ samples) | 7-10 years | Leaf-wise growth needs more data |
| LSTM | 7-10 years | 10-15+ years | Deep models need substantially more |
| Transformer | 10+ years | 15+ years of daily, or 3+ years intraday | Largest data appetite |

**Critical nuance**: These are not just about volume -- you need data covering multiple market regimes (bull, bear, sideways, high-vol, low-vol, crisis). 10 years of bull market data is LESS useful than 5 years that includes a crisis.

### The Learning Curve Approach (Most Practical)
Instead of guessing:
1. Train your model on increasing amounts of data (1yr, 2yr, 3yr, ...)
2. Measure out-of-sample performance at each step
3. Plot the learning curve
4. When improvement flattens, you have enough data
5. If performance keeps improving, collect more data before going live

**For daily equity data**: You need at minimum data covering the most recent complete market cycle. For US equities, that means at minimum back to 2020 (COVID crash) and ideally to 2007 (GFC).

---

## 6. Regime Change Detection and Adaptation Using ML

### The Proven Approach: Hidden Markov Models

**HMMs are the gold standard for regime detection in production trading.** They model market conditions as hidden states that generate observable data (returns, volatility, correlations).

### Implementation Architecture

```
Step 1: Feature Engineering for Regime Detection
- Daily/weekly returns
- Realized volatility (various windows)
- Return distribution moments (skew, kurtosis)
- Cross-asset correlations
- VIX level and term structure
- Credit spreads

Step 2: HMM Training
- Use hmmlearn library (GaussianHMM class)
- Start with 2-3 states (low-vol, high-vol, crisis)
- Train on 10+ years of data
- Validate: states should correspond to economically meaningful regimes

Step 3: Regime-Adaptive Strategy Switching
Option A: Risk filter (simplest)
  - Identify current regime state
  - Reduce position sizes in high-volatility regimes
  - Eliminate trading during crisis regimes

Option B: Specialist models (more sophisticated)
  - Train separate ML models for each regime
  - Model 0: Low-volatility specialist (trend-following)
  - Model 1: High-volatility specialist (mean-reversion)
  - Switch models based on HMM-detected regime

Step 4: Live Deployment
- Serialize trained HMM with pickle
- Run regime check before each trading decision
- Retrain HMM quarterly with expanding window
```

### Performance Evidence
- HMM-based regime filtering outperformed buy-and-hold across 2006-2023
- State Street Global Advisors (2025) identified 4 distinct regimes in 30 years of US asset data using ML
- Ensemble approach (combining HMM + tree-based ensemble) provides most robust regime detection

### Alternative Approaches
- **Clustering algorithms**: Unsupervised grouping of market conditions by return distributions, volume, correlations
- **Change-point detection**: Statistical tests (CUSUM, Bai-Perron) for structural breaks
- **Ensemble voting**: Multi-model framework combining HMM + bagging + boosting for regime shift detection (2025 research)

### Critical Adaptation Parameters
- Position sizing: Scale inversely with detected volatility regime
- Execution tactics: Widen limit order spreads in high-volatility regimes
- Risk parameters: Tighten stop-losses during regime transitions
- Signal thresholds: Require stronger signals during uncertain regimes

---

## 7. Practical Cross-Validation for Time Series Financial Data

### Why Standard K-Fold CV is WRONG for Finance

Standard cross-validation randomly splits data, which creates information leakage: your model trains on data from 2024 to predict 2023. In finance, this is fatal -- it produces models that look brilliant in backtests and fail in live trading.

### The Three Methods That Work (Ranked by Robustness)

#### Method 1: Purged K-Fold Cross-Validation
**What it does**: Standard k-fold, but removes ("purges") training observations whose labels overlap temporally with test set observations.

**Implementation**:
- Split data into K folds chronologically
- For each fold used as test set:
  - Remove training observations within +/- `purge_window` of test boundaries
  - The purge window should equal the label horizon (e.g., if predicting 5-day returns, purge 5 days)
- Add an **embargo period** after each test set before the next training fold begins
- Embargo period: typically 1-2x the label horizon

**When to use**: Default method for most trading ML. Simple to implement, meaningful improvement over naive approaches.

#### Method 2: Walk-Forward Validation
**What it does**: Mimics actual trading by training on past data and testing on subsequent data, then advancing the window.

**Implementation**:
- Define training window (e.g., 3 years) and test window (e.g., 6 months)
- Train on window 1, test on subsequent period
- Advance by test window length, retrain, repeat
- Options: expanding window (growing training set) vs. rolling window (fixed training size)

**Weakness identified in 2025 research**: Walk-forward exhibits "notable shortcomings in false discovery prevention, characterized by increased temporal variability and weaker stationarity." It can produce inconsistent estimates.

**When to use**: Good for production deployment simulation. Use expanding window unless you believe old data is harmful.

#### Method 3: Combinatorial Purged Cross-Validation (CPCV) -- Gold Standard
**What it does**: Generates a large number of train-test paths through historical data, each with purging and embargo. Produces a distribution of performance estimates rather than a single number.

**2025 evidence**: CPCV demonstrates "marked superiority in mitigating overfitting risks, outperforming traditional methods as evidenced by its lower Probability of Backtest Overfitting (PBO) and superior Deflated Sharpe Ratio (DSR) test statistic."

**Limitation**: Requires sufficiently long time series. With <5 years of daily data, the windows become too short for statistically meaningful results.

**When to use**: Final validation before deploying capital. When you need confidence that your strategy is not overfit.

### Comparison Matrix

| Method | Overfitting Prevention | Ease of Implementation | Data Requirement | Production Relevance |
|--------|----------------------|----------------------|-----------------|---------------------|
| Purged K-Fold | Good | Easy | Moderate | Medium |
| Walk-Forward | Moderate | Easy | Low | Highest (mimics reality) |
| CPCV | Best | Complex | High (5+ years) | Medium (statistical confidence) |

### Recommended Approach
Use **all three** in sequence:
1. **Purged K-Fold** during model development and feature selection
2. **Walk-Forward** to simulate production performance
3. **CPCV** as final gate before deploying capital

If walk-forward and CPCV disagree significantly, do not deploy.

---

## Summary: The Contrarian Playbook for ML Trading

1. **Start with gradient boosted trees** (LightGBM or XGBoost), not neural networks. They work on the data sizes retail traders have.

2. **Fewer features, better features.** Cut to 10-15 economically meaningful features. Momentum, volatility-adjusted returns, and fundamental ratios beat 200 technical indicators.

3. **Triple-barrier labeling** aligns your ML labels with actual trading mechanics. Stop using fixed-horizon up/down labels.

4. **Overfitting is your enemy, not model complexity.** An 85% accurate model that makes money beats a 95% accurate model that loses money.

5. **Detect regimes first, then trade.** A 2-state HMM (low-vol / high-vol) as a risk filter is the single highest-value ML component you can add to any trading system.

6. **Purged cross-validation is non-negotiable.** If you are using standard k-fold or simple train/test split on financial data, your results are meaningless.

7. **Require consistency.** Any strategy must show positive performance across multiple independent time periods, regime types, and validation methods before deployment.

---

## Sources

- [ML Enhanced Multi-Factor Quantitative Trading (2025)](https://arxiv.org/html/2507.07107)
- [Significance of Predictors: Stock Return Predictions Using Explainable AI](https://link.springer.com/article/10.1007/s10479-025-06717-2)
- [Deep Learning for Algorithmic Trading: Systematic Review](https://www.sciencedirect.com/science/article/pii/S2590005625000177)
- [ML Approaches to Cryptocurrency Trading Optimization](https://link.springer.com/article/10.1007/s44163-025-00519-y)
- [GT-Score: Robust Objective Function for Reducing Overfitting](https://www.mdpi.com/1911-8074/19/1/60)
- [Overfitting in Trading Models: Causes and Prevention](https://bluechipalgos.com/blog/overfitting-in-trading-models-causes-and-prevention/)
- [Market Regime Detection with ML (QuestDB)](https://questdb.com/glossary/market-regime-change-detection-with-ml/)
- [Two Sigma: ML Approach to Regime Modeling](https://www.twosigma.com/articles/a-machine-learning-approach-to-regime-modeling/)
- [State Street: Decoding Market Regimes with ML (2025)](https://www.ssga.com/library-content/assets/pdf/global/pc/2025/decoding-market-regimes-with-machine-learning.pdf)
- [HMM Regime Detection in QSTrader (QuantStart)](https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/)
- [Regime-Adaptive Trading with HMM + Random Forest](https://blog.quantinsti.com/regime-adaptive-trading-python/)
- [Purged Cross-Validation (Wikipedia)](https://en.wikipedia.org/wiki/Purged_cross-validation)
- [Backtest Overfitting Comparison of Out-of-Sample Methods (2025)](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110)
- [CPCV for Optimization (QuantBeckman)](https://www.quantbeckman.com/p/with-code-combinatorial-purged-cross)
- [Key Takeaways from Lopez de Prado's AFML](https://abouttrading.substack.com/p/my-key-takeways-from-maros-lopez)
- [Machine Learning for Trading (Stefan Jansen)](https://github.com/stefan-jansen/machine-learning-for-trading)
- [Gradient Boosting for Quantitative Finance (Risk.net)](https://www.risk.net/journal-of-computational-finance/7812386/gradient-boosting-for-quantitative-finance)
- [Stock Return Prediction: Transformers vs Simple NN](https://www.sciencedirect.com/science/article/abs/pii/S1544612325020379)
- [Walk-Forward Validation for Market Microstructure Signals](https://arxiv.org/html/2512.12924v1)
- [Ensemble-HMM Voting Framework for Regime Shift Detection (2025)](https://www.aimspress.com/article/id/69045d2fba35de34708adb5d)
- [XGBoost vs LightGBM Comprehensive Analysis](https://medium.com/@data-overload/comparing-xgboost-and-lightgbm-a-comprehensive-analysis-9b80b7b0079b)
