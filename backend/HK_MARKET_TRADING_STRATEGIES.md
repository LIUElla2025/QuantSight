# Hong Kong Stock Market Trading Strategies: Comprehensive Research

**Date:** 2026-03-14
**Scope:** Market microstructure, Stock Connect flows, warrants/CBBCs, session timing, sector rotation, AH premium arbitrage

---

## 1. HK Market Microstructure Characteristics

### 1.1 Board Lot Sizes

Hong Kong stocks trade in board lots that vary by company. Currently 44 different board lot sizes exist on HKEX, ranging from 1 share to 100,000 shares. This is a departure from global norms (US uses 1 share; China A-shares use 100 shares).

**Current State (2025-2026):**
- Most blue chips: 100-500 shares per lot
- Examples: Tencent (00700) = 100 shares/lot; HSBC (00005) = 400 shares/lot
- Small caps can have lots of 1,000 to 10,000 shares
- Entry cost varies enormously: Tencent at HK$400/share = HK$40,000 minimum; some penny stocks at HK$0.10 with 10,000 lot = HK$1,000 minimum

**Proposed Reform (HKEX Dec 2025 Consultation):**
- Reduce from 44 board lot options to 8 standardized options: 1, 50, 100, 500, 1,000, 2,000, 5,000, 10,000
- Goal: improve hedging precision, reduce operational complexity, align with global standards
- Impact on trading: smaller lots improve accessibility and allow finer position sizing

**Trading Strategy Implications:**
- Odd lot trading (less than one board lot) is possible but at wider spreads and lower liquidity
- Position sizing must account for lot size constraints -- cannot buy arbitrary share counts
- For algorithmic trading: lot size must be a parameter in order sizing logic
- Smaller lot reforms will improve granularity for portfolio rebalancing

### 1.2 Tick Size (Minimum Spread) Table

HKEX uses a variable tick size system based on price bands. This directly affects bid-ask spreads and transaction costs.

**Current Tick Size Table (Pre-Phase 1):**

| Price Band (HKD)    | Tick Size (HKD) | Tick-to-Price Ratio |
|---------------------|-----------------|---------------------|
| 0.01 - 0.25         | 0.001           | 0.4% - 10%          |
| 0.25 - 0.50         | 0.005           | 1.0% - 2.0%         |
| 0.50 - 10.00        | 0.010           | 0.1% - 2.0%         |
| 10.00 - 20.00       | 0.020           | 0.1% - 0.2%         |
| 20.00 - 100.00      | 0.050           | 0.05% - 0.25%       |
| 100.00 - 200.00     | 0.100           | 0.05% - 0.1%        |
| 200.00 - 500.00     | 0.200           | 0.04% - 0.1%        |
| 500.00 - 1000.00    | 0.500           | 0.05% - 0.1%        |
| 1000.00 - 2000.00   | 1.000           | 0.05% - 0.1%        |
| 2000.00 - 5000.00   | 2.000           | 0.04% - 0.1%        |
| 5000.00 - 9995.00   | 5.000           | 0.05% - 0.1%        |

**Phase 1 Reduction (Mid-2025 Launch):**
- HKD 10-20 band: tick reduced from 0.020 to 0.010 (50% reduction)
- HKD 20-50 band: tick reduced from 0.050 to 0.020 (60% reduction)
- Target: 4-10 bps tick-to-price ratio for these bands

**Phase 2 (Planned Mid-2026):**
- HKD 0.50-10 band: tick reduced by 50% (from 0.010 to 0.005)
- Subject to assessment of Phase 1 results

**Trading Strategy Implications:**
- Tighter tick sizes = narrower spreads = lower trading costs for mid-priced stocks
- Market-making strategies become more competitive with smaller tick sizes
- Scalping strategies require recalibration of profit targets after tick size changes
- For stocks priced HKD 10-50 (many Hang Seng constituents), the Phase 1 reduction materially improves execution quality

### 1.3 Trading Hours and Volatility Impact

**Session Structure:**

| Session                    | Time (HKT)     | Duration |
|---------------------------|-----------------|----------|
| Pre-opening Session       | 09:00 - 09:30   | 30 min   |
| Morning Continuous        | 09:30 - 12:00   | 2.5 hrs  |
| Lunch Break (Extended)    | 12:00 - 13:00   | 1 hr     |
| Afternoon Continuous      | 13:00 - 16:00   | 3 hrs    |
| Closing Auction Session   | 16:00 - 16:10   | 10 min   |

Total continuous trading: 5.5 hours (vs US 6.5 hours, A-shares 4 hours)

**Volatility Pattern -- Double U-Shape:**

Academic research confirms a distinct double U-shaped intraday volatility pattern unique to HK due to the lunch break:

1. **Morning spike (09:30-10:00):** Highest volatility -- overnight information from US/Europe gets priced in. ~15% of daily volume in first 30 minutes.
2. **Morning decay (10:00-11:30):** Volatility decreases as morning information is absorbed.
3. **Pre-lunch spike (11:30-12:00):** Moderate increase as traders position before lunch break.
4. **Post-lunch spike (13:00-13:30):** Second volatility spike as A-share midday activity and lunch-break news get priced in.
5. **Afternoon decay (13:30-15:30):** Gradual decline.
6. **Closing surge (15:30-16:10):** ~18% of daily volume in last 30 minutes. MOC (market-on-close) orders create price pressure.

---

## 2. Northbound/Southbound Stock Connect Flow Signals

### 2.1 Southbound Flow (Mainland to HK) as Trading Signal

**Academic Evidence:**
- Southbound investors' net purchases positively predict returns of connected Hong Kong stocks (ScienceDirect, 2023)
- Daily net buying amount shows significant predictive power for stock returns at daily frequency
- Weekly frequency prediction is NOT significant -- signal is short-term
- Positive relationship between lagged southbound flow volume and HK stock volatility

**Signal Construction:**

```
Flow Momentum Signal:
  EMA_short = EMA(daily_net_flow, 5)     # 1-week
  EMA_long  = EMA(daily_net_flow, 20)    # 1-month
  flow_momentum = EMA_short / EMA_long - 1

Flow Acceleration Signal:
  flow_accel = EMA_short[t] - EMA_short[t-1]
  accel_norm = flow_accel / 50  # normalized by HKD 5B baseline

Combined Signal:
  signal = 0.7 * clip(flow_momentum / 0.5, -1, 1) +
           0.3 * clip(accel_norm, -1, 1)
```

**Key Parameters (2024-2025 Calibration):**
- Short window: 5 days (one trading week)
- Long window: 20 days (one trading month)
- Strong signal threshold: net buy > HKD 5 billion/day
- Very strong signal: 3+ consecutive days of accelerating net buy
- Signal holding period: 1-5 days (daily frequency alpha)

**Concentration Factor:**
When southbound capital concentrates on a single stock (>5% of total daily southbound flow), it often signals institutional conviction. This is especially powerful for mid-cap stocks (market cap rank 20-100).

### 2.2 Northbound Flow (HK to Mainland) as Contrasting Signal

- Northbound capital is primarily institutional with international investment experience
- Negative relationship between lagged northbound flow and A-share volatility (stabilizing effect)
- Northbound flows are less useful as HK stock signals but serve as macro sentiment indicators
- Large northbound outflows can signal risk-off sentiment that spills into HK market

### 2.3 Data Sources and Access

| Source | Data | Latency | Cost |
|--------|------|---------|------|
| HKEX Official Stats | Daily aggregate flows | T+1 | Free |
| HKEX Historical Daily | Complete daily history | Historical | Free |
| MacroMicro | Southbound flow vs HSI chart | Daily | Free tier |
| CEIC Data | Granular daily flow data | T+0 EOD | Paid |
| Wind/Bloomberg Terminal | Real-time intraday flow | Real-time | Expensive |
| Tiger/Futu API | Some flow data via API | Near real-time | Broker account |

**HKEX Official URL:** https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/Historical-Daily

**Implementation Note:** Your existing `factor_southbound_flow()` in `hk_alpha_factors.py` already implements the EMA-based flow momentum signal. The concentration factor (`factor_southbound_concentration()`) adds stock-level granularity.

---

## 3. Hong Kong Warrant and CBBC Strategies

### 3.1 Warrants (Structured Warrants / Derivative Warrants)

**What They Are:**
Structured warrants are exchange-listed options issued by investment banks (not the underlying company). They give the holder the right (not obligation) to buy (call) or sell (put) the underlying at a set price before expiry.

**Key Greeks for Selection:**

| Greek | What It Measures | Optimal Range for Trading |
|-------|-----------------|--------------------------|
| Delta | Price sensitivity to underlying | 0.4-0.7 (avoid deep OTM <0.2) |
| Gamma | Rate of delta change | Higher = more responsive, but more volatile |
| Theta | Time decay per day | Minimize by choosing >3 months to expiry |
| Vega | Sensitivity to implied volatility | Be aware -- IV can crush warrant value even if underlying moves right |
| Rho | Interest rate sensitivity | Negligible for short-dated warrants |

**Warrant Selection Criteria:**

1. **Effective Gearing:** 3x-10x is the sweet spot. Below 3x -- insufficient leverage to justify the time decay cost. Above 10x -- too sensitive to small adverse moves.
   - Effective Gearing = Delta x Underlying Price / Warrant Price x Conversion Ratio

2. **Time to Expiry:** Minimum 3 months, ideally 6+ months. Short-dated warrants suffer extreme theta decay. Even correct directional views get destroyed by time erosion in sideways markets.

3. **Implied Volatility (IV):** Compare to VHSI (Hang Seng Volatility Index).
   - IV < VHSI: warrant is relatively cheap -- favorable entry
   - IV > VHSI significantly: warrant is expensive -- avoid or look for alternatives
   - Track IV percentile over 30-day history

4. **Moneyness:** Prefer slightly in-the-money (ITM) or at-the-money (ATM) warrants.
   - OTM warrants are cheaper but have lower probability of profit and higher theta decay
   - Deep ITM warrants have low gearing, defeating the purpose

5. **Issuer Spread:** Check the bid-ask spread. Major issuers (HSBC, UBS, Macquarie, SG) typically provide tighter spreads. Wide spreads kill profitability for short-term trades.

**Warrant Trading Strategies:**

Strategy A -- Directional Play:
- Conviction on underlying direction (use southbound flow signal or technical analysis)
- Select call warrant with delta 0.5-0.7, effective gearing 5-8x, expiry 4-6 months
- Stop loss: 30% of warrant value (equates to ~4-6% underlying move against you)
- Take profit: 50-100% warrant gain (equates to ~6-12% underlying move in your favor)
- Risk: time decay of ~0.3-0.5% of warrant value per day for ATM warrants

Strategy B -- Event Play:
- Before earnings, policy announcements, or index rebalancing events
- Select warrant with higher gamma (more responsive to sudden moves)
- Enter 3-5 days before event, exit within 1-2 days after
- Warning: IV typically rises before events (expensive entry) and crashes after (IV crush)

Strategy C -- VHSI Mean-Reversion:
- When VHSI spikes above 30 (panic), buy HSI call warrants
- When VHSI drops below 16 (complacency), buy HSI put warrants as hedges
- This is the warrant equivalent of your existing `factor_vhsi_mean_reversion()` signal

### 3.2 CBBCs (Callable Bull/Bear Contracts)

**What They Are:**
CBBCs are leveraged instruments that track the underlying asset's price movement almost linearly. Unlike warrants, CBBCs have minimal time value decay and are less affected by implied volatility. However, they have a mandatory call (knock-out) feature.

**Key Mechanics:**

| Feature | Bull Contract | Bear Contract |
|---------|--------------|---------------|
| Profits when | Underlying rises | Underlying falls |
| Strike Price | Below current price | Above current price |
| Call Price | Between strike and current | Between current and strike |
| Intrinsic Value | (Underlying - Strike) / Ratio | (Strike - Underlying) / Ratio |

**Category N vs Category R:**
- **Category N:** Call price = Strike price. If knocked out, investor gets ZERO residual value. Higher gearing but total loss risk.
- **Category R:** Call price differs from strike price. If knocked out, investor MAY receive residual value based on settlement during the Mandatory Call Event Valuation Period. Still possible to receive zero.

**CBBC Selection -- 3-Step Process:**

1. **Choose Direction:** Bull (long) or Bear (short) based on your signal
2. **Choose Call Price Distance:** How far the call price is from current underlying price
   - Close call price (2-5%): Higher gearing (10-30x), higher knock-out risk
   - Medium call price (5-10%): Moderate gearing (5-10x), balanced risk
   - Far call price (10-20%): Lower gearing (2-5x), safer but less leveraged
3. **Choose Expiry:** 1-6 months. Unlike warrants, longer expiry does not significantly increase CBBC cost (minimal time value).

**CBBC Risk Management Rules:**

1. **Never hold CBBCs near the call price.** When underlying approaches call price, CBBC prices become extremely volatile and disproportionate.
2. **Position sizing:** Never allocate more than 5% of portfolio to a single CBBC position.
3. **Stop loss BEFORE knock-out:** Exit when underlying is 3-5% from call price, not when it is touching. After knock-out, Category N = total loss, Category R = uncertain residual value.
4. **Daily monitoring required.** The mandatory call can trigger at ANY time during trading hours, including pre-market.

**CBBC Trading Strategies:**

Strategy A -- Trend Following:
- Use intraday momentum signal (your existing IntradayMomentumStrategy)
- Select bull CBBC with call price 7-10% below current underlying price
- Effective gearing: 5-10x
- Exit before close if intraday, or hold overnight only with conviction
- Stop loss: exit when underlying drops to within 4% of call price

Strategy B -- Overnight Gap Play:
- US market closes at 04:00 HKT. HK opens at 09:30 HKT.
- If US markets surge/crash, select CBBC in pre-market for the gap trade
- Higher risk but CBBC gearing amplifies overnight gaps effectively
- Close position within first 30 minutes (capture the gap, avoid reversal)

**Why CBBCs Over Warrants for Short-Term Trades:**
- No time decay drag (critical for 1-5 day holding periods)
- No IV risk (IV changes don't affect CBBC price significantly)
- Near-linear price tracking (easier to model and predict P&L)
- But: mandatory call risk is the tradeoff

---

## 4. Optimal Entry/Exit Timing Based on HK Trading Sessions

### 4.1 Morning Open Strategy (09:30-10:00)

**The Setup:**
The morning open is the highest-volatility period. ~15% of daily volume trades in the first 30 minutes. This is driven by overnight information from US and European markets being priced in.

**Opening Range Breakout (ORB) -- Optimized Parameters:**

Your existing `OpeningRangeBreakoutStrategy` in `intraday_strategies.py` implements this. Optimal parameters from research:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| ORB window | 15 minutes (3 x 5min bars) | Best balance of signal quality vs. timeliness |
| Extension | 0% (direct breakout) | No buffer needed; HK opens are decisive |
| Profit target | 1.5-2.0x OR width | Academic: ~75% win rate at 1.5x |
| Stop loss | OR midpoint | Tight enough for good risk/reward |
| VHSI filter | Skip if VHSI > 35 | High-vol ORB has negative expectancy |
| Best underlying | Blue chips (Tencent, HSBC, AIA) | Sufficient liquidity for reliable ORB |
| Min OR width | 0.3% | Too narrow = no signal |
| Max OR width | 2.5% | Too wide = excessive risk |

**Pre-Opening Session (09:00-09:30) Intelligence:**
- Monitor US futures (S&P 500, Nasdaq) direction at HK pre-open
- Check A-share pre-open (Shanghai/Shenzhen open at 09:15)
- If US futures and A-share pre-open are aligned in direction, ORB signal is stronger

### 4.2 Lunch Break Discontinuity Effect (12:00-13:00)

**The Phenomenon:**
HK market closes for lunch 12:00-13:00. During this break:
- A-shares continue trading (A-share lunch is 11:30-13:00, but morning ends at 11:30)
- Global news continues to flow
- Institutional order flow accumulates

**Trading the Discontinuity:**

Strategy: Post-Lunch Gap
- At 12:55-13:00, check A-share midday performance and any news during break
- If A-shares moved significantly during 11:30-12:00 (while HK was still open) AND continued moving from 13:00 onward, HK stocks with A-share correlation will gap at 13:00
- Enter at 13:00-13:05 in the direction of the A-share move
- Target: 50% of the A-share move to be reflected in correlated HK stocks
- Stop: 0.3% adverse move from 13:00 open price
- Best pairs: Dual-listed stocks (AH stocks), Hong Kong-listed tech stocks sensitive to A-share sentiment

**Quantified Patterns (2024-2025):**
- Post-lunch volatility spike averages 30-60% higher than the 10:30-11:30 session
- Correlation between A-share afternoon session and HK afternoon session: ~0.65 for dual-listed stocks
- The first 15 minutes after lunch (13:00-13:15) capture ~8% of afternoon session volume

### 4.3 Afternoon Session and Closing Auction (15:30-16:10)

**End-of-Day Statistics (2024-2025 HK Market):**

| Intraday Return by EOD | Avg Last-30-Min Move | Next-Day Open Move |
|------------------------|---------------------|-------------------|
| > +2%                  | -0.15%              | -0.08%            |
| +1% to +2%            | -0.05%              | +0.02%            |
| -1% to 0%             | +0.04%              | +0.03%            |
| < -2%                 | +0.12%              | +0.10%            |

**Key Finding:** Mean reversion effect is strongest for large daily moves (>2%). The last 30 minutes shows statistically significant reversal tendency.

**Closing Auction Session (CAS) 16:00-16:10:**
- Random close between 16:08-16:10 prevents gaming
- MOC (market-on-close) order imbalances create price pressure
- ~5.5 bps average price movement during CAS
- Strategy: if you have a reversal position, hold through CAS for additional alpha

**Implementation:** Your existing `EndOfDayMOCStrategy` and `Last30MinStatStrategy` in `intraday_strategies.py` implement these patterns. Key calibration:
- min_intraday_move: 1.0% (threshold for reversal signal)
- strong_reversal_threshold: 2.0% (position size scales up)
- entry_window: 15:30-15:55
- exit: CAS or next-day open (if overnight hold enabled)

---

## 5. Sector Rotation Within HSI and HSTECH

### 5.1 Hang Seng Index Composition

The HSI contains ~80 constituents across these major sectors:

| Sector | Weight (approx 2025) | Key Names |
|--------|---------------------|-----------|
| Financials | ~30% | HSBC, AIA, HK Exchanges, Ping An |
| Technology | ~25% (rising) | Tencent, Alibaba, Meituan, JD, Xiaomi |
| Property | ~8% | CK Asset, Sun Hung Kai, Henderson |
| Consumer | ~10% | Li Ning, Budweiser APAC |
| Healthcare | ~5% | WuXi Biologics, Sino Biopharm |
| Energy/Utilities | ~8% | CNOOC, CLP, China Gas |
| Industrials | ~7% | BYD, CSPC Pharma |
| Telecoms | ~5% | China Mobile, China Unicom |

**2024-2025 Rotation Pattern:**
- 2024 leaders: Technology, Healthcare, Information Technology
- 2025 leaders: Real Estate, Materials, Industrials (rotation away from tech)
- This rotation was driven by: property policy easing in China, stimulus for infrastructure, and tech sector consolidation after AI-driven rally

### 5.2 Hang Seng Tech Index (HSTECH) Dynamics

**Structure:**
- 30 largest tech companies listed in HK
- Market-cap weighted, 8% max individual constituent weight
- Themes: cloud, digital, e-commerce, fintech, internet, semiconductors
- Quarterly rebalancing (March, June, September, December)

**2025 Performance:** +34% YTD through April 2025, driven by:
- Alibaba: cloud and AI business momentum (largest contributor)
- DeepSeek AI catalyst boosted entire index
- Policy support for technology sector from mainland China

**Internal Rotation Dynamic:**
As the index rises, internal rotation occurs: stocks at high levels correct while laggards catch up. This creates a mean-reversion opportunity within the index.

**September 2025 Rebalancing:**
- Technology weight in HSI increased by 2%
- Emerging technology and healthcare companies replaced older industrial firms
- Hang Seng Semiconductor Industry Theme Index rebranded (October 2025)

### 5.3 Sector Rotation Trading Strategies

**Strategy A -- Momentum-Based Sector Rotation:**

```
Parameters:
  lookback_period: 20 trading days (1 month)
  holding_period: 20 trading days
  rebalance_frequency: monthly
  top_n_sectors: 2-3 sectors

Algorithm:
  1. Calculate trailing 20-day return for each HSI sector
  2. Rank sectors by momentum
  3. Overweight top 2-3 sectors, underweight bottom 2-3
  4. Rebalance monthly
  5. Filter: skip sectors with negative 60-day momentum (avoid catching falling knives)
```

**Strategy B -- Mean-Reversion Within HSTECH:**

```
Parameters:
  lookback: 60 trading days (3 months)
  z_score_entry: 1.5 standard deviations below mean
  z_score_exit: 0 (return to mean)
  universe: HSTECH 30 constituents

Algorithm:
  1. For each HSTECH constituent, calculate 60-day relative performance vs index
  2. Compute z-score of relative performance
  3. Buy stocks with z-score < -1.5 (laggards due for catch-up)
  4. Sell when z-score > 0 (returned to mean)
  5. Position size inversely proportional to volatility
```

**Strategy C -- Index Rebalancing Front-Running:**

- HSTECH rebalances quarterly
- Hang Seng Indexes announces changes ~2 weeks before effective date
- Stocks being ADDED to index tend to outperform by 2-5% in the 2 weeks between announcement and inclusion
- Stocks being REMOVED tend to underperform by 1-3%
- Strategy: buy additions and short (via CBBCs or options) removals on announcement day

**Data Source for Rebalancing:**
- https://www.hsi.com.hk/eng/indexes/all-indexes/hstech
- Press releases: https://www.hsi.com.hk/eng/ (News section)

---

## 6. AH Premium Arbitrage Strategies

### 6.1 AH Premium Mechanics

**Definition:**
AH Premium = (A-share price in HKD / H-share price) - 1

Where: A-share price in HKD = A-share price (CNY) / CNY-HKD exchange rate

**Historical Levels (2024-2025):**
- Historical average: ~35% premium (A-shares trade at 35% premium to H-shares)
- 2024 range: AH Premium Index ~120-140
- Q1 2025: Premium briefly INVERTED (H-shares traded at premium to A-shares for first time)
- Current "new normal": ~5-15% premium (significantly compressed from historical ~20-50%)

**Why the Premium Exists (Multiple Perspectives):**

From the retail investor perspective:
- A-share market is dominated by retail investors who are momentum-chasing and speculative
- H-share market is dominated by institutional investors who are valuation-disciplined
- Different risk-free rates: China's rates vs HK's USD-linked rates

From the structural perspective:
- A-shares and H-shares are legally DISTINCT share classes -- NOT fungible
- You cannot convert A-shares to H-shares or vice versa
- This non-fungibility is the fundamental reason the premium persists
- Short-selling A-shares is extremely difficult (few eligible securities, massive borrow rates)

From the macro perspective:
- Capital controls between mainland China and HK
- Exchange rate risk (CNY/HKD)
- Different monetary policy regimes

### 6.2 AH Premium Trading Strategy

**WARNING: This is NOT true arbitrage.** True arbitrage requires simultaneous buying and selling of identical instruments. AH shares are NOT identical (different share classes, different markets, different regulations). The "arbitrage" is really a mean-reversion bet on the premium level.

**Strategy: Premium Mean-Reversion**

```
Parameters:
  historical_mean_premium: 0.35 (35%)   -- needs updating to ~0.10 given 2025 compression
  historical_std: 0.15 (15%)
  entry_z_score: 1.5
  exit_z_score: 0.5
  exchange_rate: dynamic (currently ~0.92 HKD per CNY)

Entry Rules:
  z_score = (current_premium - historical_mean) / historical_std

  If z_score > 1.5:
    # Premium is abnormally HIGH (A too expensive, H too cheap)
    # BUY H-shares (they should appreciate as premium compresses)
    signal = +1 (long H-share)

  If z_score < -1.5:
    # Premium is abnormally LOW or inverted (H expensive relative to A)
    # SELL H-shares or avoid (premium may expand back to normal)
    signal = -1 (reduce H-share exposure)

Exit Rules:
  Exit long when z_score drops to 0.5
  Exit short when z_score rises to -0.5
  Hard stop: z_score moves 1.0 beyond entry (e.g., entered at 1.5, stop at 2.5)

Holding Period: 1-3 months (premium mean-reversion is slow)
```

**CRITICAL UPDATE for 2025-2026:**
Your existing `factor_ah_premium()` in `hk_alpha_factors.py` uses `historical_premium_mean = 0.35` and `historical_premium_std = 0.15`. These parameters need recalibration:
- The premium has structurally compressed to the 5-15% range
- Suggested update: `historical_premium_mean = 0.10`, `historical_premium_std = 0.08`
- The old parameters would generate false "buy H-share" signals because they think H-shares are always cheap

### 6.3 Cross-Sectional AH Premium Strategy (Research Finding)

Academic research from Rayliant demonstrates a profitable cross-sectional strategy:

**Strategy: Low-Premium Outperformance**
- Sort all AH-listed stocks by their AH premium level
- Buy the quintile with LOWEST AH premiums
- Sell/avoid the quintile with HIGHEST AH premiums
- Result: Low-premium quintile outperforms high-premium quintile by 28%
- Rationale: H-share prices tend to be more accurate valuations; A-share prices migrate toward H-share prices over time

**Implementation:**
```
1. Collect all dual-listed AH pairs (~140 stocks)
2. Calculate current AH premium for each pair
3. Rank by premium level
4. Buy H-shares of lowest-premium quintile (28 stocks)
5. Equal weight or market-cap weight within quintile
6. Rebalance monthly
7. Expected alpha: ~5-8% annually above HSI
```

### 6.4 Structural Risks and Constraints

| Risk | Description | Mitigation |
|------|-------------|------------|
| Non-fungibility | Cannot convert between A and H shares | Accept as basis risk; strategy is mean-reversion, not arbitrage |
| Capital controls | China may tighten/loosen capital flows | Monitor PBOC and SAFE policy announcements |
| Exchange rate | CNY/HKD moves affect premium calculation | Hedge FX exposure or use as additional signal |
| Regulatory | China could change short-selling rules, Stock Connect rules | Position size limits; don't bet on convergence to 0% |
| Premium regime change | "New normal" of 5-15% may be permanent | Use rolling parameters rather than fixed historical |
| Liquidity | Some H-shares have very low liquidity | Only trade AH pairs with H-share daily volume > HKD 50M |

---

## Integration Notes for Existing Codebase

### Files Already Covering These Topics:
- `/backend/hk_alpha_factors.py` -- AH premium factors, southbound flow factors, VHSI factors, T+0 intraday factors
- `/backend/intraday_strategies.py` -- ORB, VWAP reversion, EOD MOC, Last 30 Min strategies

### Recommended Updates:
1. **Update AH premium parameters** in `hk_alpha_factors.py`: change `historical_premium_mean` from 0.35 to 0.10
2. **Add sector rotation module**: new file for HSI/HSTECH sector momentum and mean-reversion strategies
3. **Add warrant/CBBC risk calculator**: effective gearing, distance to call price, theta decay estimation
4. **Add Stock Connect flow data ingestion**: connect to HKEX daily stats API or scraper
5. **Add lunch break discontinuity strategy**: new strategy in `intraday_strategies.py` for 13:00 gap trade

### Data Requirements:
- HKEX daily Stock Connect flow data (free, T+1)
- VHSI daily values (available from HKEX)
- AH premium data for ~140 dual-listed pairs
- HSTECH constituent list and weights (from hsi.com.hk)
- Warrant/CBBC live pricing (from issuer websites or broker API)

---

## Sources

- [HKEX Board Lot Framework Consultation (Dec 2025)](https://www.hkex.com.hk/News/Market-Communications/2025/251218news?sc_lang=en)
- [HKEX Minimum Spread Reduction Consultation (Jun 2024)](https://www.hkex.com.hk/-/media/HKEX-Market/News/Market-Consultations/2016-Present/June-2024-Review-of-Minimum-Spreads/Consultation-Paper/cp202406.pdf)
- [HKEX Minimum Spread Reduction Implementation (Dec 2024)](https://www.hkex.com.hk/News/Market-Communications/2024/241217news?sc_lang=en)
- [Southbound Stock Connect: Trends and Prospects (HKEX Insight)](https://www.hkexgroup.com/Media-Centre/Insight/Insight/2024/HKEX-Insight/Southbound-Stock-Connect-Trends-and-Prospects?sc_lang=en)
- [Cross-border equity flows and information transmission (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S1042443123000239)
- [Southbound capital flows and stock return predictability (ScienceDirect 2025)](https://www.sciencedirect.com/science/article/abs/pii/S0927538X25002240)
- [HKEX Stock Connect Historical Daily Statistics](https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/Historical-Daily?sc_lang=en)
- [MacroMicro: Southbound Fund Inflows vs HSI](https://en.macromicro.me/collections/1658/hk-stock-relative/15374/hk-southward-funds-and-hsi)
- [HKEX CBBC FAQ](https://www.hkex.com.hk/Global/Exchange/FAQ/Products/Securities/CBBC?sc_lang=en)
- [Macquarie CBBC Tutorial](https://www.warrants.com.hk/en/education/cbbc-tutorial)
- [HSBC Warrants and CBBCs](https://www.warrants.hsbc.com.hk/en/index)
- [UBS Warrants Top 30 Implied Volatility](https://warrants.ubs.com/en/market_statistics/top30_average_implied_volatility)
- [Intraday stock return volatility: Hong Kong evidence (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/0927538X94900205)
- [Intraday and intraweek volatility patterns of HSI (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0927538X02000690)
- [Market closure effects on HK index futures (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S104244319800047X)
- [HK Stock Market Trading Hours Guide (fxcns)](https://www.fxcns.com/en/hk-stocks/basic-knowledge-of-hk-stocks/mastering-hong-kong-stock-market-hours)
- [Hang Seng Tech Index (EBC Financial)](https://www.ebc.com/forex/hang-seng-tech-index-basics-what-beginners-should-know)
- [Hong Kong Market 2026 Outlook (IG)](https://www.ig.com/en/news-and-trade-ideas/hong-kong-equities-progress-review-260204)
- [Hang Seng Indexes](https://www.hsi.com.hk/eng/)
- [HSTECH Index Details](https://www.hsi.com.hk/eng/indexes/all-indexes/hstech)
- [Trading the A-H Share Arbitrage (Epsilon Journal)](https://epsilonjournal.substack.com/p/trading-the-a-h-share-arbitrage)
- [The A-H Premium: Same Stock Different Story (Rayliant)](https://rayliant.com/the-a-h-premium-same-stock-different-story/)
- [AH Premium Siamese Twin Stocks (ScienceDirect 2025)](https://www.sciencedirect.com/science/article/abs/pii/S0927539825000210)
- [AH Premium Arbitrage Opportunities (SciTePress 2025)](https://www.scitepress.org/Papers/2025/138324/138324.pdf)
- [Information in the A-H Premium (NYU Stern)](https://pages.stern.nyu.edu/~rwhitela/papers/Information%20in%20the%20A-H%20Premium.pdf)
