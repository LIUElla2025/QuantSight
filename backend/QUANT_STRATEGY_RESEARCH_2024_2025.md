# Comprehensive Quantitative Trading Strategy Research Report
## 2024-2025 | Retail-Focused | HK Market Emphasis

**Researcher**: Ava Sterling | **Date**: 2026-03-13
**Scope**: 9 research threads, 19 parallel searches, English + Chinese sources

---

## Table of Contents

1. [Strategies That Work for Retail Traders ($1K-$100K)](#1-strategies-for-retail-traders)
2. [Hong Kong Stock Market Specific Strategies](#2-hong-kong-specific-strategies)
3. [Open Source Strategies with Sharpe > 1.5](#3-open-source-high-sharpe-strategies)
4. [Machine Learning / AI Trading Strategies](#4-ml-ai-strategies)
5. [Competition-Winning Strategies](#5-competition-winning-strategies)
6. [Momentum + Mean Reversion Hybrids](#6-momentum-mean-reversion-hybrids)
7. [Statistical Arbitrage & Pairs Trading](#7-statistical-arbitrage-pairs-trading)
8. [Volatility-Based Strategies](#8-volatility-strategies)
9. [Strategies Claiming 100%+ Annual Returns](#9-high-return-strategies)
10. [Strategic Synthesis & Recommendations](#10-strategic-synthesis)

---

## 1. Strategies for Retail Traders ($1K-$100K)

### Capital Tier Breakdown

| Capital Range | Viable Strategies | Key Constraints |
|---|---|---|
| $1,000-$5,000 | Single-stock mean reversion, momentum on ETFs, crypto bot trading | Commission drag significant, limited diversification |
| $5,000-$20,000 | Pairs trading (2-3 pairs), factor rotation, options mean reversion | Can run 2-5 concurrent positions |
| $20,000-$100,000 | Full stat arb portfolios, multi-factor models, volatility selling | Proper diversification possible |

### Risk Management for Small Accounts

- **Fixed Fractional**: Risk 1-2% of capital per trade (optimal for retail per QuantInsti research)
- **For $10,000 account**: Risk no more than $100-$200 per trade
- **Position sizing formula**: Position Size = (Account * Risk%) / (Entry - StopLoss)
- **Minimum viable**: Need at least 20x the average trade size to survive drawdowns
- **Kelly Criterion (half-Kelly recommended)**: f* = (bp - q) / b, where b=odds, p=win probability, q=1-p

### Best Strategies by Capital Size

**$1K-$10K: Mean Reversion on Liquid ETFs**
- Trade SPY, QQQ, or HK ETFs (2800.HK, 2828.HK)
- RSI(14) < 30 entry, RSI(14) > 70 exit
- Backtest result: 58% win rate on SPY (2014-2024), avg winner +5.2%, avg loser -2.8%
- Annual return: ~11.4%, Max drawdown: -18%

**$10K-$50K: Multi-Factor Momentum + Reversion**
- Combine 3-6 month momentum lookback with RSI mean reversion filter
- Rebalance monthly to minimize commission impact
- Sharpe historically strong across construction choices

**$50K-$100K: Pairs Trading + Volatility Premium**
- Run 3-5 cointegrated pairs simultaneously
- Sell covered calls or cash-secured puts for additional premium
- Diversify across sectors/markets

### Platforms Accessible to Retail

| Platform | Best For | Cost | Language |
|---|---|---|---|
| QuantConnect | Backtesting & live trading | Free tier available | Python/C# |
| Freqtrade | Crypto trading bots | Open source | Python |
| VNPy (vnpy) | Chinese market trading | Open source | Python |
| Backtrader | Backtesting | Open source | Python |
| WonderTrader | Full-stack Chinese markets | Open source | C++/Python |
| QMT/PTrade | Chinese broker integration | Broker-dependent | Python |

---

## 2. Hong Kong Stock Market Specific Strategies

### HK Market Characteristics

- **T+0 settlement** for stocks (unlike A-shares T+1) -- enables intraday strategies
- **No daily price limits** (unlike A-shares +/-10%)
- **Stamp duty**: 0.13% (each way) -- significant cost for high-frequency
- **Market hours**: 9:30-12:00, 13:00-16:00 HKT
- **2024 performance**: HSI +18% after 4-year losing streak
- **2025 performance**: HK50 +35.4% YTD as of Oct 2025

### Proven HK-Specific Strategies

#### Strategy 1: HSI Constituent Pairs Trading
**Research basis**: Academic paper "The profitability of pairs trading strategies on Hong-Kong stock market" (Warsaw School of Economics, 2022)

**Key finding**: All three methods (distance, cointegration, correlation) are profitable in HK and beat the market on risk-adjusted basis.

**Implementation**:
- Universe: HSI 60 constituent stocks
- Formation period: 12 months
- Trading period: 6 months
- Cointegration test: Engle-Granger or Johansen
- Entry: Z-score > 2.0 standard deviations from mean
- Exit: Z-score crosses 0 (mean)
- Stop-loss: Z-score > 4.0 (relationship breakdown)

**Sensitivity**: Results sensitive to number of pairs traded and rebalancing period, less sensitive to leverage

#### Strategy 2: HK T+0 Intraday Mean Reversion
**Concept**: Exploit HK's T+0 settlement for intraday mean reversion

**Implementation**:
- Hold a "base position" (底仓) in liquid HK stocks or ETFs
- Buy dips intraday, sell base position at higher price (or vice versa)
- Net position stays constant; profit from intraday spread
- Works best with: 2800.HK (Tracker Fund), 9988.HK (Alibaba), 0700.HK (Tencent)

**Parameters**:
- Bollinger Band period: 20 (5-min bars)
- Entry: Price touches lower band + volume spike > 1.5x average
- Exit: Price returns to middle band
- Position: 30-50% of base position per trade
- Risk: Set max daily loss at 0.5% of portfolio

**Chinese broker T0 services**: Many brokers (e.g., HTSC via Futu) now offer T0 algorithm services for retail, though commissions increase from ~0.01% to ~0.019%

#### Strategy 3: AH Premium Arbitrage
**Concept**: Exploit price differences between A-share and H-share listed companies

**Implementation**:
- Monitor AH premium index
- When premium is historically high: long H-share, short A-share (via Stock Connect)
- When premium narrows: close both positions
- Common pairs: China Construction Bank (0939.HK/601939.SS), ICBC (1398.HK/601398.SS)

**Caveat**: Capital controls and settlement differences create friction

#### Strategy 4: HK Market Momentum + Policy Signal
**Concept**: Chinese policy announcements drive HK tech/property rallies
- Monitor PBOC rate decisions, CSRC policy, property sector support
- September 2024 rally (+18% in weeks) was policy-driven
- Long Hang Seng Tech Index constituents on policy easing signals

### Open-Source Quantitative Portfolios (Port Stock Selection, 2024)
- KaiYuan Securities HK quant portfolio: +5.5% alpha over benchmark in 2024
- Strategy: Multi-factor model (value + momentum + quality factors)
- Monthly rebalancing, top 20 stock selection from HSI universe

---

## 3. Open Source Strategies with Sharpe > 1.5

### Framework: FinRL (Deep Reinforcement Learning)
- **GitHub**: github.com/AI4Finance-Foundation/FinRL
- **Best result**: DDPG agent achieved **Sharpe ratio 2.21** with 36.01% annual return on Dow 30 stocks
- **Algorithms**: PPO, A2C, DDPG, SAC, TD3
- **Data**: Yahoo Finance, Alpaca, RiceQuant
- **Implementation**: Python, OpenAI Gym interface

### Framework: Qbot (AI Quantitative Trading Robot)
- **GitHub**: github.com/UFund-Me/Qbot
- **Features**: AI stock selection, strategy development, backtesting, paper trading, live trading
- **Fully local deployment**

### Framework: awesome-systematic-trading
- **GitHub**: github.com/paperswithbacktest/awesome-systematic-trading
- **Content**: 97 libraries, 40+ institutional/academic strategies
- **Notable strategies with documented Sharpe > 1.5**:
  - Trend following on futures (CTA): Sharpe 1.5-2.5 historically
  - Cross-sectional momentum on equities: Sharpe 1.5-2.0
  - Volatility risk premium harvesting: Sharpe 1.5-3.0

### Specific High-Sharpe Strategies from Literature

#### 1. Short-Term Reversal (1-week lookback)
- Long bottom decile, short top decile by past-week returns
- Historical Sharpe: 1.5-2.5 (before transaction costs)
- **Warning**: Transaction costs eat most alpha at retail scale

#### 2. Carry Trade + Momentum Combo (FX)
- Sharpe ~1.8 in academic backtests
- Combine interest rate differentials with 3-month price momentum
- Accessible via forex brokers at retail scale

#### 3. Volatility Risk Premium (Options Selling)
- Sell SPX put spreads or iron condors
- Implied vol consistently exceeds realized vol by 2-4%
- Sharpe 1.5-3.0 in backtests (but negative skew!)
- **Specific implementation**: Sell 30-delta puts, 45 DTE, manage at 50% profit or 200% loss

### Chinese Open Source Resources
- **VNPy** (github.com/vnpy/vnpy): Most popular Chinese quant framework, 20K+ stars
- **QUANTAXIS**: Full-stack for Chinese stocks, futures, crypto
- **hugo2046/QuantsPlaybook**: Replication of Chinese brokerage research reports
- **Claimed results from Chinese community**:
  - "Bollinger Band + Order Flow" combo on SPY options: 82% annualized
  - ETH/USDT volatility strategy: 243% annualized (2021-2023 backtest) -- likely overfitted

---

## 4. Machine Learning / AI Trading Strategies

### Category 1: Deep Learning Price Prediction

#### LSTM Networks
- **Architecture**: 2-3 LSTM layers, 50-128 units each, dropout 0.2-0.3
- **Input window**: 60 trading days predicting day 61
- **Early stopping**: patience=10 epochs
- **Training data**: OHLCV + technical indicators (SMA, EMA, RSI, Bollinger Bands)
- **Enhancement**: Add sentiment scores from news (NLP)
- **Realistic Sharpe**: 0.5-1.0 as standalone strategy

#### Transformer-Based (Quantformer)
- **Published**: arxiv.org/abs/2404.00424
- **Backtest period**: March 2020 - April 2023
- **Results**: Total return 56.41%, annual return 15.63%, excess return 52.96%
- **Frequency finding**: Monthly rebalancing > weekly > daily (less noise)
- **Architecture**: Standard transformer encoder with positional encoding for time series

#### Hybrid LSTM-Transformer
- **LAMFormer**: Multi-head Agent Attention + Mixture-of-Experts
- **Key innovation**: Reduced computational burden while extracting multi-scale temporal features
- **Best for**: Combining price prediction with sentiment analysis

### Category 2: Reinforcement Learning Trading

#### FinRL Framework (Recommended for Implementation)
**Best documented results**:
| Algorithm | Sharpe | Annual Return | Notes |
|---|---|---|---|
| DDPG | 2.21 | 36.01% | Best single agent |
| Ensemble (PPO+A2C+DDPG) | 1.8-2.5 | 25-40% | Switches between agents |
| Hi-DARTS | 0.75 | 25.17% | AAPL Jan 2024 - May 2025 |

**Implementation steps**:
1. Install: `pip install finrl`
2. Data: Download via Yahoo Finance API
3. Environment: Use StockTradingEnv with Dow 30 or custom universe
4. Train: 2+ years of data, validate on 6 months
5. Backtest: Walk-forward on unseen data
6. Key hyperparameters: learning_rate=3e-4, batch_size=128, buffer_size=1e6

### Category 3: Feature Engineering + Gradient Boosting

#### LightGBM / XGBoost for Alpha Generation
- **Features**: Technical indicators (SMA, EMA, RSI, MACD, Bollinger) + sentiment scores
- **Target**: Next-day return direction or magnitude
- **Approach**: Classification (up/down/flat) or regression
- **Key parameters**:
  - n_estimators: 500-2000
  - max_depth: 5-8
  - learning_rate: 0.01-0.05
  - Feature importance for alpha signal weighting

**Practical advantage**: Faster to train, more interpretable, less prone to overfitting than deep learning

### Category 4: NLP Sentiment-Based

- **Approach**: LLM-based sentiment scoring of financial news
- **Tools**: FinBERT, GPT-4 API for earnings call analysis
- **Integration**: Sentiment score as additional feature in multi-factor model
- **Edge**: Retail traders can now access what was institutional-only capability

---

## 5. Competition-Winning Strategies (WorldQuant, Kaggle)

### WorldQuant BRAIN / IQC

#### Competition Scale
- **2024 IQC**: 37,300 contestants, 111 countries, 5,388 universities, $400K prize pool
- **2025 IQC**: 80,000 participants, 11,000 universities, 142 countries, 263,000+ alphas submitted

#### Alpha Fitness Formula
```
Fitness = sqrt(abs(Returns) / max(Turnover, 0.125)) * Sharpe
```
**Optimization target**: High Sharpe, high returns, LOW turnover

#### Winning Strategy Patterns

1. **Price Reversion Dominates**: All top alphas incorporate price reversion
   - Example: `rank(-delta(close, 5))` -- simple 5-day price reversal
   - Neutralized by subindustry for better fitness

2. **Turnover Reduction Techniques**:
   - `ts_rank()` to smooth signals
   - `ts_decay_linear()` to slow signal changes
   - Lower turnover = higher fitness even if Sharpe dips slightly

3. **Neutralization Strategy**:
   - Market neutralization: Reduces Sharpe but greatly increases fitness
   - Subindustry neutralization: Best Sharpe
   - Best practice: Start with subindustry, test market neutral

4. **Alpha Design Principles**:
   - Keep it simple: Best alphas rarely exceed 5-6 factors
   - Avoid overfitting: Few parameters
   - Use high-frequency data (price/volume) for delay-0 alphas
   - Combine with news/sentiment/option data for diversification

#### 101 Formulaic Alphas (Kakushadze 2016)
- **Paper**: arxiv.org/abs/1601.00991
- **Content**: 101 real-world alpha formulas used in production
- **Example alphas**:
  - Alpha#1: `rank(ts_argmax(SignedPower(returns<0 ? stddev(returns,20) : close, 2.), 5)) - 0.5`
  - Alpha#6: `-1 * correlation(open, volume, 10)`
  - Alpha#12: `sign(delta(volume, 1)) * (-1 * delta(close, 1))`

### Kaggle Finance Competitions
- Focus on feature engineering with gradient boosting models
- Top approaches combine:
  - Lag features (1-day, 5-day, 20-day returns)
  - Volume features (relative volume, VWAP deviation)
  - Volatility features (realized vol, vol of vol)
  - Cross-asset correlations

---

## 6. Momentum + Mean Reversion Hybrid Strategies

### Strategy 1: Stochastic Momentum (Trend + Mean Reversion)

**Concept**: Use momentum for trend direction, mean reversion for entry timing

**Parameters**:
| Parameter | Value | Purpose |
|---|---|---|
| Stochastic %K period | 14 | Mean reversion oscillator |
| Stochastic %D period | 3 | Signal smoothing |
| %K smoothing | 3 | Noise reduction |
| Trend filter MA | 30-period SMA | Direction filter |
| ATR period | 14 | Volatility measurement |
| ATR multiplier | 1.0 | Stop-loss distance |
| Volatility lookback | 20 | Position sizing input |
| Max position | 95% | Upper limit |
| Min position | 30% | Lower limit |
| Oversold level | 20 | Buy signal threshold |
| Overbought level | 80 | Sell signal threshold |

**Rules**:
- LONG: Price above 30-SMA (momentum up) AND Stochastic crosses up from below 20 (mean reversion)
- SHORT: Price below 30-SMA (momentum down) AND Stochastic crosses down from above 80
- Stop-loss: 1.0 * ATR from entry
- Trailing stop: Adjusts with ATR

**Backtest**: Outperforms pure momentum and pure mean reversion in FX markets

### Strategy 2: Dual Timeframe Approach

**Parameters**:
- **Momentum (weekly)**: 12-week rate of change > 0 for trend direction
- **Mean reversion (daily)**: RSI(2) < 10 for oversold entry

**Rules**:
- Only buy when weekly momentum is positive
- Enter when RSI(2) drops below 10
- Exit when RSI(2) rises above 70
- Stop-loss: 5% below entry

**Historical performance**: Connors RSI(2) strategy has shown 60-70% win rates in backtests

### Strategy 3: Bollinger Band + RSI Combo

**Parameters**:
- Bollinger Bands: 20-period, 2.0 standard deviations
- RSI: 14-period
- Entry: Price at lower BB AND RSI < 30
- Exit: Price at middle BB OR RSI > 70

**Backtest (SPY, 2014-2024)**:
- Win rate: 58%
- Average winner: +5.2%
- Average loser: -2.8%
- Annual return: 11.4%
- Max drawdown: -18%

### Strategy 4: Factor Rotation (Momentum of Factors)

**Concept**: Apply momentum to factor returns, rotating between value, momentum, quality, low-vol

**Implementation**:
- Calculate 3-month and 12-month returns of each factor ETF
- Allocate to top 2 performing factors
- Rebalance monthly
- Skip 1 month (skip the most recent month to avoid reversal)

**2024 result**: Momentum was best-performing factor globally for 4th time in 20 years
**2025 warning**: Momentum ETFs have stalled significantly -- factor rotation helps avoid this crash

---

## 7. Statistical Arbitrage & Pairs Trading

### Implementation Framework

#### Step 1: Pair Selection
```
Method 1 - Distance:
  Normalize prices, calculate SSD (Sum of Squared Distances)
  Select pairs with minimum SSD

Method 2 - Cointegration:
  Engle-Granger test (simpler, for 2 assets)
  Johansen test (for multiple assets, more robust)
  p-value threshold: < 0.05

Method 3 - Correlation:
  Rolling 60-day correlation > 0.8
  Must ALSO pass cointegration test
```

#### Step 2: Spread Construction
```
Spread = log(Price_A) - hedge_ratio * log(Price_B)
Hedge ratio: OLS regression coefficient
Z-score = (Spread - Mean(Spread)) / StdDev(Spread)
```

#### Step 3: Trading Rules
| Signal | Z-score Threshold | Action |
|---|---|---|
| Entry Long Spread | Z < -2.0 | Buy A, Sell B |
| Entry Short Spread | Z > +2.0 | Sell A, Buy B |
| Exit | Z crosses 0 | Close both legs |
| Stop Loss | abs(Z) > 4.0 | Close both (relationship broken) |

#### Step 4: Risk Management
- Maximum 5-10 pairs simultaneously
- Equal dollar allocation per pair
- Correlation check: Ensure pairs are not correlated with each other
- Half-life check: Mean reversion half-life < 30 days preferred

### Specific Pairs for HK Market

**Sector-Based Pairs** (test with Johansen/Engle-Granger before trading):

| Sector | Pair 1 | Pair 2 | Rationale |
|---|---|---|---|
| Banking | 0005.HK (HSBC) | 0011.HK (Hang Seng Bank) | Parent-subsidiary |
| Tech | 9988.HK (Alibaba) | 9618.HK (JD.com) | E-commerce peers |
| Property | 0016.HK (SHK Props) | 0012.HK (Henderson Land) | HK property developers |
| Insurance | 2318.HK (Ping An) | 2628.HK (China Life) | Chinese insurers |
| Telecom | 0941.HK (China Mobile) | 0762.HK (China Unicom) | Chinese telcos |

### ETF Pairs (Lower Risk)
- 2800.HK (Tracker Fund) vs 2828.HK (HSI ETF) -- near-identical tracking
- 3188.HK (ChinaAMC CSI 300) vs 2846.HK (iShares CSI 300)

### 2024 Research Advances
- **Multivariate cointegration** (SSRN 4906546): Extends beyond 2-asset pairs to portfolio-level stat arb
- **Graph clustering** (arxiv 2406.10695): Use graph theory to find related asset clusters
- **Reinforcement learning for pairs** (arxiv 2403.12180): RL agent learns optimal entry/exit dynamically

---

## 8. Volatility-Based Strategies

### Strategy 1: Volatility Risk Premium Harvesting

**Concept**: Implied volatility consistently exceeds realized volatility by 2-4 percentage points

**Implementation**:
- Sell 30-delta SPX/SPY puts, 45 DTE
- Manage at 50% profit target
- Stop at 200% of premium received
- Position size: 2-5% of portfolio per trade

**Performance**: Sharpe 1.5-3.0 in backtests
**Risk**: Negative skew -- rare but large losses (e.g., March 2020)

### Strategy 2: VIX Mean Reversion

**Concept**: VIX tends to revert to its long-term mean (~18-20)

**Implementation**:
- When VIX > 30: Buy SPY (or sell VIX futures if available)
- When VIX < 12: Buy VIX calls as hedge / reduce equity exposure
- Use VIX futures term structure (contango vs backwardation) as confirmation

**Parameters**:
- Entry: VIX z-score > 2.0 above 60-day mean
- Exit: VIX returns to 60-day mean
- Position: 5-10% of portfolio

### Strategy 3: Gamma Scalping

**Concept**: Profit from difference between implied and realized volatility

**Implementation**:
- Buy ATM straddle
- Delta-hedge continuously as underlying moves
- Profit if realized vol > implied vol (you paid)
- Loss if realized vol < implied vol

**Best conditions**: After earnings, before major events
**Not recommended for**: Small accounts (high commission drag)

### Strategy 4: Calendar Spread on VIX Term Structure

**Concept**: Exploit VIX futures term structure normalization

**When contango is steep** (normal market):
- Sell front-month VIX futures
- Buy back-month VIX futures
- Profit as contango rolls down

**When backwardation** (fear market):
- Opposite trade -- sell back, buy front
- Profit as term structure normalizes

### Strategy 5: Variance Swap Replication (Advanced)
- Replicate variance swap payoff using strip of options
- Go long realized variance vs short implied variance
- Requires multiple option positions -- capital intensive

---

## 9. Strategies Claiming 100%+ Annual Returns

### Reality Check

Research consistently shows:

1. **Legitimate documented backtests** show 6-15% annual returns for most strategies
2. **Top hedge funds** (Renaissance Medallion): ~66% annual gross, ~39% net (exceptional)
3. **FinRL DDPG best case**: 36% annual with Sharpe 2.21
4. **Overfitting danger**: Testing 10,000 parameter combinations found one with 32% annual returns -- lost 24.5% in first 3 months live
5. **Random chance**: 8.4% of randomly generated strategies show "strong" performance metrics

### Claims Found (Use Extreme Caution)

| Claimed Strategy | Claimed Return | Source | Red Flags |
|---|---|---|---|
| "Bollinger + Order Flow" SPY options | 82% annualized | Chinese GitHub community | No live trading proof |
| ETH/USDT volatility | 243% annualized | GitHub backtest (2021-2023) | Crypto bull market bias, likely overfitted |
| FinRL DDPG Dow 30 | 36% annual | Academic paper | Paper trading only |
| Transformer strategy | 15.63% annual | arxiv paper | March 2020 start (bottom) |

### What "100% Returns" Actually Requires

- To achieve 100% annually, you need:
  - Very high leverage (5-10x), OR
  - Options strategies with convex payoff, OR
  - Concentrated bets in volatile assets (crypto)
- All of these dramatically increase risk of ruin
- **Kelly Criterion warning**: Even with 60% win rate and 2:1 reward/risk, optimal Kelly fraction is only ~20% -- not enough for 100% returns without leverage

### Honest Performance Expectations

| Strategy Type | Realistic Annual Return | Realistic Sharpe | Risk Level |
|---|---|---|---|
| Mean reversion (ETFs) | 8-15% | 0.8-1.2 | Low-Medium |
| Momentum (single factor) | 10-20% | 0.6-1.0 | Medium |
| Pairs trading | 8-15% | 1.0-1.5 | Low-Medium |
| ML/AI enhanced | 15-35% | 1.0-2.5 | Medium-High |
| Volatility premium | 10-25% | 1.0-3.0 | High (tail risk) |
| Leveraged hybrid | 20-50% | 0.8-1.5 | High |

---

## 10. Strategic Synthesis & Recommendations

### Second-Order Effects to Consider

1. **Strategy crowding**: As quant strategies become more accessible (VNPy, FinRL, QuantConnect), alpha decays faster. The "Bollinger + RSI" mean reversion strategy is so well-known that its edge has compressed significantly.

2. **Regime sensitivity**: Momentum dominated 2024 but collapsed in 2025. Any single-factor strategy will have multi-year drawdowns. The solution is factor rotation or regime detection.

3. **HK market structural advantage**: T+0 settlement gives HK an edge for intraday strategies that A-shares cannot replicate. The AH premium also provides a unique arbitrage opportunity.

4. **AI democratization**: FinRL, LightGBM, and LLM-based sentiment analysis are now accessible to retail. But the edge is shrinking as adoption increases. The window is 2-3 years before these become fully commoditized.

5. **Commission erosion**: For small accounts ($1K-$10K), commission costs can consume 30-50% of strategy alpha. Prefer low-turnover strategies (monthly rebalancing) or commission-free platforms.

### Recommended Strategy Stack for Retail HK Trader

#### Tier 1: Core (60% of capital)
- **Multi-factor HK stock selection**: Value + Momentum + Quality
- Monthly rebalancing, top 10-20 from HSI constituent universe
- Expected: 8-12% alpha over HSI, Sharpe ~1.0

#### Tier 2: Tactical (25% of capital)
- **Pairs trading on HK stocks**: 3-5 cointegrated pairs from banking/property/tech sectors
- Z-score entry at 2.0, exit at 0, stop at 4.0
- Expected: 10-15% annual, Sharpe ~1.2

#### Tier 3: Alpha Capture (15% of capital)
- **ML-enhanced signals**: LightGBM on technical + sentiment features
- Or FinRL RL agent for dynamic position management
- Expected: 15-30% annual if well-implemented, but higher variance

### Implementation Roadmap

1. **Week 1-2**: Set up backtesting environment (QuantConnect or Backtrader)
2. **Week 3-4**: Implement and backtest mean reversion (Bollinger + RSI) on HK ETFs
3. **Month 2**: Add pairs trading module, test cointegration on HSI constituents
4. **Month 3**: Implement LightGBM feature engineering pipeline
5. **Month 4**: Paper trade all strategies simultaneously
6. **Month 5-6**: Live trade with minimal capital, track slippage and real-world performance
7. **Ongoing**: Walk-forward optimization, regime detection, factor rotation

---

## Sources

### English Sources
- [Top Quant Trading Firms 2026 - QuantVPS](https://www.quantvps.com/blog/top-quant-trading-firms)
- [FinRL: Deep Reinforcement Learning Framework](https://arxiv.org/abs/2011.09607)
- [Quantformer: From Attention to Profit](https://arxiv.org/abs/2404.00424)
- [101 Formulaic Alphas - Kakushadze](https://arxiv.org/abs/1601.00991)
- [Pairs Trading on HK Stock Market](https://ideas.repec.org/p/war/wpaper/2022-02.html)
- [WorldQuant IQC 2024 Winners](https://www.businesswire.com/news/home/20240923051396/en/The-Winners-of-the-2024-International-Quant-Championship)
- [WorldQuant IQC 2025 Winners](https://www.businesswire.com/news/home/20251005939788/en/WorldQuant-Announces-the-Winners-of-the-2025-International-Quant-Championship)
- [Multivariate Cointegration in Statistical Arbitrage](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4906546)
- [Statistical Arbitrage with Graph Clustering](https://arxiv.org/abs/2406.10695)
- [Advanced Statistical Arbitrage with RL](https://arxiv.org/abs/2403.12180)
- [Momentum Factor 2024 - SSGA](https://www.ssga.com/us/en/intermediary/insights/what-drove-momentums-strong-2024-and-what-it-could-mean-for-2025)
- [WorldQuant BRAIN Alpha Documentation](https://github.com/jglazar/notes/blob/main/quant_interview/alpha_ideas.md)
- [7 Advanced Volatility Trading Strategies 2025](https://chartswatcher.com/pages/blog/7-advanced-volatility-trading-strategies-for-2025)
- [awesome-systematic-trading GitHub](https://github.com/paperswithbacktest/awesome-systematic-trading)
- [FinRL GitHub](https://github.com/AI4Finance-Foundation/FinRL)
- [awesome-quant GitHub](https://github.com/wilsonfreitas/awesome-quant)
- [Combining Mean Reversion and Momentum in FX - QuantConnect](https://www.quantconnect.com/research/15255/combining-mean-reversion-and-momentum-in-forex-market/)
- [Mean Reversion Strategies - QuantifiedStrategies](https://www.quantifiedstrategies.com/mean-reversion-trading-strategy/)
- [Stochastic Momentum Hybrid Strategy](https://pyquantlab.com/article.php?file=Stochastic+Momentum+Strategy+A+Trend-Following+and+Mean-Reversion+Hybrid.html)
- [Position Sizing - QuantInsti](https://blog.quantinsti.com/position-sizing/)
- [Deep Learning for Algorithmic Trading Review](https://www.sciencedirect.com/science/article/pii/S2590005625000177)
- [8 Proven Trading Strategies of HK Traders 2025](https://ngcbgroup.com/blogdetails/8-proven-trading-strategies-of-hong-kongs-top-traders-2025)

### Chinese Sources
- [港股量化：2024年全年组合超额5.5%](https://finance.sina.com.cn/roll/2025-01-06/doc-inecznxx2473589.shtml)
- [量化交易全面入门指南 2025 - CSDN](https://blog.csdn.net/drdairen/article/details/146101780)
- [散户如何进行量化交易 - 知乎](https://www.zhihu.com/question/653589264)
- [量化交易入门、AI选股策略 - HTSC](https://zlglobal.htsc.com.hk/zl/zh-hans/course/detail-what-is-algorithmic-trading.html)
- [VNPy开源量化框架](https://github.com/vnpy/vnpy)
- [Qbot AI量化交易机器人](https://github.com/UFund-Me/Qbot)
- [量化研究券商研报复现](https://github.com/hugo2046/QuantsPlaybook)
- [日内回转交易策略 - 掘金量化](https://www.myquant.cn/docs/python_strategyies/108)
- [T0算法交易 - 财联社](https://www.cls.cn/detail/1951037)
- [量化工具下沉到散户 - 界面新闻](https://m.jiemian.com/article/12835024.html)
- [2025投资方向 - 富途](https://www.futuhk.com/en/blog/detail-2025-invest-strategy-102-241252010)
