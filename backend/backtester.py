"""
回测引擎
使用历史K线数据对策略进行回测，计算各项绩效指标
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from strategies import get_strategy, Signal


@dataclass
class BacktestResult:
    """回测结果 v2.0"""
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float          # 总收益率 %
    annual_return: float         # 年化收益率 %
    max_drawdown: float          # 最大回撤 %
    sharpe_ratio: float          # 夏普比率
    sortino_ratio: float         # Sortino比率（仅下行波动率）
    calmar_ratio: float          # Calmar比率（年化收益/最大回撤）
    win_rate: float              # 胜率 %
    total_trades: int            # 总交易次数
    profit_trades: int           # 盈利交易次数
    loss_trades: int             # 亏损交易次数
    avg_profit: float            # 平均每笔盈利
    avg_loss: float              # 平均每笔亏损
    profit_factor: float         # 盈亏比
    trade_log: list              # 交易明细
    equity_curve: list           # 权益曲线
    monthly_returns: list        # 月度收益分布

    def to_dict(self):
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_capital": round(self.final_capital, 2),
            "total_return": round(self.total_return, 2),
            "annual_return": round(self.annual_return, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "sortino_ratio": round(self.sortino_ratio, 2),
            "calmar_ratio": round(self.calmar_ratio, 2),
            "win_rate": round(self.win_rate, 2),
            "total_trades": self.total_trades,
            "profit_trades": self.profit_trades,
            "loss_trades": self.loss_trades,
            "avg_profit": round(self.avg_profit, 2),
            "avg_loss": round(self.avg_loss, 2),
            "profit_factor": round(self.profit_factor, 2),
            "trade_log": self.trade_log,
            "equity_curve": self.equity_curve,
            "monthly_returns": self.monthly_returns,
        }


class Backtester:
    """回测引擎核心 v2.0"""

    def __init__(self, initial_capital: float = 1_000_000, commission_rate: float = 0.0016):
        """
        commission_rate: 港股交易总成本（默认0.16%/单边）
        包含：印花税0.13% + 交易费0.005% + 证监会征费0.0027% + 佣金0.03%
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate

    def run(self, df: pd.DataFrame, strategy_key: str, strategy_params: dict,
            symbol: str) -> BacktestResult:
        """
        执行回测
        df: 包含 time, open, high, low, close, volume 的 DataFrame
        """
        strategy = get_strategy(strategy_key, strategy_params)

        capital = self.initial_capital
        position_qty = 0
        position_cost = 0.0
        trade_log = []
        equity_curve = []
        daily_returns = []

        for i in range(1, len(df)):
            # 用截止到当前的数据生成信号
            window = df.iloc[:i + 1].copy()
            signal = strategy.generate_signal(window, symbol, position_qty)
            price = df["close"].iloc[i]
            time_str = str(df["time"].iloc[i])
            if " " in time_str:
                time_str = time_str.split(" ")[0]

            if signal.signal == Signal.BUY and position_qty == 0 and capital > 0:
                # 计算可买数量（考虑佣金）
                qty = signal.quantity
                cost = qty * price * (1 + self.commission_rate)
                if cost <= capital:
                    capital -= cost
                    position_qty = qty
                    position_cost = price
                    trade_log.append({
                        "time": time_str,
                        "action": "BUY",
                        "price": round(price, 2),
                        "quantity": qty,
                        "reason": signal.reason,
                        "capital_after": round(capital, 2),
                    })

            elif signal.signal == Signal.SELL and position_qty > 0:
                revenue = position_qty * price * (1 - self.commission_rate)
                # 修正：PnL应扣除买入时的佣金成本（买入总成本 = qty * cost * (1 + commission)）
                buy_total_cost = position_qty * position_cost * (1 + self.commission_rate)
                pnl = revenue - buy_total_cost
                capital += revenue
                trade_log.append({
                    "time": time_str,
                    "action": "SELL",
                    "price": round(price, 2),
                    "quantity": position_qty,
                    "pnl": round(pnl, 2),
                    "reason": signal.reason,
                    "capital_after": round(capital, 2),
                })
                position_qty = 0
                position_cost = 0.0

            # 记录每日权益（现金 + 持仓市值）
            equity = capital + position_qty * price
            equity_curve.append({"time": time_str, "equity": round(equity, 2)})

            if len(equity_curve) >= 2:
                prev_eq = equity_curve[-2]["equity"]
                daily_ret = (equity - prev_eq) / prev_eq if prev_eq > 0 else 0
                daily_returns.append(daily_ret)

        # 如果回测结束还有持仓，按最后价格计算
        final_price = df["close"].iloc[-1]
        final_equity = capital + position_qty * final_price

        # 计算绩效指标
        total_return = ((final_equity - self.initial_capital) / self.initial_capital) * 100

        # 年化收益率
        trading_days = len(df)
        years = trading_days / 252
        # 修正：短期回测（<30天）不做年化，避免虚高数字
        if years < 30 / 252:
            annual_return = total_return  # 不足30天直接用总收益率
        else:
            annual_return = ((final_equity / self.initial_capital) ** (1 / years) - 1) * 100

        # 最大回撤
        max_drawdown = self._calc_max_drawdown(equity_curve)

        # 夏普/Sortino比率（港股无风险利率~4%，略高于美国）
        sharpe = self._calc_sharpe(daily_returns, risk_free_rate=0.04)
        sortino = self._calc_sortino(daily_returns, risk_free_rate=0.04)

        # Calmar比率 = 年化收益 / 最大回撤（越高越好）
        calmar = annual_return / max(max_drawdown, 0.01)

        # 月度收益分布
        monthly_returns = self._calc_monthly_returns(equity_curve)

        # 交易统计
        sells = [t for t in trade_log if t["action"] == "SELL"]
        profits = [t["pnl"] for t in sells if t.get("pnl", 0) > 0]
        losses = [t["pnl"] for t in sells if t.get("pnl", 0) <= 0]
        total_trades = len(sells)
        win_rate = (len(profits) / total_trades * 100) if total_trades > 0 else 0
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_factor = abs(sum(profits) / sum(losses)) if losses and sum(losses) != 0 else float("inf") if profits else 0

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=symbol,
            start_date=str(df["time"].iloc[0]).split(" ")[0] if " " in str(df["time"].iloc[0]) else str(df["time"].iloc[0]),
            end_date=str(df["time"].iloc[-1]).split(" ")[0] if " " in str(df["time"].iloc[-1]) else str(df["time"].iloc[-1]),
            initial_capital=self.initial_capital,
            final_capital=final_equity,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            win_rate=win_rate,
            total_trades=total_trades,
            profit_trades=len(profits),
            loss_trades=len(losses),
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trade_log=trade_log,
            equity_curve=equity_curve,
            monthly_returns=monthly_returns,
        )

    def _calc_max_drawdown(self, equity_curve: list) -> float:
        if not equity_curve:
            return 0
        equities = [e["equity"] for e in equity_curve]
        peak = equities[0]
        max_dd = 0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def _calc_sharpe(self, daily_returns: list, risk_free_rate: float = 0.04) -> float:
        if len(daily_returns) < 2:
            return 0
        returns = np.array(daily_returns)
        excess = returns - risk_free_rate / 252
        if np.std(returns) == 0:
            return 0
        return float(np.mean(excess) / np.std(returns) * np.sqrt(252))

    def _calc_sortino(self, daily_returns: list, risk_free_rate: float = 0.04) -> float:
        """Sortino比率：只用下行波动率（不惩罚上行波动）"""
        if len(daily_returns) < 2:
            return 0
        returns = np.array(daily_returns)
        excess = returns - risk_free_rate / 252
        downside = returns[returns < 0]
        if len(downside) == 0:
            return 9.99  # 无亏损，极高Sortino
        downside_std = np.std(downside)
        if downside_std == 0:
            return 0
        return float(np.mean(excess) / downside_std * np.sqrt(252))

    def _calc_monthly_returns(self, equity_curve: list) -> list:
        """计算月度收益分布"""
        if len(equity_curve) < 20:
            return []
        try:
            df_eq = pd.DataFrame(equity_curve)
            df_eq['month'] = df_eq['time'].apply(
                lambda t: str(t)[:7] if len(str(t)) >= 7 else str(t)
            )
            monthly = df_eq.groupby('month')['equity'].agg(['first', 'last'])
            monthly['return_pct'] = (monthly['last'] - monthly['first']) / monthly['first'] * 100
            return [
                {"month": m, "return_pct": round(float(r), 2)}
                for m, r in monthly['return_pct'].items()
            ]
        except Exception:
            return []
