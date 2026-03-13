"""
LLM情绪增强策略
技术面（多因子） + DeepSeek LLM 情绪面 = 更聪明的交易决策
原理：技术指标看"图"，LLM看"新闻/财报"，两者结合弥补各自盲区
"""
import pandas as pd
import logging
from strategies import BaseStrategy, Signal, TradeSignal, MultiFactorStrategy
from sentiment import analyze_market_sentiment, SentimentResult

logger = logging.getLogger(__name__)


class LLMSentimentStrategy(BaseStrategy):
    """
    LLM情绪增强策略（DeepSeek驱动）

    工作原理：
    1. 先用多因子策略分析技术面（RSI/MACD/布林带/均线/量价）
    2. 再用 DeepSeek LLM 分析最近新闻的情绪
    3. 技术面和情绪面双重确认才交易

    优势：
    - 技术面捕捉价格趋势和动量
    - LLM捕捉基本面和事件驱动（财报、政策、并购等）
    - 双重过滤大幅降低假信号

    使用方法：
    - 在 params 中传入 "headlines" 字段（新闻标题列表）
    - 或者系统自动获取新闻（需要新闻数据源）
    """

    name = "LLM情绪增强策略"
    description = "DeepSeek分析新闻情绪+多因子技术面，双重确认交易"

    def __init__(self, params: dict = None):
        defaults = {
            # 技术面参数（继承多因子策略）
            "buy_threshold": 3,
            "sell_threshold": 3,
            "quantity": 100,
            "stop_loss_pct": 0.07,
            "take_profit_pct": 0.20,
            # 情绪面参数
            "sentiment_weight": 0.4,     # 情绪在总决策中的权重（0-1）
            "sentiment_threshold": 0.3,   # 情绪分数超过此值才算有效信号
            "require_sentiment_confirm": True,  # 是否要求情绪面确认
        }
        super().__init__({**defaults, **(params or {})})
        self._multi_factor = MultiFactorStrategy(params)

    def generate_signal(self, df: pd.DataFrame, symbol: str, position_qty: int = 0) -> TradeSignal:
        p = self.params
        price = df["close"].iloc[-1]

        # Step 1: 技术面分析（用多因子策略）
        tech_signal = self._multi_factor.generate_signal(df, symbol, position_qty)

        # Step 2: 情绪面分析（用 DeepSeek）
        headlines = p.get("headlines", [])
        sentiment = None

        if headlines:
            try:
                sentiment = analyze_market_sentiment(symbol, headlines)
                logger.info(f"[{symbol}] LLM情绪分析: score={sentiment.score}, rec={sentiment.recommendation}")
            except Exception as e:
                logger.warning(f"[{symbol}] LLM情绪分析失败: {e}")

        # Step 3: 综合决策
        if sentiment and abs(sentiment.score) >= p["sentiment_threshold"]:
            # 有有效的情绪信号
            return self._combined_decision(tech_signal, sentiment, symbol, price, position_qty)
        else:
            # 没有情绪数据或情绪中性，看是否要求确认
            if p["require_sentiment_confirm"]:
                if tech_signal.signal != Signal.HOLD:
                    return TradeSignal(
                        Signal.HOLD, symbol, price, 0,
                        f"技术面信号: {tech_signal.reason}，但缺少LLM情绪确认，暂不交易",
                    )
            # 不要求确认时，直接用技术面信号
            return tech_signal

    def _combined_decision(
        self, tech: TradeSignal, sentiment: SentimentResult,
        symbol: str, price: float, position_qty: int,
    ) -> TradeSignal:
        p = self.params

        tech_score = 0
        if tech.signal == Signal.BUY:
            tech_score = 1.0
        elif tech.signal == Signal.SELL:
            tech_score = -1.0

        # 加权综合评分
        tech_weight = 1.0 - p["sentiment_weight"]
        combined = tech_score * tech_weight + sentiment.score * p["sentiment_weight"]

        # 决策
        if combined > 0.3 and position_qty == 0:
            reason = (
                f"【LLM+技术面看多】综合评分{combined:.2f} | "
                f"技术面: {tech.reason} | "
                f"情绪面({sentiment.score:+.2f}): {sentiment.summary}"
            )
            return TradeSignal(
                Signal.BUY, symbol, price, p["quantity"], reason,
                stop_loss=price * (1 - p["stop_loss_pct"]),
                take_profit=price * (1 + p["take_profit_pct"]),
            )

        if combined < -0.3 and position_qty > 0:
            reason = (
                f"【LLM+技术面看空】综合评分{combined:.2f} | "
                f"技术面: {tech.reason} | "
                f"情绪面({sentiment.score:+.2f}): {sentiment.summary}"
            )
            return TradeSignal(Signal.SELL, symbol, price, position_qty, reason)

        # 特殊情况：技术面和情绪面矛盾
        if (tech_score > 0 and sentiment.score < -p["sentiment_threshold"]) or \
           (tech_score < 0 and sentiment.score > p["sentiment_threshold"]):
            return TradeSignal(
                Signal.HOLD, symbol, price, 0,
                f"技术面与情绪面矛盾（技术{tech_score:+.0f} vs 情绪{sentiment.score:+.2f}），观望"
            )

        return TradeSignal(
            Signal.HOLD, symbol, price, 0,
            f"综合评分{combined:.2f}，未达交易阈值 | 情绪: {sentiment.summary}"
        )
