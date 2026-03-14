"""
风险平价(Risk Parity)多策略资金分配模块

核心思想:
    传统的等权分配忽略了策略间的风险差异。
    风险平价使得每个策略贡献相等的风险,
    波动率高的策略分配更少资金, 波动率低的分配更多。

数学框架:
    设有N个策略, 权重向量 w = [w_1, ..., w_N]
    协方差矩阵 Sigma
    组合方差 sigma_p^2 = w^T * Sigma * w

    每个策略的风险贡献:
    RC_i = w_i * (Sigma * w)_i / sigma_p

    风险平价条件:
    RC_i = RC_j, 对所有 i, j

    等价于最小化:
    min sum_{i=1}^{N} (RC_i - sigma_p / N)^2
    s.t. sum(w_i) = 1, w_i > 0

优化方法:
    1. 解析近似 (逆波动率加权)
    2. 数值优化 (SciPy minimize)
    3. Riskfolio-Lib (专业库)

参考文献:
    - Maillard, Roncalli, Teiletche (2010) "The Properties of Equally Weighted Risk Contribution Portfolios"
    - Qian (2005) "Risk Parity Portfolios"
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. 基础计算工具
# ═══════════════════════════════════════════════════════════════

def calculate_strategy_returns(
    equity_curves: Dict[str, pd.Series],
) -> pd.DataFrame:
    """
    从策略净值曲线计算日收益率

    参数:
        equity_curves: {策略名: 净值时间序列}

    返回: 策略收益率DataFrame
    """
    returns = pd.DataFrame()
    for name, equity in equity_curves.items():
        returns[name] = equity.pct_change().dropna()
    return returns.dropna()


def calculate_risk_metrics(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.04,
    annualization_factor: int = 252,
) -> Dict[str, Dict]:
    """
    计算各策略的风险指标

    参数:
        returns: 策略日收益率DataFrame
        risk_free_rate: 无风险利率 (年化)
        annualization_factor: 年化因子

    返回: {策略名: {volatility, sharpe, max_drawdown, calmar, ...}}
    """
    metrics = {}
    rf_daily = risk_free_rate / annualization_factor

    for col in returns.columns:
        r = returns[col]
        vol = r.std() * np.sqrt(annualization_factor)
        ann_return = r.mean() * annualization_factor
        sharpe = (ann_return - risk_free_rate) / vol if vol > 0 else 0

        # 最大回撤
        cumulative = (1 + r).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_dd = float(drawdown.min())

        # Calmar比率
        calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

        # 偏度和峰度
        skew = float(r.skew())
        kurt = float(r.kurt())

        metrics[col] = {
            "annual_return": round(ann_return, 4),
            "annual_volatility": round(vol, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd, 4),
            "calmar_ratio": round(calmar, 4),
            "skewness": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "daily_var_95": round(float(r.quantile(0.05)), 6),
        }

    return metrics


# ═══════════════════════════════════════════════════════════════
# 2. 风险平价权重计算
# ═══════════════════════════════════════════════════════════════

def inverse_volatility_weights(
    returns: pd.DataFrame,
    lookback: Optional[int] = None,
) -> np.ndarray:
    """
    方法1: 逆波动率加权 (最简单的风险平价近似)

    数学公式:
        w_i = (1/sigma_i) / sum(1/sigma_j)
        其中 sigma_i 是策略i的波动率

    优点: 计算极快, 无需优化
    缺点: 忽略策略间的相关性

    参数:
        returns: 策略收益率
        lookback: 回看天数 (None=全部)

    返回: 权重数组
    """
    if lookback:
        r = returns.tail(lookback)
    else:
        r = returns

    vols = r.std()
    vols = vols.replace(0, vols[vols > 0].min() if (vols > 0).any() else 1e-6)

    inv_vols = 1.0 / vols
    weights = inv_vols / inv_vols.sum()

    return weights.values


def risk_contribution(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
) -> np.ndarray:
    """
    计算每个策略的风险贡献

    数学公式:
        portfolio_vol = sqrt(w^T * Sigma * w)
        marginal_risk_i = (Sigma * w)_i / portfolio_vol
        risk_contribution_i = w_i * marginal_risk_i
        risk_contribution_pct_i = risk_contribution_i / portfolio_vol

    参数:
        weights: 权重向量
        cov_matrix: 协方差矩阵

    返回: 各策略的风险贡献百分比
    """
    port_var = weights @ cov_matrix @ weights
    port_vol = np.sqrt(port_var)

    if port_vol == 0:
        return np.ones(len(weights)) / len(weights)

    marginal_risk = cov_matrix @ weights / port_vol
    rc = weights * marginal_risk
    rc_pct = rc / port_vol

    return rc_pct


def risk_parity_objective(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    target_risk_budget: Optional[np.ndarray] = None,
) -> float:
    """
    风险平价目标函数

    最小化: sum((RC_i - target_i)^2)
    其中 RC_i 是策略i的风险贡献, target_i 是目标风险贡献

    默认target: 每个策略贡献1/N的风险

    参数:
        weights: 权重向量
        cov_matrix: 协方差矩阵
        target_risk_budget: 目标风险预算 (默认等风险)

    返回: 目标函数值
    """
    n = len(weights)
    if target_risk_budget is None:
        target_risk_budget = np.ones(n) / n

    port_var = weights @ cov_matrix @ weights
    port_vol = np.sqrt(port_var)

    if port_vol < 1e-10:
        return 1e10

    # 风险贡献
    marginal_risk = cov_matrix @ weights
    rc = weights * marginal_risk / port_vol

    # 与目标的偏差
    target_rc = target_risk_budget * port_vol
    objective = np.sum((rc - target_rc) ** 2)

    return objective


def calculate_risk_parity_weights(
    returns: pd.DataFrame,
    lookback: Optional[int] = 252,
    target_risk_budget: Optional[Dict[str, float]] = None,
    min_weight: float = 0.02,
    max_weight: float = 0.50,
) -> Dict:
    """
    方法2: 数值优化求解风险平价权重 (推荐方法)

    使用SciPy的SLSQP优化器求解:
    min sum((RC_i - target_i)^2)
    s.t.
        sum(w_i) = 1
        min_weight <= w_i <= max_weight

    参数:
        returns: 策略收益率DataFrame
        lookback: 回看天数
        target_risk_budget: {策略名: 目标风险占比}, None=等风险
        min_weight: 最小权重
        max_weight: 最大权重

    返回: {
        weights: {策略名: 权重},
        risk_contributions: {策略名: 风险贡献},
        portfolio_metrics: {...},
    }
    """
    if lookback:
        r = returns.tail(lookback)
    else:
        r = returns

    n = len(returns.columns)
    strategy_names = list(returns.columns)
    cov_matrix = r.cov().values

    # 目标风险预算
    if target_risk_budget:
        budget = np.array([target_risk_budget.get(name, 1.0/n) for name in strategy_names])
        budget = budget / budget.sum()  # 归一化
    else:
        budget = np.ones(n) / n

    # 初始值: 逆波动率权重
    x0 = inverse_volatility_weights(r)

    # 约束
    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},  # 权重和=1
    ]

    # 边界
    bounds = [(min_weight, max_weight)] * n

    # 优化
    result = minimize(
        risk_parity_objective,
        x0,
        args=(cov_matrix, budget),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 1000},
    )

    if not result.success:
        logger.warning(f"风险平价优化未完全收敛: {result.message}")
        # 退回逆波动率权重
        optimal_weights = x0
    else:
        optimal_weights = result.x

    # 归一化
    optimal_weights = optimal_weights / optimal_weights.sum()

    # 计算风险贡献
    rc = risk_contribution(optimal_weights, cov_matrix)

    # 组合指标
    port_return = r.mean().values @ optimal_weights * 252
    port_vol = np.sqrt(optimal_weights @ cov_matrix @ optimal_weights * 252)
    sharpe = (port_return - 0.04) / port_vol if port_vol > 0 else 0

    return {
        "weights": {name: round(float(w), 4) for name, w in zip(strategy_names, optimal_weights)},
        "risk_contributions": {name: round(float(rc_i), 4) for name, rc_i in zip(strategy_names, rc)},
        "target_budget": {name: round(float(b), 4) for name, b in zip(strategy_names, budget)},
        "portfolio_metrics": {
            "annual_return": round(float(port_return), 4),
            "annual_volatility": round(float(port_vol), 4),
            "sharpe_ratio": round(float(sharpe), 4),
        },
        "optimization_converged": result.success,
    }


# ═══════════════════════════════════════════════════════════════
# 3. 自适应风险平价 (动态调仓)
# ═══════════════════════════════════════════════════════════════

def adaptive_risk_parity(
    returns: pd.DataFrame,
    rebalance_frequency: str = "monthly",
    lookback_days: int = 63,
    shrinkage_factor: float = 0.5,
    min_weight: float = 0.05,
    max_weight: float = 0.40,
) -> pd.DataFrame:
    """
    自适应风险平价 (定期再平衡)

    核心改进:
    1. 定期重新计算权重 (月度/季度)
    2. 使用收缩估计器改善协方差矩阵估计
    3. 权重平滑过渡 (避免大幅调仓)

    协方差矩阵收缩 (Ledoit-Wolf):
        Sigma_shrunk = (1-alpha) * Sigma_sample + alpha * Sigma_target
        其中 Sigma_target 通常是对角矩阵
        alpha = shrinkage_factor

    参数:
        returns: 策略收益率
        rebalance_frequency: "monthly" | "quarterly" | "weekly"
        lookback_days: 回看天数
        shrinkage_factor: 收缩因子 (0-1, 推荐0.3-0.7)
        min_weight: 最小权重
        max_weight: 最大权重

    返回: 权重时间序列DataFrame
    """
    n_strategies = len(returns.columns)
    strategy_names = list(returns.columns)

    # 确定再平衡日期
    if rebalance_frequency == "monthly":
        rebal_dates = returns.resample("ME").last().index
    elif rebalance_frequency == "quarterly":
        rebal_dates = returns.resample("QE").last().index
    elif rebalance_frequency == "weekly":
        rebal_dates = returns.resample("W").last().index
    else:
        rebal_dates = returns.resample("ME").last().index

    weight_history = []

    for date in rebal_dates:
        # 截取回看窗口
        mask = returns.index <= date
        window = returns.loc[mask].tail(lookback_days)

        if len(window) < 20:
            # 数据不足, 使用等权
            weights = np.ones(n_strategies) / n_strategies
        else:
            # 样本协方差矩阵
            sample_cov = window.cov().values

            # 收缩目标: 对角矩阵
            target_cov = np.diag(np.diag(sample_cov))

            # Ledoit-Wolf收缩
            shrunk_cov = (
                (1 - shrinkage_factor) * sample_cov +
                shrinkage_factor * target_cov
            )

            # 求解风险平价
            x0 = inverse_volatility_weights(window)
            budget = np.ones(n_strategies) / n_strategies

            result = minimize(
                risk_parity_objective,
                x0,
                args=(shrunk_cov, budget),
                method="SLSQP",
                bounds=[(min_weight, max_weight)] * n_strategies,
                constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
                options={"ftol": 1e-12, "maxiter": 500},
            )

            weights = result.x if result.success else x0
            weights = weights / weights.sum()

        weight_history.append({
            "date": date,
            **{name: round(float(w), 4) for name, w in zip(strategy_names, weights)}
        })

    return pd.DataFrame(weight_history).set_index("date")


# ═══════════════════════════════════════════════════════════════
# 4. 多策略组合引擎
# ═══════════════════════════════════════════════════════════════

class MultiStrategyPortfolio:
    """
    多策略组合管理器

    将多个策略按风险平价原则组合, 动态调整资金分配。

    使用示例:
        portfolio = MultiStrategyPortfolio(
            strategy_names=["MA交叉", "RSI", "动量", "均值回归", "PEAD"],
            initial_capital=1_000_000,
        )

        # 用历史回测数据计算权重
        portfolio.fit(strategy_returns_df, lookback_days=126)

        # 获取当前分配
        allocation = portfolio.get_allocation()
        # {"MA交叉": 280000, "RSI": 220000, "动量": 150000, ...}

        # 月度再平衡
        portfolio.rebalance(latest_returns_df)
    """

    def __init__(
        self,
        strategy_names: List[str],
        initial_capital: float = 1_000_000,
        min_weight: float = 0.05,
        max_weight: float = 0.40,
        rebalance_frequency: str = "monthly",
        risk_free_rate: float = 0.04,
    ):
        self.strategy_names = strategy_names
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.rebalance_frequency = rebalance_frequency
        self.risk_free_rate = risk_free_rate

        self.weights = None
        self.risk_contributions = None
        self.allocation = None
        self.history = []

    def fit(
        self,
        returns: pd.DataFrame,
        lookback_days: int = 126,
        target_budget: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        根据历史收益率计算风险平价权重

        参数:
            returns: 策略收益率DataFrame
            lookback_days: 回看天数 (默认半年)
            target_budget: 目标风险预算

        返回: 权重和风险贡献
        """
        result = calculate_risk_parity_weights(
            returns,
            lookback=lookback_days,
            target_risk_budget=target_budget,
            min_weight=self.min_weight,
            max_weight=self.max_weight,
        )

        self.weights = result["weights"]
        self.risk_contributions = result["risk_contributions"]

        # 计算资金分配
        self.allocation = {
            name: round(self.current_capital * weight, 2)
            for name, weight in self.weights.items()
        }

        self.history.append({
            "timestamp": pd.Timestamp.now(),
            "weights": self.weights.copy(),
            "capital": self.current_capital,
        })

        return {
            "weights": self.weights,
            "risk_contributions": self.risk_contributions,
            "allocation": self.allocation,
            "portfolio_metrics": result["portfolio_metrics"],
        }

    def rebalance(
        self,
        latest_returns: pd.DataFrame,
        updated_capital: Optional[float] = None,
    ) -> Dict:
        """
        再平衡

        参数:
            latest_returns: 最新收益率数据
            updated_capital: 更新后的总资金

        返回: 新的权重和分配
        """
        if updated_capital is not None:
            self.current_capital = updated_capital

        return self.fit(latest_returns)

    def get_allocation(self) -> Dict[str, float]:
        """获取当前资金分配"""
        if self.allocation is None:
            # 未初始化, 返回等权
            equal_weight = self.current_capital / len(self.strategy_names)
            return {name: equal_weight for name in self.strategy_names}
        return self.allocation

    def get_rebalance_trades(
        self,
        current_positions: Dict[str, float],
    ) -> Dict[str, float]:
        """
        计算再平衡所需的交易

        参数:
            current_positions: {策略名: 当前持仓市值}

        返回: {策略名: 需要调整的金额} (正=增加, 负=减少)
        """
        target = self.get_allocation()
        trades = {}

        for name in self.strategy_names:
            current = current_positions.get(name, 0)
            target_val = target.get(name, 0)
            diff = target_val - current
            if abs(diff) > self.current_capital * 0.01:  # 忽略<1%的微调
                trades[name] = round(diff, 2)

        return trades

    def summary(self) -> str:
        """生成组合摘要"""
        if self.weights is None:
            return "组合未初始化, 请先调用fit()方法"

        lines = ["=== 多策略风险平价组合摘要 ===\n"]
        lines.append(f"总资金: {self.current_capital:,.0f} 港元\n")
        lines.append(f"{'策略':<20} {'权重':>8} {'风险贡献':>8} {'分配资金':>12}")
        lines.append("-" * 52)

        for name in self.strategy_names:
            w = self.weights.get(name, 0)
            rc = self.risk_contributions.get(name, 0)
            alloc = self.allocation.get(name, 0)
            lines.append(f"{name:<20} {w:>7.1%} {rc:>7.1%} {alloc:>11,.0f}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 5. 使用示例和工具函数
# ═══════════════════════════════════════════════════════════════

def demo_risk_parity():
    """
    风险平价演示

    模拟5个策略的收益率并计算风险平价权重。
    """
    np.random.seed(42)
    dates = pd.bdate_range("2024-01-01", "2025-12-31")

    # 模拟5个策略的收益率
    # 高波动策略: 更高收益但风险大
    # 低波动策略: 更低收益但风险小
    strategies = {
        "趋势跟踪": np.random.normal(0.0005, 0.015, len(dates)),   # 年化12.6%, 波动23.8%
        "均值回归": np.random.normal(0.0003, 0.008, len(dates)),   # 年化7.6%, 波动12.7%
        "动量策略": np.random.normal(0.0004, 0.012, len(dates)),   # 年化10.1%, 波动19.0%
        "PEAD策略": np.random.normal(0.0003, 0.006, len(dates)),   # 年化7.6%, 波动9.5%
        "日内反转": np.random.normal(0.0002, 0.004, len(dates)),   # 年化5.0%, 波动6.3%
    }

    returns = pd.DataFrame(strategies, index=dates)

    # 计算风险平价权重
    result = calculate_risk_parity_weights(returns)

    print("=== 风险平价权重计算结果 ===\n")
    print("策略权重:")
    for name, w in result["weights"].items():
        print(f"  {name}: {w:.1%}")

    print("\n风险贡献:")
    for name, rc in result["risk_contributions"].items():
        print(f"  {name}: {rc:.1%}")

    print(f"\n组合指标:")
    for key, val in result["portfolio_metrics"].items():
        print(f"  {key}: {val}")

    # 对比等权和逆波动率
    eq_weights = np.ones(5) / 5
    iv_weights = inverse_volatility_weights(returns)
    cov = returns.cov().values

    print("\n=== 权重对比 ===")
    print(f"{'策略':<12} {'等权':>8} {'逆波动率':>8} {'风险平价':>8}")
    for i, name in enumerate(returns.columns):
        print(f"{name:<12} {eq_weights[i]:>7.1%} {iv_weights[i]:>7.1%} "
              f"{result['weights'][name]:>7.1%}")

    return result


if __name__ == "__main__":
    demo_risk_parity()
