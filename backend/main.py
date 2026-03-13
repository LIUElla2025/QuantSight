"""
QuantSight - 量化交易自动化平台 API
连接老虎证券 OpenAPI，支持自动化策略交易、回测、持仓管理
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
import os
import pandas as pd
import logging

# 老虎证券 OpenAPI
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.tiger_open_client import TigerOpenClient
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
from engine import engine as strategy_engine
from sentiment import analyze_sentiment, analyze_market_sentiment, analyze_earnings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QuantSight - 量化交易自动化平台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ═══════════════════════════════════════════════════
#  基础 API
# ═══════════════════════════════════════════════════

@app.get("/")
def read_root():
    return {"status": "ok", "message": "QuantSight 量化交易平台已就绪！"}


# ═══════════════════════════════════════════════════
#  账户 API
# ═══════════════════════════════════════════════════

@app.get("/api/account")
def get_account_info():
    """获取账户资产信息"""
    try:
        trade_client = get_trade_client()
        accounts = trade_client.get_prime_assets()
        base_info = []
        for acc in accounts:
            if hasattr(acc, 'summary') and acc.summary:
                base_info.append({
                    "currency": acc.currency,
                    "equity": acc.summary.equity,
                    "available_funds": getattr(acc.summary, 'available_funds', 0),
                    "unrealized_pnl": getattr(acc.summary, 'unrealized_pnl', 0),
                    "realized_pnl": getattr(acc.summary, 'realized_pnl', 0),
                    "buying_power": getattr(acc.summary, 'buying_power', 0),
                    "net_liquidation": getattr(acc.summary, 'net_liquidation', 0),
                })
        return {"success": True, "data": base_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
#  行情 API
# ═══════════════════════════════════════════════════

@app.get("/api/quote/{symbol}")
def get_quote(symbol: str):
    """获取实时行情快照"""
    try:
        quote_client = get_quote_client()
        snapshots = quote_client.get_stock_snapshot([symbol])
        if snapshots is not None and len(snapshots) > 0:
            if hasattr(snapshots, 'iloc'):
                snap = snapshots.iloc[0].to_dict()
                # 将 NaN 转换为 None (JSON 兼容)
                snap = {k: (None if pd.isna(v) else v) for k, v in snap.items()}
            else:
                snap = snapshots[0].__dict__ if hasattr(snapshots[0], '__dict__') else snapshots[0]
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
        bars = quote_client.get_bars([symbol], period=BarPeriod.DAY, limit=days)
        if bars is not None and len(bars) > 0 and hasattr(bars, 'iterrows'):
            result = []
            for _, row in bars.iterrows():
                t = row['time'].strftime('%Y-%m-%d') if hasattr(row['time'], 'strftime') else str(row['time'])
                if len(str(t)) > 10 and ' ' in str(t):
                    t = str(t).split(' ')[0]
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

@app.post("/api/order")
def place_order(req: OrderRequest):
    """手动下单（买入/卖出）"""
    try:
        trade_client = get_trade_client()

        # 判断市场
        market = Market.HK if req.symbol.isdigit() else Market.US

        if req.order_type == "MKT":
            order = trade_client.create_order(
                account=TIGER_ACCOUNT,
                contract=trade_client.get_contracts(symbols=[req.symbol], sec_type=SecurityType.STK, currency=Currency.HKD if market == Market.HK else Currency.USD)[0] if hasattr(trade_client, 'get_contracts') else None,
                action=req.action,
                order_type='MKT',
                quantity=req.quantity,
            )
        else:
            if req.price is None:
                raise ValueError("限价单必须指定价格")
            order = trade_client.create_order(
                account=TIGER_ACCOUNT,
                contract=trade_client.get_contracts(symbols=[req.symbol], sec_type=SecurityType.STK)[0] if hasattr(trade_client, 'get_contracts') else None,
                action=req.action,
                order_type='LMT',
                quantity=req.quantity,
                limit_price=req.price,
            )

        result = trade_client.place_order(order)
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


@app.post("/api/strategy/create")
def create_strategy(req: StrategyCreateRequest):
    """创建策略实例"""
    try:
        inst = strategy_engine.create_strategy(req.strategy_key, req.symbol, req.params)
        return {"success": True, "data": inst.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/strategy/{instance_id}/start")
def start_strategy(instance_id: str):
    """启动策略"""
    try:
        inst = strategy_engine.start_strategy(instance_id)
        return {"success": True, "data": inst.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/strategy/{instance_id}/stop")
def stop_strategy(instance_id: str):
    """停止策略"""
    try:
        inst = strategy_engine.stop_strategy(instance_id)
        return {"success": True, "data": inst.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/strategy/{instance_id}")
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

        # 运行回测
        backtester = Backtester(initial_capital=req.initial_capital)
        result = backtester.run(df, req.strategy_key, req.params or {}, req.symbol)
        return {"success": True, "data": result.to_dict()}
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
#  启动时初始化
# ═══════════════════════════════════════════════════

@app.on_event("startup")
def startup():
    """注入行情获取器和下单执行器到策略引擎"""

    def fetch_klines(symbol: str) -> pd.DataFrame:
        """获取K线数据供策略引擎使用"""
        try:
            quote_client = get_quote_client()
            from tigeropen.quote.quote_client import BarPeriod
            bars = quote_client.get_bars([symbol], period=BarPeriod.DAY, limit=100)
            return bars
        except Exception as e:
            logger.error(f"获取 {symbol} K线数据失败: {e}")
            return pd.DataFrame()

    def execute_order(symbol: str, action: str, qty: int, price: float) -> dict:
        """执行下单"""
        try:
            trade_client = get_trade_client()
            market = Market.HK if symbol.isdigit() else Market.US

            order = trade_client.create_order(
                account=TIGER_ACCOUNT,
                contract=trade_client.get_contracts(
                    symbols=[symbol],
                    sec_type=SecurityType.STK,
                    currency=Currency.HKD if market == Market.HK else Currency.USD,
                )[0],
                action=action,
                order_type='MKT',
                quantity=qty,
            )
            result = trade_client.place_order(order)
            logger.info(f"自动下单成功: {action} {qty}股 {symbol}, 订单ID: {result}")
            return {"order_id": str(result), "status": "submitted"}
        except Exception as e:
            logger.error(f"自动下单失败: {e}")
            raise

    strategy_engine.set_quote_fetcher(fetch_klines)
    strategy_engine.set_order_executor(execute_order)
    logger.info("QuantSight 量化交易平台启动完成！策略引擎已就绪。")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
