---
task: Read Tiger docs then optimize quant trading system
slug: 20260313-000000_tiger-docs-quant-optimization
effort: comprehensive
phase: verify
progress: 62/65
mode: interactive
started: 2026-03-13T00:00:00+08:00
updated: 2026-03-13T00:10:00+08:00
---

## Context

用户要求全面优化QuantSight量化交易系统，目标是"超过幻方量化"（世界级水平）。
系统基于老虎证券OpenAPI，交易港股（HK market），包含多种量化策略和风控模块。

已存在的系统架构：
- backend/strategies.py — 8种基础/高级策略
- backend/advanced_strategies.py — RegimeAdaptive, MomentumVolatility, StatArbPairs
- backend/super_strategy.py — SuperAlphaStrategy（8因子Alpha引擎）
- backend/alpha_factors.py — 8个alpha因子库
- backend/engine.py — 策略执行引擎（线程、风控、追踪止损）
- backend/main.py — FastAPI，一键自动交易
- backend/push_client.py — 实时价格推送
- backend/intraday_strategies.py / event_driven.py — 日内/事件策略

### Risks

1. RSI计算错误：alpha_factors.py和advanced_strategies.py仍用rolling().mean()（SMA法），不是Wilder EWM法
2. 仓位管理：目前使用固定15%+均分资金，不是信号强度驱动的Kelly仓位
3. 多因子权重未经过统计验证，靠直觉分配
4. 股票池太窄（仅10只），且只用流动性排序，缺乏动量/质量过滤
5. 策略评估只有得分，缺少Sharpe/Sortino等专业指标
6. 追踪止损固定5%，高波动时太宽，低波动时太紧
7. 开盘前15分钟（假信号高发期）无过滤

### Plan

优先修复正确性问题（RSI）→ 增加Alpha因子 → Kelly仓位 → 扩展选股池 → 专业指标 → 风控升级

## Criteria

### Alpha因子修复
- [x] ISC-1: alpha_factors.py的factor_rsi_extreme改用Wilder EWM法计算RSI
- [x] ISC-2: RegimeAdaptiveStrategy._calc_rsi改用Wilder EWM法
- [x] ISC-3: MomentumVolatilityStrategy的RSI计算改用Wilder EWM法
- [x] ISC-4: StatArbPairsStrategy的RSI计算改用Wilder EWM法
- [x] ISC-5: alpha_factors.py实现_wilder_rsi内置函数（避免循环导入）

### 新Alpha因子
- [x] ISC-6: 新增factor_vwap_deviation()函数 — VWAP偏离度因子
- [x] ISC-7: VWAP因子: 价格低于VWAP且回落中→看多，高于VWAP且放量→看空
- [x] ISC-8: 新增factor_52week_high()函数 — 52周高点接近度因子
- [x] ISC-9: 52周高点因子: 接近历史高点+放量→突破看多，离高点超40%→反弹看多
- [x] ISC-10: 新增factor_market_trend()函数 — 均线斜率感知市场趋势
- [x] ISC-11: compute_alpha_score更新为包含11个因子（加VWAP偏离+52高点+市场趋势）
- [x] ISC-12: 新权重经过性能研究调整，反转因子权重从0.20降至0.15，新因子权重合理

### Kelly仓位管理
- [x] ISC-13: engine.py中实现_kelly_fraction()方法
- [x] ISC-14: Kelly公式基于策略历史胜率和盈亏比计算最优仓位比例
- [x] ISC-15: 使用半Kelly（0.5×Kelly）保守模式，防止过度投注
- [x] ISC-16: Kelly仓位兜底：至少有5笔交易数据才启用，否则用默认15%
- [x] ISC-17: 每个策略最大仓位硬上限为总资产20%（Kelly基础上的安全阀）
- [x] ISC-18: 最小仓位HKD 5000（低于此金额跳过下单）

### 市场时段过滤
- [x] ISC-19: 开盘前15分钟+开盘初期9:45前识别为高假突破期，禁止新开仓
- [x] ISC-20: 开盘前5分钟（9:25-9:30）开始扫描最新K线为开盘做准备
- [x] ISC-21: 收盘前10分钟（15:50-16:00）强制检查持仓，可选日内平仓（eod_close参数）

### 策略性能评估升级
- [x] ISC-22: evaluate_strategies()增加Sharpe比率计算
- [x] ISC-23: evaluate_strategies()增加Sortino比率（只用下行波动率）
- [x] ISC-24: evaluate_strategies()增加最大连续亏损次数（max_consec_losses）
- [x] ISC-25: evaluate_strategies()增加期望盈利（expected_value）
- [x] ISC-26: get_portfolio_summary()增加整体Sharpe比率（portfolio_sharpe）

### 动态追踪止损
- [x] ISC-27: trailing_stop随利润动态调整（利润越高止损越紧）
- [x] ISC-28: 随利润增加，追踪止损比例收紧（利润>10%时收紧到3%）
- [x] ISC-29: 追踪止损最小值设为2%（防止过度收紧导致被正常波动洗出）

### 股票池扩展
- [x] ISC-30: _screen_hk_stocks候选池从10只扩展到20只（加入更多港股龙头）
- [x] ISC-31: 筛选增加动量过滤（正向涨跌幅的标的获得额外评分加成）
- [x] ISC-32: 筛选基于成交额综合评分（流动性+动量双维度）
- [x] ISC-33: 选股结果带有momentum和amount字段，供前端展示

### 订单执行优化
- [x] ISC-34: execute_order支持限价单模式（order_type参数）
- [x] ISC-35: 限价单默认在市价基础上+/-0.5%（比市价单更省印花税）
- [x] ISC-36: 大单（>HKD 100万）自动拆分为3笔分批执行

### 风控升级
- [x] ISC-37: 连续亏损3次后，下次买入仓位自动缩减50%（心理资本保护）
- [x] ISC-38: 单日最大亏损限额（超过参考净值2%暂停当日新开仓）
- [ ] ISC-39: 组合相关性检查（新建仓前检查是否与现有持仓高度相关）

### SuperAlphaStrategy优化
- [x] ISC-40: SuperAlphaStrategy自动使用新增的11因子compute_alpha_score
- [x] ISC-41: 危机模式（高波动）时SuperAlpha的买入阈值从0.25提高到0.50（已有逻辑）
- [x] ISC-42: 趋势模式时动量因子权重额外加倍（regime-aware factor weighting）

### RegimeAdaptiveStrategy优化
- [x] ISC-43: Hurst指数计算使用更多历史数据点（从60改为120）
- [x] ISC-44: 高波动（危机）模式下止损收紧到3%（原固定6%）
- [ ] ISC-45: 添加Kalman滤波趋势估计（简化版，减少噪音）

### 回测器升级
- [x] ISC-46: Backtester.run()结果增加Sharpe比率字段
- [x] ISC-47: Backtester.run()结果增加Sortino比率字段
- [x] ISC-48: Backtester.run()结果增加Calmar比率（年化收益/最大回撤）
- [x] ISC-49: Backtester.run()增加月度收益分布数据

### 实时价格优化
- [x] ISC-50: push_client支持自动重连（后台守护线程30秒检查，断开后重试）
- [x] ISC-51: 价格更新超过60秒无推送则记录警告日志

### 主程序API改进
- [x] ISC-52: 添加GET /api/health接口（系统健康检查）
- [x] ISC-53: /api/screener/hk返回动量分数字段
- [x] ISC-54: 添加GET /api/portfolio/sharpe接口

### 代码质量
- [x] ISC-55: alpha_factors.py所有RSI改用Wilder EWM，修复精度
- [x] ISC-56: 所有新因子函数有try/except错误处理，异常时返回0.0
- [x] ISC-57: 新alpha因子返回值用np.clip确保在[-1, +1]范围内
- [x] ISC-58: Kelly仓位数据不足时安全回退到默认15%

### 前端展示
- [x] ISC-59: Dashboard展示策略Sharpe比率列
- [x] ISC-60: Dashboard展示连续亏损次数列（风险预警）
- [x] ISC-61: 健康检查状态在topbar展示（绿点=正常/红点=异常）

### 港股特有优化
- [x] ISC-62: 印花税(0.1%)和交易费用(0.03%)纳入回测成本模型（commission_rate=0.0016）
- [x] ISC-63: 港股最小交易手数检查（20只股票手数静态映射，默认100股/手）
- [ ] ISC-64: 加入港股分时成交量模型（开盘和收盘前成交量更大）

### 系统架构
- [x] ISC-65: 所有修改向后兼容，不破坏现有已运行策略实例的状态

## Decisions

## Verification
