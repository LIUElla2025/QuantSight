"""
订单执行优化模块 — TWAP/VWAP拆单、冰山订单、滑点控制

核心问题: 大单直接下会造成市场冲击(Market Impact),
实际成交价远差于预期价格。拆单算法将大单分解为小单,
分时段执行, 最小化市场冲击。

数学模型:
    市场冲击模型 (Almgren-Chriss):
    Impact = sigma * sqrt(V/ADV) * (V/ADV)^0.6
    其中:
    - sigma = 日波动率
    - V = 订单量
    - ADV = 日均成交量
    - 0.6 = 冲击指数 (实证值0.5-0.8)

    TWAP最优切片:
    slice_qty = total_qty / n_slices
    slice_interval = total_time / n_slices

    VWAP最优切片:
    slice_qty_i = total_qty * (expected_volume_i / sum(expected_volume))
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrderSlice:
    """单个子订单"""
    slice_id: int
    quantity: int
    scheduled_time: datetime
    price_limit: Optional[float] = None
    executed: bool = False
    executed_price: Optional[float] = None
    executed_qty: Optional[int] = None
    executed_time: Optional[datetime] = None
    slippage_bps: float = 0.0


@dataclass
class ExecutionPlan:
    """执行计划"""
    algorithm: str
    total_quantity: int
    side: str  # "BUY" or "SELL"
    slices: List[OrderSlice] = field(default_factory=list)
    estimated_impact_bps: float = 0.0
    estimated_cost: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════
# 1. 市场冲击估算
# ═══════════════════════════════════════════════════════════════

def estimate_market_impact(
    order_qty: int,
    adv: float,
    daily_volatility: float,
    price: float,
    impact_exponent: float = 0.6,
) -> Dict:
    """
    估算市场冲击 (Almgren-Chriss模型简化版)

    数学公式:
        participation_rate = order_qty / adv
        impact_bps = 10000 * daily_volatility * sqrt(participation_rate) * participation_rate^(impact_exponent-0.5)

    参考值 (港股大盘股):
        参与率 < 5%: 冲击 < 5bps
        参与率 5-10%: 冲击 5-15bps
        参与率 10-20%: 冲击 15-40bps
        参与率 > 20%: 冲击 > 40bps (应避免)

    参数:
        order_qty: 订单总量(股)
        adv: 20日平均日成交量(股)
        daily_volatility: 日波动率 (如0.02=2%)
        price: 当前价格
        impact_exponent: 冲击指数

    返回: {impact_bps, impact_cost, participation_rate, recommendation}
    """
    if adv <= 0 or order_qty <= 0:
        return {
            "impact_bps": 0, "impact_cost": 0,
            "participation_rate": 0, "recommendation": "无法估算"
        }

    participation_rate = order_qty / adv
    impact_bps = (
        10000 * daily_volatility *
        np.sqrt(participation_rate) *
        participation_rate ** (impact_exponent - 0.5)
    )
    impact_cost = price * order_qty * impact_bps / 10000

    # 推荐
    if participation_rate < 0.05:
        recommendation = "可直接下单, 冲击较小"
        algo = "DIRECT"
    elif participation_rate < 0.10:
        recommendation = "建议使用TWAP, 分5-10个切片"
        algo = "TWAP"
    elif participation_rate < 0.20:
        recommendation = "建议使用VWAP, 分10-20个切片"
        algo = "VWAP"
    elif participation_rate < 0.30:
        recommendation = "建议使用冰山订单, 隐藏真实量"
        algo = "ICEBERG"
    else:
        recommendation = "参与率过高! 建议分多日执行或降低订单量"
        algo = "MULTI_DAY"

    return {
        "impact_bps": round(impact_bps, 2),
        "impact_cost": round(impact_cost, 2),
        "participation_rate": round(participation_rate * 100, 2),
        "recommendation": recommendation,
        "suggested_algo": algo,
    }


# ═══════════════════════════════════════════════════════════════
# 2. TWAP (时间加权平均价格) 拆单
# ═══════════════════════════════════════════════════════════════

def create_twap_plan(
    total_qty: int,
    side: str,
    price: float,
    start_time: datetime,
    duration_minutes: int = 120,
    n_slices: int = 10,
    randomize: bool = True,
    random_pct: float = 0.2,
    price_limit_offset_bps: float = 10,
) -> ExecutionPlan:
    """
    TWAP拆单计划

    将大单均匀分割到指定时间段内执行。
    可选随机化 (避免被算法探测器识别)。

    数学公式:
        base_qty_per_slice = total_qty / n_slices
        actual_qty_i = base_qty * (1 + uniform(-random_pct, random_pct))
        interval = duration / n_slices

    港股TWAP最佳实践:
        - 持续时间: 建议30分钟至2小时
        - 切片数: 10-20个
        - 随机化: 开启, 幅度20%
        - 避开开盘前15分钟和收盘前5分钟
        - 港股交易时段: 09:30-12:00, 13:00-16:00

    参数:
        total_qty: 总量(股), 港股最小交易单位通常为手(100股)
        side: "BUY" or "SELL"
        price: 当前价格
        start_time: 开始时间
        duration_minutes: 执行持续时间(分钟)
        n_slices: 切片数
        randomize: 是否随机化切片大小
        random_pct: 随机化幅度
        price_limit_offset_bps: 限价偏移(基点)

    返回: ExecutionPlan
    """
    plan = ExecutionPlan(
        algorithm="TWAP",
        total_quantity=total_qty,
        side=side,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=duration_minutes),
    )

    base_qty = total_qty // n_slices
    remainder = total_qty % n_slices
    interval = timedelta(minutes=duration_minutes / n_slices)

    # 价格限制: 买单设上限, 卖单设下限
    if side == "BUY":
        price_limit = price * (1 + price_limit_offset_bps / 10000)
    else:
        price_limit = price * (1 - price_limit_offset_bps / 10000)

    allocated = 0
    for i in range(n_slices):
        qty = base_qty + (1 if i < remainder else 0)

        if randomize and i > 0 and i < n_slices - 1:
            # 随机化中间切片 (首尾保持稳定)
            random_factor = 1.0 + np.random.uniform(-random_pct, random_pct)
            qty = max(1, int(qty * random_factor))

        # 最后一个切片调整确保总量正确
        if i == n_slices - 1:
            qty = total_qty - allocated

        scheduled = start_time + interval * i

        plan.slices.append(OrderSlice(
            slice_id=i + 1,
            quantity=qty,
            scheduled_time=scheduled,
            price_limit=round(price_limit, 2),
        ))
        allocated += qty

    return plan


# ═══════════════════════════════════════════════════════════════
# 3. VWAP (成交量加权平均价格) 拆单
# ═══════════════════════════════════════════════════════════════

# 港股典型日内成交量分布 (占全天成交量的比例)
# 数据来源: HKEX 2024年统计
HK_INTRADAY_VOLUME_PROFILE = {
    "09:30": 0.08, "09:45": 0.06, "10:00": 0.05, "10:15": 0.04,
    "10:30": 0.04, "10:45": 0.03, "11:00": 0.03, "11:15": 0.03,
    "11:30": 0.04, "11:45": 0.05,
    # 午间休市 12:00-13:00
    "13:00": 0.06, "13:15": 0.05, "13:30": 0.04, "13:45": 0.04,
    "14:00": 0.03, "14:15": 0.03, "14:30": 0.03, "14:45": 0.04,
    "15:00": 0.04, "15:15": 0.05, "15:30": 0.06, "15:45": 0.11,
}


def create_vwap_plan(
    total_qty: int,
    side: str,
    price: float,
    start_time: datetime,
    end_time: datetime,
    volume_profile: Optional[Dict[str, float]] = None,
    price_limit_offset_bps: float = 15,
    min_slice_qty: int = 100,
) -> ExecutionPlan:
    """
    VWAP拆单计划

    根据历史日内成交量分布, 在成交量大的时段下更多量,
    目标是使执行均价接近市场VWAP。

    数学公式:
        expected_volume_fraction_i = historical_volume_i / sum(historical_volume)
        slice_qty_i = total_qty * expected_volume_fraction_i
        调整: 保证每个切片 >= min_slice_qty

    港股VWAP策略要点:
        - 开盘和收盘时段成交量最大 (U型分布)
        - 港股收盘前15分钟约占全天11%的成交量
        - 午间休市(12:00-13:00)不交易
        - VWAP优于TWAP的场景: 大盘蓝筹股

    参数:
        total_qty: 总量(股)
        side: "BUY" or "SELL"
        price: 当前价格
        start_time: 开始时间
        end_time: 结束时间
        volume_profile: 日内成交量分布, None则用默认港股分布
        price_limit_offset_bps: 限价偏移(基点)
        min_slice_qty: 每个切片最小数量

    返回: ExecutionPlan
    """
    if volume_profile is None:
        volume_profile = HK_INTRADAY_VOLUME_PROFILE

    plan = ExecutionPlan(
        algorithm="VWAP",
        total_quantity=total_qty,
        side=side,
        start_time=start_time,
        end_time=end_time,
    )

    # 筛选时间范围内的时段
    start_str = start_time.strftime("%H:%M")
    end_str = end_time.strftime("%H:%M")

    active_slots = {
        k: v for k, v in volume_profile.items()
        if start_str <= k <= end_str
    }

    if not active_slots:
        # 如果没有匹配的时段, 退化为TWAP
        return create_twap_plan(total_qty, side, price, start_time)

    # 归一化权重
    total_weight = sum(active_slots.values())
    if total_weight == 0:
        total_weight = 1

    # 价格限制
    if side == "BUY":
        price_limit = price * (1 + price_limit_offset_bps / 10000)
    else:
        price_limit = price * (1 - price_limit_offset_bps / 10000)

    allocated = 0
    slot_list = sorted(active_slots.items())

    for i, (time_slot, weight) in enumerate(slot_list):
        fraction = weight / total_weight
        qty = max(min_slice_qty, int(total_qty * fraction))

        # 最后一个切片调整
        if i == len(slot_list) - 1:
            qty = total_qty - allocated

        # 解析时间
        hour, minute = map(int, time_slot.split(":"))
        scheduled = start_time.replace(hour=hour, minute=minute, second=0)

        plan.slices.append(OrderSlice(
            slice_id=i + 1,
            quantity=qty,
            scheduled_time=scheduled,
            price_limit=round(price_limit, 2),
        ))
        allocated += qty

    return plan


# ═══════════════════════════════════════════════════════════════
# 4. 冰山订单 (Iceberg Order)
# ═══════════════════════════════════════════════════════════════

def create_iceberg_plan(
    total_qty: int,
    side: str,
    price: float,
    visible_ratio: float = 0.1,
    price_improve_bps: float = 2,
    refill_threshold: float = 0.3,
    max_visible_qty: int = 5000,
) -> ExecutionPlan:
    """
    冰山订单计划

    只显示总量的一小部分(冰山顶端), 成交后自动补单。
    目的: 隐藏真实订单量, 避免被其他算法探测。

    工作原理:
        1. 挂出 visible_qty = total_qty * visible_ratio 的限价单
        2. 当挂单成交超过 refill_threshold 时, 自动补单
        3. 每次补单微调价格 (改善成交概率)
        4. 重复直到总量全部成交

    港股冰山订单要点:
        - 港交所支持原生冰山订单 (Enhanced Limit Order)
        - 显示量建议为总量的5-15%
        - 最大显示量不超过5000股 (避免引起注意)
        - 适用于中小盘股 (流动性较差)

    参数:
        total_qty: 总量
        side: "BUY" or "SELL"
        price: 目标价格
        visible_ratio: 显示比例 (默认10%)
        price_improve_bps: 每次补单的价格改善(基点)
        refill_threshold: 补单触发阈值(已成交比例)
        max_visible_qty: 最大显示量

    返回: ExecutionPlan (包含多轮补单计划)
    """
    plan = ExecutionPlan(
        algorithm="ICEBERG",
        total_quantity=total_qty,
        side=side,
    )

    visible_qty = min(int(total_qty * visible_ratio), max_visible_qty)
    visible_qty = max(visible_qty, 100)  # 最少100股

    n_rounds = (total_qty + visible_qty - 1) // visible_qty
    remaining = total_qty

    for i in range(n_rounds):
        qty = min(visible_qty, remaining)

        # 每轮微调价格
        if side == "BUY":
            # 买单: 逐步提高价格以改善成交率
            slice_price = price * (1 + i * price_improve_bps / 10000)
        else:
            # 卖单: 逐步降低价格
            slice_price = price * (1 - i * price_improve_bps / 10000)

        plan.slices.append(OrderSlice(
            slice_id=i + 1,
            quantity=qty,
            scheduled_time=datetime.now(),  # 实际由成交触发
            price_limit=round(slice_price, 2),
        ))
        remaining -= qty

    plan.estimated_impact_bps = estimate_market_impact(
        visible_qty, total_qty * 10, 0.02, price
    )["impact_bps"]

    return plan


# ═══════════════════════════════════════════════════════════════
# 5. 滑点控制与执行质量评估
# ═══════════════════════════════════════════════════════════════

def calculate_slippage(
    planned_price: float,
    executed_price: float,
    side: str,
) -> float:
    """
    计算滑点 (基点)

    数学公式:
        买入滑点 = (executed_price - planned_price) / planned_price * 10000
        卖出滑点 = (planned_price - executed_price) / planned_price * 10000
        正值 = 不利滑点, 负值 = 有利滑点

    参数:
        planned_price: 计划价格
        executed_price: 实际成交价
        side: "BUY" or "SELL"

    返回: 滑点(基点), 正值表示不利
    """
    if planned_price <= 0:
        return 0.0

    if side == "BUY":
        slippage = (executed_price - planned_price) / planned_price * 10000
    else:
        slippage = (planned_price - executed_price) / planned_price * 10000

    return round(slippage, 2)


def evaluate_execution_quality(
    plan: ExecutionPlan,
    market_vwap: float,
) -> Dict:
    """
    评估执行质量

    指标:
    1. VWAP差距: 执行均价 vs 市场VWAP
    2. 实现滑点: 执行均价 vs 计划价格
    3. 完成率: 已执行量 / 计划总量
    4. 时间合规性: 是否按计划时间执行

    参数:
        plan: 执行计划(含已成交记录)
        market_vwap: 市场当日VWAP

    返回: 质量评估报告
    """
    executed_slices = [s for s in plan.slices if s.executed]

    if not executed_slices:
        return {"status": "未执行", "metrics": {}}

    total_executed_qty = sum(s.executed_qty or 0 for s in executed_slices)
    if total_executed_qty == 0:
        return {"status": "成交量为零", "metrics": {}}

    # 执行均价
    total_cost = sum(
        (s.executed_price or 0) * (s.executed_qty or 0)
        for s in executed_slices
    )
    avg_exec_price = total_cost / total_executed_qty

    # VWAP差距 (基点)
    vwap_gap = calculate_slippage(market_vwap, avg_exec_price, plan.side)

    # 完成率
    fill_rate = total_executed_qty / plan.total_quantity * 100

    # 各切片滑点
    slice_slippages = [s.slippage_bps for s in executed_slices]

    return {
        "status": "完成" if fill_rate >= 99 else "部分完成",
        "metrics": {
            "avg_exec_price": round(avg_exec_price, 4),
            "market_vwap": round(market_vwap, 4),
            "vwap_gap_bps": vwap_gap,
            "fill_rate_pct": round(fill_rate, 2),
            "total_executed_qty": total_executed_qty,
            "num_slices_executed": len(executed_slices),
            "avg_slippage_bps": round(np.mean(slice_slippages), 2) if slice_slippages else 0,
            "max_slippage_bps": round(max(slice_slippages), 2) if slice_slippages else 0,
        },
    }


# ═══════════════════════════════════════════════════════════════
# 6. 智能路由器 (自动选择算法)
# ═══════════════════════════════════════════════════════════════

def smart_order_router(
    total_qty: int,
    side: str,
    price: float,
    adv: float,
    daily_volatility: float,
    urgency: str = "normal",
    start_time: Optional[datetime] = None,
) -> ExecutionPlan:
    """
    智能订单路由器

    根据订单大小、流动性和紧急程度自动选择最优执行算法。

    决策逻辑:
    | 参与率     | 紧急程度 | 推荐算法   |
    |-----------|---------|-----------|
    | < 5%      | 任何    | 直接下单   |
    | 5-10%     | 高      | TWAP(短)  |
    | 5-10%     | 正常    | TWAP(标准) |
    | 10-20%    | 任何    | VWAP      |
    | 20-30%    | 任何    | 冰山订单   |
    | > 30%     | 任何    | 分日执行   |

    参数:
        total_qty: 总量
        side: "BUY" or "SELL"
        price: 当前价格
        adv: 20日平均日成交量
        daily_volatility: 日波动率
        urgency: "low" | "normal" | "high"
        start_time: 开始时间 (默认当前)

    返回: 最优ExecutionPlan
    """
    if start_time is None:
        start_time = datetime.now().replace(second=0, microsecond=0)

    impact = estimate_market_impact(total_qty, adv, daily_volatility, price)
    participation = total_qty / adv if adv > 0 else 1.0

    if participation < 0.05:
        # 直接下单
        plan = ExecutionPlan(
            algorithm="DIRECT",
            total_quantity=total_qty,
            side=side,
            start_time=start_time,
        )
        plan.slices.append(OrderSlice(
            slice_id=1,
            quantity=total_qty,
            scheduled_time=start_time,
            price_limit=price,
        ))
        return plan

    elif participation < 0.10:
        if urgency == "high":
            return create_twap_plan(
                total_qty, side, price, start_time,
                duration_minutes=30, n_slices=5
            )
        else:
            return create_twap_plan(
                total_qty, side, price, start_time,
                duration_minutes=120, n_slices=10
            )

    elif participation < 0.20:
        end_time = start_time + timedelta(hours=3)
        return create_vwap_plan(
            total_qty, side, price, start_time, end_time
        )

    elif participation < 0.30:
        return create_iceberg_plan(
            total_qty, side, price,
            visible_ratio=0.08,
        )

    else:
        # 分日执行: 每天执行ADV的15%
        daily_qty = int(adv * 0.15)
        n_days = (total_qty + daily_qty - 1) // daily_qty
        logger.warning(
            f"参与率{participation*100:.0f}%过高, "
            f"建议分{n_days}天执行, 每天{daily_qty}股"
        )
        # 返回第一天的计划
        first_day_qty = min(daily_qty, total_qty)
        return create_twap_plan(
            first_day_qty, side, price, start_time,
            duration_minutes=300, n_slices=20
        )
