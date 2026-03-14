# Momentum Crash Protection, Regime Detection & Adaptive Strategy Switching
## Research Report -- Ava Sterling, Strategic Research

**Date**: 2026-03-14
**Scope**: Academic literature review with implementation parameters
**Focus**: Momentum crash hedging, HMM regime detection, adaptive switching, Asian market specifics

---

## 1. Momentum Crash Protection Strategies

### 1.1 Daniel & Moskowitz (2016) -- "Momentum Crashes"

**Core Finding**: Momentum strategies experience infrequent but devastating crashes that are partly forecastable. Crashes occur in "panic states" following market declines when volatility is high, and are contemporaneous with market rebounds.

**Dynamic Momentum Strategy (DMS)**:

The key innovation is a dynamic strategy that levers up or down so that conditional volatility is proportional to the conditional Sharpe ratio:

```
w_t = (1/sigma^2_t) * mu_t

Where:
  w_t    = dynamic weight at time t
  mu_t   = conditional expected return (forecasted mean)
  sigma^2_t = conditional variance (forecasted variance)
```

**Implementation Steps**:
1. Form the static WML (Winner-minus-Loser) momentum portfolio
2. Regress static momentum returns on other factors using daily returns
3. Use residuals to forecast conditional mean and variance
4. Dynamic weight = forecasted mean / forecasted variance
5. Scale to match target volatility

**Key Parameters**:
- **Beta estimation window**: 42 trading days (approximately 2 months) of lagged returns
- **Variance estimation**: Rolling 126-day (6-month) realized variance of daily returns
- **Mean estimation**: Regress on bear market indicator and interaction terms
- **Rebalancing**: Monthly

**Performance**:
- Approximately doubles the alpha and Sharpe ratio vs. static momentum
- Robust across international equity markets and asset classes
- Not explained by other known factors

**Citation**: Daniel, K., & Moskowitz, T. J. (2016). Momentum Crashes. *Journal of Financial Economics*, 122(2), 221-247.

---

### 1.2 Barroso & Santa-Clara (2015) -- "Momentum Has Its Moments"

**Core Finding**: The risk of momentum is highly variable over time and predictable. Managing this risk virtually eliminates crashes and nearly doubles the Sharpe ratio.

**Constant Volatility Scaling (CVS) Strategy**:

```
w_t = sigma_target / sigma_realized_t

Where:
  sigma_target    = 12% (annualized target volatility)
  sigma_realized_t = annualized realized standard deviation of daily
                     momentum portfolio returns over past 126 trading days (6 months)
```

**Implementation Steps**:
1. Form standard long-short momentum portfolio (e.g., top decile minus bottom decile)
2. Each month, compute annualized realized volatility from daily returns over prior 6 months (126 trading days)
3. Scale factor = 12% / realized_volatility
4. Multiply portfolio weights by scale factor
5. Cap scale factor at reasonable maximum (e.g., 2.0) to prevent excessive leverage

**Key Parameters**:
- **Target volatility**: 12% annualized
- **Lookback for realized volatility**: 126 trading days (6 months) of daily returns
- **Scale factor range**: Average 0.90, range 0.13 to 2.00
- **Rebalancing**: Monthly
- **Leverage cap**: Implicit at ~2x based on historical range

**Performance**:
- Gross Sharpe ratio nearly doubles: 0.53 --> 0.97
- Worst monthly return improves: -80.0% --> -28.4%
- Worst annual drawdown improves: -97.0% --> -45.2%
- Turnover comparable to plain momentum (feasible transaction costs)

**Citation**: Barroso, P., & Santa-Clara, P. (2015). Momentum Has Its Moments. *Journal of Financial Economics*, 116(1), 111-120.

---

### 1.3 Comparison: CVS vs. DVS

| Feature | CVS (Barroso & Santa-Clara) | DVS (Daniel & Moskowitz) |
|---------|----------------------------|--------------------------|
| Scaling basis | Inverse of realized variance only | Conditional mean / conditional variance |
| Mean forecast | Not used | Yes (bear market indicator) |
| Complexity | Simple, easily implementable | More complex, requires mean estimation |
| Equivalence | Equivalent when Sharpe ratio is time-invariant | Optimal when Sharpe ratio varies over time |
| Recommendation | Start here -- simpler, robust | Add if mean forecasting is reliable |

**Strategic Insight**: Begin with CVS (simpler, more robust). Layer DVS mean-forecasting on top once you have validated the volatility-scaling foundation. The incremental benefit of DVS is largest during regime transitions, which is precisely when mean forecasting is hardest.

---

## 2. Market Regime Detection Using Hidden Markov Models

### 2.1 HMM Architecture for Trading

**Model Structure**:
- **Hidden states**: 2-3 states (Bull / Bear, or Bull / Bear / Neutral)
- **Observable features**: Returns, volatility, drawdown metrics
- **Transition matrix**: Defines probability of regime persistence vs. switching
- **Emission distributions**: Gaussian profiles for each regime

**Recommended Configuration (3-State Model)**:

```
State 0 (Bull):    mean_return > 0, low_volatility
State 1 (Neutral): mean_return ~ 0, medium_volatility
State 2 (Bear):    mean_return < 0, high_volatility
```

### 2.2 Key Implementation Parameters

**Observable Features (Input Vector)**:
1. Daily log returns
2. Realized volatility (rolling 21-day annualized std dev)
3. Drawdown from recent peak (rolling 126-day peak)
4. VIX or implied volatility level (if available)
5. Return at multiple horizons: 5-day, 21-day, 63-day

**Lookback Window for Training**:
- **Recommended**: 2500-2700 trading days (~10 years)
- **Sliding window**: Retrain daily on most recent window
- **Minimum viable**: 1260 trading days (~5 years)

**Model Hyperparameters**:
- **Number of states**: 2 or 3 (use BIC/AIC for selection)
- **Covariance type**: "full" (captures correlation between features)
- **EM iterations**: max 100-200, convergence tolerance 1e-4
- **Learning rate** (for online updates): 0.01-0.1
- **Random restarts**: 10-20 (HMM is sensitive to initialization)

**Regime Classification Logic**:
```python
# After fitting, classify regimes by characteristics
regime_means = model.means_
regime_covs = model.covars_

# Sort regimes by mean return
bear_regime = argmin(regime_means[:, 0])   # Lowest return
bull_regime = argmax(regime_means[:, 0])   # Highest return
neutral_regime = remaining index
```

### 2.3 Alternative ML Approaches for Regime Detection

| Method | Strengths | Weaknesses | Best For |
|--------|-----------|------------|----------|
| HMM (Gaussian) | Probabilistic, interpretable, handles temporal dynamics | Assumes Gaussian emissions, fixed # states | Core regime framework |
| Bayesian Online CPD | Real-time, no fixed states | Can be noisy | Detecting regime transitions |
| LSTM/Deep Learning | Captures nonlinear patterns | Black box, needs large data | Enhancing signal quality |
| Random Forest on features | Feature importance, robust | No temporal structure | Confirming regime signals |
| Ensemble HMM + Voting | Reduces false signals | More complex | Production systems |

### 2.4 Practical Implementation Notes

**Avoiding Look-Ahead Bias**:
- Train only on data available at decision time
- Use expanding or sliding window (never include future data)
- Add 1-day lag between signal generation and execution

**Regime Persistence Filter**:
- Require regime to persist for N consecutive days before switching (N = 3-5)
- Alternatively, use probability threshold: act only when P(regime) > 0.7

**Transition Smoothing**:
- Exponential moving average of regime probabilities
- Prevents whipsawing between regimes on noisy days

---

## 3. Adaptive Strategy Switching: Momentum vs. Mean Reversion

### 3.1 Theoretical Framework

**Core Insight**: Momentum and mean reversion are regime-dependent phenomena:
- **Bull markets**: Momentum dominates (trends persist)
- **Bear markets**: Mean reversion dominates (short-squeeze rallies, oversold bounces)
- **Transition periods**: Both signals are unreliable -- reduce exposure

### 3.2 Regime-Switching Model (Giner & Zakamulin, 2023)

A two-state regime-switching process reproduces:
- Fat tails and negative skewness
- Volatility clustering
- Short-term momentum within regimes
- Medium-term mean reversion across regimes

**Optimal Trading Rules by Model Type**:

| Market Model | Optimal Rule | Implementation |
|--------------|-------------|----------------|
| Markov (geometric durations) | Exponential Moving Average (EMA) | EMA crossover |
| Semi-Markov (duration dependence) | MACD-like rule | MACD(12,26,9) or similar |
| Unknown | 10-month SMA or 12-month Momentum | Simple trend following |

**Key Finding**: Under a semi-Markov model (more realistic, as bull/bear duration increases termination probability), the optimal rule resembles MACD and outperforms the popular 10-month SMA and 12-month momentum rules.

### 3.3 Deep Learning + Changepoint Detection Approach

**Architecture** (from "Slow Momentum with Fast Reversion"):
1. **LSTM Deep Momentum Network** for trend estimation and position sizing
2. **Online Changepoint Detection (CPD)** module inserted into the pipeline
3. Model simultaneously learns:
   - **Slow momentum**: Exploits persisting trends without overreacting
   - **Fast mean reversion**: Captures rapid reversals at turning points

**Performance**: Adding CPD module improves Sharpe ratio by approximately one-third, with especially significant benefits during periods of high nonstationarity (regime transitions).

### 3.4 Practical Adaptive Switching Implementation

**Simple Rules-Based Approach**:

```
Step 1: Detect regime using HMM or simpler indicators
Step 2: Apply strategy based on regime

IF regime == BULL:
    strategy = TIME_SERIES_MOMENTUM
    lookback = 12 months (252 days)
    signal = sign(cumulative_return_252d)
    position_size = vol_target / realized_vol

ELIF regime == BEAR:
    strategy = MEAN_REVERSION
    lookback = 5-20 days
    signal = -zscore(price, lookback=20)
    entry = zscore < -2.0
    exit  = zscore > 0.0
    position_size = 0.5 * vol_target / realized_vol  # Reduced size

ELIF regime == TRANSITION/NEUTRAL:
    strategy = RISK_OFF
    position_size = 0.25 * normal_size  # Minimal exposure

Step 3: Apply volatility scaling (Barroso-Santa-Clara) regardless of regime
Step 4: Apply maximum drawdown stop-loss (e.g., -15% trailing)
```

**Regime Detection Indicators (Simple Alternative to HMM)**:
- 200-day SMA trend: price > SMA200 = bull tendency
- Realized volatility percentile: vol > 80th percentile = stress
- Drawdown from peak: DD > 10% = bear tendency
- Composite: require 2 of 3 for regime classification

---

## 4. Asian Market Specifics: Hong Kong & China

### 4.1 Critical Differences from Western Markets

**China A-Shares (Shanghai/Shenzhen)**:
- **NO medium-term momentum**: Traditional 6-12 month momentum is weak or negative
- **Strong short-term reversal**: Weekly returns reverse significantly
- **Daily momentum exists**: Stocks rising today tend to rise tomorrow, then reverse within a week
- **T+1 mechanism**: Cannot sell on same day of purchase, creating unique microstructure effects
- **Contrarian strategies dominate**: 4-8 week formation/holding periods generate ~0.2%/week

**Hong Kong (Hang Seng)**:
- **Intermediate-term momentum exists** but becomes insignificant after risk adjustment
- **Momentum is highly cyclical**: One of the most cyclical factors in HK
- **Low volatility and quality**: Most defensive factors in HK
- **Small cap factor**: Highly cyclical, similar to momentum

### 4.2 Recommended Parameters for Asian Markets

**For China A-Shares**:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Strategy Type | Contrarian / Mean Reversion | Momentum is weak; reversal dominates |
| Formation Period | 4-8 weeks (20-40 trading days) | Empirically optimal for A-shares |
| Holding Period | 4-8 weeks (20-40 trading days) | Matches formation period |
| Daily Momentum | 1 day formation, 1-2 day hold | Very short-term momentum exists |
| 52-Week High | Proximity to 52-week high | Produces positive returns 1995-2018 (0.28%/month) |
| Volatility Scaling | 6-month realized vol, target 10-15% | Lower target due to higher base volatility |
| Regime Detection | 3-state HMM, retrain weekly | More frequent regime changes |

**For Hong Kong**:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Strategy Type | Adaptive (momentum + mean reversion) | Momentum works in intermediate term but is cyclical |
| Momentum Formation | 6-12 months (126-252 days) | Standard intermediate-term works somewhat |
| Momentum Holding | 1-3 months (21-63 days) | Shorter holding than formation |
| Mean Reversion Trigger | Drawdown > 15% from peak | Switch to contrarian in stress |
| Volatility Scaling | 6-month realized vol, target 12% | Similar to US approach |
| Skip Month | Yes, skip most recent month | Removes short-term reversal noise |
| Regime Detection | 2-state HMM (sufficient) | Simpler market structure |

### 4.3 Asian Market Regime Detection Adjustments

**Additional Features for HMM in Asian Markets**:
- Northbound/Southbound flow data (Stock Connect)
- USD/CNH exchange rate momentum
- China credit impulse indicators
- PBoC policy stance proxies
- US-China yield spread

**Regime Characteristics (China-Specific)**:

```
Bull Regime:
  - Northbound flows positive and accelerating
  - CNH appreciating
  - Volatility below 20th percentile
  - Strategy: Momentum on 52-week high proximity

Bear Regime:
  - Northbound flows negative
  - CNH depreciating
  - Volatility above 70th percentile
  - Strategy: Mean reversion (4-8 week contrarian)

Policy Regime (China-unique):
  - PBoC easing signals
  - Credit impulse turning positive
  - Strategy: Sector rotation toward policy beneficiaries
```

### 4.4 Market State Dependency

Research shows asymmetric momentum effects in China:
- **Post-UP-market**: Momentum effect is stronger
- **Post-DOWN-market**: Momentum effect weakens substantially
- **Implication**: Use market state as a conditioning variable for strategy selection

---

## 5. Complete Implementation Architecture

### 5.1 Integrated System Design

```
Layer 1: REGIME DETECTION
  Input:  Daily OHLCV, macro indicators, flow data
  Model:  3-state Gaussian HMM (retrain weekly on 2500-day window)
  Output: Regime probabilities [P(bull), P(neutral), P(bear)]
  Filter: Require P(regime) > 0.7 for 3+ consecutive days

Layer 2: STRATEGY SELECTION
  IF P(bull) > 0.7:
    Activate: Time-series momentum (12-month lookback for HK,
              52-week high for China A-shares)
  IF P(bear) > 0.7:
    Activate: Mean reversion (20-day lookback for HK,
              4-8 week contrarian for China A-shares)
  IF no regime > 0.7:
    Activate: Risk-off (minimal positions, cash-heavy)

Layer 3: CRASH PROTECTION (always active)
  Barroso-Santa-Clara volatility scaling:
    weight = sigma_target / sigma_realized_126d
    Cap weight at 2.0, floor at 0.1

  Daniel-Moskowitz dynamic adjustment (optional layer):
    IF bear_market_indicator AND high_volatility:
      Further reduce exposure by 50%

Layer 4: RISK MANAGEMENT
  - Position-level stop-loss: -8% from entry
  - Portfolio-level stop-loss: -15% trailing drawdown
  - Sector concentration limit: max 30% in any sector
  - Single stock limit: max 5% of portfolio
```

### 5.2 Key Thresholds Summary

| Parameter | Value | Source |
|-----------|-------|--------|
| Volatility target (standard) | 12% annualized | Barroso & Santa-Clara |
| Volatility target (Asia, conservative) | 10% annualized | Adjusted for higher base vol |
| Realized vol lookback | 126 trading days (6 months) | Both BSC and DM |
| Beta estimation window | 42 trading days (2 months) | Daniel & Moskowitz |
| HMM training window | 2500-2700 trading days | Empirical best practice |
| HMM number of states | 2-3 | BIC/AIC selected |
| Regime probability threshold | 0.7 | Reduces false signals |
| Regime persistence filter | 3-5 consecutive days | Prevents whipsaw |
| Momentum lookback (US/HK) | 252 days (12 months) | Academic standard |
| Momentum lookback (China) | 5-40 days (contrarian) | Empirical finding |
| Mean reversion lookback | 5-20 days | Short-term oversold |
| Max leverage (vol scaling) | 2.0x | Barroso & Santa-Clara range |
| Min leverage (vol scaling) | 0.1x | Risk-off floor |
| Portfolio drawdown stop | -15% trailing | Risk management |

---

## 6. Strategic Insights & Second-Order Effects

### 6.1 Three Moves Ahead

1. **Crowding Risk**: As volatility-managed momentum becomes more popular, the strategy's capacity decreases. The very act of scaling down during high volatility creates additional selling pressure, potentially amplifying crashes. Consider implementing slightly ahead of the crowd (scale down at the 60th volatility percentile rather than waiting for extremes).

2. **Regime Detection Lag**: HMMs are inherently backward-looking. By the time the model confidently detects a bear regime, the worst of the crash may have already occurred. Complement HMM with forward-looking indicators (options-implied volatility, credit spreads, flow data) to anticipate regime transitions.

3. **China Policy Regime**: Unlike Western markets where regimes are primarily market-driven, China has a distinct "policy regime" where government intervention can create sharp regime transitions. The National Team (national funds buying equities) and PBoC actions create a third axis of regime that HMMs trained purely on price data will miss.

### 6.2 Implementation Priorities

**Phase 1 (Immediate)**: Implement Barroso-Santa-Clara CVS on existing momentum strategies. This is the highest-impact, lowest-complexity improvement.

**Phase 2 (1-2 months)**: Add 3-state HMM regime detection with regime-conditional strategy selection. Start with 2 states, validate, then extend to 3.

**Phase 3 (3-6 months)**: Layer in Daniel-Moskowitz dynamic adjustments and LSTM-based changepoint detection for anticipating regime transitions.

**Phase 4 (6-12 months)**: Full adaptive system with China-specific features (flow data, policy indicators) and real-time regime-conditional execution.

---

## Sources

- [Daniel & Moskowitz - Momentum Crashes (NBER Working Paper)](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf)
- [Daniel & Moskowitz - Momentum Crashes (JFE 2016)](https://www.sciencedirect.com/science/article/pii/S0304405X16301490)
- [Barroso & Santa-Clara - Momentum Has Its Moments (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2041429)
- [Risk-Managed Industry Momentum (Quantitative Finance)](https://www.tandfonline.com/doi/full/10.1080/14697688.2017.1420211)
- [Risk of Momentum Crashes - Alpha Architect](https://alphaarchitect.com/risk-of-momentum-crashes/)
- [Risk Adjusted Momentum: CVS vs DVS (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3076715)
- [Avoiding Momentum Crashes: Dynamic Momentum](https://www.sciencedirect.com/science/article/abs/pii/S1042443118303093)
- [HMM Market Regime Detection - QuantStart](https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/)
- [Regime-Switching Factor Investing with HMMs (MDPI)](https://www.mdpi.com/1911-8074/13/12/311)
- [HMM Market Regime Detection (Medium)](https://datadave1.medium.com/detecting-market-regimes-hidden-markov-model-2462e819c72e)
- [Market Regime Detection - QuestDB](https://questdb.com/glossary/market-regime-detection-using-hidden-markov-models/)
- [Regime-Switching Model with Momentum and Mean Reversion (Giner & Zakamulin)](https://www.sciencedirect.com/science/article/pii/S0264999323000494)
- [Optimal Trend Following in Regime-Switching Models](https://link.springer.com/article/10.1057/s41260-024-00357-0)
- [Slow Momentum with Fast Reversion (JF Data Science)](https://jfds.pm-research.com/content/4/1/111)
- [Mean-Reversion and Momentum Regime Switching](https://www.priceactionlab.com/Blog/2024/01/mean-reversion-and-momentum-regime-switching/)
- [Daily Momentum in Emerging Markets](https://wxiong.mycpanel.princeton.edu/papers/DailyMomentum.pdf)
- [Momentum in Chinese Stock Market](https://www.sciencedirect.com/science/article/abs/pii/S0927538X19305323)
- [Momentum Trading in Hong Kong](https://www.sciencedirect.com/science/article/abs/pii/S1059056010000304)
- [Contrarian Strategies in China](https://www.sciencedirect.com/science/article/abs/pii/S1059056018301928)
- [52-Week High Momentum in China (SSRN)](https://papers.ssrn.com/sol3/Delivery.cfm/4925973.pdf?abstractid=4925973)
- [T+1 Contrarian Effect in China](https://www.sciencedirect.com/science/article/abs/pii/S1059056024006452)
- [Smart Beta in Hong Kong - S&P Global](https://www.spglobal.com/spdji/en/documents/research/research-how-smart-beta-strategies-work-in-the-hong-kong-market.pdf)
- [Volatility Scaling for Momentum - CXO Advisory](https://www.cxoadvisory.com/volatility-effects/volatility-scaling-for-momentum-strategies/)
- [Enhanced Momentum Strategies](https://www.sciencedirect.com/science/article/abs/pii/S0378426622002928)
- [Ensemble HMM Voting for Regime Detection](https://www.aimspress.com/article/id/69045d2fba35de34708adb5d)
