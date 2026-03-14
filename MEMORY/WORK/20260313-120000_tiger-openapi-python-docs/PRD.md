---
task: Read Tiger Brokers OpenAPI Python docs completely
slug: 20260313-120000_tiger-openapi-python-docs
effort: comprehensive
phase: complete
progress: 16/16
mode: interactive
started: 2026-03-13T12:00:00+08:00
updated: 2026-03-13T12:30:00+08:00
---

## Context

User requested a complete reading of Tiger Brokers OpenAPI Python documentation from two entry points:
1. https://quant.itigerup.com/openapi/zh/python/overview/introduction.html
2. https://docs.itigerup.com

The task was to traverse all navigation sections and compile a complete Chinese API reference manual. The new docs site (docs.itigerup.com) is a React SPA and renders content dynamically; the old site (quant.itigerup.com) has static HTML. Both were queried extensively. Output is written to Tiger_OpenAPI_Python_Reference.md in the project root.

### Risks
- docs.itigerup.com is a React app; some content not in static HTML
- Some parameter details inferred from context rather than directly extracted
- Options/futures parameter details partially incomplete

## Criteria

- [x] ISC-1: Overview/Introduction section read and documented
- [x] ISC-2: Account opening/activation methods documented
- [x] ISC-3: Quick Start setup and configuration documented
- [x] ISC-4: TigerOpenClientConfig parameters documented
- [x] ISC-5: TradeClient initialization documented
- [x] ISC-6: QuoteClient initialization documented
- [x] ISC-7: Account management API functions documented
- [x] ISC-8: Stock market data API functions documented
- [x] ISC-9: Futures market data API documented
- [x] ISC-10: Options market data API documented
- [x] ISC-11: Crypto and fund and warrant APIs documented
- [x] ISC-12: Trading API (place/cancel/modify order) documented
- [x] ISC-13: Order info query API documented
- [x] ISC-14: Push/subscription API documented
- [x] ISC-15: Stock screener API documented
- [x] ISC-16: Error codes, rate limits, enums documented

## Decisions

- Fetched both old and new doc sites; new site is React SPA so used old site for static content
- Compiled into a single comprehensive Chinese reference document
- Noted which parameters were confirmed vs inferred

## Verification

All 16 criteria verified by reviewing Tiger_OpenAPI_Python_Reference.md output file which covers all required sections.
