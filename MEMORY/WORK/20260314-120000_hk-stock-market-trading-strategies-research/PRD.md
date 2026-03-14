---
task: Research HK stock market trading strategies comprehensively
slug: 20260314-120000_hk-stock-market-trading-strategies-research
effort: extended
phase: complete
progress: 18/18
mode: interactive
started: 2026-03-14T12:00:00+08:00
updated: 2026-03-14T12:01:00+08:00
---

## Context

User requests comprehensive research on 6 specific Hong Kong stock market trading strategy domains: market microstructure, Stock Connect flows, warrants/CBBCs, intraday session timing, sector rotation, and AH premium arbitrage. The user has an existing quantitative trading platform with hk_alpha_factors.py and intraday_strategies.py already implemented. Research should be actionable and complementary to existing code.

### Risks
- Warrant/CBBC strategies carry extreme leverage risk and mandatory call risk
- AH premium arbitrage is structurally limited by non-fungibility of share classes
- Stock Connect flow data may have lag that reduces signal alpha
- Sector rotation signals may be too slow for the existing intraday-focused system

## Criteria

- [x] ISC-1: HK market lot size rules documented with current and proposed changes
- [x] ISC-2: HK tick size spread table documented across all price bands
- [x] ISC-3: Trading hours and session structure documented with volatility patterns
- [x] ISC-4: Southbound flow signal mechanics documented with parameters
- [x] ISC-5: Northbound flow characteristics documented as contrasting signal
- [x] ISC-6: Stock Connect flow data sources and access methods identified
- [x] ISC-7: Warrant Greeks and selection criteria documented
- [x] ISC-8: CBBC mandatory call mechanism and Category N vs R explained
- [x] ISC-9: Warrant/CBBC gearing calculation and risk framework documented
- [x] ISC-10: Morning session open strategy with parameters documented
- [x] ISC-11: Lunch break discontinuity effect quantified
- [x] ISC-12: Afternoon session and closing auction strategy documented
- [x] ISC-13: HSI sector composition and rotation patterns documented
- [x] ISC-14: HSTECH constituent dynamics and rebalancing impact documented
- [x] ISC-15: Sector momentum signals with lookback parameters specified
- [x] ISC-16: AH premium calculation methodology documented
- [x] ISC-17: AH premium mean-reversion trading rules specified
- [x] ISC-18: AH premium structural constraints and risks documented

## Decisions

## Verification

All 18 ISC criteria verified. Research document covers all 6 domains with actionable parameters, mathematical formulas, and integration guidance for existing codebase. Key finding: AH premium parameters in hk_alpha_factors.py need recalibration from 0.35 to 0.10 mean premium.
