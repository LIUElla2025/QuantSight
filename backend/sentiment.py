"""
DeepSeek LLM 情绪分析模块
通过 DeepSeek API 分析金融新闻、财报、社交媒体情绪
DeepSeek 使用 OpenAI 兼容 API，价格极低（约 GPT-4 的 1/50）
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from openai import OpenAI

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


@dataclass
class SentimentResult:
    symbol: str
    score: float           # -1.0 (极度看空) 到 +1.0 (极度看多)
    confidence: float      # 0.0 - 1.0 置信度
    summary: str           # 一句话总结
    key_factors: list      # 关键因素列表
    recommendation: str    # BUY / SELL / HOLD
    analysis_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "score": self.score,
            "confidence": self.confidence,
            "summary": self.summary,
            "key_factors": self.key_factors,
            "recommendation": self.recommendation,
            "analysis_time": self.analysis_time,
        }


def _get_client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 文件中设置")
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def analyze_sentiment(symbol: str, news_text: str) -> SentimentResult:
    """
    用 DeepSeek 分析一段新闻/财报文本对某只股票的影响
    """
    client = _get_client()

    prompt = f"""你是一位顶级量化基金的金融分析师。请分析以下关于 {symbol} 的信息，给出交易建议。

## 待分析内容：
{news_text}

## 要求：
请以严格 JSON 格式返回分析结果（不要包含 markdown 代码块标记）：
{{
    "score": <float, -1.0到1.0, 负数看空正数看多>,
    "confidence": <float, 0.0到1.0, 分析置信度>,
    "summary": "<一句话总结该信息对股价的影响>",
    "key_factors": ["<因素1>", "<因素2>", "<因素3>"],
    "recommendation": "<BUY/SELL/HOLD>"
}}

## 评分标准：
- score > 0.5: 强烈看多（重大利好，如业绩大幅超预期、重大合同、行业政策利好）
- score 0.2~0.5: 温和看多
- score -0.2~0.2: 中性
- score -0.5~-0.2: 温和看空
- score < -0.5: 强烈看空（重大利空，如财务造假、监管处罚、业绩暴雷）
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是金融量化分析专家，所有回复必须是纯 JSON 格式。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
    )

    raw = response.choices[0].message.content.strip()
    # 去除可能的 markdown 代码块标记
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"DeepSeek 返回格式异常: {raw}")
        return SentimentResult(
            symbol=symbol, score=0.0, confidence=0.0,
            summary="分析失败：LLM返回格式异常",
            key_factors=[], recommendation="HOLD",
        )

    return SentimentResult(
        symbol=symbol,
        score=float(data.get("score", 0)),
        confidence=float(data.get("confidence", 0)),
        summary=data.get("summary", ""),
        key_factors=data.get("key_factors", []),
        recommendation=data.get("recommendation", "HOLD"),
    )


def analyze_market_sentiment(symbol: str, headlines: list[str]) -> SentimentResult:
    """
    批量分析多条新闻标题，综合给出情绪评分
    适合快速扫描多条新闻得到整体情绪
    """
    client = _get_client()

    headlines_text = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))

    prompt = f"""你是一位顶级量化基金的金融分析师。请综合分析以下关于 {symbol} 的多条新闻标题，给出整体交易建议。

## 新闻标题列表：
{headlines_text}

## 要求：
请以严格 JSON 格式返回（不要包含 markdown 代码块标记）：
{{
    "score": <float, -1.0到1.0>,
    "confidence": <float, 0.0到1.0>,
    "summary": "<综合分析一句话总结>",
    "key_factors": ["<最重要的3-5个因素>"],
    "recommendation": "<BUY/SELL/HOLD>"
}}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是金融量化分析专家，所有回复必须是纯 JSON 格式。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"DeepSeek 返回格式异常: {raw}")
        return SentimentResult(
            symbol=symbol, score=0.0, confidence=0.0,
            summary="批量分析失败",
            key_factors=[], recommendation="HOLD",
        )

    return SentimentResult(
        symbol=symbol,
        score=float(data.get("score", 0)),
        confidence=float(data.get("confidence", 0)),
        summary=data.get("summary", ""),
        key_factors=data.get("key_factors", []),
        recommendation=data.get("recommendation", "HOLD"),
    )


def analyze_earnings(symbol: str, earnings_text: str) -> SentimentResult:
    """
    专门分析财报数据，给出更深度的评估
    """
    client = _get_client()

    prompt = f"""你是一位华尔街顶级财报分析师（CFA持证）。请深度分析 {symbol} 的以下财报信息。

## 财报内容：
{earnings_text}

## 要求：
请以严格 JSON 格式返回（不要包含 markdown 代码块标记）：
{{
    "score": <float, -1.0到1.0>,
    "confidence": <float, 0.0到1.0>,
    "summary": "<财报解读一句话总结>",
    "key_factors": [
        "<营收分析>",
        "<利润分析>",
        "<增长趋势>",
        "<估值水平>",
        "<风险因素>"
    ],
    "recommendation": "<BUY/SELL/HOLD>"
}}

## 重点关注：
1. 营收和利润是否超预期（beat/miss）
2. 同比增长率趋势
3. 利润率变化
4. 管理层展望（guidance）
5. 隐藏的风险信号
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是CFA持证的财报分析专家，擅长发现财报中的隐藏信号。所有回复必须是纯 JSON 格式。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=800,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"DeepSeek 财报分析返回异常: {raw}")
        return SentimentResult(
            symbol=symbol, score=0.0, confidence=0.0,
            summary="财报分析失败",
            key_factors=[], recommendation="HOLD",
        )

    return SentimentResult(
        symbol=symbol,
        score=float(data.get("score", 0)),
        confidence=float(data.get("confidence", 0)),
        summary=data.get("summary", ""),
        key_factors=data.get("key_factors", []),
        recommendation=data.get("recommendation", "HOLD"),
    )
