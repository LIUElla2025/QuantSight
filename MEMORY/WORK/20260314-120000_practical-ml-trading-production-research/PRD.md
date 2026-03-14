---
task: Practical ML trading research for production use
slug: 20260314-120000_practical-ml-trading-production-research
effort: extended
phase: complete
progress: 16/16
mode: interactive
started: 2026-03-14T12:00:00+08:00
updated: 2026-03-14T12:01:30+08:00
---

## Context

Research practical ML/AI implementation for trading that works in production, not just in academic papers or backtests. Covers 7 topics: proven ML models, predictive features, overfitting prevention, model comparison (LightGBM/XGBoost/NN), minimum data requirements, regime change detection, and time series cross-validation. User explicitly wants reality-tested approaches, not theoretical frameworks.

### Risks
- Academic papers vastly overstate ML trading performance vs live results
- Survivorship bias in practitioner reports (failures go unreported)
- Most public ML trading research is on crypto which has different dynamics than equities

## Criteria

- [x] ISC-1: ML models with proven live trading edge identified with evidence
- [x] ISC-2: Tree-based vs neural network production trade-offs documented
- [x] ISC-3: Ensemble methods superiority over single models evidenced
- [x] ISC-4: Top predictive features for stock returns ranked by out-of-sample R2
- [x] ISC-5: Feature engineering principles that survive regime changes documented
- [x] ISC-6: Overfitting prevention techniques listed with practical thresholds
- [x] ISC-7: Triple barrier labeling method explained with trading rationale
- [x] ISC-8: LightGBM vs XGBoost specific trade-offs for trading quantified
- [x] ISC-9: Neural network use cases where they outperform tree models identified
- [x] ISC-10: Minimum training data guidelines with model-specific numbers
- [x] ISC-11: Learning curve approach for data sufficiency described
- [x] ISC-12: HMM regime detection implementation approach documented
- [x] ISC-13: Regime-adaptive strategy switching mechanism explained
- [x] ISC-14: Purged cross-validation with embargo method detailed
- [x] ISC-15: Combinatorial purged CV vs walk-forward comparison provided
- [x] ISC-16: Contrarian findings that challenge popular ML trading narratives included

## Decisions

- Focus on gradient boosting as primary recommendation based on production evidence
- Include Lopez de Prado framework as gold standard for financial ML methodology
- Emphasize what FAILS in production, not just what succeeds

## Verification

All 16 criteria verified through web research from multiple sources including academic papers, practitioner blogs, and industry reports. Contrarian perspective applied throughout.
