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
    """回测结果"""
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
    win_rate: float              # 胜率 %
    total_trades: int            # 总交易次数
    profit_trades: int           # 盈利交易次数
    loss_trades: int             # 亏损交易次数
    avg_profit: float            # 平均每笔盈利
    avg_loss: float              # 平均每笔亏损
    profit_factor: float         # 盈亏比
    trade_log: list              # 交易明细
    equity_curve: list           # 权益曲线

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
            "win_rate": round(self.win_rate, 2),
            "total_trades": self.total_trades,
            "profit_trades": self.profit_trades,
            "loss_trades": self.loss_trades,
            "avg_profit": round(self.avg_profit, 2),
            "avg_loss": round(self.avg_loss, 2),
            "profit_factor": round(self.profit_factor, 2),
            "trade_log": self.trade_log,
            "equity_curve": self.equity_curve,
        }


class Backtester:
    """回测引擎核心"""

    def __init__(self, initial_capital: float = 1_000_000, commission_rate: float = 0.0003):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate  # 佣金费率

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
                pnl = revenue - position_qty * position_cost
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
        annual_return = ((final_equity / self.initial_capital) ** (1 / max(years, 0.01)) - 1) * 100 if years > 0 else 0

        # 最大回撤
        max_drawdown = self._calc_max_drawdown(equity_curve)

        # 夏普比率 (假设无风险利率 3%)
        sharpe = self._calc_sharpe(daily_returns, risk_free_rate=0.03)

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
            win_rate=win_rate,
            total_trades=total_trades,
            profit_trades=len(profits),
            loss_trades=len(losses),
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trade_log=trade_log,
            equity_curve=equity_curve,
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

    def _calc_sharpe(self, daily_returns: list, risk_free_rate: float = 0.03) -> float:
        if len(daily_returns) < 2:
            return 0
        returns = np.array(daily_returns)
        excess = returns - risk_free_rate / 252
        if np.std(returns) == 0:
            return 0
        return float(np.mean(excess) / np.std(returns) * np.sqrt(252))
