"""
Tiger OpenAPI Python SDK 参考手册（程序内嵌版）
来源：https://quant.itigerup.com/openapi/zh/python/ 及 https://docs.itigerup.com
整理日期：2026-03-13  |  SDK 版本：3.4.6

本模块将 Tiger API 的关键参数、枚举、错误码、频率限制等
以 Python 常量/字典形式保存，供策略引擎和下单模块直接引用。
"""

# ═══════════════════════════════════════════════════
#  支持的市场和产品
# ═══════════════════════════════════════════════════
SUPPORTED_MARKETS = {
    "US": {"products": ["股票", "ETF", "期权", "期货"], "currency": "USD"},
    "HK": {"products": ["股票", "ETF", "期权", "期货", "窝轮", "牛熊证"], "currency": "HKD"},
    "SG": {"products": ["股票", "ETF", "期货"], "currency": "SGD"},
    "AU": {"products": ["股票", "ETF"], "currency": "AUD"},
}

# ═══════════════════════════════════════════════════
#  交易时间（港股）
# ═══════════════════════════════════════════════════
HK_TRADING_HOURS = {
    "pre_open_auction": ("09:00", "09:20"),      # 开市前竞价
    "pre_open_matching": ("09:20", "09:28"),      # 对盘前时段
    "random_close_auction": ("09:28", "09:30"),   # 随机对盘
    "morning_session": ("09:30", "12:00"),        # 上午持续交易
    "lunch_break": ("12:00", "13:00"),            # 午间休市
    "afternoon_session": ("13:00", "16:00"),      # 下午持续交易
    "closing_auction": ("16:00", "16:10"),        # 收市竞价
}

# ═══════════════════════════════════════════════════
#  订单类型
# ═══════════════════════════════════════════════════
ORDER_TYPES = {
    "MKT": "市价单 - 保证成交不保证价格",
    "LMT": "限价单 - 指定价格或更优",
    "STP": "止损单 - 触及止损价后变为市价单",
    "STP_LMT": "止损限价单 - 触及止损价后变为限价单",
    "TRAIL": "追踪止损单 - 止损价随市价移动",
}

# 算法订单类型
ALGO_ORDER_TYPES = {
    "TWAP": "时间加权均价 - 等时间间隔拆分执行",
    "VWAP": "成交量加权均价 - 按历史成交量分布拆分",
}

# ═══════════════════════════════════════════════════
#  港股手数表（常用蓝筹）
# ═══════════════════════════════════════════════════
HK_LOT_SIZES = {
    "00700": 100,   # 腾讯
    "09988": 100,   # 阿里巴巴
    "01810": 200,   # 小米
    "03690": 100,   # 美团
    "09618": 50,    # 京东
    "02318": 500,   # 中国平安
    "00005": 400,   # 汇丰控股
    "01398": 1000,  # 工商银行
    "00388": 100,   # 香港交易所
    "00941": 500,   # 中国移动
    "00883": 1000,  # 中海油
    "02020": 100,   # 安踏体育
    "09999": 10,    # 网易
    "00992": 2000,  # 联想集团
    "01088": 500,   # 中国神华
    "00011": 100,   # 恒生银行
    "02388": 500,   # 中银香港
    "00762": 2000,  # 中国联通
    "06862": 500,   # 海底捞
    "01177": 2000,  # 中国生物制药
}

# ═══════════════════════════════════════════════════
#  K线周期
# ═══════════════════════════════════════════════════
BAR_PERIODS = {
    "day":   "BarPeriod.DAY",
    "week":  "BarPeriod.WEEK",
    "month": "BarPeriod.MONTH",
    "year":  "BarPeriod.YEAR",
    "1min":  "BarPeriod.ONE_MINUTE",
    "3min":  "BarPeriod.THREE_MINUTES",
    "5min":  "BarPeriod.FIVE_MINUTES",
    "10min": "BarPeriod.TEN_MINUTES",
    "15min": "BarPeriod.FIFTEEN_MINUTES",
    "30min": "BarPeriod.HALF_HOUR",
    "45min": "BarPeriod.FORTY_FIVE_MINUTES",
    "60min": "BarPeriod.ONE_HOUR",
    "2hour": "BarPeriod.TWO_HOURS",
    "3hour": "BarPeriod.THREE_HOURS",
    "4hour": "BarPeriod.FOUR_HOURS",
    "6hour": "BarPeriod.SIX_HOURS",
}

# ═══════════════════════════════════════════════════
#  交易成本（港股）
# ═══════════════════════════════════════════════════
HK_TRADING_COSTS = {
    "stamp_duty": 0.0013,        # 印花税 0.13%（买卖双边）
    "trading_fee": 0.00005,      # 交易费 0.005%
    "sfc_levy": 0.000027,        # 证监会征费 0.0027%
    "frc_levy": 0.0000015,       # 财汇局征费 0.00015%
    "ccass_fee": 0.00002,        # 中央结算费 0.002%（最低2港元，最高100港元）
    "broker_commission": 0.0003, # 老虎佣金 0.03%（最低3港元）
    "total_one_side": 0.0016,    # 单边总成本约 0.16%
    "total_round_trip": 0.0032,  # 双边总成本约 0.32%
}

# ═══════════════════════════════════════════════════
#  API 频率限制
# ═══════════════════════════════════════════════════
RATE_LIMITS = {
    "high": {"limit": 120, "per": "minute", "methods": [
        "get_market_status", "get_briefs", "get_stock_detail",
        "get_timeline", "get_bars", "get_trade_ticks",
    ]},
    "medium": {"limit": 60, "per": "minute", "methods": [
        "get_symbols", "get_industry_list", "get_capital_distribution",
        "get_capital_flow", "get_stock_broker", "get_short_interest",
        "get_financial_daily", "get_financial_report", "get_corporate_action",
        "get_trade_metas", "get_contracts",
    ]},
    "low": {"limit": 10, "per": "minute", "methods": [
        "get_option_chain", "get_option_briefs", "get_option_kline",
        "get_warrant_filter", "get_warrant_real_time_quote",
        "market_scanner",
    ]},
    "trade": {"limit": 60, "per": "minute", "methods": [
        "place_order", "cancel_order", "modify_order",
        "get_orders", "get_positions", "get_assets",
    ]},
}

# ═══════════════════════════════════════════════════
#  常见错误码
# ═══════════════════════════════════════════════════
ERROR_CODES = {
    # 通用错误
    "A001": "签名校验不通过",
    "A002": "tigerId无效",
    "A003": "权限不足",
    "A100": "请求过于频繁",
    # 交易错误
    "T001": "账户不存在",
    "T002": "合约不存在",
    "T003": "委托数量非法（非整手）",
    "T004": "委托价格非法",
    "T005": "资金不足",
    "T006": "持仓不足",
    "T010": "非交易时段",
    "T011": "订单已被取消",
    "T012": "订单已完全成交",
    # 行情错误
    "Q001": "行情权限不足（需订阅）",
    "Q002": "标的代码无效",
    "Q003": "历史数据超过限制",
}

# ═══════════════════════════════════════════════════
#  合约工具函数参考
# ═══════════════════════════════════════════════════
CONTRACT_UTILS = """
# 使用 contract_utils 简化合约创建
from tigeropen.trade.domain.order_utils import (
    market_order, limit_order, stop_order, stop_limit_order,
    trail_order, algo_order
)
from tigeropen.common.util.contract_utils import (
    stock_contract, option_contract, future_contract, warrant_contract
)

# 创建股票合约
contract = stock_contract(symbol='00700', currency='HKD')

# 创建限价单
order = limit_order(
    account='账户ID', contract=contract,
    action='BUY', quantity=100, limit_price=350.0
)

# 创建市价单
order = market_order(
    account='账户ID', contract=contract,
    action='BUY', quantity=100
)

# 创建算法订单（TWAP）
order = algo_order(
    account='账户ID', contract=contract,
    action='BUY', quantity=1000, limit_price=350.0,
    algo_params={'strategy': 'TWAP', 'start_time': '09:30', 'end_time': '12:00'}
)

# 创建追踪止损单
order = trail_order(
    account='账户ID', contract=contract,
    action='SELL', quantity=100, trailing_percent=5.0
)
"""

# ═══════════════════════════════════════════════════
#  推送订阅参考
# ═══════════════════════════════════════════════════
PUSH_API_REFERENCE = """
# Push API 关键方法
push_client = PushClient(config, use_full_tick=False)

# 回调设置
push_client.quote_changed = on_quote_changed        # 行情变动
push_client.order_changed = on_order_changed          # 订单状态变动
push_client.position_changed = on_position_changed    # 持仓变动
push_client.asset_changed = on_asset_changed          # 资产变动
push_client.disconnect_callback = on_disconnect       # 断开连接回调

# 连接和订阅
push_client.connect(timeout=10)
push_client.subscribe_quote(['00700', '09988'])       # 订阅行情
push_client.subscribe_position(account)                # 订阅持仓变动
push_client.subscribe_order(account)                   # 订阅订单变动
push_client.subscribe_asset(account)                   # 订阅资产变动

# 行情推送数据字段
# frame.symbol - 标的代码
# frame.latest_price - 最新价
# frame.volume - 成交量
# frame.amount - 成交额
# frame.pre_close - 昨收价
# frame.open - 开盘价
# frame.high - 最高价
# frame.low - 最低价
"""

# ═══════════════════════════════════════════════════
#  实用行情 API 参考
# ═══════════════════════════════════════════════════
QUOTE_API_REFERENCE = {
    "get_stock_detail": "获取股票详情（替代已废弃的 get_stock_briefs），返回最新价/涨跌/成交量等",
    "get_bars": "获取K线数据，支持日/周/月/分钟级别，limit 参数控制返回条数",
    "get_trade_ticks": "获取逐笔成交数据，每次最多1000条",
    "get_timeline": "获取分时数据（当日分钟级价格+成交量）",
    "get_capital_distribution": "获取资金流向分布（大/中/小单）",
    "get_capital_flow": "获取历史资金流向，支持 day/week/month",
    "get_trade_metas": "获取交易规则（手数/最小变动价位/交易时间）",
    "get_stock_broker": "获取股票经纪商席位（Level 2 数据）",
    "get_short_interest": "获取做空数据",
    "get_financial_daily": "获取每日财务指标（PE/PB/PS/市值等）",
    "get_financial_report": "获取季度/年度财务报告",
    "get_corporate_action": "获取公司行动（分红/拆股/配股等）",
    "market_scanner": "选股器 - 按多因子筛选股票",
    "get_trade_rank": "热门交易排行榜（约20秒更新）",
}
