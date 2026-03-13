"""
策略执行引擎
管理策略的运行状态，定时检查信号并自动下单
"""
import threading
import time
import uuid
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from strategies import get_strategy, Signal, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class StrategyInstance:
    """一个运行中的策略实例"""
    id: str
    strategy_key: str
    strategy_name: str
    symbol: str
    params: dict
    status: str = "stopped"          # running / stopped / error
    position_qty: int = 0
    position_cost: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_trades: int = 0
    last_signal: Optional[str] = None
    last_check: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    trade_history: list = field(default_factory=list)
    error_msg: Optional[str] = None

    def to_dict(self):
        return {
            "id": self.id,
            "strategy_key": self.strategy_key,
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "params": self.params,
            "status": self.status,
            "position_qty": self.position_qty,
            "position_cost": round(self.position_cost, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "total_trades": self.total_trades,
            "last_signal": self.last_signal,
            "last_check": self.last_check,
            "created_at": self.created_at,
            "trade_history": self.trade_history[-20:],  # 只返回最近20条
            "error_msg": self.error_msg,
        }


class StrategyEngine:
    """策略执行引擎（单例）"""

    def __init__(self):
        self.instances: dict[str, StrategyInstance] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._stop_flags: dict[str, threading.Event] = {}
        self._quote_fetcher = None   # 将在 main.py 注入
        self._order_executor = None  # 将在 main.py 注入

    def set_quote_fetcher(self, fetcher):
        """设置行情数据获取函数: fetcher(symbol) -> pd.DataFrame"""
        self._quote_fetcher = fetcher

    def set_order_executor(self, executor):
        """设置下单执行函数: executor(symbol, action, qty, price) -> dict"""
        self._order_executor = executor

    def create_strategy(self, strategy_key: str, symbol: str, params: dict = None) -> StrategyInstance:
        """创建一个策略实例"""
        strategy = get_strategy(strategy_key, params)
        instance = StrategyInstance(
            id=str(uuid.uuid4())[:8],
            strategy_key=strategy_key,
            strategy_name=strategy.name,
            symbol=symbol,
            params=strategy.params,
        )
        self.instances[instance.id] = instance
        return instance

    def start_strategy(self, instance_id: str) -> StrategyInstance:
        """启动策略"""
        inst = self.instances.get(instance_id)
        if not inst:
            raise ValueError(f"策略实例不存在: {instance_id}")
        if inst.status == "running":
            return inst

        inst.status = "running"
        inst.error_msg = None
        stop_flag = threading.Event()
        self._stop_flags[instance_id] = stop_flag

        thread = threading.Thread(
            target=self._run_loop,
            args=(instance_id,),
            daemon=True,
        )
        self._threads[instance_id] = thread
        thread.start()
        return inst

    def stop_strategy(self, instance_id: str) -> StrategyInstance:
        """停止策略"""
        inst = self.instances.get(instance_id)
        if not inst:
            raise ValueError(f"策略实例不存在: {instance_id}")

        if instance_id in self._stop_flags:
            self._stop_flags[instance_id].set()

        inst.status = "stopped"
        return inst

    def remove_strategy(self, instance_id: str):
        """移除策略实例"""
        self.stop_strategy(instance_id)
        self.instances.pop(instance_id, None)
        self._stop_flags.pop(instance_id, None)
        self._threads.pop(instance_id, None)

    def get_all(self) -> list:
        return [inst.to_dict() for inst in self.instances.values()]

    def get_one(self, instance_id: str) -> dict:
        inst = self.instances.get(instance_id)
        if not inst:
            raise ValueError(f"策略实例不存在: {instance_id}")
        return inst.to_dict()

    def _run_loop(self, instance_id: str):
        """策略运行主循环"""
        stop_flag = self._stop_flags.get(instance_id)
        inst = self.instances.get(instance_id)
        if not inst or not stop_flag:
            return

        while not stop_flag.is_set():
            try:
                self._check_signal(inst)
            except Exception as e:
                logger.error(f"策略 {instance_id} 执行异常: {e}")
                inst.error_msg = str(e)
                inst.status = "error"
                break

            # 每60秒检查一次信号（生产环境可改为更短）
            stop_flag.wait(60)

    def _check_signal(self, inst: StrategyInstance):
        """检查一次信号并决定是否下单"""
        if not self._quote_fetcher:
            inst.error_msg = "行情数据获取器未配置"
            return

        # 获取历史K线数据
        df = self._quote_fetcher(inst.symbol)
        if df is None or len(df) == 0:
            inst.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            inst.last_signal = "数据获取失败"
            return

        strategy = get_strategy(inst.strategy_key, inst.params)
        signal = strategy.generate_signal(df, inst.symbol, inst.position_qty)

        inst.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inst.last_signal = f"{signal.signal.value}: {signal.reason}"

        # 更新未实现盈亏
        if inst.position_qty > 0:
            current_price = df["close"].iloc[-1]
            inst.unrealized_pnl = (current_price - inst.position_cost) * inst.position_qty

        if signal.signal == Signal.BUY and inst.position_qty == 0:
            self._execute_buy(inst, signal)
        elif signal.signal == Signal.SELL and inst.position_qty > 0:
            self._execute_sell(inst, signal)

    def _execute_buy(self, inst: StrategyInstance, signal: TradeSignal):
        """执行买入"""
        trade_record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "BUY",
            "price": signal.price,
            "quantity": signal.quantity,
            "reason": signal.reason,
            "order_result": None,
        }

        if self._order_executor:
            try:
                result = self._order_executor(inst.symbol, "BUY", signal.quantity, signal.price)
                trade_record["order_result"] = result
            except Exception as e:
                trade_record["order_result"] = {"error": str(e)}
                inst.error_msg = f"下单失败: {e}"

        inst.position_qty = signal.quantity
        inst.position_cost = signal.price
        inst.total_trades += 1
        inst.trade_history.append(trade_record)

    def _execute_sell(self, inst: StrategyInstance, signal: TradeSignal):
        """执行卖出"""
        pnl = (signal.price - inst.position_cost) * inst.position_qty
        trade_record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "SELL",
            "price": signal.price,
            "quantity": inst.position_qty,
            "pnl": round(pnl, 2),
            "reason": signal.reason,
            "order_result": None,
        }

        if self._order_executor:
            try:
                result = self._order_executor(inst.symbol, "SELL", inst.position_qty, signal.price)
                trade_record["order_result"] = result
            except Exception as e:
                trade_record["order_result"] = {"error": str(e)}
                inst.error_msg = f"下单失败: {e}"

        inst.realized_pnl += pnl
        inst.position_qty = 0
        inst.position_cost = 0.0
        inst.unrealized_pnl = 0.0
        inst.total_trades += 1
        inst.trade_history.append(trade_record)


# 全局单例
engine = StrategyEngine()
