"""
QuantSight - 量化交易自动化平台 API
连接老虎证券 OpenAPI，支持自动化策略交易、回测、持仓管理
"""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
import os
import secrets
import pandas as pd
import logging

# 老虎证券 OpenAPI
from tigeropen.trade.trade_client import TradeClient
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.consts import Market, SecurityType, Currency
try:
    from tigeropen.trade.domain.order import ORDER_STATUS
except ImportError:
    ORDER_STATUS = None

# 本地模块
from strategies import list_strategies
from backtester import Backtester
from engine import engine as strategy_engine, set_price_cache
from push_client import price_cache
from sentiment import analyze_sentiment, analyze_market_sentiment, analyze_earnings
from news_fetcher import init_news_fetcher, get_news_fetcher

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QuantSight - 量化交易自动化平台")

# ─── CORS 安全配置（只允许本地前端访问）───────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API 认证（保护交易接口）───────────────────────────
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """验证 API Key — 所有交易相关接口必须携带"""
    if not API_SECRET_KEY:
        # 未配置密钥时，记录警告但允许访问（开发模式）
        logger.warning("⚠️ API_SECRET_KEY 未配置! 交易接口无认证保护，请在 .env 中设置")
        return True
    if not api_key or not secrets.compare_digest(api_key, API_SECRET_KEY):
        raise HTTPException(status_code=403, detail="无效的 API Key")
    return True


# ─── 老虎证券配置 ───────────────────────────────────
TIGER_ID = os.getenv("TIGER_ID")
TIGER_ACCOUNT = os.getenv("TIGER_ACCOUNT")
TIGER_PRIVATE_KEY = os.getenv("TIGER_PRIVATE_KEY")


def get_tiger_config():
    if not all([TIGER_ID, TIGER_ACCOUNT, TIGER_PRIVATE_KEY]):
        raise ValueError("老虎证券 API 凭证未配置，请检查 .env 文件")
    config = TigerOpenClientConfig()
    config.tiger_id = TIGER_ID
    config.account = TIGER_ACCOUNT
    config.private_key = TIGER_PRIVATE_KEY.replace('\\n', '\n')
    return config


def get_trade_client():
    return TradeClient(get_tiger_config())


def get_quote_client():
    return QuoteClient(get_tiger_config())


# ─── Pydantic 请求模型 ─────────────────────────────
class OrderRequest(BaseModel):
    symbol: str
    action: str          # BUY / SELL
    quantity: int
    price: Optional[float] = None   # None = 市价单
    order_type: str = "MKT"         # MKT / LMT

class StrategyCreateRequest(BaseModel):
    strategy_key: str
    symbol: str
    params: Optional[dict] = None

class BacktestRequest(BaseModel):
    strategy_key: str
    symbol: str
    params: Optional[dict] = None
    initial_capital: float = 1_000_000
    days: int = 200        # 回测天数

class SentimentRequest(BaseModel):
    symbol: str
    text: str              # 新闻/财报文本

class BatchSentimentRequest(BaseModel):
    symbol: str
    headlines: list[str]   # 多条新闻标题

class EarningsRequest(BaseModel):
    symbol: str
    earnings_text: str     # 财报内容

class NewsRequest(BaseModel):
    symbol: str
    force: bool = False    # 强制刷新缓存

class NewsWatchRequest(BaseModel):
    symbols: list[str]
    interval: int = 1800   # 自动抓取间隔（秒）


# ═══════════════════════════════════════════════════
#  基础 API
# ═══════════════════════════════════════════════════

@app.get("/")
def read_root():
    return {"status": "ok", "message": "QuantSight 量化交易平台已就绪！"}


@app.get("/api/health")
def health_check():
    """系统健康检查 — 检测Tiger API连接、推送客户端、策略引擎状态"""
    from push_client import price_cache as pc
    from engine import engine as eng
    try:
        tiger_ok = False
        try:
            qc = get_quote_client()
            tiger_ok = qc is not None
        except Exception:
            pass

        return {
            "status": "ok",
            "tiger_api": tiger_ok,
            "push_connected": pc.is_connected,
            "push_subscribed": len(pc._subscribed),
            "strategies_running": sum(1 for i in eng.instances.values() if i.status == "running"),
            "strategies_total": len(eng.instances),
            "emergency_stopped": eng._emergency_stopped,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════
#  账户 API
# ═══════════════════════════════════════════════════

@app.get("/api/account")
def get_account_info():
    """获取账户资产信息"""
    try:
        trade_client = get_trade_client()
        accounts = trade_client.get_assets()
        base_info = []
        for acc in accounts:
            if hasattr(acc, 'summary') and acc.summary:
                s = acc.summary
                base_info.append({
                    "currency": getattr(s, 'currency', 'USD'),
                    "equity": getattr(s, 'equity_with_loan', 0),
                    "available_funds": getattr(s, 'available_funds', 0),
                    "unrealized_pnl": getattr(s, 'unrealized_pnl', 0),
                    "realized_pnl": getattr(s, 'realized_pnl', 0),
                    "buying_power": getattr(s, 'buying_power', 0),
                    "net_liquidation": getattr(s, 'net_liquidation', 0),
                    "cash": getattr(s, 'cash', 0),
                })
        return {"success": True, "data": base_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  行情 API
# ═══════════════════════════════════════════════════

@app.get("/api/quote/{symbol}")
def get_quote(symbol: str):
    """获取实时行情快照（港股/A股实时，美股需要订阅）"""
    try:
        quote_client = get_quote_client()
        briefs = quote_client.get_stock_briefs([symbol])
        if briefs is not None and len(briefs) > 0:
            if hasattr(briefs, 'iloc'):
                snap = briefs.iloc[0].to_dict()
                snap = {k: (None if pd.isna(v) else v) for k, v in snap.items()}
            else:
                snap = briefs[0].__dict__ if hasattr(briefs[0], '__dict__') else briefs[0]
            return {"success": True, "data": snap}
        return {"success": True, "data": None}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/klines/{symbol}")
def get_klines(symbol: str, days: int = 100):
    """获取历史日 K 线数据"""
    try:
        quote_client = get_quote_client()
        from tigeropen.quote.quote_client import BarPeriod
        from datetime import datetime as dt
        bars = quote_client.get_bars([symbol], period=BarPeriod.DAY, limit=days)
        if bars is not None and len(bars) > 0 and hasattr(bars, 'iterrows'):
            result = []
            for _, row in bars.iterrows():
                # 老虎 API 返回毫秒时间戳，需转换为日期字符串
                t = row['time']
                if isinstance(t, (int, float)) and t > 1e12:
                    t = dt.fromtimestamp(t / 1000).strftime('%Y-%m-%d')
                elif hasattr(t, 'strftime'):
                    t = t.strftime('%Y-%m-%d')
                else:
                    t = str(t).split(' ')[0] if ' ' in str(t) else str(t)
                entry = {
                    "time": t,
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                }
                if 'volume' in row:
                    entry["volume"] = float(row['volume'])
                result.append(entry)
            return {"success": True, "data": result}
        return {"success": True, "data": []}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  下单交易 API
# ═══════════════════════════════════════════════════

@app.post("/api/order", dependencies=[Depends(verify_api_key)])
def place_order(req: OrderRequest):
    """手动下单（买入/卖出）"""
    try:
        trade_client = get_trade_client()

        # 判断市场
        market = Market.HK if req.symbol.isdigit() else Market.US

        # 获取合约（带null检查）
        currency = Currency.HKD if market == Market.HK else Currency.USD
        contracts = trade_client.get_contracts(
            symbols=[req.symbol], sec_type=SecurityType.STK, currency=currency
        )
        if not contracts:
            raise ValueError(f"无法获取 {req.symbol} 的合约信息，请检查股票代码是否正确")
        contract = contracts[0]

        if req.order_type == "MKT":
            order = trade_client.create_order(
                account=TIGER_ACCOUNT,
                contract=contract,
                action=req.action,
                order_type='MKT',
                quantity=req.quantity,
            )
        else:
            if req.price is None:
                raise ValueError("限价单必须指定价格")
            order = trade_client.create_order(
                account=TIGER_ACCOUNT,
                contract=contract,
                action=req.action,
                order_type='LMT',
                quantity=req.quantity,
                limit_price=req.price,
            )

        result = trade_client.place_order(order)
        # 检查下单结果
        if hasattr(result, 'code') and result.code != 0:
            return {"success": False, "error": f"下单失败: {getattr(result, 'message', str(result))}"}
        return {"success": True, "data": {"order_id": str(result), "message": f"{req.action} {req.quantity}股 {req.symbol} 已提交"}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  持仓 API
# ═══════════════════════════════════════════════════

@app.get("/api/positions")
def get_positions():
    """获取当前持仓"""
    try:
        trade_client = get_trade_client()
        positions = trade_client.get_positions(account=TIGER_ACCOUNT)
        result = []
        if positions:
            for pos in positions:
                result.append({
                    "symbol": getattr(pos, 'contract', {}).get('symbol', '') if isinstance(getattr(pos, 'contract', None), dict) else getattr(getattr(pos, 'contract', None), 'symbol', ''),
                    "quantity": getattr(pos, 'quantity', 0),
                    "average_cost": getattr(pos, 'average_cost', 0),
                    "market_value": getattr(pos, 'market_value', 0),
                    "unrealized_pnl": getattr(pos, 'unrealized_pnl', 0),
                    "realized_pnl": getattr(pos, 'realized_pnl', 0),
                    "latest_price": getattr(pos, 'latest_price', 0),
                })
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/orders")
def get_orders():
    """获取订单历史"""
    try:
        trade_client = get_trade_client()
        orders = trade_client.get_orders(account=TIGER_ACCOUNT)
        result = []
        if orders:
            for order in orders:
                result.append({
                    "order_id": getattr(order, 'order_id', ''),
                    "symbol": getattr(order, 'symbol', ''),
                    "action": getattr(order, 'action', ''),
                    "order_type": getattr(order, 'order_type', ''),
                    "quantity": getattr(order, 'quantity', 0),
                    "filled_quantity": getattr(order, 'filled_quantity', 0),
                    "limit_price": getattr(order, 'limit_price', 0),
                    "avg_fill_price": getattr(order, 'avg_fill_price', 0),
                    "status": getattr(order, 'status', ''),
                    "order_time": str(getattr(order, 'order_time', '')),
                })
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  策略 API
# ═══════════════════════════════════════════════════

@app.get("/api/strategies")
def get_available_strategies():
    """获取所有可用策略列表"""
    return {"success": True, "data": list_strategies()}


@app.post("/api/strategy/create", dependencies=[Depends(verify_api_key)])
def create_strategy(req: StrategyCreateRequest):
    """创建策略实例"""
    try:
        inst = strategy_engine.create_strategy(req.strategy_key, req.symbol, req.params)
        return {"success": True, "data": inst.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/strategy/{instance_id}/start", dependencies=[Depends(verify_api_key)])
def start_strategy(instance_id: str):
    """启动策略"""
    try:
        inst = strategy_engine.start_strategy(instance_id)
        return {"success": True, "data": inst.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/strategy/{instance_id}/stop", dependencies=[Depends(verify_api_key)])
def stop_strategy(instance_id: str):
    """停止策略"""
    try:
        inst = strategy_engine.stop_strategy(instance_id)
        return {"success": True, "data": inst.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/strategy/{instance_id}", dependencies=[Depends(verify_api_key)])
def remove_strategy(instance_id: str):
    """删除策略实例"""
    try:
        strategy_engine.remove_strategy(instance_id)
        return {"success": True, "message": "策略已删除"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/strategy/instances")
def get_strategy_instances():
    """获取所有策略实例"""
    return {"success": True, "data": strategy_engine.get_all()}


@app.get("/api/strategy/{instance_id}")
def get_strategy_detail(instance_id: str):
    """获取策略实例详情"""
    try:
        return {"success": True, "data": strategy_engine.get_one(instance_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  回测 API
# ═══════════════════════════════════════════════════

@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    """执行策略回测"""
    try:
        # 获取历史K线数据
        quote_client = get_quote_client()
        from tigeropen.quote.quote_client import BarPeriod
        bars = quote_client.get_bars([req.symbol], period=BarPeriod.DAY, limit=req.days)

        if bars is None or len(bars) == 0:
            return {"success": False, "error": f"无法获取 {req.symbol} 的历史数据"}

        # 转为标准 DataFrame
        df = bars.copy() if hasattr(bars, 'copy') else pd.DataFrame(bars)
        required_cols = ['time', 'open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                return {"success": False, "error": f"数据缺少 {col} 列"}

        # 老虎 API 返回毫秒时间戳，转换为日期字符串
        from datetime import datetime as dt
        if df['time'].dtype in ['int64', 'float64'] and df['time'].iloc[0] > 1e12:
            df['time'] = df['time'].apply(lambda x: dt.fromtimestamp(x / 1000).strftime('%Y-%m-%d'))

        # 运行回测
        backtester = Backtester(initial_capital=req.initial_capital)
        result = backtester.run(df, req.strategy_key, req.params or {}, req.symbol)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  一键自动交易 API
# ═══════════════════════════════════════════════════

def _screen_hk_stocks(top_n: int = 6) -> list[dict]:
    """
    用老虎行情接口筛选港股蓝筹 v2.0：
    - 候选池从10扩展到20只（恒生指数成分股+科技龙头+消费+医疗）
    - 筛选标准：按成交额排序（流动性），只选流动性最好的top_n只
    - 每只股票分配最适合其特性的策略
    - 失败时返回默认标的
    """
    # 候选池（20只）：恒生指数核心 + 各行业龙头
    candidates = [
        # 科技/互联网
        {"symbol": "00700", "strategy": "super_alpha",         "name": "腾讯控股",   "sector": "tech"},
        {"symbol": "09988", "strategy": "regime_adaptive",     "name": "阿里巴巴",   "sector": "tech"},
        {"symbol": "01810", "strategy": "momentum_volatility", "name": "小米集团",   "sector": "tech"},
        {"symbol": "03690", "strategy": "stat_arb_pairs",      "name": "美团",       "sector": "tech"},
        {"symbol": "09618", "strategy": "super_alpha",         "name": "京东集团",   "sector": "tech"},
        {"symbol": "00992", "strategy": "regime_adaptive",     "name": "联想集团",   "sector": "tech"},
        # 金融
        {"symbol": "02318", "strategy": "multi_factor",        "name": "中国平安",   "sector": "finance"},
        {"symbol": "00005", "strategy": "mean_reversion",      "name": "汇丰控股",   "sector": "finance"},
        {"symbol": "01398", "strategy": "trend_tail_hedge",    "name": "工商银行",   "sector": "finance"},
        {"symbol": "00388", "strategy": "volume_breakout",     "name": "香港交易所", "sector": "finance"},
        {"symbol": "00011", "strategy": "stat_arb_pairs",      "name": "恒生银行",   "sector": "finance"},
        {"symbol": "02388", "strategy": "multi_factor",        "name": "中银香港",   "sector": "finance"},
        # 消费/零售
        {"symbol": "02020", "strategy": "rsi",                 "name": "安踏体育",   "sector": "consumer"},
        {"symbol": "06862", "strategy": "momentum_volatility", "name": "海底捞",     "sector": "consumer"},
        {"symbol": "09999", "strategy": "regime_adaptive",     "name": "网易",       "sector": "tech"},
        # 电信/公用
        {"symbol": "00941", "strategy": "macd",                "name": "中国移动",   "sector": "telecom"},
        {"symbol": "00762", "strategy": "mean_reversion",      "name": "中国联通",   "sector": "telecom"},
        # 能源/资源
        {"symbol": "00883", "strategy": "trend_tail_hedge",    "name": "中国海洋石油","sector": "energy"},
        {"symbol": "01088", "strategy": "momentum_volatility", "name": "中国神华",   "sector": "energy"},
        # 医疗
        {"symbol": "01177", "strategy": "super_alpha",         "name": "中国生物制药","sector": "health"},
    ]
    try:
        quote_client = get_quote_client()
        symbols = [c["symbol"] for c in candidates]
        briefs = quote_client.get_stock_briefs(symbols)
        if briefs is None or len(briefs) == 0:
            return candidates[:top_n]

        if hasattr(briefs, 'iterrows'):
            vol_map = {}
            change_map = {}
            for _, row in briefs.iterrows():
                sym = str(row.get('symbol', ''))
                amt = float(row.get('amount', 0) or row.get('volume', 0) or 0)
                chg = float(row.get('change', 0) or 0)
                vol_map[sym] = amt
                change_map[sym] = chg

            # 综合评分：流动性权重0.7 + 动量方向权重0.3
            for c in candidates:
                sym = c["symbol"]
                amt = vol_map.get(sym, 0)
                chg = change_map.get(sym, 0)
                # 综合分（成交额归一化后加权，动量正向加分）
                c["_score"] = amt * (1.0 + 0.1 * (1 if chg > 0 else -0.5))
                c["momentum"] = round(chg, 4)
                c["amount"] = amt

            candidates.sort(key=lambda c: c.get("_score", 0), reverse=True)

        return candidates[:top_n]
    except Exception as e:
        logger.warning(f"选股器筛选失败，使用默认标的: {e}")
        return candidates[:top_n]


@app.get("/api/screener/hk")
def screener_hk(top_n: int = 10):
    """港股动态选股 — 按流动性从备选池筛选"""
    try:
        result = _screen_hk_stocks(top_n)
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/auto-trade/start", dependencies=[Depends(verify_api_key)])
def auto_trade_start(top_n: int = 2):
    """
    一键启动自动交易 — 系统自动选择最优策略和港股标的
    v3.1: 默认只跑 2 只股票，适合小资金账户（1万-5万 HKD）
    top_n 参数可调：资金<2万建议1-2只，2-5万建议2-3只，5万+可选更多
    """
    try:
        # ── 余额预检（根据余额自动调整标的数量）──
        cash = 0
        try:
            trade_client = get_trade_client()
            accounts = trade_client.get_assets()
            for acc in accounts:
                if hasattr(acc, 'summary') and acc.summary:
                    cash = getattr(acc.summary, 'cash', 0)
            if cash < 1000:
                return {
                    "success": False,
                    "error": f"账户余额不足（当前: HKD {cash:.2f}），请先充值。最少需要 HKD 3,000。"
                }
        except Exception as e:
            logger.warning(f"余额预检失败（不影响启动）: {e}")

        # 根据资金量自动限制标的数量（安全上限）
        if cash > 0:
            # 每只股票至少分配 3000 HKD
            max_by_cash = max(1, int(cash / 3000))
            top_n = min(top_n, max_by_cash)
            logger.info(f"账户余额 HKD {cash:.0f}，自动调整标的数量为 {top_n} 只")

        # ── 清除旧的已停止实例，避免重复（保留有持仓的）──
        old_ids = [
            iid for iid, inst in strategy_engine.instances.items()
            if inst.status != "running" and inst.position_qty == 0
        ]
        for iid in old_ids:
            strategy_engine.remove_strategy(iid)

        # ── 动态选股：按流动性从备选池筛选最优标的 ──
        targets = _screen_hk_stocks(top_n=top_n)

        created = []
        subscribed_symbols = []
        for t in targets:
            try:
                inst = strategy_engine.create_strategy(
                    t["strategy"], t["symbol"],
                    {"quantity": 100}
                )
                strategy_engine.start_strategy(inst.id)
                subscribed_symbols.append(t["symbol"])
                created.append({
                    "id": inst.id,
                    "symbol": t["symbol"],
                    "name": t["name"],
                    "strategy": inst.strategy_name,
                    "status": "running",
                })
            except Exception as e:
                created.append({
                    "symbol": t["symbol"],
                    "name": t["name"],
                    "error": str(e),
                })

        # 订阅所有运行中标的的实时行情推送
        if subscribed_symbols:
            price_cache.subscribe(subscribed_symbols)

        success_count = len([c for c in created if 'error' not in c])
        return {
            "success": True,
            "message": f"已启动 {success_count} 个自动交易策略（智能仓位+追踪止损+风控保护）",
            "data": created,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/portfolio/summary")
def portfolio_summary():
    """获取组合级别汇总（总盈亏、风控状态）"""
    return {"success": True, "data": strategy_engine.get_portfolio_summary()}


@app.post("/api/portfolio/reset-emergency", dependencies=[Depends(verify_api_key)])
def reset_emergency():
    """重置紧急停止状态"""
    strategy_engine.reset_emergency()
    return {"success": True, "message": "紧急停止已重置，可重新启动策略"}


@app.get("/api/strategy/evaluate")
def evaluate_strategies():
    """评估所有策略表现排名"""
    return {"success": True, "data": strategy_engine.evaluate_strategies()}


@app.post("/api/strategy/auto-optimize", dependencies=[Depends(verify_api_key)])
def auto_optimize():
    """自动淘汰差策略，用最佳策略替换"""
    result = strategy_engine.auto_optimize()
    return {"success": True, "data": result}


@app.get("/api/portfolio/sharpe")
def portfolio_sharpe():
    """计算整个组合的综合Sharpe比率"""
    try:
        all_sells = []
        for inst in strategy_engine.instances.values():
            for t in inst.trade_history:
                if t.get("action") == "SELL":
                    all_sells.append(t.get("pnl", 0))

        sharpe = strategy_engine._calc_sharpe(all_sells)
        sortino = strategy_engine._calc_sortino(all_sells)
        return {
            "success": True,
            "data": {
                "portfolio_sharpe": sharpe,
                "portfolio_sortino": sortino,
                "trades_counted": len(all_sells),
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/capital-flow/{symbol}")
def capital_flow(symbol: str):
    """
    港股资金流向分析 — 大/中/小单买卖分布
    基于 Tiger get_capital_distribution() API
    聪明钱信号：大单净买入 > 0 → 机构看多
    """
    try:
        qc = get_quote_client()
        # 资金流向分布（今日）
        dist = qc.get_capital_distribution(symbol, market=Market.HK)
        # 历史资金流向（5日）
        try:
            flow = qc.get_capital_flow(symbol, period="day", market=Market.HK, limit=5)
        except Exception:
            flow = None

        dist_data = {}
        if dist is not None:
            if hasattr(dist, 'to_dict'):
                dist_data = dist.to_dict()
            elif hasattr(dist, '__dict__'):
                dist_data = dist.__dict__

        flow_data = []
        if flow is not None and len(flow) > 0:
            if hasattr(flow, 'iterrows'):
                for _, row in flow.iterrows():
                    flow_data.append({
                        "date": str(row.get("time", "")),
                        "net_inflow": float(row.get("net_inflow", 0) or 0),
                    })

        return {"success": True, "data": {"distribution": dist_data, "flow_history": flow_data}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/market-scanner")
def market_scanner(market: str = "HK", top_n: int = 20):
    """
    Tiger 内置选股器 — 按多因子筛选港股/美股
    使用 market_scanner API，支持 PE/ROE/成交量等财务指标筛选
    """
    try:
        from tigeropen.quote.request.market_scanner import SortFilterData
        from tigeropen.common.consts.market_scanner import StockField, SortDirection
        mkt = Market.HK if market.upper() == "HK" else Market.US
        qc = get_quote_client()

        # 筛选：港股成交额 > 0 + 按成交额降序排列
        sort_data = SortFilterData(
            field=StockField.volume,
            sort_dir=SortDirection.DESC,
        )
        result = qc.market_scanner(
            market=mkt,
            sort_field_data=sort_data,
            page=0,
            page_size=top_n,
        )

        items = []
        if result is not None:
            result_items = getattr(result, 'items', None) or []
            for item in result_items:
                items.append({
                    "symbol": getattr(item, 'symbol', ''),
                    "latest_price": getattr(item, 'latest_price', 0),
                    "change_rate": getattr(item, 'change_rate', 0),
                    "volume": getattr(item, 'volume', 0),
                    "market_cap": getattr(item, 'market_cap', 0),
                })

        return {"success": True, "data": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/hot-stocks")
def hot_stocks():
    """
    热门交易榜 — 基于 Tiger get_trade_rank() API
    约20秒更新一次，反映最新市场热度（动量因子参考）
    """
    try:
        qc = get_quote_client()
        rank = qc.get_trade_rank(market=Market.HK)
        items = []
        if rank is not None:
            for item in (rank if hasattr(rank, '__iter__') else []):
                items.append({
                    "symbol": getattr(item, 'symbol', ''),
                    "change_rate": getattr(item, 'change_rate', 0),
                    "buy_order_rate": getattr(item, 'buy_order_rate', 0),
                    "sell_order_rate": getattr(item, 'sell_order_rate', 0),
                })
        return {"success": True, "data": items}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/auto-trade/stop", dependencies=[Depends(verify_api_key)])
def auto_trade_stop():
    """一键停止所有自动交易"""
    try:
        stopped = 0
        for inst_id, inst in list(strategy_engine.instances.items()):
            if inst.status == "running":
                strategy_engine.stop_strategy(inst_id)
                stopped += 1
        return {"success": True, "message": f"已停止 {stopped} 个策略"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  LLM 情绪分析 API
# ═══════════════════════════════════════════════════

@app.post("/api/sentiment/analyze")
def sentiment_analyze(req: SentimentRequest):
    """用 DeepSeek 分析单条新闻/文本对股票的影响"""
    try:
        result = analyze_sentiment(req.symbol, req.text)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/sentiment/batch")
def sentiment_batch(req: BatchSentimentRequest):
    """批量分析多条新闻标题，综合情绪评分"""
    try:
        result = analyze_market_sentiment(req.symbol, req.headlines)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/sentiment/earnings")
def sentiment_earnings(req: EarningsRequest):
    """深度分析财报内容"""
    try:
        result = analyze_earnings(req.symbol, req.earnings_text)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  自动新闻抓取 API
# ═══════════════════════════════════════════════════

# 固定路径端点必须在 {symbol} 通配路由之前，否则会被拦截

@app.get("/api/news/status")
def news_status():
    """获取新闻聚合器状态"""
    fetcher = get_news_fetcher()
    if not fetcher:
        return {"success": False, "error": "新闻聚合器未初始化"}
    return {"success": True, "data": fetcher.get_status()}


@app.post("/api/news/auto-analyze")
def news_auto_analyze(req: NewsRequest):
    """一键：自动抓取新闻 + DeepSeek情绪分析（全自动流水线）"""
    fetcher = get_news_fetcher()
    if not fetcher:
        return {"success": False, "error": "新闻聚合器未初始化"}
    try:
        headlines = fetcher.get_headlines(req.symbol, max_count=10)
        if not headlines:
            return {"success": True, "data": {"headlines": [], "sentiment": None},
                    "message": "未找到相关新闻"}
        sentiment = analyze_market_sentiment(req.symbol, headlines)
        return {
            "success": True,
            "data": {
                "headlines": headlines,
                "sentiment": sentiment.to_dict(),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/news/watch")
def news_watch(req: NewsWatchRequest):
    """启动后台自动抓取监控"""
    fetcher = get_news_fetcher()
    if not fetcher:
        return {"success": False, "error": "新闻聚合器未初始化"}
    fetcher.start_auto_fetch(req.symbols, req.interval)
    return {"success": True, "message": f"已启动 {len(req.symbols)} 只股票的自动新闻监控，间隔 {req.interval}秒"}


@app.post("/api/news/watch/stop")
def news_watch_stop():
    """停止后台自动抓取"""
    fetcher = get_news_fetcher()
    if not fetcher:
        return {"success": False, "error": "新闻聚合器未初始化"}
    fetcher.stop_auto_fetch()
    return {"success": True, "message": "自动新闻监控已停止"}


@app.get("/api/news/{symbol}")
def get_news(symbol: str, force: bool = False):
    """获取某只股票的新闻（自动多源抓取：Tiger + DeepSeek + OpenAI）"""
    fetcher = get_news_fetcher()
    if not fetcher:
        return {"success": False, "error": "新闻聚合器未初始化"}
    try:
        result = fetcher.fetch_news([symbol], force=force)
        items = result.get(symbol, [])
        news = [item.to_dict() for item in items]
        return {"success": True, "data": news, "count": len(news)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/news/{symbol}/headlines")
def get_headlines(symbol: str, max_count: int = 10):
    """获取某只股票的新闻标题列表（供情绪分析直接使用）"""
    fetcher = get_news_fetcher()
    if not fetcher:
        return {"success": False, "error": "新闻聚合器未初始化"}
    try:
        headlines = fetcher.get_headlines(symbol, max_count)
        return {"success": True, "data": headlines, "count": len(headlines)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  启动时初始化
# ═══════════════════════════════════════════════════

@app.on_event("startup")
def startup():
    """注入行情获取器和下单执行器到策略引擎"""

    def fetch_klines(symbol: str) -> pd.DataFrame:
        """获取K线数据供策略引擎使用 — 智能选择日K或分钟K"""
        try:
            quote_client = get_quote_client()
            from tigeropen.quote.quote_client import BarPeriod
            from datetime import datetime as dt
            from engine import is_hk_trading_hours

            # 盘中用15分钟K线（更灵敏），非盘中用日K线（更稳定）
            if is_hk_trading_hours():
                try:
                    bars = quote_client.get_bars([symbol], period=BarPeriod.MIN15, limit=200)
                except Exception:
                    bars = quote_client.get_bars([symbol], period=BarPeriod.DAY, limit=100)
            else:
                bars = quote_client.get_bars([symbol], period=BarPeriod.DAY, limit=100)

            if bars is not None and len(bars) > 0:
                if bars['time'].dtype in ['int64', 'float64'] and bars['time'].iloc[0] > 1e12:
                    bars = bars.copy()
                    bars['time'] = bars['time'].apply(
                        lambda x: dt.fromtimestamp(x / 1000).strftime('%Y-%m-%d %H:%M')
                        if is_hk_trading_hours()
                        else dt.fromtimestamp(x / 1000).strftime('%Y-%m-%d')
                    )
            return bars
        except Exception as e:
            logger.error(f"获取 {symbol} K线数据失败: {e}")
            return pd.DataFrame()

    def _poll_fill_price(tc, order_id, timeout: float = 3.0) -> Optional[float]:
        """提交订单后短暂轮询，尝试获取实际成交均价"""
        import time
        deadline = time.time() + timeout
        oid = str(order_id)
        while time.time() < deadline:
            try:
                orders = tc.get_orders(account=TIGER_ACCOUNT)
                if orders:
                    for o in orders:
                        if str(getattr(o, 'order_id', '')) == oid:
                            filled = getattr(o, 'filled_quantity', 0) or 0
                            avg_price = getattr(o, 'avg_fill_price', 0) or 0
                            status = str(getattr(o, 'status', ''))
                            if filled > 0 and avg_price > 0:
                                return float(avg_price)
                            if 'FILLED' in status.upper() or 'CANCELLED' in status.upper():
                                return float(avg_price) if avg_price > 0 else None
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def execute_order(symbol: str, action: str, qty: int, price: float,
                      order_type: str = "LMT") -> dict:
        """
        执行下单 v2.0 — 支持限价单/市价单
        - order_type="LMT"（默认）：限价单，买入比市价低0.5%，卖出比市价高0.5%
          优点：比市价单节省交易成本（尤其是港股印花税按成交额计算）
          缺点：可能无法立即成交（极端行情下滑点大时失效）
        - order_type="MKT"：市价单，保证成交，不保证价格
        - 大单（>HKD 100万）自动拆分3笔分批执行，降低市场冲击
        """
        try:
            trade_client = get_trade_client()
            market = Market.HK if symbol.isdigit() else Market.US
            currency = Currency.HKD if market == Market.HK else Currency.USD

            contracts = trade_client.get_contracts(
                symbols=[symbol], sec_type=SecurityType.STK, currency=currency
            )
            contract = contracts[0]

            # 大单拆分（>100万港元自动拆3笔）
            order_value = price * qty
            if order_value > 1_000_000 and qty >= 3:
                split_sizes = [qty // 3, qty // 3, qty - 2 * (qty // 3)]
                results = []
                for i, split_qty in enumerate(split_sizes):
                    if split_qty <= 0:
                        continue
                    if order_type == "LMT":
                        # 每笔限价稍有差异（后续批次更激进）
                        adj = 0.005 + i * 0.001
                        lmt = round(price * (1 - adj) if action == "BUY" else price * (1 + adj), 3)
                        sub_order = trade_client.create_order(
                            account=TIGER_ACCOUNT, contract=contract,
                            action=action, order_type='LMT',
                            quantity=split_qty, limit_price=lmt,
                        )
                    else:
                        sub_order = trade_client.create_order(
                            account=TIGER_ACCOUNT, contract=contract,
                            action=action, order_type='MKT', quantity=split_qty,
                        )
                    sub_result = trade_client.place_order(sub_order)
                    if hasattr(sub_result, 'code') and sub_result.code != 0:
                        logger.error(f"拆单第{i+1}笔失败: {getattr(sub_result, 'message', str(sub_result))}")
                        continue
                    results.append(str(sub_result))
                logger.info(f"大单拆分下单: {action} {qty}股 {symbol} 拆3笔, IDs: {results}")
                return {"order_id": ",".join(results), "status": "submitted", "split": True}

            # 普通单
            if order_type == "LMT":
                # 买入低0.5%，卖出高0.5% — 提高成交概率同时节省成本
                limit_price = round(
                    price * 0.995 if action == "BUY" else price * 1.005, 3
                )
                order = trade_client.create_order(
                    account=TIGER_ACCOUNT, contract=contract,
                    action=action, order_type='LMT',
                    quantity=qty, limit_price=limit_price,
                )
                logger.info(f"限价单: {action} {qty}股 {symbol} 限价{limit_price:.3f}（参考{price:.3f}）")
            else:
                order = trade_client.create_order(
                    account=TIGER_ACCOUNT, contract=contract,
                    action=action, order_type='MKT', quantity=qty,
                )
                logger.info(f"市价单: {action} {qty}股 {symbol} 参考价{price:.3f}")

            result = trade_client.place_order(order)
            # 检查下单结果错误码
            if hasattr(result, 'code') and result.code != 0:
                raise RuntimeError(f"下单被拒: {getattr(result, 'message', str(result))}")
            logger.info(f"自动下单成功: 订单ID {result}")

            # 尝试获取实际成交价（轮询最多3秒）
            avg_fill_price = _poll_fill_price(trade_client, result, timeout=3.0)
            resp = {"order_id": str(result), "status": "submitted"}
            if avg_fill_price and avg_fill_price > 0:
                resp["avg_fill_price"] = avg_fill_price
                resp["filled"] = True
                logger.info(f"实际成交价: {avg_fill_price:.3f}（信号价{price:.3f}）")
            return resp
        except Exception as e:
            logger.error(f"自动下单失败: {e}")
            raise

    def fetch_account() -> dict:
        """获取账户余额供引擎智能仓位使用"""
        try:
            trade_client = get_trade_client()
            accounts = trade_client.get_assets()
            for acc in accounts:
                if hasattr(acc, 'summary') and acc.summary:
                    s = acc.summary
                    return {
                        "equity": getattr(s, 'equity_with_loan', 0),
                        "cash": getattr(s, 'cash', 0),
                        "buying_power": getattr(s, 'buying_power', 0),
                    }
            return {"equity": 0, "cash": 0, "buying_power": 0}
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return {"equity": 0, "cash": 0, "buying_power": 0}

    strategy_engine.set_quote_fetcher(fetch_klines)
    strategy_engine.set_order_executor(execute_order)
    strategy_engine.set_account_fetcher(fetch_account)

    # ── 初始化新闻自动抓取聚合器 ──
    try:
        fetcher = init_news_fetcher(get_quote_client_fn=get_quote_client)
        # 自动监控常用港股蓝筹的新闻
        default_watch = ["00700", "09988", "01810", "03690", "09618"]
        fetcher.start_auto_fetch(default_watch, interval=1800)
        logger.info(f"新闻聚合器已启动，监控: {default_watch}")
    except Exception as e:
        logger.warning(f"新闻聚合器初始化失败（不影响交易）: {e}")

    # ── 从Tiger API获取真实手数（替换硬编码表）──
    try:
        qc = get_quote_client()
        all_symbols = [
            "00700","09988","01810","03690","09618","00992",
            "02318","00005","01398","00388","00011","02388",
            "02020","06862","09999","00941","00762","00883","01088","01177"
        ]
        metas = qc.get_trade_metas(all_symbols)
        if metas is not None and len(metas) > 0:
            lot_map = {}
            if hasattr(metas, 'iterrows'):
                for _, row in metas.iterrows():
                    sym = str(row.get('symbol', ''))
                    lot = int(row.get('lot_size', 100))
                    if sym and lot > 0:
                        lot_map[sym] = lot
            elif hasattr(metas, '__iter__'):
                for m in metas:
                    sym = getattr(m, 'symbol', '') or ''
                    lot = int(getattr(m, 'lot_size', 100) or 100)
                    if sym and lot > 0:
                        lot_map[sym] = lot
            if lot_map:
                strategy_engine.update_lot_sizes(lot_map)
    except Exception as e:
        logger.warning(f"获取真实手数失败，使用默认表: {e}")

    # ── 初始化实时推送客户端 ──
    try:
        config = get_tiger_config()
        connected = price_cache.setup(config)
        set_price_cache(price_cache)
        if connected:
            logger.info("实时推送客户端已启动，止损检查升级为实时价格")
            # 订阅账户推送（持仓/订单/资产实时变动）
            if TIGER_ACCOUNT:
                price_cache.subscribe_account(TIGER_ACCOUNT)
        else:
            logger.info("推送客户端不可用，继续使用轮询模式")
    except Exception as e:
        logger.warning(f"推送客户端初始化失败（不影响正常交易）: {e}")

    logger.info("QuantSight 量化交易平台启动完成！策略引擎已就绪。")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
