---
task: Research retail quant trading frequency viability analysis
slug: 20260314-120000_retail-quant-frequency-research
effort: extended
phase: complete
progress: 16/16
mode: interactive
started: 2026-03-14T12:00:00+08:00
updated: 2026-03-14T12:05:00+08:00
---

## Context

Research the practical reality of trading frequency selection for retail quant traders using broker APIs (Tiger Brokers, Interactive Brokers). The user is building a quant trading platform and needs evidence-based guidance on what frequency bands are viable, what costs look like, and what strategies actually work at retail scale.

### Risks
- Survivorship bias in "successful retail quant" examples
- Backtest-to-live decay making theoretical strategies look better than reality
- Broker-specific constraints may change without notice

## Criteria

- [x] ISC-1: Retail API latency ranges documented with specific numbers
- [x] ISC-2: Co-located HFT latency ranges documented for comparison
- [x] ISC-3: Tiger Brokers API rate limits quantified
- [x] ISC-4: Interactive Brokers API rate limits quantified
- [x] ISC-5: Intraday frequency viability assessed for retail
- [x] ISC-6: Daily frequency viability assessed for retail
- [x] ISC-7: Weekly frequency viability assessed for retail
- [x] ISC-8: Pairs trading stat arb strategy documented with rules
- [x] ISC-9: ETF stat arb strategy documented with rules
- [x] ISC-10: Commission costs quantified by frequency band
- [x] ISC-11: Slippage costs quantified by frequency band
- [x] ISC-12: Market impact costs quantified by frequency band
- [x] ISC-13: Optimal trades per day range identified with evidence
- [x] ISC-14: Optimal trades per week range identified with evidence
- [x] ISC-15: Real retail quant trader examples documented
- [x] ISC-16: Contrarian analysis challenging popular narratives included

## Decisions

- Focus on Tiger Brokers and Interactive Brokers as primary API references
- Use academic research + practitioner data for cost analysis
- Apply contrarian lens to challenge "day trading is best" narrative

## Verification

- All latency numbers sourced from broker documentation or independent tests
- Cost analysis uses real commission schedules
- Strategy rules are specific enough to implement
- Contrarian perspective challenges conventional wisdom with data
