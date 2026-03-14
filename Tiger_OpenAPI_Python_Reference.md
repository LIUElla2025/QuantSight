# Tiger Brokers OpenAPI Python SDK - Complete Reference

> Source: https://docs.itigerup.com/docs/intro (all pages fetched 2026-03-14)
> SDK: `tigeropen` (pip install tigeropen)
> Python: 3.8+

---

## Table of Contents

1. [Overview & Supported Markets](#1-overview--supported-markets)
2. [User & Account Types](#2-user--account-types)
3. [SDK Setup & Configuration](#3-sdk-setup--configuration)
4. [Rate Limits & Restrictions](#4-rate-limits--restrictions)
5. [Market Data Permissions](#5-market-data-permissions)
6. [Trading Fees](#6-trading-fees)
7. [Quote API - Common](#7-quote-api---common)
8. [Quote API - Stocks](#8-quote-api---stocks)
9. [Quote API - Futures](#9-quote-api---futures)
10. [Quote API - Options](#10-quote-api---options)
11. [Quote API - Warrants & CBBC](#11-quote-api---warrants--cbbc)
12. [Quote API - Crypto](#12-quote-api---crypto)
13. [Quote API - Funds](#13-quote-api---funds)
14. [Stock Screener](#14-stock-screener)
15. [Contract Management](#15-contract-management)
16. [Order Placement](#16-order-placement)
17. [Order Modification & Cancellation](#17-order-modification--cancellation)
18. [Order Query](#18-order-query)
19. [Account Management](#19-account-management)
20. [Push Subscriptions - Market Data](#20-push-subscriptions---market-data)
21. [Push Subscriptions - Account Events](#21-push-subscriptions---account-events)
22. [Enums & Constants](#22-enums--constants)
23. [Error Codes](#23-error-codes)
24. [Best Practices & Gotchas](#24-best-practices--gotchas)
25. [MCP Integration](#25-mcp-integration)
26. [Option Tools (QuantLib)](#26-option-tools-quantlib)
27. [Trading Hours Reference](#27-trading-hours-reference)
28. [Version History](#28-version-history)

---

## 1. Overview & Supported Markets

The Tiger Open Platform provides API services for individual and institutional investors. The SDK (`tigeropen`) supports:

- **Account Information**: Query assets and positions
- **Trade Management**: Create, modify, cancel orders; track status and execution
- **Market Data**: Stocks, options, futures, warrants, CBBC, crypto, funds
- **Real-time Push**: Order changes, asset/position updates, market movements

### Supported Markets & Instruments

| Market | Products | Comprehensive | Simulated |
|--------|----------|:---:|:---:|
| **US** | Stocks, ETFs (fractional shares - comprehensive only), Options, Futures | Yes | Yes |
| **Hong Kong** | Stocks, ETFs, Options, Futures, Warrants, CBBC | Yes | Yes (no CBBC) |
| **Singapore** | Stocks, ETFs, Futures | Yes | Yes |
| **Australia** | Stocks, ETFs | Yes | Yes |

### Supported Order Types
Market, Limit, Stop-Loss, Stop-Limit, Trailing Stop, Bracket Orders, TWAP, VWAP, Auction (HK)

### Supported Languages
Java, Python, C++, C#

---

## 2. User & Account Types

### User Types
- **Individual Investors**: Complete online account opening + deposit, then enable API at https://developer.itigerup.com/profile
- **Institutional Investors**: Register through institutional backend

### Account Types

| Type | Description | Markets | Features |
|------|-------------|---------|----------|
| **Comprehensive** | Recommended | All | Margin, short-selling, all instruments |
| **Global** | Not recommended | All | Margin, short-selling, stocks/options/futures |
| **Paper/Demo** | Simulated | US, HK, A-shares | Options supported, no intl markets |

### Account Identifiers
- Global account: U-prefix
- Standard account: 5-10 digits
- Paper account: 17 digits

### AccountProfile Properties
- `account` (str): Account ID
- `account_type` (str): GLOBAL / STANDARD / PAPER
- `status` (str): Funded / Open / Pending / Rejected / Closed / New / Abandoned / Unknown
- `capability` (str): CASH / RegTMargin / PMGRN

---

## 3. SDK Setup & Configuration

### Installation
```bash
pip3 install tigeropen
pip3 install tigeropen --upgrade  # upgrade
# Optional for option tools:
pip install quantlib==1.40
```

### Configuration - Properties File
```python
from tigeropen.tiger_open_config import TigerOpenClientConfig

client_config = TigerOpenClientConfig(props_path='/path/to/properties/')
```

Properties file format (`tiger_openapi_config.properties`):
```properties
tiger_id=YOUR_TIGER_ID
account=YOUR_ACCOUNT_NUMBER
private_key=YOUR_RSA_PRIVATE_KEY
sandbox=False
standard_account=YOUR_STANDARD_ACCOUNT
is_grab_permission=True
```

### Configuration - Programmatic
```python
from tigeropen.tiger_open_config import TigerOpenClientConfig

client_config = TigerOpenClientConfig()
client_config.private_key = read_private_key('/path/to/key.pem')
client_config.tiger_id = 'YOUR_TIGER_ID'
client_config.account = 'YOUR_ACCOUNT'
client_config.license = 'TBSG'  # or TBHK, TBNZ
```

### TigerOpenClientConfig Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tiger_id` | str | Developer ID |
| `account` | str | Trading account |
| `private_key` | str | RSA private key for signing |
| `sandbox` | bool | Deprecated, default False |
| `is_grab_permission` | bool | Auto-claim quote permissions, default True |
| `standard_account` | str | Comprehensive account number |
| `props_path` | str | Config file path |
| `token_refresh_duration` | int | Token refresh interval in seconds |
| `use_full_tick` | bool | Enable full tick mode for push |
| `language` | str | Language setting |
| `timezone` | str | Timezone setting |

### Key Points
- Python SDK requires **PKCS#1** format private key (Java uses PKCS#8)
- Private keys cannot be recovered after page refresh -- save immediately
- Token validity: 30 days (TBHK license)
- Auto-refresh token: `client_config.token_refresh_duration = 24 * 60 * 60`

### Three Client Types
```python
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.push.push_client import PushClient

quote_client = QuoteClient(client_config)
trade_client = TradeClient(client_config)

protocol, host, port = client_config.socket_host_port
push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'))
push_client.connect(client_config.tiger_id, client_config.private_key)
```

---

## 4. Rate Limits & Restrictions

Rate limits are per **tigerId + method** (each endpoint has independent counters), using a 60-second rolling window.

### Three Tiers

| Tier | Limit | Examples |
|------|-------|---------|
| **High-frequency** | 120 calls/min | Order management (create/place/modify/cancel), order queries, real-time quotes, tick-by-tick, options briefs, futures real-time |
| **Mid-frequency** | 60 calls/min | Options chains/expirations, depth quotes, contracts, shortable stocks, account/asset/position queries, K-line, options analysis |
| **Low-frequency** | 10 calls/min | Quote permissions, market status, symbol lookups, stock details, futures exchanges, trading rankings |

### Violation Consequences
- Error: `code=4 msg=rate limit error(current limiting interface:<name>, up to X times per minute)`
- **Persistent excessive traffic leads to automatic blacklisting** (all API calls blocked)

---

## 5. Market Data Permissions

API market data permissions operate **independently from APP** and require separate purchase.

### Permission Types

| Permission | Description |
|-----------|-------------|
| `usQuoteBasic` | US Stocks L1 - Nasdaq Basic, real-time quotes, bid-ask, tick data |
| `usStockQuoteLv2Totalview` | US Stocks L2 - Nasdaq Totalviews, 40-level depth |
| `hkStockQuoteLv2` | HK Stocks L2 - auto-refresh, 10-level book, tick, broker queue |
| `hkStockQuoteLv2Global` | HK Stocks L2 Global |
| `usOptionQuote` | US Options L1 - real-time, optimal pricing across 16 exchanges |
| `CBOEFuturesQuoteLv2` | CBOE Futures L2 |
| `HKEXFuturesQuoteLv2` | HKEX Futures L2 |
| `SGXFuturesQuoteLv2` | SGX Futures L2 |
| `OSEFuturesQuoteLv2` | OSE Futures L2 |
| `NYMEXFuturesQuoteLv2` | NYMEX Futures L2 |

### Subscription Quotas by Account Tier

| Tier | Historical Data | Standard Subs | Depth Subs |
|------|----------------|--------------|------------|
| API Access Only | 20 stocks; 10 futures; 10 options | 20 | 10 |
| $10K+ assets / $100K+ volume | 200 stocks; 20 futures; 200 options | 100 | 20 |
| $50K+ / $500K+ volume | 500 stocks; 50 futures; 500 options | 500 | 100 |
| Higher tiers ($2M/$5M) | Scales proportionally | 2000 | 500 |

- Historical data: first request consumes quota; repeated requests within 30 days don't deplete
- Different timeframes for the same symbol count as single allocation
- Customer tier updates: **weekly, Tuesday 8am GMT+8**, based on prior week's average daily closing positions in USD

### Verify/Claim Permissions
```python
permissions = quote_client.get_quote_permission()
permissions = quote_client.grab_quote_permission()  # claim across devices
quota = quote_client.get_kline_quota(with_details=True)
```

---

## 6. Trading Fees

- **No additional charges** for OpenAPI trading -- same fees as mobile app
- Market data requires **separate purchase** from APP permissions
- OpenAPI quotes have **reduced latency** and **faster refresh rates** compared to APP

---

## 7. Quote API - Common

### QuoteClient Initialization
```python
from tigeropen.quote.quote_client import QuoteClient

quote_client = QuoteClient(client_config, logger=None, is_grab_permission=True)
```

**CRITICAL**: Create QuoteClient **once** at module level to avoid rate limiting from multiple instantiations. `is_grab_permission=True` (default since SDK 2.0.9+) auto-claims quote permissions.

### grab_quote_permission()
Claims market data privileges across devices when same account uses multiple devices.
```python
permissions = quote_client.grab_quote_permission()
# Returns: [{'name': 'usStockQuoteLv2Totalview', 'expire_at': -1}, ...]
# expire_at: -1 = perpetual, otherwise millisecond timestamp
```

**Error without permission**: `code=4 msg=4000:permission denied(current device does not have permission)`

### get_quote_permission()
Queries currently held permissions. Same return format as `grab_quote_permission()`.

### get_kline_quota(with_details=False)
Usage and remaining subscribable symbol count based on user tier.
```python
quota = quote_client.get_kline_quota(with_details=True)
# Returns: [
#   {'remain': 200, 'used': 0, 'method': 'kline', 'symbol_details': []},
#   {'remain': 20, 'used': 0, 'method': 'future_kline', 'symbol_details': []},
#   {'remain': 197, 'used': 3, 'method': 'option_kline',
#    'symbol_details': [{'code': 'TCH.HK', 'last_request_timestamp': '1750851341848'}]}
# ]
```

---

## 8. Quote API - Stocks

### Market Status & Calendar

```python
# get_market_status(market, lang=Language.en_US)
status = quote_client.get_market_status(Market.US)
# Returns: List[MarketStatus] with market, trading_status, status, open_time

# get_trading_calendar(market, begin_date, end_date)
# begin_date/end_date: 'yyyy-MM-dd', data from 2015 onwards
calendar = quote_client.get_trading_calendar(Market.US, '2024-01-01', '2024-12-31')
# Returns: List[dict] with date, type (TRADING/EARLY_CLOSE), open_time, close_time
```

### Symbol Information

```python
# get_symbols(market, include_otc=False) - all symbols including delisted
symbols = quote_client.get_symbols(Market.US)
# Indices start with "." (e.g., .DJI for Dow Jones)

# get_symbol_names(market, lang, include_otc=False)
names = quote_client.get_symbol_names(Market.US)
# Returns: List[tuple(symbol, name)]
```

### Real-Time Quotes

```python
# get_stock_briefs(symbols, include_hour_trading=False, lang=Language.en_US)
# Max 50 symbols per request
briefs = quote_client.get_stock_briefs(['AAPL', 'GOOGL'])
```

**DataFrame columns**: symbol, ask_price, ask_size, bid_price, bid_size, pre_close, latest_price, latest_time (ms), volume, open, high, low, status, change, changeRate, amplitude, adj_pre_close, hour_trading fields

**Status values**: UNKNOWN, NORMAL, HALTED, DELIST, NEW, ALTER, CIRCUIT_BREAKER, ST

```python
# get_depth_quote(symbols, market) - N-level bid/ask
# Max 50 symbols
depth = quote_client.get_depth_quote(['AAPL'])
# Returns: dict with asks/bids lists of (price, volume, order_count)

# get_stock_delay_briefs(symbols, lang) - FREE delayed quotes (~15min, US only)
# Max 50 symbols
delayed = quote_client.get_stock_delay_briefs(['AAPL'])
# Columns: symbol, pre_close, time (ms), volume, open, high, low, close, halted
```

### Trade Ticks

```python
# get_trade_ticks(symbols, trade_session, begin_index, end_index, limit=200, lang)
# Max 50 symbols, limit max 2000
# begin_index=end_index=-1 returns latest
# Direction: "+" buy, "-" sell, "*" neutral
# Results are front-closed, back-open intervals
ticks = quote_client.get_trade_ticks(['AAPL'], limit=500)
# Columns: index, time (ms), price, volume, direction
```

### K-Line / Candlestick Data

```python
# get_bars(symbols, period, begin_time, end_time, date, right, limit=251,
#          lang, page_token, trade_session, with_fundamental=False)
# Max 50 symbols (A-stock limit 30)
# date format: yyyyMMdd
bars = quote_client.get_bars(['AAPL'], period=BarPeriod.DAY, limit=100)
```

**DataFrame columns**: time (ms), open, close, high, low, volume, amount, optional turnover_rate, ttm_pe, lyr_pe, next_page_token

**Data availability**: 1/5-min ~1 month; 15/30/60-min ~1 year

**Intraday K-lines**: Require specific `trade_session` values with minute-level periods

```python
# get_bars_by_page(symbol, period, begin_time, end_time, total=10000,
#                  page_size=1000, right, time_interval=2, lang, trade_session)
# Single symbol, paginated, time_interval = seconds between requests (default 2)
bars = quote_client.get_bars_by_page('AAPL', period=BarPeriod.DAY, total=5000)
# Columns: time, open, close, high, low, volume, next_page_token
```

### Intraday / Timeline Data

```python
# get_timeline(symbols, include_hour_trading, begin_time, lang, trade_session)
# Max 50 symbols, most recent trading day minute-level data
timeline = quote_client.get_timeline(['AAPL'])
# Columns: symbol, time (ms), price, avg_price, pre_close, volume, trading_session

# get_timeline_history(symbols, date, right, trade_session)
# Max 50 symbols, historical minute data for specific date
# date format: yyyy-MM-dd
hist = quote_client.get_timeline_history(['AAPL'], date='2024-01-15')
# Columns: symbol, time (ms), price, avg_price
```

### Capital Flow

```python
# get_capital_flow(symbol, period, market, begin_time, end_time, limit=200, lang)
# limit max 1200
# begin_time/end_time: millisecond timestamps
flow = quote_client.get_capital_flow('AAPL', period=CapitalPeriod.DAY)
# Columns: time, timestamp (13-digit), net_inflow, symbol, period

# get_capital_distribution(symbol, market, lang)
dist = quote_client.get_capital_distribution('AAPL')
# Returns CapitalDistribution: net_inflow, in_all, in_big/mid/small, out_all, out_big/mid/small
```

### HK Broker Data

```python
# get_stock_broker(symbol, limit=40, lang) - HK stocks only, max 60
broker = quote_client.get_stock_broker('00700')
# Returns StockBroker with bid_broker/ask_broker arrays
# Each LevelBroker: level, price, broker_count, broker list

# get_broker_hold(market='HK', limit=50, page=0, order_by, direction, lang)
# max 500, page from 0
# order_by: marketValue/sharesHold/buyAmount variants (1/5/20/60-day)
# direction: DESC/ASC
hold = quote_client.get_broker_hold(market=Market.HK)
# Columns: org_id, org_name, date, shares_hold, market_value, buy_amount, market
```

### Rankings & Metadata

```python
# get_trade_rank(market, lang) - hot stocks, ~20sec update frequency
# US: 30 rows, HK/SG: 10 rows
rank = quote_client.get_trade_rank(Market.US)
# Columns: symbol, market, name, sec_type, change_rate, sell/buy_order_rate, hour_trading fields

# get_trade_metas(symbols) - trading parameters per security
# Max 50 symbols
metas = quote_client.get_trade_metas(['AAPL', '00700'])
# Columns: symbol, lot_size (shares per lot), min_tick, spread_scale
```

---

## 9. Quote API - Futures

### Exchange & Contract Info

```python
# get_future_exchanges() - all exchanges
exchanges = quote_client.get_future_exchanges()
# Columns: code, name, zone

# get_future_contracts(exchange) - tradable contracts for exchange
contracts = quote_client.get_future_contracts('CME')
# Columns: contract_code, type, symbol, name, contract_month, currency, exchange,
#           first_notice_date, last_trading_date, multiplier, min_tick

# get_future_contract(contract_code) - single contract details
contract = quote_client.get_future_contract('ES2306')

# get_current_future_contract(future_type) - lead/primary contract
current = quote_client.get_current_future_contract('ES')

# get_all_future_contracts(future_type) - all contracts for type
all_contracts = quote_client.get_all_future_contracts('CL')

# get_future_continuous_contracts(future_type) - continuous contracts (e.g., CLmain)
continuous = quote_client.get_future_continuous_contracts('CL')
```

### Trading Hours & Quotes

```python
# get_future_trading_times(identifier, trading_date)
# Returns: start/end timestamps, trading/bidding flags, timezone
times = quote_client.get_future_trading_times('ES2306', '2024-01-15')

# get_future_brief(identifiers) - real-time quotes
# bid/ask prices+sizes, latest_price, volume, open_interest, OHLC, limit_up/limit_down
brief = quote_client.get_future_brief(['ES2306', 'CLmain'])

# get_future_depth(identifiers) - order book depth
# asks/bids lists with price-volume pairs
depth = quote_client.get_future_depth(['ES2306'])

# get_future_trade_ticks(identifier) - tick-by-tick
# Columns: index, timestamp, price, volume
ticks = quote_client.get_future_trade_ticks('ES2306')
```

### Historical Data

```python
# get_future_bars(identifiers, period, begin_time, end_time, limit, page_token)
# Periods: day/week/month/year/1min/5min/15min/30min/60min
# Returns: OHLC, settlement, volume, open_interest
bars = quote_client.get_future_bars(['ES2306'], period=BarPeriod.DAY)

# get_future_bars_by_page(identifier, period, total, page_size)
# Paginated with configurable time intervals between requests
bars = quote_client.get_future_bars_by_page('ES2306', period=BarPeriod.ONE_MINUTE)
```

---

## 10. Quote API - Options

```python
# get_option_expirations(symbol) - expiration dates
expirations = quote_client.get_option_expirations('AAPL')
# Columns: symbol, date (YYYY-MM-DD), timestamp (ms), period_tag (m=monthly, w=weekly)

# get_option_briefs(identifiers) - real-time quotes with Greeks
# Supports US and HK markets
briefs = quote_client.get_option_briefs(['AAPL 20240119 155.0 PUT'])

# get_option_chain(symbol, expiry, option_filter=None)
# Supports filtering by Greeks (delta, gamma, theta, vega, rho), IV, open interest, ITM status
chain = quote_client.get_option_chain('AAPL', '2024-01-19')

# get_option_depth(identifiers) - multi-level bid/ask with exchange code
depth = quote_client.get_option_depth(['AAPL 20240119 155.0 PUT'])

# get_option_trade_ticks(identifiers) - tick data
ticks = quote_client.get_option_trade_ticks(['AAPL 20240119 155.0 PUT'])

# get_option_bars(identifiers, period, begin_time, end_time) - K-line
# Periods: day, 1h, 5min, 30min, 1min. Includes OHLCV + open_interest
bars = quote_client.get_option_bars(['AAPL 20240119 155.0 PUT'], period=BarPeriod.DAY)

# get_option_timeline(identifiers) - HK options only
timeline = quote_client.get_option_timeline(['TCH 20240228 300.0 CALL'])

# get_option_symbols(market) - HK option codes with underlying stock mappings
symbols = quote_client.get_option_symbols(Market.HK)

# get_option_analysis(symbol, market) - analytical metrics
# IV, HV, IV/HV ratio, call/put ratio, IV percentile, IV rank across multiple time horizons
analysis = quote_client.get_option_analysis('AAPL')
```

**Option identifier format**: `"AAPL 230317C000135000"` or `"AAPL 20240119 155.0 PUT"`

---

## 11. Quote API - Warrants & CBBC

### Warrant Filter (Advanced Search)

```python
from tigeropen.quote.request.model import WarrantFilterParams

params = WarrantFilterParams()
params.set_issuer_name('name')
params.set_expire_ym('2024-06')          # yyyy-MM format
params.set_state(1)                       # 0=all, 1=normal, 2=terminated, 3=pending
params.add_warrant_type(2)                # 1=call, 2=put, 3=bull, 4=bear
params.add_in_out_price(1)                # 1=in-the-money, -1=out
params.add_lot_size(10000)                # shares per lot
params.set_premium_range(0, 1)            # premium % range
params.set_strike_range(100, 200)
params.set_leverage_ratio_range(5, 20)
params.set_effective_leverage_range(3, 15)
params.set_call_price_range(100, 200)     # recall price (bull/bear only)
params.set_implied_volatility_range(0.1, 0.5)

result = quote_client.get_warrant_filter(
    symbol='00700',                       # underlying asset
    page=0, page_size=50,
    sort_field_name='expireDate',         # default sort field
    sort_dir=SortDirection.ASC,
    filter_params=params
)
# Returns WarrantFilterItem:
#   .page, .total_page, .total_count
#   .bounds (WarrantFilterBounds) - available filter options
#   .items (DataFrame)
```

**Items DataFrame columns**: symbol, name, type, sec_type, market, entitlement_ratio, entitlement_price, premium, breakeven_point, call_price, before_call_level, expire_date, last_trading_date, state, change_rate, change, latest_price, volume, outstanding_ratio, lot_size, strike, in_out_price, delta, leverage_ratio, effective_leverage, implied_volatility

### Warrant Briefs

```python
# get_warrant_briefs(symbols) - max 50, real-time quotes
briefs = quote_client.get_warrant_briefs(['15792', '58603'])
```

**DataFrame columns**: symbol, name, exchange, market, sec_type (WAR/IOPT), currency, expiry, strike, right (put/call), multiplier, last_trading_date, entitlement_ratio, entitlement_price, min_tick, listing_date, call_price, halted (Normal/Halted), underlying_symbol, timestamp, latest_price, pre_close, open, high, low, volume, amount, premium, outstanding_ratio, implied_volatility, in_out_price, delta, leverage_ratio, breakeven_point

**Contract Types**: WAR (warrants), IOPT (bull/bear certificates)

---

## 12. Quote API - Crypto

```python
# get_symbols(sec_type=SecurityType.CC) - all crypto symbols
symbols = quote_client.get_symbols(sec_type=SecurityType.CC)
# e.g., ['BTC.USD', 'ETH.USD', 'SOL.USD', 'DOGE.USD', ...]

# get_cc_briefs(symbols, sec_type=SecurityType.CC, lang) - real-time quotes, max 50
briefs = quote_client.get_cc_briefs(['BTC', 'ETH'], sec_type=SecurityType.CC)
# Columns: symbol, pre_close, latest_price, latest_time (ms), volume_decimal,
#           open, high, low, change, changeRate

# get_bars(symbols, sec_type=SecurityType.CC, period, begin_time, end_time, limit=251)
# Max limit 1200
# Minute data: BTC from 2024-03-27; Daily: from 2010-07-13
bars = quote_client.get_bars(['ETH'], sec_type=SecurityType.CC, period=BarPeriod.DAY)
# Columns: time (ms), open, close, high, low, volume_decimal

# get_timeline(symbols, sec_type=SecurityType.CC, begin_time) - max 10 symbols
timeline = quote_client.get_timeline(['ETH'], sec_type=SecurityType.CC)
# Columns: symbol, time (ms), price, avg_price, volume_decimal
```

---

## 13. Quote API - Funds

```python
# get_fund_symbols() - all fund codes
symbols = quote_client.get_fund_symbols()
# e.g., ["IE00B11XZ988.USD", "LU0790902711.USD"]

# get_fund_contracts(symbols) - contract info
contracts = quote_client.get_fund_contracts(['IE00B11XZ988.USD'])
# Columns: symbol, name, company_name, market, sec_type, currency, tradeable,
#           sub_type, dividend_type, tiger_vault

# get_fund_quote(symbols) - latest NAV, max 500
quote = quote_client.get_fund_quote(['IE00B11XZ988.USD'])
# Columns: symbol, close (NAV), timestamp (ms)

# get_fund_history_quote(symbols, begin_time, end_time, limit) - historical NAV, max 500
# begin_time/end_time: millisecond timestamps
history = quote_client.get_fund_history_quote(['IE00B11XZ988.USD'], begin_time=1700000000000)
# Columns: symbol, nav, time (ms)
```

---

## 14. Stock Screener

```python
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Market
from tigeropen.quote.domain.filter import StockFilter, SortFilterData
from tigeropen.common.consts.filter_fields import (
    StockField, AccumulateField, FinancialField, MultiTagField, AccumulatePeriod
)

# market_scanner(market, filters, sort_field_data, page=0, page_size=100, cursor_id=None)
# Markets: US, SG, HK
# page_size max 200
# Use cursor_id for pagination (NOT page, which is deprecated)

# Basic filter (StockField)
base_filter = StockFilter(StockField.DivideRate, filter_min=0.05)

# Financial filter (FinancialField) - LTM basis only
fin_filter = StockFilter(FinancialField.TotalRevenues3YrCagr, filter_min=0.1)

# Accumulate filter (AccumulateField) - requires accumulate_period
acc_filter = StockFilter(AccumulateField.ChangeRate,
                         accumulate_period=AccumulatePeriod.FIVE_DAYS,
                         filter_min=0.05)

# Multi-tag filter (MultiTagField) - requires tag_list
tag_filter = StockFilter(MultiTagField.IndustryGics, tag_list=[45, 35])

result = quote_client.market_scanner(
    market=Market.US,
    filters=[base_filter, fin_filter],
    sort_field_data=SortFilterData(StockField.MarketValue, SortDirection.DESC),
    page_size=100,
    cursor_id=None
)
# Returns ScannerResult:
#   .page, .total_page, .total_count, .page_size
#   .cursor_id (use for next page; None if last)
#   .items: List[ScannerResultItem] - .symbol, .market, .field_data (dict)
#   .symbols: List[str]
```

### StockFilter Parameters

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `field` | FilterField enum | Yes | StockField/AccumulateField/FinancialField/MultiTagField |
| `filter_min` | float | No | Lower bound (closed interval) |
| `filter_max` | float | No | Upper bound (closed interval) |
| `is_no_filter` | bool | No | Disable filter if True |
| `accumulate_period` | AccumulatePeriod | Conditional | Required for AccumulateField |
| `financial_period` | FinancialPeriod | Conditional | Required for FinancialField |
| `tag_list` | list | Conditional | Required for MultiTagField |

### Filter Categories
- **StockField**: 57 indicators (price, volume, market_cap, PE, turnover_rate, etc.)
- **AccumulateField**: 27 cumulative indicators (YoY growth, ROE, margins) with period ranges (5-min to 5-year, earnings reports)
- **FinancialField**: 68 financial metrics (gross_margin, net_margin, debt_ratios, ROA) -- LTM basis only
- **MultiTagField**: 18 categorical filters (industry, concepts, 52-week highs, OTC, options, ETF type, stock classification)

```python
# Get available tag values for filtering
tags = quote_client.get_market_scanner_tags(market=Market.US, tag_fields=[MultiTagField.IndustryGics])
# Returns: list with market, multi_tag_field, tag_list
```

---

## 15. Contract Management

### Remote Contract Retrieval

```python
from tigeropen.trade.trade_client import TradeClient

trade_client = TradeClient(client_config)

# get_contract(symbol, sec_type=STK, currency, exchange, expiry, strike, put_call)
contract = trade_client.get_contract('AAPL', sec_type=SecurityType.STK, currency='USD')

# get_contracts(symbols, sec_type=STK, currency, exchange) -- max 50
contracts = trade_client.get_contracts(['AAPL', 'GOOGL'])

# get_derivative_contracts(symbol, sec_type, expiry, lang)
# sec_type: OPT/WAR/IOPT, expiry: yyyyMMdd, lang: zh_CN/zh_TW/en_US
derivatives = trade_client.get_derivative_contracts('AAPL', SecurityType.OPT, '20240119')
```

### Local Contract Construction (No API call needed)

```python
from tigeropen.common.util.contract_utils import (
    stock_contract, option_contract_by_symbol, future_contract
)

# Stock
contract = stock_contract(symbol='AAPL', currency='USD')

# Option
contract = option_contract_by_symbol('AAPL', '20240119', strike=155.0,
                                      put_call='PUT', currency='USD')

# Future
contract = future_contract(symbol='ES2306', currency='USD')

# Also available: warrant_contract, fund contracts, crypto contracts
```

### Contract Object Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `identifier` | str | Unique ID (21-char OCC format for options) |
| `symbol` | str | Asset code |
| `sec_type` | str | STK/OPT/FUT/WAR/IOPT |
| `name` | str | Contract name |
| `currency` | str | USD/HKD/CNH |
| `expiry` | str | Expiration date (derivatives) |
| `strike` | float | Strike price (options) |
| `put_call` | str | CALL/PUT |
| `multiplier` | float | Quantity per contract |
| `shortable` | bool | Short-sell availability |
| `short_initial_margin` | float | Short margin ratio |
| `long_initial_margin` | float | Long margin ratio |
| `market` | str | US/HK/CN |
| `min_tick` | float | Minimum price increment |
| `tickSizes` | array | Price range tiers |
| `status` | str | Trading status (0/1) |
| `support_overnight_trading` | bool | Night market support |
| `support_fractional_share` | bool | Fractional share support |

Most contracts require 4 basic properties: symbol, security type, currency, exchange. Options/futures need additional identifiers (expiry, strike, put_call/exchange).

---

## 16. Order Placement

### Core Method
```python
order_id = trade_client.place_order(order)
# Returns order ID; confirms receipt only (execution is ASYNC)
```

### Order Utility Functions

```python
from tigeropen.common.util.order_utils import (
    market_order, limit_order, stop_order, stop_limit_order, trail_order, algo_order
)

# Market Order (MKT)
order = market_order(account=client_config.account,
                     contract=contract,
                     action='BUY',       # BUY or SELL
                     quantity=100)
# NOTE: Not available in pre/post-market hours

# Limit Order (LMT)
order = limit_order(account=client_config.account,
                    contract=contract,
                    action='BUY',
                    quantity=100,
                    limit_price=150.0,
                    time_in_force='DAY')  # DAY, GTC, GTD, OPG, IOC, FOK

# Stop Order (STP) - triggers market order at stop price
order = stop_order(account=client_config.account,
                   contract=contract,
                   action='SELL',
                   quantity=100,
                   aux_price=145.0)

# Stop-Limit Order (STP_LMT) - triggers limit order at stop price
order = stop_limit_order(account=client_config.account,
                         contract=contract,
                         action='SELL',
                         quantity=100,
                         limit_price=144.0,
                         aux_price=145.0)

# Trailing Stop Order (TRAIL)
order = trail_order(account=client_config.account,
                    contract=contract,
                    action='SELL',
                    quantity=100,
                    trailing_percent=5.0)   # percentage-based
# OR: aux_price for fixed amount trailing

# Algorithm Order (TWAP/VWAP)
order = algo_order(account=client_config.account,
                   contract=contract,
                   action='BUY',
                   quantity=1000,
                   algo_type='TWAP',        # TWAP or VWAP
                   start_time=...,          # millisecond timestamp
                   end_time=...,
                   limit_price=None)
```

### Order Types

| Type | Code | Description |
|------|------|-------------|
| Market | MKT | Immediate at market price |
| Limit | LMT | At specified price or better |
| Stop | STP | Triggers market order at stop price |
| Stop-Limit | STP_LMT | Triggers limit order at stop price |
| Trailing Stop | TRAIL | Dynamic stop following price |
| Auction Market | AM | HK auction session |
| Auction Limit | AL | HK auction session |

### time_in_force Values

| Value | Description |
|-------|-------------|
| `DAY` | Valid for current session (default) |
| `GTC` | Good-til-cancelled |
| `GTD` | Good-til-date |
| `OPG` | Opening price order |
| `IOC` | Immediate or cancel |
| `FOK` | Fill or kill |

### Advanced Order Types

- **Attached Orders**: Take-profit (PROFIT) and stop-loss (LOSS) on primary positions
- **Bracket Orders (BRACKETS)**: Primary order + profit-taking + loss-mitigation sub-orders
- **OCA Orders**: One-Cancels-All -- execution of one cancels remaining legs
- **Algorithm Orders**: TWAP/VWAP via AlgoParams
- **Forex Orders**: `trade_client.place_forex_order()` for currency exchange between segments

### Market/Product Order Support

| Market | Product | Supported Order Types |
|--------|---------|----------------------|
| US | Stocks/ETF | LMT, MKT, STP, STP_LMT, TRAIL, Brackets, TWAP/VWAP |
| US | Options | LMT, MKT, STP_LMT, Brackets |
| US | Futures | LMT, MKT, STP_LMT, STP, Brackets |
| HK | Stocks/ETF | LMT, MKT, STP, STP_LMT, TRAIL, Brackets, AM, AL |
| HK | Options | LMT, MKT, STP_LMT, STP |
| HK | Warrants/CBBC | LMT, STP_LMT, Brackets |
| SG/AU | Stocks/ETF | LMT, MKT, STP, STP_LMT, TRAIL, Brackets |

### Preview Order
```python
preview = trade_client.preview_order(order)
# Returns: is_pass (bool), init_margin, maint_margin, commission, gst,
#          available_ee, excess_liquidity, message (error if rejected)
```

---

## 17. Order Modification & Cancellation

### Cancel Order
```python
# cancel_order(account=None, id=None, order_id=None)
# Only HELD (submitted) or PARTIALLY_FILLED orders can be cancelled
# Completed or rejected orders CANNOT be cancelled
# Async: returns True for request sent; verify via get_order()
trade_client.cancel_order(id=26731241425469440)
```

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `account` | str | No | Defaults to client_config |
| `id` | int | Yes (recommended) | Global order ID via Order.id |
| `order_id` | int | No | Local order ID via Order.order_id |

### Modify Order
```python
# modify_order(order, quantity, limit_price, aux_price, trail_stop_price,
#              trailing_percent, percent_offset, time_in_force, outside_rth)
# Order type CANNOT be modified
order = trade_client.get_order(id=26731241425469440)
trade_client.modify_order(order, quantity=200, limit_price=155.0)
```

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `order` | Order | Yes | Original order object (must contain id) |
| `quantity` | int | No | New share count |
| `limit_price` | float | No | Required for LMT/STP/STP_LMT |
| `aux_price` | float | No | Stop trigger price (STP/STP_LMT) or trailing amount |
| `trail_stop_price` | float | No | For TRAIL orders |
| `trailing_percent` | float | No | For TRAIL (mutually exclusive with aux_price) |
| `time_in_force` | str | No | DAY or GTC |
| `outside_rth` | bool | No | Pre/post-market (US only) |

---

## 18. Order Query

### Get Orders (all statuses)
```python
# get_orders(account, sec_type, market, symbol, start_time, end_time,
#            limit=100, is_brief, states, sort_by, seg_type, page_token)
# limit max 300
# start_time/end_time: ms timestamps or date strings ('2019-01-01')
# sort_by: LATEST_CREATED or LATEST_STATUS_UPDATED
orders = trade_client.get_orders(limit=100, start_time='2024-01-01', end_time='2024-06-01')
# Returns: List[Order] or OrdersResponse (with next_page_token)
```

### Specific Order Queries
```python
# get_order(account, id, order_id, is_brief, show_charges)
order = trade_client.get_order(id=26731241425469440)

# get_open_orders(account, sec_type, market, symbol, start_time, end_time,
#                 parent_id, sort_by, seg_type)
# May include partially filled orders
open_orders = trade_client.get_open_orders()

# get_cancelled_orders(...) - includes system-cancelled and expired
cancelled = trade_client.get_cancelled_orders()

# get_filled_orders(account, sec_type, market, symbol, start_time, end_time, sort_by, seg_type)
# BOTH start_time AND end_time are MANDATORY, max 90-day interval
filled = trade_client.get_filled_orders(start_time='2024-01-01', end_time='2024-03-01')
```

### Transaction Details
```python
# get_transactions(account, order_id, symbol, sec_type, start_time, end_time,
#                  limit=100, expiry, strike, put_call)
# Requires either order_id OR both symbol+sec_type
# Comprehensive/simulation accounts only
# since_date/to_date: format "20250101" (SDK v3.5.0+)
transactions = trade_client.get_transactions(symbol='AAPL', sec_type=SecurityType.STK,
                                              start_time='2024-01-01', end_time='2024-06-01')
# Returns: List[Transaction] or TransactionsResponse
```

### Order Object Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Global order identifier |
| `order_id` | int | Local order ID |
| `account` | str | Account |
| `contract` | Contract | Contract specifications |
| `action` | str | BUY or SELL |
| `order_type` | OrderType | MKT/LMT/STP/STP_LMT/TRAIL |
| `quantity` | int | Order size |
| `filled` | int | Executed quantity |
| `remaining` | int | Unfilled quantity |
| `avg_fill_price` | float | Average execution price |
| `limit_price` | float | Limit price |
| `aux_price` | float | Trigger price |
| `status` | OrderStatus | Order state |
| `time_in_force` | str | DAY/GTC/GTD |
| `order_time` | int | Submission timestamp (ms) |
| `trade_time` | int | Status update timestamp |
| `create_time` | int | Creation timestamp (ms) |
| `update_time` | int | Update timestamp (ms) |
| `commission` | float | Estimated/actual fees |
| `realized_pnl` | float | Realized P&L |
| `reason` | str | Status-change rationale |

---

## 19. Account Management

### Account Profile
```python
# get_managed_accounts(account=None) - linked accounts
# Institutional: returns primary + all sub-accounts
accounts = trade_client.get_managed_accounts()
# Returns: List[AccountProfile]
# AccountProfile: account, capability (CASH/RegTMargin/PMGRN),
#                 status (Funded/Open/Pending/Rejected/Closed),
#                 account_type (GLOBAL/STANDARD/PAPER)
```

### Asset Queries
```python
# For Standard/Paper accounts:
# get_prime_assets(account, base_currency, consolidated=True)
assets = trade_client.get_prime_assets()
# Returns: List[PortfolioAccount] with segments dict:
#   'S' (securities), 'C' (commodities), 'F' (funds), 'D' (digital currency)
# Each segment has currency-specific CurrencyAsset with cash balance, buying power, margins

# For Global accounts:
# get_assets(account, sub_accounts, segment=False, market_value=False)
assets = trade_client.get_assets(market_value=True)
# Returns: PortfolioAccount with summary, segments by sec_type,
#          market_value dict by currency (USD/HKD/CNH)
```

### Position Queries
```python
# get_positions(account, sec_type, currency, market, symbol, sub_accounts,
#               expiry, strike, put_call)
positions = trade_client.get_positions(sec_type=SecurityType.STK, market=Market.US)
# Returns: List[Position]
# Position: contract, quantity, average_cost, market_price,
#           realized_pnl, unrealized_pnl, salable_quantity
```

### Analytics
```python
# get_analytics_asset(account, start_date, end_date, seg_type, currency, sub_account)
analytics = trade_client.get_analytics_asset(start_date='2024-01-01', end_date='2024-06-01')
# Returns dict: 'summary' (pnl, pnl_percentage, annualized_return),
#               'history' (daily records: asset values, deposits/withdrawals)
```

### Segment Fund Transfers (Composite/Paper)
```python
# get_segment_fund_available(from_segment, currency) - check transferable amount
available = trade_client.get_segment_fund_available(from_segment='SEC', currency='USD')
# Returns: List[SegmentFundAvailableItem] with from_segment, currency, available

# transfer_segment_fund(from_segment, to_segment, amount, currency) - execute transfer
result = trade_client.transfer_segment_fund(from_segment='SEC', to_segment='FUT',
                                             amount=10000, currency='USD')
# Returns: SegmentFundItem with status (NEW/PROC/SUCC/FAIL/CANC), timestamps, ID

# cancel_segment_fund(id) - cancel pending transfer
trade_client.cancel_segment_fund(id=transfer_id)

# get_segment_fund_history(limit) - transfer history, max 500
history = trade_client.get_segment_fund_history(limit=100)
```

### Financial History
```python
# get_funding_history(seg_type) - deposit/withdrawal records
funding = trade_client.get_funding_history(seg_type='SEC')
# Returns DataFrame: type, currency, amount, business_date, status

# get_fund_details(seg_types, account, fund_type, currency, start, limit, start_date, end_date)
# limit: 50-100
details = trade_client.get_fund_details(seg_types=['SEC'])
# Returns DataFrame: transaction_id, description, type (trade/fee/corporate_action), amount, timestamps
```

### Tradable Quantity Estimate
```python
# get_estimate_tradable_quantity(order, seg_type)
estimate = trade_client.get_estimate_tradable_quantity(order)
# Returns: TradableQuantityItem with cash_tradable, financing_capacity,
#          current_holdings, tradable_position
```

---

## 20. Push Subscriptions - Market Data

### Connection Setup
```python
from tigeropen.push.push_client import PushClient

protocol, host, port = client_config.socket_host_port
push_client = PushClient(host, port, use_ssl=(protocol == 'ssl'))
push_client.connect(client_config.tiger_id, client_config.private_key)
```

### Stock Quote Subscription
```python
push_client.subscribe_quote(['AAPL', 'GOOGL'])
push_client.unsubscribe_quote(['AAPL'])

# Callbacks:
push_client.quote_changed = lambda data: print(data)      # QuoteBasicData
push_client.quote_bbo_changed = lambda data: print(data)   # QuoteBBOData
```

### Options Subscription
```python
push_client.subscribe_option(['AAPL 20240119 155.0 PUT', 'SPY 20221118 386.0 CALL'])
# Uses same callbacks as stock quotes
```

### Futures Subscription
```python
push_client.subscribe_future(['CLmain', 'ES2209', 'BTCmain'])
```

### Cryptocurrency Subscription
```python
push_client.subscribe_cc(['BTC', 'ETH.USD'])
push_client.unsubscribe_cc(['BTC'])
```

### Depth Quote Subscription
```python
push_client.subscribe_depth_quote(['AAPL'])
push_client.unsubscribe_depth_quote(['AAPL'])
push_client.quote_depth_changed = lambda data: print(data)  # QuoteDepthData
```
- US depth push frequency: **300ms**
- HK depth push frequency: **2s**
- Max **40 levels** bid/ask
- OrderBook structure: `price[]`, `volume[]`, `orderCount[]`, `exchange`, `time`

### Trade Tick Subscription
```python
push_client.subscribe_tick(['AAPL'])
push_client.unsubscribe_tick(['AAPL'])
push_client.tick_changed = lambda data: print(data)  # TradeTick
```
- Push frequency: **200ms** (snapshot mode, 50 most recent records per push)
- Full tick mode: `client_config.use_full_tick = True`, callback: `push_client.full_tick_changed`

### K-line Subscription
```python
push_client.subscribe_kline(['AAPL'])
push_client.unsubscribe_kline(['AAPL'])
push_client.kline_changed = lambda data: print(data)
# Fields: time, open, high, low, close, avg, volume, count, amount, serverTimestamp
```

### Stock Rankings Subscription
```python
push_client.subscribe_stock_top(market=Market.US,
                                 indicators=['changeRate', 'volume', 'amount'])
push_client.unsubscribe_stock_top()
push_client.stock_top_changed = lambda data: print(data)
```
- Push interval: **30s**, Top **30** per indicator
- Indicators: changeRate, changeRate5Min, turnoverRate, amount, volume, amplitude

### Options Rankings Subscription
```python
push_client.subscribe_option_top(market=Market.US,
                                  indicators=['volume', 'amount'])
push_client.unsubscribe_option_top()
push_client.option_top_changed = lambda data: print(data)
```
- Push interval: **30s**, Top **50** per indicator
- Indicators: bigOrder, volume, amount, openInt

### Query Subscribed Symbols
```python
push_client.query_subscribed_quote()
push_client.query_subscribed_callback = lambda data: print(data)
# Returns: limit, used, subscribedSymbols, askBidLimit, askBidUsed,
#          subscribedAskBidSymbols, tradeTickLimit, tradeTickUsed, subscribedTradeTickSymbols
```

### Important Limitations
- **Cannot subscribe** to HK or US stock indices
- `push_client.disconnect()` cancels **ALL** active subscriptions
- No rank data during non-trading hours

---

## 21. Push Subscriptions - Account Events

### Asset Changes
```python
push_client.subscribe_asset(account=client_config.account)
push_client.unsubscribe_asset()
push_client.asset_changed = lambda frame: print(frame)
```
Fields: account, currency, segType, availableFunds, excessLiquidity, netLiquidation, equityWithLoan, buyingPower, cashBalance, grossPositionValue, initMarginReq, maintMarginReq, timestamp

### Position Changes
```python
push_client.subscribe_position(account=client_config.account)
push_client.unsubscribe_position()
push_client.position_changed = lambda frame: print(frame)
```
Fields: symbol, identifier, market, currency, position (qty), averageCost, latestPrice, marketValue, unrealizedPnl, timestamp

### Order Changes
```python
push_client.subscribe_order(account=client_config.account)
push_client.unsubscribe_order()
push_client.order_changed = lambda frame: print(frame)
```
Fields: id, symbol, identifier, action (BUY/SELL), totalQuantity, filledQuantity, limitPrice, stopPrice, avgFillPrice, status, replaceStatus, cancelStatus, orderType (MKT/LMT/STP/STP_LMT/TRAIL), timeInForce (DAY/GTC/GTD)

### Transaction Details
```python
push_client.subscribe_transaction(account=client_config.account)
push_client.unsubscribe_transaction()
push_client.transaction_changed = lambda frame: print(frame)
```
Fields: id (execution ID), orderId, symbol, identifier, multiplier, filledPrice, filledQuantity, createTime, transactTime, updateTime

### Important Notes
- Omitting account subscribes to **ALL** linked accounts -- always check `account` field in callbacks
- Data uses Protocol Buffer objects (e.g., `AssetData_pb2.AssetData`)

### Alternative: HTTP Webhook
- Configure callback domain (must be domain, not IP:port) at developer platform
- Supported types: OrderStatus, Asset, Position, Quote, QuoteDepth
- Signature verification via RSA (same as API requests)

---

## 22. Enums & Constants

### Market
```python
from tigeropen.common.consts import Market
Market.ALL  Market.US  Market.HK  Market.CN  Market.SG  Market.AU  Market.NZ
```

### SecurityType
```python
from tigeropen.common.consts import SecurityType
SecurityType.STK   # Stock
SecurityType.OPT   # US stock options
SecurityType.WAR   # HK warrants
SecurityType.IOPT  # HK bull/bear certificates
SecurityType.CASH  # Forex
SecurityType.FUT   # Futures
SecurityType.FOP   # Futures options
SecurityType.FUND  # Funds
SecurityType.CC    # Crypto
```

### Currency
```python
from tigeropen.common.consts import Currency
Currency.ALL  Currency.USD  Currency.HKD  Currency.CNH  Currency.SGD
Currency.AUD  Currency.JPY  Currency.EUR  Currency.GBP  Currency.CAD  Currency.NZD
```

### Language
```python
from tigeropen.common.consts import Language
Language.zh_CN  Language.zh_TW  Language.en_US
```

### BarPeriod
```python
from tigeropen.common.consts import BarPeriod
# Minutes
BarPeriod.ONE_MINUTE     BarPeriod.THREE_MINUTES    BarPeriod.FIVE_MINUTES
BarPeriod.TEN_MINUTES    BarPeriod.FIFTEEN_MINUTES  BarPeriod.HALF_HOUR
BarPeriod.FORTY_FIVE_MINUTES  BarPeriod.ONE_HOUR
BarPeriod.TWO_HOURS      BarPeriod.THREE_HOURS      BarPeriod.FOUR_HOURS
BarPeriod.SIX_HOURS
# Daily+
BarPeriod.DAY  BarPeriod.WEEK  BarPeriod.MONTH  BarPeriod.YEAR
```

### QuoteRight
```python
from tigeropen.common.consts import QuoteRight
QuoteRight.BR   # Front-adjusted (default)
QuoteRight.NR   # No adjustment
QuoteRight.FR   # Back-adjusted
```

### CapitalPeriod
```python
CapitalPeriod.INTRADAY  CapitalPeriod.DAY  CapitalPeriod.WEEK  CapitalPeriod.MONTH
CapitalPeriod.YEAR  CapitalPeriod.QUARTER  CapitalPeriod.HALFAYEAR
```

### OrderType
```python
from tigeropen.common.consts import OrderType
OrderType.MKT  OrderType.LMT  OrderType.STP  OrderType.STP_LMT  OrderType.TRAIL
OrderType.AM   OrderType.AL    # HK auction
# Attached: PROFIT, LOSS, BRACKETS
```

### OrderStatus
```python
from tigeropen.common.consts import OrderStatus
OrderStatus.EXPIRED           # -2 (Invalid)
OrderStatus.NEW               # -1 (Initial)
OrderStatus.PARTIALLY_FILLED  # 2/5/8
OrderStatus.CANCELLED         # 4
OrderStatus.HELD              # 5 (Submitted)
OrderStatus.FILLED            # 6
OrderStatus.REJECTED          # 7 (Inactive)
```

### Order Modification Status
```python
# NONE - Default/terminated
# RECEIVED - Accepted (pretrade check passed)
# REPLACED - Successful (confirmed)
# FAILED - Rejected
```

### Order Cancellation Status
```python
# NONE - Default/terminated
# RECEIVED - Accepted (pretrade check passed)
# FAILED - Rejected
```

### Trading Session
```python
# RTH - Regular trading hours
# PRE_RTH_POST - Pre/regular/post hours
# OVERNIGHT - Overnight trading
# FULL - Full-time
# HK_AUC - HK auction session
# HK_CTS - HK continuous session
# HK_AUC_CTS - HK combined sessions
```

### Account Types & Segments
```python
# Account capability: CASH, RegTMargin, PMGRN
# Account status: New, Funded, Open, Pending, Abandoned, Rejected, Closed, Unknown
# Segment types: ALL, SEC (Securities), FUT (Futures), FUND (Funds)
```

### AssetQuoteType
```python
# ETH - Pre/regular/post hours (uses T-1 close for overnight)
# RTH - Regular hours only
# OVERNIGHT - Overnight sessions only
```

### Sort Direction
```python
SortDirection.NO  SortDirection.ASC  SortDirection.DESC
```

### Options Exchange Codes
```python
# AMEX, BOX, CBOE, EMLD, EDGX, GEM, ISE, MCRY, MIAX, ARCA, MPRL, NSDQ, BX, C2, PHLX, BZX
```

### Stock Screener Field Counts
- **StockField**: 57 basic indicators
- **AccumulateField**: 27 cumulative indicators
- **FinancialField**: 68 financial metrics (LTM basis)
- **MultiTagField**: 18 categorical filters

---

## 23. Error Codes

### Success & General

| Code | Message | Description |
|------|---------|-------------|
| 0 | success | Request completed |
| 1 | server error | Internal error or bad parameters |
| 2 | network read time out | Network issues; consider deploying closer |
| 4 | access forbidden | IP whitelist mismatch, blacklisting, signature failure, subscription limit exceeded, missing credentials |
| 5 | rate limit error | HTTP 429, request frequency exceeded |

### Parameter Errors

| Code | Message | Description |
|------|---------|-------------|
| 1000 | common param error | Unsupported method, incorrect URL, non-JSON, invalid timestamp/signature, empty params, device ID issues |
| 1010 | biz param error | Market support limitations, bad pagination token, malformed option IDs, symbol count violations |

### Trading Errors

| Code | Description | Common messages |
|------|-------------|-----------------|
| 1100 | Global account errors | Duplicate orders, blocked trading |
| 1200 | Integrated account errors | Timing restrictions, pre/after-hours limits, insufficient position, unsupported securities |
| 1300 | Paper account errors | Mirrors integrated account issues |

### Market Data Errors

| Code | Description |
|------|-------------|
| 2100 | Stock market data errors |
| 2200 | Option market data errors |
| 2300 | Futures market data errors |
| 2400 | Cryptocurrency market data errors |

### Subscription Errors

| Code | Description |
|------|-------------|
| 3xxx | Invalid tiger ID, service issues, unsupported subscription types |

### Permission Errors

| Code | Message | Description |
|------|---------|-------------|
| 4000 | permission denied | Insufficient access, timeframe restrictions, device limitations |
| 4001 | kick out by new connection | WebSocket replaced by newer session |

### Common Error Scenarios

| Error | Cause | Fix |
|-------|-------|-----|
| "Orders cannot be placed at this moment" | Account not verified or non-trading hours | Complete verification in APP; check hours |
| "Cannot place market or stop orders during pre/after-market" | MKT/STP not supported outside regular hours | Use LMT orders |
| "Order quantity exceeds available position" | Selling more than held | Query positions first |
| "We don't support trading of this stock now" | Invalid or untradeable symbol | Verify via APP or quote API |

---

## 24. Best Practices & Gotchas

### Client Management
1. **Create QuoteClient ONCE at module level** -- do NOT instantiate repeatedly (triggers rate limiting)
2. QuoteClient auto-claims permissions with `is_grab_permission=True` (default since SDK 2.0.9+)
3. `grab_quote_permission()` needed when switching between devices

### Rate Limiting
4. Rate limits are per **tigerId + method** -- different endpoints have independent counters
5. **Persistent excessive traffic leads to automatic blacklisting** (all API calls blocked permanently)
6. Batch stock requests: use 50 symbols per call with 0.5-second delays between batches
7. Use **push subscriptions** instead of polling to avoid hitting rate limits

### Order Management
8. `place_order()` returns order ID confirming receipt only -- execution is **async**
9. Order type **cannot be modified** after submission
10. Only HELD/PARTIALLY_FILLED orders can be cancelled (completed/rejected cannot)
11. `get_filled_orders()` requires BOTH start_time AND end_time (max 90-day range)
12. `get_transactions()` requires either order_id OR both symbol+sec_type
13. US pre/post-market does NOT support market orders or stop orders -- use limit orders
14. Monitor order execution by checking every 10 seconds, modify price at 50% mark if unfilled

### Market Data
15. API market data operates **independently from APP** -- requires separate purchase
16. K-line first request consumes quota; same symbol within 30 days doesn't re-consume
17. 1/5-minute K-lines: ~1 month history; 15/30/60-min: ~1 year
18. `get_stock_delay_briefs()` is FREE but US stocks only (~15min delay)
19. Cannot subscribe to HK or US stock **indices** via push
20. Depth quote push: US 300ms, HK 2s frequency
21. Trade tick push: 200ms snapshot, 50 most recent records per push

### Push/WebSocket
22. `push_client.disconnect()` cancels ALL active subscriptions
23. When subscribing without account parameter, callbacks receive multi-account data -- always check `account` field
24. Data uses Protocol Buffer objects (default since SDK 3.0.0)
25. SDK 3.3.9+ adds `timeInForce` field to order push callbacks

### Authentication
26. Python SDK requires **PKCS#1** private key format (Java uses PKCS#8)
27. Token validity: 30 days (TBHK license) -- enable auto-refresh
28. Private keys cannot be recovered after page refresh -- save immediately

### General Architecture
29. REST API (HTTPS + RSA) for queries; WebSocket (Protocol Buffers) for push
30. All timestamps are milliseconds unless otherwise noted
31. Time parameters accept both millisecond timestamps and date strings ('yyyy-MM-dd' or 'yyyy-MM-dd HH:mm:ss')

---

## 25. MCP Integration

Tiger OpenAPI supports MCP (Model Context Protocol) for AI platform integration.

### Setup
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # install UV package manager
```

### Configuration
```json
{
  "mcpServers": {
    "tigermcp": {
      "command": "uvx",
      "args": ["--python", "3.13", "tigermcp"],
      "env": {
        "TIGEROPEN_TIGER_ID": "your tiger id",
        "TIGEROPEN_PRIVATE_KEY": "your private key",
        "TIGEROPEN_ACCOUNT": "your account id",
        "TIGERMCP_READONLY": true
      }
    }
  }
}
```

- Set `TIGERMCP_READONLY` to `true` for read-only mode (trading disabled), `false` for full access
- Alternative: Use `TIGEROPEN_PROPS_PATH` for config file path
- macOS 12 or earlier may need: `brew install coreutils`

---

## 26. Option Tools (QuantLib)

### Dependencies
```bash
pip install quantlib==1.40
```

### American Option Helper (US/HK/ETF Options)
```python
from tigeropen.examples.option_helpers.helpers import FDAmericanDividendOptionHelper

helper = FDAmericanDividendOptionHelper(
    option_type='CALL',          # CALL or PUT
    underlying_price=200.0,
    strike=210.0,
    risk_free_rate=0.05,
    dividend_rate=0.01,
    volatility=0.25,
    expiry_date='2025-06-20',    # YYYY-MM-DD
    evaluation_date='2025-03-13'
)

price = helper.npv()
delta = helper.delta()
gamma = helper.gamma()
theta = helper.theta()
vega = helper.vega()
rho = helper.rho()
iv = helper.implied_volatility(target_price=12.5)
```

### European Option Helper (Index Options)
```python
from tigeropen.examples.option_helpers.helpers import FDEuropeanDividendOptionHelper

helper = FDEuropeanDividendOptionHelper(
    option_type='PUT',
    underlying_price=4500.0,
    strike=4400.0,
    risk_free_rate=0.05,
    dividend_rate=0.015,
    volatility=0.20,
    expiry_date='2025-06-20',
    evaluation_date='2025-03-13'
)
```

---

## 27. Trading Hours Reference

### US Stocks (Beijing Time)
| Session | Summer | Winter |
|---------|--------|--------|
| Pre-market | 16:00-21:30 | 17:00-22:30 |
| Regular | 21:30-04:00 | 22:30-05:00 |
| After-hours | 04:00-08:00 | 05:00-09:00 |
| Overnight | 08:00-16:00 | 09:00-17:00 |

### US Stocks (Eastern Time)
| Session | Time |
|---------|------|
| Pre-market | 4:00 AM - 9:30 AM |
| Regular | 9:30 AM - 4:00 PM |
| After-hours | 4:00 PM - 8:00 PM |
| Overnight | 8:00 PM - 4:00 AM |

### HK Stocks
| Session | Time |
|---------|------|
| Opening Auction | 9:00-9:22 (phased submission/modification windows) |
| Morning | 9:30-12:00 |
| Afternoon | 13:00-16:00 |
| Closing Auction | 16:01-16:10 (phased restrictions) |

### A-Shares
| Session | Time |
|---------|------|
| Morning | 9:30-11:30 |
| Afternoon | 13:00-15:00 |

Note: A-shares only tradeable when Shanghai, Shenzhen, and Hong Kong markets all open.

---

## 28. Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 3.4.6 | 2025-08-28 | `get_positions` adds `name` and `underlying_contract_name` fields |
| 3.4.5 | 2025-08-22 | Futures depth quotes; QuoteClient overnight support; MCP Server preview |
| 3.4.3 | 2025-07-22 | `time_in_force` in order utils; futures contract new fields; page_token pagination |
| 3.4.1 | 2025-06-26 | Option timeline API; fractional share support indicator; quota timestamps |
| 3.4.0 | 2025-06-16 | Extended minute K-line time ranges |
| 3.3.9 | 2025-06-12 | `timeInForce` in order push callbacks |
| 3.3.8 | 2025-05-29 | Fund details query; order preview |
| 3.3.6 | 2025-04-28 | Broker holding market value query; sandbox config deprecated |
| 3.3.0 | 2024-12-17 | Stock fundamentals (ROE, P/B); WebSocket error callback fix |
| 3.2.5 | 2024-06-19 | Option depth quotes; option symbol list |
| 3.0.0 | 2023-06-08 | WebSocket default: STOMP -> Protocol Buffers |
| 2.4.0 | 2023-06-07 | Options combo orders |

---

### Support Channels
- WeChat: Official enterprise WeChat support
- Telegram: https://t.me/TigerBrokersAPISupport
- Developer portal: https://developer.itigerup.com/profile
- Regional logins: itigerup.com / tigerbrokers.com.sg / tigerbrokers.com.hk

---

*Generated from https://docs.itigerup.com/docs/ (all pages) on 2026-03-14*
*SDK version: tigeropen 3.4.6*
