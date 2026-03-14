# Open-Source Quantitative Trading Strategies Research
## Compiled 2026-03-13 | All GitHub URLs verified via API

---

## 1. TOP GITHUB REPOS FOR QUANTITATIVE TRADING (Python, by stars)

| Rank | Repository | Stars | Description |
|------|-----------|-------|-------------|
| 1 | [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 47,616 | Free, open-source crypto trading bot with backtesting, ML optimization |
| 2 | [microsoft/qlib](https://github.com/microsoft/qlib) | 38,681 | AI-oriented Quant investment platform (supervised, RL, market dynamics) |
| 3 | [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | 31,963 | Multi-agent LLM financial trading framework |
| 4 | [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | 24,810 | Curated list of quant finance libraries and resources |
| 5 | [mementum/backtrader](https://github.com/mementum/backtrader) | 20,718 | Python backtesting library for trading strategies |
| 6 | [quantopian/zipline](https://github.com/quantopian/zipline) | 19,504 | Pythonic algorithmic trading library (event-driven) |
| 7 | [AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | 18,816 | Open-source financial LLMs for sentiment analysis and trading |
| 8 | [akfamily/akshare](https://github.com/akfamily/akshare) | 17,174 | Financial data interface library (A-shares, HK, US, futures) |
| 9 | [stefan-jansen/machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading) | 16,745 | Code for ML for Algorithmic Trading, 2nd edition |
| 10 | [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 14,177 | Financial reinforcement learning (DQN, DDPG, PPO, SAC, A2C, TD3) |
| 11 | [goldmansachs/gs-quant](https://github.com/goldmansachs/gs-quant) | 9,958 | Goldman Sachs Python toolkit for quantitative finance |
| 12 | [je-suis-tm/quant-trading](https://github.com/je-suis-tm/quant-trading) | 9,390 | 15+ Python strategies (pairs, momentum, mean reversion, options) |
| 13 | [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | 8,038 | Lightweight backtesting framework |
| 14 | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | 6,856 | Fastest vectorized backtesting engine (NumPy/Numba) |

---

## 2. STRATEGIES WITH >50% ANNUAL RETURN BACKTESTS

**Important caveat:** Claims of >50% annual returns in open-source backtests almost always suffer from survivorship bias, overfitting, or unrealistic transaction cost assumptions. Use these as starting points, not guarantees.

### A. FinRL Deep Reinforcement Learning Strategies
- **Repo:** https://github.com/AI4Finance-Foundation/FinRL (14,177 stars)
- **Returns:** Published results show DRL agents (PPO, A2C, DDPG) outperforming S&P 500 by 2-3x in backtests on specific periods
- **How:** Multi-agent ensemble strategy combining DQN, DDPG, PPO, SAC, A2C, TD3
- **Stack:** Python, PyTorch, Stable-Baselines3, OpenAI Gym
- **Paper:** NeurIPS 2020 Deep RL Workshop (arXiv:2011.09607)

### B. Microsoft Qlib Alpha Factors
- **Repo:** https://github.com/microsoft/qlib (38,681 stars)
- **Returns:** Built-in alpha factor models with SOTA results; specific strategies show significant excess returns in Chinese A-share backtests
- **How:** Supports LightGBM, XGBoost, LSTM, Transformer, and custom models for alpha factor mining
- **Stack:** Python, pandas, numpy, PyTorch

### C. Momentum Transformer
- **Repo:** https://github.com/kieranjwood/trading-momentum-transformer (603 stars)
- **Paper:** arXiv:2112.08534 "Trading with the Momentum Transformer"
- **Returns:** Outperforms benchmark time-series momentum strategies; adapts to regime changes (including COVID crash)
- **How:** Attention-based architecture blending momentum and mean reversion signals
- **Stack:** Python, PyTorch

### D. je-suis-tm/quant-trading Collection
- **Repo:** https://github.com/je-suis-tm/quant-trading (9,390 stars)
- **Returns:** Individual strategies (Dual Thrust, London Breakout) show high returns in specific market conditions
- **Strategies included:** VIX Calculator, Pattern Recognition, CTA, Monte Carlo, Options Straddle, Shooting Star, London Breakout, Heikin-Ashi, Pair Trading, RSI, Bollinger Bands, Parabolic SAR, Dual Thrust, MACD

---

## 3. MACHINE LEARNING MODELS THAT ACTUALLY WORK

### Production-Quality (not toy examples)

#### A. Microsoft Qlib - The Gold Standard
- **Repo:** https://github.com/microsoft/qlib (38,681 stars)
- **Why it's real:** Microsoft-backed, used in production, continuously updated
- **Models:** LightGBM, XGBoost, LSTM, GRU, Transformer, TabNet, DoubleEnsemble
- **Key feature:** RD-Agent integration for automated R&D of quant factors
- **Data pipeline:** Full end-to-end from data collection to portfolio optimization
- **Stack:** Python, PyTorch, pandas, numpy

#### B. FinRL - Reinforcement Learning for Trading
- **Repo:** https://github.com/AI4Finance-Foundation/FinRL (14,177 stars)
- **Why it's real:** NeurIPS published, actively maintained, 3-layer architecture
- **Models:** DQN, DDPG, PPO, SAC, A2C, TD3 ensemble
- **Key feature:** Market environment simulation with realistic constraints
- **Stack:** Python, PyTorch, Stable-Baselines3, OpenAI Gym

#### C. TradeMaster - RL Trading Platform
- **Repo:** https://github.com/TradeMaster-NTU/TradeMaster (2,523 stars)
- **Why it's real:** University research-backed (NTU), multi-asset support
- **Models:** Various RL algorithms with market environment simulation
- **Stack:** Python, PyTorch

#### D. Machine Learning for Trading (Stefan Jansen)
- **Repo:** https://github.com/stefan-jansen/machine-learning-for-trading (16,745 stars)
- **Why it's real:** Comprehensive textbook code covering full ML pipeline
- **Models:** Linear models, tree-based (RF, GBM), deep learning (RNN, CNN, autoencoders), NLP for trading, RL
- **Key feature:** 20+ chapters of production-oriented code with real data
- **Stack:** Python, pandas, scikit-learn, TensorFlow, PyTorch

---

## 4. HONG KONG STOCK MARKET QUANTITATIVE STRATEGIES

### HK-Specific Trading Platforms

#### A. Futu Algo - HK Stock Algorithmic Trading
- **Repo:** https://github.com/billpwchan/futu_algo (565 stars)
- **What:** Full algorithmic trading solution built on Futu OpenD API
- **Markets:** Hong Kong stocks, US stocks via Futu/Moomoo
- **Features:** Real-time data, automated order execution, strategy framework
- **Stack:** Python, Futu OpenAPI

#### B. Futu OpenAPI Python SDK
- **Repo:** https://github.com/FutunnOpen/py-futu-api (1,240 stars)
- **What:** Official Futu SDK for HK stock market data and trading
- **Features:** Real-time quotes, historical data, order management
- **Stack:** Python, protobuf

#### C. Futubot - Intraday Trading Robot
- **Repo:** https://github.com/quincylin1/futubot (37 stars)
- **What:** Intraday trading robot with real-time dashboard for HK stocks
- **Stack:** Python, Futu OpenAPI

### HK-Compatible Data Sources

#### D. AKShare
- **Repo:** https://github.com/akfamily/akshare (17,174 stars)
- **What:** Financial data interface supporting A-shares, HK stocks, US stocks, bonds, futures
- **HK data:** Hong Kong stock quotes, historical data, financial statements
- **Stack:** Python, pandas

#### E. qstock
- **What:** Open-source quantitative finance package with 4 modules (data, visualization, stock selection, backtesting)
- **HK data:** Supports A-shares, US stocks, Hong Kong stocks, bonds, futures

#### F. OpenBB with AKShare/Tushare Extensions
- **What:** Extending OpenBB for A-Share and Hong Kong stock analysis
- **Reference:** https://openbb.co/blog/extending-openbb-for-a-share-and-hong-kong-stock-analysis-with-akshare-and-tushare

---

## 5. HOLY GRAIL STRATEGIES: Pairs Trading & Statistical Arbitrage

### A. QuantConnect Pairs Trading (Cointegration)
- **Repo:** https://github.com/QuantConnect/Research (720 stars)
- **Notebook:** `Analysis/05 Pairs Trading Strategy Based on Cointegration.ipynb`
- **Method:** Select cointegrated pair, trade spread divergence/convergence
- **Stack:** Python, QuantConnect framework

### B. High-Frequency Statistical Arbitrage
- **Repo:** https://github.com/bradleyboyuyang/Statistical-Arbitrage (251 stars)
- **Method:** Intraday stat arb using cointegration tests, Ornstein-Uhlenbeck process, time series analysis
- **Features:** Full backtesting pipeline, both traditional spread models and continuous-time models
- **Stack:** Python, pandas, numpy, statsmodels

### C. Pairs Trading with LSTM Signal
- **Repo:** https://github.com/shimonanarang/pair-trading
- **Method:** Combines cointegration-based pairs trading with LSTM for next-day signal prediction
- **Innovation:** ML-enhanced entry/exit timing on mean-reverting spreads
- **Stack:** Python, TensorFlow/Keras

### D. Statistical Arbitrage Strategy (KO/PEP Example)
- **Repo:** https://github.com/nirajdsouza/statistical-arbitage-strategy
- **Method:** Cointegration testing, spread modeling via linear regression, entry/exit signals based on spread deviations
- **Data:** Yahoo Finance via yfinance
- **Stack:** Python, statsmodels, yfinance

### E. Crypto Pairs Trading
- **Repo:** https://github.com/coderaashir/Crypto-Pairs-Trading
- **Method:** Statistical arbitrage for cryptocurrency pairs
- **Stack:** Python

### Key Technique Reference
- **Cointegration & Pairs Trading Tutorial:** https://letianzj.github.io/cointegration-pairs-trading.html
- **Core test:** `statsmodels.tsa.stattools.coint()` - p-value < 0.05 indicates cointegrated pair

---

## 6. LLM/AI SENTIMENT-DRIVEN TRADING STRATEGIES

### A. TradingAgents - Multi-Agent LLM Framework (TOP PICK)
- **Repo:** https://github.com/TauricResearch/TradingAgents (31,963 stars)
- **What:** Mirrors real-world trading firms with specialized LLM agents (fundamental analysts, sentiment experts, technical analysts)
- **LLM Support:** GPT, Gemini, Claude, Grok, Ollama, OpenRouter
- **Innovation:** Multi-agent debate and consensus for trading decisions
- **Stack:** Python, LangChain, multiple LLM providers

### B. FinGPT - Financial LLM
- **Repo:** https://github.com/AI4Finance-Foundation/FinGPT (18,816 stars)
- **What:** Open-source financial LLM fine-tuned for sentiment analysis
- **Models:** FinGPT v3 (LoRA fine-tuned on news/tweets sentiment), FinGPT-RAG
- **Cost:** Train SOTA financial model for <$300 on single RTX 3090
- **Paper:** arXiv:2306.06031
- **Stack:** Python, PyTorch, HuggingFace Transformers

### C. LLM-Enhanced Trading (FinGPT-based)
- **Repo:** https://github.com/Ronitt272/LLM-Enhanced-Trading (39 stars)
- **What:** Sentiment-driven trading using FinGPT for real-time news/social media sentiment
- **Stack:** Python, FinGPT

### D. Algorithmic Trading with GenAI Sentiment
- **Repo:** https://github.com/risabhmishra/algotrading-sentimentanalysis-genai (22 stars)
- **What:** OpenAI and Llama clients for sentiment analysis, backtrader integration
- **Features:** Stock data processors, sentiment preprocessing, backtest runners
- **Stack:** Python, OpenAI API, Llama, Backtrader

### E. QuantMuse - AI-Powered Trading System
- **Repo:** https://github.com/0xemmkty/QuantMuse (2,020 stars)
- **What:** Comprehensive quant trading system with AI-powered analysis and risk management
- **Stack:** Python

### Sentiment Data Sources
- Financial news APIs (Alpha Vantage, NewsAPI, GDELT)
- Twitter/X social media sentiment
- SEC filings (EDGAR)
- Reddit (r/wallstreetbets, r/stocks)
- FinGPT pre-trained sentiment models on HuggingFace

---

## 7. ADAPTIVE STRATEGIES: Regime Detection + Momentum/Mean-Reversion Switching

### A. Slow Momentum with Fast Reversion (Paper Implementation)
- **Repo:** https://github.com/kieranjwood/slow-momentum-fast-reversion (266 stars)
- **Paper:** arXiv:2105.13727 "Slow Momentum with Fast Reversion"
- **Method:** Deep learning + changepoint detection to balance slow momentum exploitation with fast mean-reversion
- **Innovation:** Automatically optimizes balance between momentum and reversion based on detected regime changes
- **Stack:** Python, PyTorch

### B. Trading with the Momentum Transformer (Paper Implementation)
- **Repo:** https://github.com/kieranjwood/trading-momentum-transformer (603 stars)
- **Paper:** arXiv:2112.08534 "Trading with the Momentum Transformer"
- **Method:** Attention-based architecture that intelligently switches between and blends classical strategies based on data patterns
- **Innovation:** Naturally adapts to new market regimes (validated during COVID-19 crisis)
- **Stack:** Python, PyTorch

### C. Enhanced Momentum with Momentum Transformers (2024)
- **Paper:** arXiv:2412.12516 (December 2024)
- **Method:** Extends Momentum Transformer to equities (original focused on futures/indices)
- **Innovation:** Combines attention with LSTM for long-term dependencies, accounts for transaction costs

### D. Regime-Adaptive Trading with HMM + Random Forest
- **Reference:** https://blog.quantinsti.com/regime-adaptive-trading-python/
- **Method:** Hidden Markov Model detects current regime, specialist Random Forest models trained per regime
- **Innovation:** Uses the most relevant ML model based on detected regime state
- **Stack:** Python, hmmlearn, scikit-learn

### E. Market Regime Detection (LSEG/Refinitiv)
- **Repo:** https://github.com/LSEG-API-Samples/Article.RD.Python.MarketRegimeDetectionUsingStatisticalAndMLBasedApproaches (60 stars)
- **Method:** Statistical and ML-based regime detection approaches
- **Stack:** Python, Jupyter notebooks

### F. QuantConnect Momentum + Mean Reversion Combination
- **Repo:** https://github.com/QuantConnect/Tutorials
- **Path:** `04 Strategy Library/02 Combining Mean Reversion and Momentum in Forex Market/`
- **Method:** Combines both strategies in forex markets with regime-based switching

---

## 8. STRATEGIES FROM QUANT FINANCE PAPERS (2023-2025) WITH CODE

### A. Momentum Transformer Papers (2021-2024, with code)
- **Paper 1:** "Trading with the Momentum Transformer" (arXiv:2112.08534)
  - Code: https://github.com/kieranjwood/trading-momentum-transformer
- **Paper 2:** "Slow Momentum with Fast Reversion" (arXiv:2105.13727)
  - Code: https://github.com/kieranjwood/slow-momentum-fast-reversion
- **Paper 3:** "Enhanced Momentum with Momentum Transformers" (arXiv:2412.12516, Dec 2024)
  - Extends to equities, combines attention with LSTM

### B. FinGPT: Open-Source Financial LLMs (2023)
- **Paper:** arXiv:2306.06031
- **Code:** https://github.com/AI4Finance-Foundation/FinGPT
- **Contribution:** Democratized financial LLM access, LoRA fine-tuning for sentiment

### C. FinRL: Deep Reinforcement Learning for Trading (NeurIPS 2020, continuously updated)
- **Paper:** arXiv:2011.09607
- **Code:** https://github.com/AI4Finance-Foundation/FinRL
- **Updates:** Continuous improvements through 2025 including meta-learning and multi-agent

### D. Python Code for Quantitative Finance Papers
- **Repo:** https://github.com/PyFE/PyfengForPapers (46 stars)
- **What:** Implementations of academic quant finance papers including Black-Scholes volatility bounds
- **Stack:** Python

### E. Quantitative Trading Strategies Using Python (Apress, 2023)
- **Repo:** https://github.com/Apress/Quantitative-Trading-Strategies-Using-Python
- **Book:** By Peng Liu, covers complete strategy implementations
- **Stack:** Python, pandas, numpy

### F. Imperial College - Systematic Trading with ML (2024-2025)
- **Reference:** https://hm-ai.github.io/Systematic_Trading_Strategies_with_Machine_Learning_Algorithms/
- **What:** Course materials with Jupyter notebooks for systematic trading strategies using ML
- **Stack:** Python, scikit-learn, PyTorch

---

## COMPARISON TABLE

| Category | Best Pick | Stars | Production Ready | HK Support |
|----------|----------|-------|-----------------|------------|
| Overall Platform | microsoft/qlib | 38,681 | Yes | Via AKShare |
| Reinforcement Learning | AI4Finance/FinRL | 14,177 | Yes | Extensible |
| LLM/Sentiment | TauricResearch/TradingAgents | 31,963 | Yes | Extensible |
| Financial LLM | AI4Finance/FinGPT | 18,816 | Yes | Extensible |
| Backtesting | mementum/backtrader | 20,718 | Yes | Any data |
| Fast Backtesting | polakowo/vectorbt | 6,856 | Yes | Any data |
| HK Trading | billpwchan/futu_algo | 565 | Yes | Native |
| HK Data | akfamily/akshare | 17,174 | Yes | Native |
| Pairs Trading | bradleyboyuyang/Statistical-Arbitrage | 251 | Research | Extensible |
| Regime Adaptive | kieranjwood/momentum-transformer | 603 | Research | Extensible |
| Strategy Collection | je-suis-tm/quant-trading | 9,390 | Educational | Extensible |
| Crypto Bot | freqtrade/freqtrade | 47,616 | Yes | No |

---

## RECOMMENDED IMPLEMENTATION ORDER

1. **Start with Qlib** - Set up Microsoft Qlib as your primary research platform. It has the most mature ML pipeline for factor research and supports multiple model paradigms.

2. **Add AKShare for HK data** - Integrate AKShare for Hong Kong stock data feeds into your backend.

3. **Implement Pairs Trading first** - Statistical arbitrage via cointegration is the most robust "Holy Grail" strategy. Use the bradleyboyuyang/Statistical-Arbitrage repo as reference.

4. **Add regime detection** - Implement HMM-based regime detection to switch between momentum and mean reversion strategies. Reference the Momentum Transformer paper.

5. **Layer in sentiment** - Use FinGPT or TradingAgents for LLM-based sentiment signals as alpha factors.

6. **Backtest everything with vectorbt** - Use vectorbt for fastest backtesting iteration cycles.

7. **Connect to Futu for HK execution** - Use futu_algo and py-futu-api for live HK stock trading.
