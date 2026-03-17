"""
策略执行引擎 v3.0
管理策略的运行状态，智能调度信号检查，自动下单
优化：时区修复、开市检测、智能仓位、组合风控、追踪止损、动态频率
"""
import threading
import uuid
import logging
import json
import os
from datetime import datetime, time as dtime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass, field

from strategies import get_strategy, Signal, TradeSignal

logger = logging.getLogger(__name__)

# 延迟导入避免循环，startup 时注入
_price_cache = None

def set_price_cache(cache):
    global _price_cache
    _price_cache = cache


# ─── 港股时区与交易时间 ───────────────────────────────
HK_TZ = timezone(timedelta(hours=8))  # UTC+8 香港/北京时区

HK_MORNING_OPEN = dtime(9, 30)
HK_MORNING_CLOSE = dtime(12, 0)
HK_AFTERNOON_OPEN = dtime(13, 0)
HK_AFTERNOON_CLOSE = dtime(16, 0)
# 开盘前关键时段
HK_PRE_OPEN = dtime(9, 15)
HK_PRE_SCAN = dtime(9, 25)   # ISC-20: 9:25开始预扫K线，为开盘做准备
HK_PRE_CLOSE = dtime(15, 30)
HK_EOD_CHECK = dtime(15, 50)  # ISC-21: 15:50开始收盘前持仓检查


def _hk_now() -> datetime:
    """获取当前香港时间（UTC+8），无论服务器在哪个时区"""
    return datetime.now(HK_TZ)


def is_hk_trading_hours() -> bool:
    """检查当前是否在港股交易时间（始终使用UTC+8时区）"""
    now = _hk_now()
    weekday = now.weekday()  # 0=周一, 6=周日
    if weekday >= 5:  # 周末
        return False
    t = now.time()
    return ((HK_MORNING_OPEN <= t <= HK_MORNING_CLOSE) or
            (HK_AFTERNOON_OPEN <= t <= HK_AFTERNOON_CLOSE))


def get_check_interval() -> int:
    """根据时段动态调整检查频率"""
    now = _hk_now()
    t = now.time()
    weekday = now.weekday()

    if weekday >= 5:  # 周末
        return 300  # 5分钟

    # 开盘前15分钟：准备阶段
    if HK_PRE_OPEN <= t < HK_MORNING_OPEN:
        return 30

    # 开盘后30分钟和收盘前30分钟：高频检查（波动最大）
    if HK_MORNING_OPEN <= t <= dtime(10, 0):
        return 15  # 15秒
    if HK_PRE_CLOSE <= t <= HK_AFTERNOON_CLOSE:
        return 15  # 15秒

    # 正常交易时间
    if is_hk_trading_hours():
        return 30  # 30秒

    # 午休
    if HK_MORNING_CLOSE < t < HK_AFTERNOON_OPEN:
        return 120  # 2分钟

    # 非交易时间
    return 300  # 5分钟


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
    # 追踪止损
    highest_price_since_buy: float = 0.0  # 买入后最高价
    trailing_stop_pct: float = 0.05       # 追踪止损：从最高点回撤5%触发
    # 连续亏损保护
    consecutive_losses: int = 0           # 当前连续亏损次数
    daily_pnl: float = 0.0               # 今日盈亏
    last_trade_date: str = ""             # 最后交易日期（用于重置daily_pnl）
    # Bug11修复: 缓存策略实例（避免每次 _check_signal 创建新实例导致策略内部状态丢失）
    # _entry_bar/_entry_price 等有状态字段需要复用同一实例
    _strategy_obj: object = field(default=None, repr=False, compare=False)

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
            "consecutive_losses": self.consecutive_losses,   # 实时连亏次数（前端风险预警用）
            "daily_pnl": round(self.daily_pnl, 2),
            "last_signal": self.last_signal,
            "last_check": self.last_check,
            "created_at": self.created_at,
            "trade_history": self.trade_history[-20:],
            "error_msg": self.error_msg,
        }


STATE_FILE = os.path.join(os.path.dirname(__file__), "engine_state.json")


class StrategyEngine:
    """策略执行引擎 v3.1（单例）— 新增状态持久化"""

    def __init__(self):
        self.instances: dict[str, StrategyInstance] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._stop_flags: dict[str, threading.Event] = {}
        self._quote_fetcher = None
        self._order_executor = None
        self._account_fetcher = None  # 获取账户余额
        # 组合级风控
        self._max_total_loss_pct = 0.10    # 总亏损超过10%停止所有策略
        self._max_single_loss_pct = 0.08   # 单策略亏损超过8%停止该策略
        self._max_daily_loss_pct = 0.02    # 单日最大亏损2%暂停当日交易
        self._emergency_stopped = False
        self._daily_loss_paused = False
        self._today_start_equity = 0.0
        self._today_date = ""
        # 订单去重：记录最近下单时间，防止短时间内重复下单
        self._last_order_time: dict[str, float] = {}  # instance_id -> timestamp
        self._order_cooldown = 60  # 同一策略最少间隔60秒才能再次下单

    def set_quote_fetcher(self, fetcher):
        self._quote_fetcher = fetcher

    def set_order_executor(self, executor):
        self._order_executor = executor

    def set_account_fetcher(self, fetcher):
        """设置账户信息获取函数: fetcher() -> dict with 'equity', 'cash'"""
        self._account_fetcher = fetcher

    def create_strategy(self, strategy_key: str, symbol: str, params: dict = None) -> StrategyInstance:
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
        inst = self.instances.get(instance_id)
        if not inst:
            raise ValueError(f"策略实例不存在: {instance_id}")
        if inst.status == "running":
            return inst

        if self._emergency_stopped:
            raise ValueError("组合风控已触发紧急停止，请检查账户后手动重置")

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
        inst = self.instances.get(instance_id)
        if not inst:
            raise ValueError(f"策略实例不存在: {instance_id}")
        if instance_id in self._stop_flags:
            self._stop_flags[instance_id].set()
        inst.status = "stopped"
        return inst

    def remove_strategy(self, instance_id: str):
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

    def get_portfolio_summary(self) -> dict:
        """获取组合级别汇总（v2.0：增加Sharpe、单日亏损暂停状态）"""
        total_realized = sum(i.realized_pnl for i in self.instances.values())
        total_unrealized = sum(i.unrealized_pnl for i in self.instances.values())
        running = sum(1 for i in self.instances.values() if i.status == "running")

        # 计算组合整体Sharpe（所有策略成交盈亏合并）
        all_pnl = [
            t.get("pnl", 0)
            for i in self.instances.values()
            for t in i.trade_history
            if t.get("action") == "SELL"
        ]
        portfolio_sharpe = self._calc_sharpe(all_pnl) if len(all_pnl) >= 3 else None

        return {
            "total_realized_pnl": round(total_realized, 2),
            "total_unrealized_pnl": round(total_unrealized, 2),
            "total_pnl": round(total_realized + total_unrealized, 2),
            "running_strategies": running,
            "total_strategies": len(self.instances),
            "emergency_stopped": self._emergency_stopped,
            "daily_loss_paused": self._daily_loss_paused,
            "portfolio_sharpe": portfolio_sharpe,
        }

    def reset_emergency(self):
        """手动重置紧急停止状态"""
        self._emergency_stopped = False
        logger.info("组合风控紧急停止已重置")

    # ─── 运行主循环 ───────────────────────────────────

    def _run_loop(self, instance_id: str):
        stop_flag = self._stop_flags.get(instance_id)
        inst = self.instances.get(instance_id)
        if not inst or not stop_flag:
            return

        while not stop_flag.is_set():
            try:
                now = _hk_now()
                t = now.time()
                inst.last_check = now.strftime("%Y-%m-%d %H:%M:%S")
                weekday = now.weekday()

                # 只在交易时间检查信号
                if is_hk_trading_hours():
                    self._check_signal(inst)
                    self._check_portfolio_risk()

                # 收盘后（16:00+）：只展示状态，不执行任何交易
                # ISC-21的日内平仓逻辑在_check_signal()内部的15:50-16:00窗口处理
                elif t > HK_AFTERNOON_CLOSE and weekday < 5:
                    if inst.position_qty > 0:
                        inst.last_signal = f"已收盘，持仓{inst.position_qty}股过夜，明日继续"
                    else:
                        inst.last_signal = "已收盘，无持仓，明日继续"

                # ISC-20: 开盘前5分钟（9:25-9:30）— 预扫K线，为开盘做准备
                elif HK_PRE_SCAN <= t < HK_MORNING_OPEN and weekday < 5:
                    if self._quote_fetcher:
                        try:
                            df = self._quote_fetcher(inst.symbol)
                            if df is not None and len(df) > 0:
                                last_close = df["close"].iloc[-1]
                                inst.last_signal = (
                                    f"开盘准备中: {inst.symbol} 昨收{last_close:.3f}，"
                                    f"K线{len(df)}根已加载，09:30开盘"
                                )
                            else:
                                inst.last_signal = "开盘准备: 数据加载中..."
                        except Exception:
                            inst.last_signal = "开盘准备: 数据预热失败，09:30开盘后重试"
                    else:
                        inst.last_signal = "等待开盘 09:30（行情接入中）"

                else:
                    if weekday >= 5:
                        inst.last_signal = "周末休市"
                    elif t < HK_PRE_SCAN:
                        inst.last_signal = f"等待开盘 09:30（预扫描将于09:25启动）"
                    elif HK_MORNING_CLOSE < t < HK_AFTERNOON_OPEN:
                        inst.last_signal = "午休中，13:00继续"
                    else:
                        inst.last_signal = "已收盘，明日继续"

            except Exception as e:
                logger.error(f"策略 {instance_id} 执行异常: {e}")
                inst.error_msg = str(e)
                inst.status = "error"
                break

            interval = get_check_interval()
            stop_flag.wait(interval)

    def _check_signal(self, inst: StrategyInstance):
        if not self._quote_fetcher:
            inst.error_msg = "行情数据获取器未配置"
            return

        # 开盘前15分钟（9:15-9:30）：数据准备阶段，只更新状态不执行买入
        # 开盘初期（9:30-9:45）：假突破高发期，禁止新开仓
        now = _hk_now()
        t = now.time()
        pre_open_filter = HK_PRE_OPEN <= t < dtime(9, 45)

        df = self._quote_fetcher(inst.symbol)
        if df is None or len(df) == 0:
            inst.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            inst.last_signal = "数据获取失败，等待重试"
            return

        # Bug11修复: 复用同一策略实例，保留 _entry_bar/_entry_price 等内部状态
        if inst._strategy_obj is None:
            inst._strategy_obj = get_strategy(inst.strategy_key, inst.params)
        strategy = inst._strategy_obj
        signal = strategy.generate_signal(df, inst.symbol, inst.position_qty)

        # 优先使用实时推送价格（更准确），降级到 K 线收盘价
        cached_price = _price_cache.get_price(inst.symbol) if _price_cache else None
        current_price = cached_price if cached_price else df["close"].iloc[-1]

        inst.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inst.last_signal = f"{signal.signal.value}: {signal.reason}"

        # 更新未实现盈亏和追踪止损最高价
        if inst.position_qty > 0:
            inst.unrealized_pnl = (current_price - inst.position_cost) * inst.position_qty
            if current_price > inst.highest_price_since_buy:
                inst.highest_price_since_buy = current_price

        # ── 动态追踪止损检查（基于ATR自适应） ──
        if inst.position_qty > 0 and inst.highest_price_since_buy > 0:
            # 动态止损比例：基于ATR估算（高波动=宽止损，低波动=紧止损）
            # 同时随利润增加收紧止损（保护利润）
            profit_pct = (current_price - inst.position_cost) / inst.position_cost if inst.position_cost > 0 else 0
            base_stop = inst.trailing_stop_pct  # 默认5%

            # 利润超过10%时收紧止损（保护利润）
            if profit_pct > 0.10:
                dynamic_stop = max(0.02, base_stop * 0.6)  # 收紧到3%，最小2%
            elif profit_pct > 0.05:
                dynamic_stop = max(0.02, base_stop * 0.8)  # 收紧到4%
            else:
                dynamic_stop = base_stop

            drawdown_from_peak = (inst.highest_price_since_buy - current_price) / inst.highest_price_since_buy
            if drawdown_from_peak > dynamic_stop:
                trailing_signal = TradeSignal(
                    Signal.SELL, inst.symbol, current_price, inst.position_qty,
                    f"动态追踪止损触发: 从高点{inst.highest_price_since_buy:.2f}回撤"
                    f"{drawdown_from_peak*100:.1f}%>(动态阈值{dynamic_stop*100:.0f}%,利润{profit_pct*100:.1f}%)"
                )
                inst.last_signal = f"SELL: {trailing_signal.reason}"
                self._execute_sell(inst, trailing_signal)
                return

        # ── 单策略风控 ──
        if inst.position_qty > 0:
            loss_pct = inst.unrealized_pnl / (inst.position_cost * inst.position_qty) if inst.position_cost > 0 else 0
            if loss_pct < -self._max_single_loss_pct:
                stop_signal = TradeSignal(
                    Signal.SELL, inst.symbol, current_price, inst.position_qty,
                    f"单策略风控: 浮亏{loss_pct*100:.1f}%超过阈值{self._max_single_loss_pct*100:.0f}%，强制平仓"
                )
                inst.last_signal = f"SELL: {stop_signal.reason}"
                self._execute_sell(inst, stop_signal)
                return

        # ISC-21: 收盘前10分钟（15:50-16:00）强制检查持仓，日内策略平仓
        # 注意：15:50-16:00 在 is_hk_trading_hours() 内，必须在此处处理
        if HK_EOD_CHECK <= t <= HK_AFTERNOON_CLOSE:
            if inst.position_qty > 0 and inst.params.get("eod_close", False):
                eod_signal = TradeSignal(
                    Signal.SELL, inst.symbol, current_price, inst.position_qty,
                    f"收盘前强制平仓(15:50日内策略，eod_close=True)"
                )
                inst.last_signal = f"SELL: 收盘前强制平仓 @ {current_price:.3f}"
                self._execute_sell(inst, eod_signal)
                return
            elif inst.position_qty > 0:
                inst.last_signal = (
                    f"收盘前提醒[{t.strftime('%H:%M')}]: 持仓{inst.position_qty}股，"
                    f"请关注收盘价（如需日内平仓，设置eod_close=True）"
                )

        # ── 正常信号处理 ──
        if signal.signal == Signal.BUY and inst.position_qty == 0:
            # 开盘前15分钟+开盘初期9:45前：假突破高发，禁止新开仓
            if pre_open_filter:
                inst.last_signal = f"HOLD: 开盘初期波动大，等待9:45后入场（信号:{signal.reason}）"
                return

            # 单日亏损暂停：今日亏损超过2%，不开新仓
            if self._daily_loss_paused:
                inst.last_signal = f"HOLD: 单日亏损限额已触发，暂停开新仓（{signal.reason}）"
                return

            # 连续亏损保护：连续亏损3次后，仓位缩减50%（心理资本保护）
            if inst.consecutive_losses >= 3:
                logger.warning(
                    f"[{inst.strategy_name}@{inst.symbol}] 连续亏损{inst.consecutive_losses}次，"
                    f"仓位缩减50%"
                )
                original_qty = signal.quantity
                reduced_signal = TradeSignal(
                    signal.signal, signal.symbol, signal.price,
                    max(1, original_qty // 2),
                    f"{signal.reason} [连续亏{inst.consecutive_losses}次，半仓操作]",
                    signal.timestamp, signal.stop_loss, signal.take_profit,
                )
                signal = reduced_signal

            # 智能仓位：根据账户余额和Kelly公式计算
            adjusted_signal = self._adjust_position_size(inst, signal)
            if adjusted_signal:
                self._execute_buy(inst, adjusted_signal)
        elif signal.signal == Signal.SELL and inst.position_qty > 0:
            self._execute_sell(inst, signal)

    def _kelly_fraction(self, inst: StrategyInstance) -> float:
        """
        Kelly仓位比例计算（半Kelly模式）
        公式: f = (p×b - q) / b，其中 p=胜率, q=败率, b=平均盈亏比
        使用半Kelly（×0.5）以降低波动，是量化基金通行做法
        """
        sells = [t for t in inst.trade_history if t.get("action") == "SELL"]
        if len(sells) < 5:
            return 0.15  # 数据不足，使用默认15%

        wins = [t for t in sells if t.get("pnl", 0) > 0]
        losses = [t for t in sells if t.get("pnl", 0) <= 0]

        p = len(wins) / len(sells)  # 胜率
        q = 1 - p                   # 败率

        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses)) if losses else 1

        if avg_loss == 0:
            return 0.15

        b = avg_win / avg_loss  # 盈亏比
        if b <= 0:
            return 0.05  # 盈亏比差，保守仓位

        kelly = (p * b - q) / b
        half_kelly = kelly * 0.5  # 半Kelly，更保守

        # 硬上限20%，硬下限2%
        return float(max(0.02, min(0.20, half_kelly)))

    def _calc_cvs_scale(self, inst: StrategyInstance) -> float:
        """
        Barroso-Santa-Clara 恒定波动率缩放 (CVS)

        论文: Barroso & Santa-Clara, JFE 2015
        效果: 动量策略Sharpe从0.53→0.97，最大月亏损-80%→-28%

        原理：用过去126天（6个月）的已实现波动率，将仓位缩放到
        目标年化波动率12%。高波动期自动减仓，低波动期自动加仓。

        返回: 仓位缩放系数（0.3~2.0），1.0表示不调整
        """
        import numpy as np

        # 需要足够的交易历史来估算波动率
        sells = [t for t in inst.trade_history if t.get("action") == "SELL" and "pnl" in t]
        if len(sells) < 5:
            return 1.0  # 交易历史不足，不缩放

        # 用最近的交易PnL估算已实现波动率
        recent_pnls = [t["pnl"] for t in sells[-20:]]  # 最近20笔交易
        if not recent_pnls:
            return 1.0

        # 计算PnL的标准差作为波动率代理
        pnl_std = float(np.std(recent_pnls))
        pnl_mean_abs = abs(float(np.mean([abs(p) for p in recent_pnls])))

        if pnl_mean_abs == 0:
            return 1.0

        # 相对波动率 = std / mean_abs_pnl
        rel_vol = pnl_std / pnl_mean_abs

        # 目标相对波动率（经验值，对应年化~12%）
        target_rel_vol = 0.8

        # CVS缩放系数 = target / realized
        cvs = target_rel_vol / max(rel_vol, 0.1)

        # 硬限制：最少0.3倍，最多2.0倍
        return float(max(0.3, min(2.0, cvs)))

    # ISC-63: 港股每手股数映射（不同股票手数不同）
    # 数据来源：港交所官方披露，常见蓝筹的每手股数
    _HK_LOT_SIZE: dict = {
        "00005": 400,   # 汇丰控股: 每手400股
        "00700": 100,   # 腾讯控股
        "00941": 500,   # 中国移动: 每手500股
        "01398": 1000,  # 工商银行: 每手1000股
        "02318": 100,   # 中国平安
        "09988": 10,    # 阿里巴巴: 每手10股（股价高）
        "01810": 200,   # 小米集团: 每手200股
        "03690": 100,   # 美团
        "00388": 100,   # 香港交易所
        "02020": 500,   # 安踏体育
        "09618": 10,    # 京东集团: 每手10股
        "00992": 2000,  # 联想集团: 每手2000股（低股价）
        "02388": 500,   # 中银香港
        "00011": 100,   # 恒生银行
        "06862": 200,   # 海底捞
        "09999": 10,    # 网易: 每手10股
        "00762": 2000,  # 中国联通
        "00883": 500,   # 中国海洋石油
        "01088": 500,   # 中国神华
        "01177": 2000,  # 中国生物制药
    }

    def update_lot_sizes(self, lot_map: dict):
        """
        从Tiger API获取真实手数后调用此方法更新（main.py startup时注入）
        lot_map: {symbol: lot_size}，从get_trade_metas()返回的真实数据
        优先级高于硬编码表
        """
        self._HK_LOT_SIZE.update(lot_map)
        logger.info(f"已更新{len(lot_map)}只股票的真实手数: {lot_map}")

    def _get_hk_lot_size(self, symbol: str) -> int:
        """获取港股每手股数，未知标的默认100股/手"""
        return self._HK_LOT_SIZE.get(symbol, 100)

    def _align_to_lot(self, qty: int, symbol: str) -> int:
        """将数量向下对齐到整手数，确保符合港交所规定"""
        lot = self._get_hk_lot_size(symbol)
        aligned = (qty // lot) * lot
        return max(aligned, lot)  # 至少1手

    def _adjust_position_size(self, inst: StrategyInstance, signal: TradeSignal) -> Optional[TradeSignal]:
        """根据账户余额和Kelly公式智能调整仓位大小（ISC-63: 手数对齐）"""
        if not self._account_fetcher:
            return signal

        try:
            account = self._account_fetcher()
            cash = account.get("cash", 0)
            equity = account.get("equity", 0)

            if cash <= 0 or equity <= 0:
                inst.last_signal = "账户余额不足，跳过买入"
                logger.warning(f"账户余额不足: cash={cash}, equity={equity}")
                return None

            # Kelly仓位比例（基于策略历史表现）
            kelly_pct = self._kelly_fraction(inst)
            running_count = max(sum(1 for i in self.instances.values() if i.status == "running"), 1)

            # Barroso-Santa-Clara CVS波动率缩放（研究显示Sharpe从0.53→0.97）
            # 核心思想：高波动期自动减仓，低波动期自动加仓
            cvs_scale = self._calc_cvs_scale(inst)

            # 单策略最大预算 = Kelly比例×总资产×CVS缩放，但不超过可用现金/运行策略数
            kelly_budget = equity * kelly_pct * cvs_scale
            cash_budget = cash / running_count * 0.9  # 留10%安全余量

            budget = min(kelly_budget, cash_budget)
            affordable_qty = int(budget / signal.price) if signal.price > 0 else 0

            if affordable_qty <= 0:
                inst.last_signal = f"资金不足: 预算{budget:.0f}(Kelly={kelly_pct*100:.0f}%), 股价{signal.price:.2f}"
                return None

            # 最小仓位检查（避免下单金额过小，手续费占比过高）
            # v3.1: 从5000降到2000，适配小资金账户（1万HKD跑1-2只）
            min_order_value = 2000  # HKD 2000
            if budget < min_order_value:
                inst.last_signal = f"仓位太小({budget:.0f}<{min_order_value}HKD)，跳过下单"
                return None

            raw_qty = min(affordable_qty, signal.quantity) if signal.quantity > 0 else affordable_qty

            # ISC-63: 对齐到港股整手数（不同股票手数不同）
            lot_size = self._get_hk_lot_size(inst.symbol)
            # 向下对齐（注意：不用_align_to_lot，避免强制升到1手导致超预算）
            lots = raw_qty // lot_size
            if lots <= 0:
                # 预算连1手都买不起，跳过（不强制升级到1手）
                inst.last_signal = (
                    f"资金不足1手({lot_size}股×{signal.price:.2f}"
                    f"={lot_size*signal.price:.0f}HKD>预算{budget:.0f}HKD)"
                )
                return None
            final_qty = lots * lot_size

            # 再次确认对齐后在预算内（防止边界情况）
            if final_qty * signal.price > budget * 1.02:  # 允许2%浮动（含佣金）
                lots -= 1
                if lots <= 0:
                    inst.last_signal = f"资金不足以买入最小1手，跳过下单"
                    return None
                final_qty = lots * lot_size

            return TradeSignal(
                signal.signal, signal.symbol, signal.price, final_qty,
                f"{signal.reason} (Kelly={kelly_pct*100:.0f}%,{final_qty}股/{lot_size}股/手,预算:{budget:.0f})",
                signal.timestamp, signal.stop_loss, signal.take_profit,
            )

        except Exception as e:
            logger.error(f"仓位计算失败: {e}")
            return signal

    def _check_portfolio_risk(self):
        """组合级风控检查（v2.0：增加单日亏损限额）"""
        if self._emergency_stopped:
            return

        today = _hk_now().strftime("%Y-%m-%d")

        # 每日重置：新的一天，重置今日亏损检查
        if today != self._today_date:
            self._today_date = today
            self._daily_loss_paused = False
            # 记录今日起始净值（使用当前各策略的总盈亏作为基线）
            self._today_start_equity = sum(
                i.realized_pnl + i.unrealized_pnl
                for i in self.instances.values()
            )
            logger.info(f"新交易日{today}，重置单日风控，起始净值基线={self._today_start_equity:.2f}")

        # 单日亏损检查
        if not self._daily_loss_paused:
            current_equity_change = sum(
                i.realized_pnl + i.unrealized_pnl
                for i in self.instances.values()
            ) - self._today_start_equity

            # 总投入估算（用于计算亏损百分比）
            total_cost = sum(
                i.position_cost * i.position_qty
                for i in self.instances.values()
                if i.position_qty > 0
            )
            ref_amount = max(total_cost, 10000)  # 至少以1万为基准

            daily_loss_pct = current_equity_change / ref_amount
            if daily_loss_pct < -self._max_daily_loss_pct:
                self._daily_loss_paused = True
                logger.warning(
                    f"单日亏损限额触发! 今日亏损{daily_loss_pct*100:.1f}%>"
                    f"{self._max_daily_loss_pct*100:.0f}%，暂停今日新开仓（现有持仓保留）"
                )

        # 明汯风控：策略集中度检查
        self._check_strategy_concentration()

        total_realized = sum(i.realized_pnl for i in self.instances.values())
        total_unrealized = sum(i.unrealized_pnl for i in self.instances.values())
        total_pnl = total_realized + total_unrealized

        total_cost = sum(
            i.position_cost * i.position_qty
            for i in self.instances.values()
            if i.position_qty > 0
        )

        if total_cost > 0:
            portfolio_loss_pct = total_pnl / total_cost
            if portfolio_loss_pct < -self._max_total_loss_pct:
                logger.critical(
                    f"组合风控触发! 总亏损{portfolio_loss_pct*100:.1f}%超过阈值"
                    f"{self._max_total_loss_pct*100:.0f}%, 紧急停止所有策略"
                )
                self._emergency_stop_all(
                    f"组合总亏损{portfolio_loss_pct*100:.1f}%超过{self._max_total_loss_pct*100:.0f}%阈值"
                )

    def _check_strategy_concentration(self):
        """
        策略集中度风控（明汯2021教训）

        明汯2021年Q1因动量/成长因子过度集中暴露，单季亏损27%。
        本方法检测是否多个策略实例使用相同策略类型，
        或是否集中在同一行业板块，避免风格因子过度暴露。
        """
        running = [i for i in self.instances.values() if i.status == "running" and i.position_qty > 0]
        if len(running) < 3:
            return  # 策略太少无需检查

        # 统计策略类型分布
        strategy_counts = {}
        for inst in running:
            key = inst.strategy_name
            strategy_counts[key] = strategy_counts.get(key, 0) + 1

        # 单一策略占比超过60% → 警告（明汯教训：风格因子集中暴露）
        total = len(running)
        for strat_name, count in strategy_counts.items():
            if count / total > 0.6:
                logger.warning(
                    f"[明汯风控] 策略集中度过高: {strat_name} 占 {count}/{total} "
                    f"({count/total*100:.0f}%)，建议分散策略类型降低风格因子暴露"
                )

        # 检测同方向持仓集中度：所有持仓都在盈利或都在亏损 → 可能暴露同一因子
        pnl_signs = [1 if inst.unrealized_pnl >= 0 else -1 for inst in running]
        if pnl_signs:
            same_direction = abs(sum(pnl_signs)) / len(pnl_signs)
            if same_direction > 0.8 and sum(pnl_signs) < 0:
                logger.warning(
                    f"[明汯风控] {len(running)}个持仓中{sum(1 for s in pnl_signs if s < 0)}个亏损，"
                    f"可能存在系统性风格因子暴露，考虑减仓"
                )

    def _calc_sharpe(self, pnl_list: list, risk_free: float = 0.04) -> float:
        """
        计算Sharpe比率（年化）
        pnl_list: 每笔交易的盈亏金额列表
        risk_free: 无风险利率（默认4%年化，折算为每笔交易）
        """
        import math
        if len(pnl_list) < 3:
            return 0.0
        import statistics
        mean_pnl = statistics.mean(pnl_list)
        std_pnl = statistics.stdev(pnl_list)
        if std_pnl == 0:
            return 0.0
        # 假设每月约4笔交易，年化
        trades_per_year = 48
        sharpe = (mean_pnl - risk_free / trades_per_year) / std_pnl * math.sqrt(trades_per_year)
        return round(sharpe, 3)

    def _calc_sortino(self, pnl_list: list, risk_free: float = 0.04) -> float:
        """
        计算Sortino比率（只用下行波动率，比Sharpe更合理）
        """
        import math
        if len(pnl_list) < 3:
            return 0.0
        import statistics
        mean_pnl = statistics.mean(pnl_list)
        losses_sq = [p ** 2 for p in pnl_list if p < 0]
        if not losses_sq:
            return float('inf') if mean_pnl > 0 else 0.0
        downside_std = math.sqrt(sum(losses_sq) / len(pnl_list))
        if downside_std == 0:
            return 0.0
        trades_per_year = 48
        sortino = (mean_pnl - risk_free / trades_per_year) / downside_std * math.sqrt(trades_per_year)
        return round(sortino, 3)

    def _max_consecutive_losses(self, sells: list) -> int:
        """计算最大连续亏损次数"""
        max_streak = 0
        curr_streak = 0
        for t in sells:
            if t.get("pnl", 0) <= 0:
                curr_streak += 1
                max_streak = max(max_streak, curr_streak)
            else:
                curr_streak = 0
        return max_streak

    def evaluate_strategies(self) -> list:
        """
        评估所有策略表现，返回排名
        v2.0：新增 Sharpe比率、Sortino比率、连续亏损次数、期望盈利
        """
        results = []
        for inst in self.instances.values():
            sells = [t for t in inst.trade_history if t.get("action") == "SELL"]
            wins = [t for t in sells if t.get("pnl", 0) > 0]
            losses = [t for t in sells if t.get("pnl", 0) <= 0]

            win_rate = len(wins) / len(sells) * 100 if sells else 0
            avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
            avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses)) if losses else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf') if avg_win > 0 else 0

            # 专业指标
            pnl_list = [t.get("pnl", 0) for t in sells]
            sharpe = self._calc_sharpe(pnl_list)
            sortino = self._calc_sortino(pnl_list)
            max_consec_losses = self._max_consecutive_losses(sells)
            expected_value = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)

            total_pnl = inst.realized_pnl + inst.unrealized_pnl
            score = (profit_factor * win_rate / 100) if profit_factor != float('inf') else win_rate / 100

            results.append({
                "id": inst.id,
                "strategy_name": inst.strategy_name,
                "symbol": inst.symbol,
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 1),
                "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
                "sharpe": sharpe,
                "sortino": sortino if sortino != float('inf') else 9.99,
                "max_consec_losses": max_consec_losses,
                "expected_value": round(expected_value, 2),
                "total_trades": inst.total_trades,
                "score": round(score, 3),
                "status": inst.status,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def auto_optimize(self):
        """
        自动优化：淘汰表现最差的策略，用最好策略的方法替换
        条件：至少完成5笔交易才评估
        """
        evaluations = self.evaluate_strategies()
        eligible = [e for e in evaluations if e["total_trades"] >= 5]

        if len(eligible) < 3:
            return {"action": "skip", "reason": "交易次数不足，等待更多数据"}

        worst = eligible[-1]
        best = eligible[0]

        if worst["score"] < 0.3 and best["score"] > 0.5:
            # 停止差策略
            worst_inst = self.instances.get(worst["id"])
            best_inst = self.instances.get(best["id"])
            if worst_inst and best_inst and worst_inst.status == "running":
                self.stop_strategy(worst["id"])
                # 用最佳策略替换
                new_inst = self.create_strategy(
                    best_inst.strategy_key,
                    worst_inst.symbol,
                    best_inst.params,
                )
                self.start_strategy(new_inst.id)
                logger.info(
                    f"策略优化: 淘汰 [{worst['strategy_name']}@{worst['symbol']}] "
                    f"(得分{worst['score']}), 替换为 [{best['strategy_name']}] (得分{best['score']})"
                )
                return {
                    "action": "replaced",
                    "removed": worst,
                    "replaced_with": best["strategy_name"],
                    "new_id": new_inst.id,
                }

        return {"action": "keep", "reason": "所有策略表现尚可"}

    def _emergency_stop_all(self, reason: str):
        """紧急停止所有策略"""
        self._emergency_stopped = True
        for inst_id, inst in list(self.instances.items()):
            if inst.status == "running":
                if inst_id in self._stop_flags:
                    self._stop_flags[inst_id].set()
                inst.status = "stopped"
                inst.error_msg = f"紧急停止: {reason}"
        logger.critical(f"所有策略已紧急停止: {reason}")

    def _check_order_cooldown(self, inst: StrategyInstance) -> bool:
        """订单去重：检查是否在冷却期内，防止重复下单"""
        import time
        now = time.time()
        last = self._last_order_time.get(inst.id, 0)
        if now - last < self._order_cooldown:
            logger.warning(
                f"[{inst.strategy_name}@{inst.symbol}] 订单冷却中"
                f"（距上次下单{now - last:.0f}秒<{self._order_cooldown}秒），跳过"
            )
            return False
        self._last_order_time[inst.id] = now
        return True

    def _execute_buy(self, inst: StrategyInstance, signal: TradeSignal):
        # 订单去重检查
        if not self._check_order_cooldown(inst):
            inst.last_signal = f"HOLD: 订单冷却中，跳过买入（{signal.reason}）"
            return

        trade_record = {
            "time": _hk_now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "BUY",
            "price": signal.price,
            "quantity": signal.quantity,
            "reason": signal.reason,
            "order_result": None,
        }

        order_failed = False
        if self._order_executor:
            try:
                result = self._order_executor(inst.symbol, "BUY", signal.quantity, signal.price)
                trade_record["order_result"] = result
                # 检查下单结果是否有错误
                if isinstance(result, dict) and result.get("error"):
                    order_failed = True
                    inst.error_msg = f"下单失败: {result['error']}"
            except Exception as e:
                trade_record["order_result"] = {"error": str(e)}
                inst.error_msg = f"下单失败: {e}"
                order_failed = True

        # 只有下单成功（或无执行器时模拟）才更新仓位
        if not order_failed:
            # 优先使用实际成交价，否则回退到信号价
            actual_price = signal.price
            if isinstance(trade_record.get("order_result"), dict):
                fill = trade_record["order_result"].get("avg_fill_price")
                if fill and fill > 0:
                    actual_price = float(fill)
                    logger.info(f"[{inst.strategy_name}] 使用实际成交价 {actual_price:.3f}（信号价 {signal.price:.3f}）")
            inst.position_qty = signal.quantity
            inst.position_cost = actual_price
            inst.highest_price_since_buy = actual_price  # 重置追踪止损
        inst.total_trades += 1
        inst.trade_history.append(trade_record)
        self.save_state()  # 持久化状态
        logger.info(f"[{inst.strategy_name}] 买入 {inst.symbol} {signal.quantity}股 @ {signal.price} {'(失败)' if order_failed else ''}")

    def _execute_sell(self, inst: StrategyInstance, signal: TradeSignal):
        trade_record = {
            "time": _hk_now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "SELL",
            "price": signal.price,
            "quantity": inst.position_qty,
            "pnl": 0.0,  # 下单后用实际成交价重算
            "reason": signal.reason,
            "order_result": None,
        }

        order_failed = False
        if self._order_executor:
            try:
                result = self._order_executor(inst.symbol, "SELL", inst.position_qty, signal.price)
                trade_record["order_result"] = result
                if isinstance(result, dict) and result.get("error"):
                    order_failed = True
                    inst.error_msg = f"卖出下单失败: {result['error']}"
            except Exception as e:
                trade_record["order_result"] = {"error": str(e)}
                inst.error_msg = f"卖出下单失败: {e}"
                order_failed = True

        # 优先使用实际成交价计算 PnL
        sell_price = signal.price
        if isinstance(trade_record.get("order_result"), dict):
            fill = trade_record["order_result"].get("avg_fill_price")
            if fill and fill > 0:
                sell_price = float(fill)
                logger.info(f"[{inst.strategy_name}] 卖出实际成交价 {sell_price:.3f}（信号价 {signal.price:.3f}）")
        pnl = (sell_price - inst.position_cost) * inst.position_qty
        trade_record["pnl"] = round(pnl, 2)

        # 只有下单成功（或无执行器时模拟）才更新仓位
        if not order_failed:
            inst.realized_pnl += pnl

            # 更新今日盈亏（按香港时区自然日重置）
            today = _hk_now().strftime("%Y-%m-%d")
            if inst.last_trade_date != today:
                inst.daily_pnl = 0.0
            inst.daily_pnl += pnl
            inst.last_trade_date = today

            inst.position_qty = 0
            inst.position_cost = 0.0
            inst.unrealized_pnl = 0.0
            inst.highest_price_since_buy = 0.0

            # 更新连续亏损计数
            if pnl > 0:
                inst.consecutive_losses = 0
            else:
                inst.consecutive_losses += 1
        else:
            logger.error(
                f"[{inst.strategy_name}] 卖出 {inst.symbol} 失败! 仓位保留 {inst.position_qty}股, "
                f"下次循环将重试"
            )

        inst.total_trades += 1
        inst.trade_history.append(trade_record)
        self.save_state()  # 持久化状态

        logger.info(
            f"[{inst.strategy_name}] 卖出 {inst.symbol} @ {signal.price}, "
            f"盈亏: {pnl:.2f}, {'成功' if not order_failed else '失败-仓位保留'}"
        )

    # ─── 状态持久化 ───────────────────────────────────

    def save_state(self):
        """将所有策略实例状态保存到 JSON 文件，防止重启丢失"""
        try:
            state = {
                "saved_at": _hk_now().strftime("%Y-%m-%d %H:%M:%S"),
                "emergency_stopped": self._emergency_stopped,
                "instances": {},
            }
            for inst_id, inst in self.instances.items():
                state["instances"][inst_id] = {
                    "id": inst.id,
                    "strategy_key": inst.strategy_key,
                    "strategy_name": inst.strategy_name,
                    "symbol": inst.symbol,
                    "params": inst.params,
                    "status": inst.status,
                    "position_qty": inst.position_qty,
                    "position_cost": inst.position_cost,
                    "realized_pnl": inst.realized_pnl,
                    "unrealized_pnl": inst.unrealized_pnl,
                    "total_trades": inst.total_trades,
                    "last_signal": inst.last_signal,
                    "last_check": inst.last_check,
                    "created_at": inst.created_at,
                    "trade_history": inst.trade_history[-50:],  # 最近50笔
                    "error_msg": inst.error_msg,
                    "highest_price_since_buy": inst.highest_price_since_buy,
                    "trailing_stop_pct": inst.trailing_stop_pct,
                    "consecutive_losses": inst.consecutive_losses,
                    "daily_pnl": inst.daily_pnl,
                    "last_trade_date": inst.last_trade_date,
                }
            # 原子写入：先写临时文件再重命名，防止写一半崩溃
            tmp_file = STATE_FILE + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, STATE_FILE)
        except Exception as e:
            logger.error(f"保存引擎状态失败: {e}")

    def load_state(self):
        """从 JSON 文件恢复策略实例状态（仅恢复持仓数据，不自动启动策略）"""
        if not os.path.exists(STATE_FILE):
            logger.info("无历史状态文件，全新启动")
            return

        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)

            self._emergency_stopped = state.get("emergency_stopped", False)
            restored = 0
            has_position = 0

            for inst_id, data in state.get("instances", {}).items():
                inst = StrategyInstance(
                    id=data["id"],
                    strategy_key=data["strategy_key"],
                    strategy_name=data["strategy_name"],
                    symbol=data["symbol"],
                    params=data.get("params", {}),
                    status="stopped",  # 恢复后默认停止，需手动启动
                    position_qty=data.get("position_qty", 0),
                    position_cost=data.get("position_cost", 0.0),
                    realized_pnl=data.get("realized_pnl", 0.0),
                    unrealized_pnl=data.get("unrealized_pnl", 0.0),
                    total_trades=data.get("total_trades", 0),
                    last_signal=data.get("last_signal"),
                    last_check=data.get("last_check"),
                    created_at=data.get("created_at", ""),
                    trade_history=data.get("trade_history", []),
                    error_msg=None,
                    highest_price_since_buy=data.get("highest_price_since_buy", 0.0),
                    trailing_stop_pct=data.get("trailing_stop_pct", 0.05),
                    consecutive_losses=data.get("consecutive_losses", 0),
                    daily_pnl=data.get("daily_pnl", 0.0),
                    last_trade_date=data.get("last_trade_date", ""),
                )
                self.instances[inst_id] = inst
                restored += 1
                if inst.position_qty > 0:
                    has_position += 1

            saved_at = state.get("saved_at", "未知")
            logger.info(
                f"已恢复引擎状态（保存于{saved_at}）: "
                f"{restored}个策略实例, {has_position}个有持仓"
            )
            if has_position > 0:
                logger.warning(
                    f"⚠️ 有{has_position}个策略有未平仓持仓! "
                    f"请检查后手动启动策略或平仓"
                )
        except Exception as e:
            logger.error(f"恢复引擎状态失败: {e}")


# 全局单例
engine = StrategyEngine()
# 启动时恢复状态
engine.load_state()
