# Statistical Arbitrage & Pairs Trading: 2024-2025 Comprehensive Analysis

## Multi-Perspective Research Report
**Analyst:** Alex Rivera | **Date:** March 13, 2026
**Scope:** Six strategy types, three markets, ML evolution

---

## 1. COINTEGRATION-BASED PAIRS TRADING

### Performance Data (2024-2025)

**Chinese Equity Market (2005-2024 backtest):**
- Distance Method (DM): Pre-cost monthly excess returns of 84 bps, post-cost 81 bps
- Mispricing Index (MPI) Copula: 30 bps pre-cost, 23 bps post-cost
- Mixed Copula: 25 bps pre-cost, 15 bps post-cost
- Mixed copula annualized value-weighted excess return: 3.68% (top 5 pairs)
- Distance Method annualized excess return: 2.30%
- **Sharpe Ratios:** Mixed copula 0.58, Distance Method 0.28

**ETF Pairs Trading (2000-2024):**
- Intraday dynamic pairs trading using correlation + cointegration: up to **26.9% annual return** with **Sharpe ratio of 3.01**
- Lower z-score thresholds increase trading opportunities and Sharpe ratios but raise volatility and drawdowns
- Short cointegration windows limit long-term profitability

**Hong Kong Stock Market:**
- Cointegration method is superior to correlation method and distance method
- Slightly better Sharpe Ratio than distance method, though distance method shows slightly higher monthly returns

**Key Insight:** Cointegration-based approaches remain viable but are highly sensitive to parameter selection. The convergence rate filter mechanism (2024 research) significantly improves results by removing pairs unlikely to be profitable.

---

## 2. MEAN REVERSION STRATEGIES

### Performance Results

**Equity Markets:**
- Pairs trading with correlation coefficient > 0.8: **68% success rate**
- Bollinger Bands mean reversion on forex: **2.3% per trade average return**, 71% win rate in ranging conditions
- Optimal entry when price deviations exceed **2.5 standard deviations** from mean
- Volume filter: trading volume within 1.5x the 20-day average

**Stat Arb Fund Composite (YTD through April 2025):**
- Return: **7.79%** YTD
- Win rates: typically 55-65% with positive skew
- Beta neutrality maintained within +/-0.10
- Maximum drawdown caps: 10-15% range

**Regime Sensitivity:**
- Performs optimally in sideways/range-bound markets
- Market regime changes pose critical threat -- traditional signals become unreliable during trend transitions
- 2025 tariff turmoil caused significant drawdowns for some quant funds (Renaissance RIEF dropped to 4.4% YTD after being up 22.7% in 2024)

---

## 3. CROSS-ASSET ARBITRAGE

### Performance (2024-2025)

**Convertible Arbitrage (standout performer):**
- 2022: Slight losses
- 2023: Mid-high single digit gains
- 2024: **Firmly double-digit annualized returns**
- Through May 2025: +4.0% (vs. +2.6% broader hedge fund average)

**Commodity-Equity Correlations:**
- 5-year US stock-bond correlation (2020-2024): +0.62 (undermining traditional hedging)
- Only China offers **negative stock-bond correlation** -- unique diversification opportunity
- Equal Weight Commodities Index: +14% in 2025, led by precious metals and copper

**Cross-Market Deep Learning Arbitrage:**
- Emerging research on cross-market statistical arbitrage using deep learning
- Multi-asset optimal execution strategies combining equities and derivatives

**Key Insight:** The positive stock-bond correlation in the US (breaking the traditional negative correlation) has created new cross-asset arbitrage opportunities, particularly for strategies that can exploit the breakdown of historical relationships.

---

## 4. ETF ARBITRAGE

### Performance and Mechanics

**S&P 500 ETF vs. Underlying:**
- ETF spreads cheaper than underlying stock portfolios (1 bp vs. 4+ bps for stocks)
- Arbitrage often affects ETF market before stock market
- Creation/redemption mechanism provides structural arbitrage opportunities

**ETF Pairs Trading (30 ETF pairs study, 2000-2024):**
- Multiple z-score threshold analysis shows inverse relationship between threshold strictness and trade frequency
- Lower thresholds: more trades, higher aggregate profits, higher Sharpe ratios, but increased volatility and drawdowns
- Short cointegration windows remain the primary profitability constraint

**Cryptocurrency Pairs Trading (2021-2024):**
- Average annual Sharpe ratio per pair: **1.53**
- Median max drawdown: 29% (high risk)
- Cointegrated crypto pairs consistently outperform conventional pairs trading and passive approaches

---

## 5. INDEX ARBITRAGE

### 2024-2025 Basis Trade Data

**S&P 500 Futures-Cash Spread (Major Finding):**
- Financing spread peaked at **over 1.4%** in December 2024 (vs. 0.3% average 2021-2023)
- Remained elevated through 2025
- Represents a 4.7x increase over the prior three-year average
- **Root cause:** Balance sheet constraints -- abnormally large demand for financing capacity exceeding constrained supply

**Arbitrage Mechanics:**
- S&P 500 futures spreads: ~1 basis point
- Underlying stock portfolio spreads: >4 basis points
- The elevated basis represents payment for scarce balance sheet capacity, not pure mispricing
- Selling futures + buying cash equities = supplying balance sheet to leveraged participants

**Opportunity Assessment:**
- The elevated S&P 500 financing spread creates a structural opportunity for well-capitalized participants
- However, this is increasingly understood as compensation for balance sheet provision rather than free alpha
- D.E. Shaw published detailed analysis on this phenomenon

---

## 6. MERGER ARBITRAGE

### ETF Performance Data

| Fund/Index | 2024 Return | 2025 Return |
|---|---|---|
| NYLI Merger Arbitrage ETF (MNA) | 4.96% | 8.60% |
| Barclay Merger Arbitrage Index | 4.45% | 7.37% |
| AltShares Merger Arbitrage ETF (ARB) | -- | 0.63% (YTD Feb 2026) |

**Characteristics:**
- Market neutral characteristics with lower volatility than S&P 500
- Low correlation to equity market returns
- Returns are generally lower than equity markets in bull periods
- M&A deal flow remains resilient entering 2026 despite higher regulatory scrutiny
- Attractive spreads driven by regulatory and execution uncertainty

---

## 7. SHARPE RATIO COMPILATION ACROSS STRATEGIES

| Strategy | Typical Sharpe | Best-Case Sharpe | Notes |
|---|---|---|---|
| Traditional Pairs (Distance Method) | 0.28 | 0.58 | Chinese equities backtest |
| Cointegration Pairs (ETFs) | 1.0-1.5 | 3.01 | Intraday dynamic approach |
| Mean Reversion (Stat Arb Funds) | 1.0-1.5 | 2.0+ | Mature sleeves target 1.5+ |
| Deep Learning Stat Arb | 2.0-3.0 | 4.0+ | Convolutional transformer approach |
| Reinforcement Learning (Crypto) | 1.5-2.5 | 2.43 | DQN agent on crypto |
| Merger Arbitrage | 0.5-1.0 | 1.2 | Low vol, low correlation |
| Convertible Arbitrage | 1.0-2.0 | 2.5+ | Strong 2023-2025 cycle |
| Quant Multi-Strategy | 1.2-1.8 | 2.0+ | 5-year Sharpe of 1.4 |
| Crypto Pairs Trading | 1.0-1.5 | 1.53 | High drawdown risk |
| Index Basis Trade | 0.8-1.5 | 2.0+ | Balance sheet dependent |

**Industry Threshold:** Most quantitative hedge funds ignore strategies with annualized Sharpe < 2.0.

---

## 8. ML/DEEP LEARNING EVOLUTION IN STAT ARB

### The Paradigm Shift (2024-2025)

**From Linear to Nonlinear:**
- Traditional: Cointegration, Ornstein-Uhlenbeck, distance methods
- Modern: Deep neural networks capturing nonlinear dependencies and complex dynamics
- 2025: Convolutional transformers + optimal trading policy formulation

**Deep Learning Statistical Arbitrage (Guijarro-Ordonez, Pelger, Zanotti - Management Science 2025):**
- Architecture: Convolutional transformer for time-series signal extraction
- Results: **Annual Sharpe ratios > 4.0**, annual OOS mean returns of 20%
- Respects short-selling constraints
- Outperforms ALL benchmark approaches in out-of-sample testing
- Can process large numbers of securities simultaneously without requiring pre-identified cointegrated pairs

**CNN-LSTM Hybrid (Quantitative Finance 2023-2024):**
- Combines convolutional neural networks with long short-term memory
- Classifies profitable vs. unprofitable spread sequences
- Large-scale market backtest (1991-2017) shows significant improvement over traditional methods

**Deep Reinforcement Learning:**
- DQN agent on crypto stat arb: 18.39% return, 12.22% volatility, **Sharpe 2.43**
- Agents autonomously learn optimal trading policies through market interaction
- Walk-forward validation with OOS Sharpe > 1.0 as deployment threshold

**AI Agent Integration (2025 frontier):**
- ML algorithms identify correlations, trends, and anomalies traditional methods miss
- Continuous model refinement through learning from historical data
- Adaptation to evolving market conditions
- NLP integration for sentiment-driven signals
- Cross-market variable processing for global inefficiency discovery

**Key Insight from Multiple Perspectives:**
- **Optimistic view:** DL stat arb with Sharpe > 4.0 represents a quantum leap in alpha generation
- **Skeptical view:** These are backtest results; live trading with slippage, market impact, and regime changes will compress Sharpe significantly
- **Practical view:** The biggest quant funds (D.E. Shaw, Renaissance, Two Sigma) are deploying these methods but their aggregate fund Sharpe ratios remain 1.0-2.0, suggesting strategy-level Sharpe is diluted at portfolio level

---

## 9. MARKET-SPECIFIC OPPORTUNITIES

### United States

**Strengths:**
- Deepest, most liquid equity market globally
- Quant multi-strategy returned +17.4% in 2024 (ranked #1 of 37 sub-strategies)
- S&P 500 basis trade offers structural 1.0-1.4% financing spread
- Convertible arbitrage in a strong cycle

**Weaknesses:**
- Most crowded stat arb market -- alpha decay is fastest
- Tariff turmoil in 2025 caused regime breaks (Renaissance RIEF -8% in one month)
- Balance sheet constraints limiting pure index arb

**Top Performers (2024):**
- D.E. Shaw Oculus: 36.1%
- Renaissance Medallion: ~30%
- Renaissance RIEF: 22.7%
- D.E. Shaw Composite: 18%
- AQR Multi-Strategy: 19.6% (2025)

**Top Performers (2025):**
- AQR: 19.6%
- D.E. Shaw Composite: 18.5%
- Millennium: 10.5%
- Citadel: 10.2%

### Hong Kong

**Strengths:**
- AH premium collapse creates compelling arbitrage opportunities
- AH Premium Index dropped to 122.81 (July 2025), down 15% from 2024 peak
- Southbound flows now 36.3% of daily HK trading volume
- H1 2025 southbound flows ~US$100 billion (nearly equal to all of 2024)
- Cointegration method proven superior in HK stock market

**Specific AH Arbitrage Opportunities:**
- CATL trading at 31% discount to A-share equivalent
- Hengrui Pharmaceuticals at 15% discount
- Sectors with A-share discounts to H-shares: financials, real estate, consumer staples
- Fast-track listing (30 business days) since October 2024 increases dual-listing pipeline

**Weaknesses:**
- Regulatory risk from both CSRC and HKEX
- Currency risk (HKD/CNY)
- Capital flow restrictions for onshore investors

### China A-Shares

**Strengths:**
- Only major market with negative stock-bond correlation (unique diversification)
- Short-selling mechanism available since March 2010 (margin trading)
- A-share IPO momentum: 100+ IPOs in 2025, >RMB110 billion proceeds
- High-frequency stat arb in Chinese futures market showing promising results

**Copula-Based Pairs Trading (Chinese Equities 2005-2024):**
- Distance method: 84 bps monthly excess return (pre-cost)
- Mixed copula Sharpe: 0.58
- Time-varying transaction costs significantly impact results

**Weaknesses:**
- Pairs trading research started relatively late in China
- Short-selling constraints more restrictive than US/HK
- Regulatory intervention risk (CSRC tightened A-share IPOs from 300-500/year to just 54 in 2025)
- Lower market microstructure efficiency

**Opportunity Ranking (Best to Weakest for Stat Arb):**
1. **US** -- deepest liquidity, most strategies viable, fastest alpha decay
2. **Hong Kong** -- AH premium arbitrage is the standout opportunity of 2024-2025
3. **China A-shares** -- growing but constrained by short-selling limitations and regulatory risk

---

## 10. STRESS-TESTED CONCLUSIONS

These conclusions hold up when examined from multiple angles:

1. **Deep learning stat arb has achieved a genuine performance breakthrough.** Sharpe ratios > 4.0 in academic backtests (convolutional transformers). Even discounting for live trading friction, this represents a meaningful advance over traditional cointegration methods (Sharpe 0.3-0.6). However, the gap between backtest and live performance remains the critical unknown.

2. **AH premium arbitrage is the single most compelling geographic opportunity.** The 15% decline in AH Premium Index, combined with US$100 billion in southbound flows, massive dual-listing pipeline, and specific stocks trading at 15-31% discounts, creates a rare structural opportunity. Multiple perspectives (regulatory, capital flow, valuation) all point the same direction.

3. **Convertible arbitrage is in a strong cyclical upswing.** From losses in 2022 to double-digit returns in 2024, this is a strategy where timing matters and 2024-2025 has been favorable.

4. **Mean reversion and traditional pairs trading remain viable but are not where the frontier is.** Sharpe ratios of 0.3-0.6 for traditional methods vs. 2.0-4.0+ for ML-enhanced approaches tells a clear story. The evolution is real.

5. **The S&P 500 basis trade is structural, not alpha.** The 1.0-1.4% financing spread reflects balance sheet provision, not mispricing. Well-capitalized participants earn a risk premium, not alpha.

6. **Merger arbitrage is a diversification tool, not a return driver.** 5-9% annual returns with low correlation and low volatility position it as portfolio insurance, not core alpha.

7. **China A-shares have potential but structural constraints (short-selling, regulation) limit practical stat arb implementation.** The negative stock-bond correlation is unique and valuable for cross-asset strategies.

8. **Industry standard: Sharpe < 2.0 is increasingly ignored by institutional quant allocators.** The bar has risen significantly, driven by ML capabilities and competition.

---

## Sources

- [Examining Pairs Trading Profitability - Yale (Zhu, 2024)](https://economics.yale.edu/sites/default/files/2024-05/Zhu_Pairs_Trading.pdf)
- [Performance of Pairs Trading Based on Copula Methods](https://www.mdpi.com/1911-8074/18/9/506)
- [Cointegration-based Pairs Trading: ETFs (Springer 2025)](https://link.springer.com/article/10.1057/s41260-025-00416-0)
- [Deep Learning Statistical Arbitrage (Management Science 2025)](https://pubsonline.informs.org/doi/10.1287/mnsc.2022.03132)
- [Survey of Stat Arb with ML/DL/RL Methods (2025)](https://ideas.repec.org/p/war/wpaper/2025-22.html)
- [Advanced Statistical Arbitrage with Reinforcement Learning](https://arxiv.org/html/2403.12180v1)
- [Statistical Arbitrage with Deep RL: Sharpe Ratio Paradox](https://medium.com/@navnoorbawa/statistical-arbitrage-with-deep-rl-solving-the-sharpe-ratio-paradox-68ab53c93f51)
- [CNN-LSTM Hybrid for Statistical Arbitrage (Quantitative Finance)](https://www.tandfonline.com/doi/full/10.1080/14697688.2023.2181707)
- [36% Returns: D.E. Shaw Beat Citadel & Millennium 2024](https://navnoorbawa.substack.com/p/36-returns-how-de-shaw-beat-citadel)
- [Top Hedge Fund Performers 2025 (Fortune)](https://fortune.com/2026/01/02/top-hedge-fund-performers-2025-bridgewater-de-shaw-citadel-millennium/)
- [Renaissance Quant Funds Losses Amid Tariff Turmoil (Hedgeweek)](https://www.hedgeweek.com/renaissance-quant-funds-see-steep-losses-amid-tariff-turmoil/)
- [Renaissance Tech and Two Sigma Lead 2024 Quant Gains (Hedgeweek)](https://www.hedgeweek.com/renaissance-tech-and-two-sigma-lead-2024-quant-gains/)
- [Stat Arb: Record Inflows](https://navnoorbawa.substack.com/p/statistical-arbitrage-the-quant-strategy)
- [Millennium Multi-Strategy Architecture](https://navnoorbawa.substack.com/p/millennium-managements-multi-strategy)
- [NYLI Merger Arbitrage ETF (MNA)](https://www.nylim.com/etf/nyli-merger-arbitrage-etf-mna)
- [AltShares Merger Arbitrage ETF (ARB)](https://www.altsharesetfs.com/arb)
- [AH Premium Index (Hang Seng)](https://www.hsi.com.hk/eng/indexes/all-indexes/ahpremium)
- [HK IPO Revival and Dual Listings (CKGSB)](https://english.ckgsb.edu.cn/knowledge/article/hong-kong-ipo-revival-and-dual-listings/)
- [Hong Kong's IPO Market Surge (CNBC)](https://www.cnbc.com/2025/07/03/hong-kong-hkse-hang-seng-nasdaq-nyse-wall-street-ipo-market-listings-2025.html)
- [High-Frequency Stat Arb in Chinese Futures (Elsevier)](https://www.sciencedirect.com/science/article/pii/S2444569X23001257)
- [S&P 500 Imbalance Sheet: Financing Spread (D.E. Shaw)](https://www.deshaw.com/library/imbalance-sheet)
- [Convertible Arbitrage 2023-2025 Comeback (Resonanz Capital)](https://resonanzcapital.com/insights/convertible-arbitrage-the-2023-2025-comeback)
- [Aurum Hedge Fund Industry Deep Dive 2024](https://www.aurum.com/wp-content/uploads/Aurum-Industry-Deep-Dive-2024-review.pdf)
- [AI Agents & Statistical Arbitrage (Tabor 2025)](https://www.francescatabor.com/articles/2025/3/15/ai-agents-amp-statistical-arbitrage-leveraging-mathematical-models-to-identify-pricing-inefficiencies)
- [Improving Cointegration Pairs Trading (Computational Economics 2024)](https://link.springer.com/article/10.1007/s10614-023-10539-4)
