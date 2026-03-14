"""
多源新闻自动抓取聚合模块
数据源：
1. Tiger API — 财报日历、分红、拆股等公司事件
2. DeepSeek — 联网搜索模式获取最新金融新闻
3. Perplexity（可选） — 实时新闻搜索API
自动定时抓取 + 缓存 + 去重，供情绪分析策略消费
"""
import os
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

MAX_CACHE_SYMBOLS = 200  # 最多缓存200只股票的新闻，防止内存泄漏

# 过滤LLM前缀/后缀说明文字（所有LLM源共用，防止分叉）
_SKIP_PHRASES = ["以下是", "以上信息", "请注意", "仅供参考", "如需更多",
                 "以上是", "注意", "希望", "如果您"]

# ═══════════════════════════════════════════════════
#  数据结构
# ═══════════════════════════════════════════════════

@dataclass
class NewsItem:
    """单条新闻/事件"""
    title: str
    source: str          # "tiger" | "deepseek" | "perplexity"
    symbol: str          # 关联的股票代码
    timestamp: float     # Unix timestamp
    content: str = ""    # 详细内容（可选）
    category: str = ""   # "earnings" | "dividend" | "split" | "news" | "market"
    relevance: float = 1.0  # 相关度 0-1

    def to_dict(self):
        return {
            "title": self.title,
            "source": self.source,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "time_str": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M"),
            "content": self.content,
            "category": self.category,
            "relevance": self.relevance,
        }


def _parse_llm_lines(raw: str, symbol: str, source: str) -> list[NewsItem]:
    """解析LLM输出文本为新闻条目列表（所有LLM源共用）"""
    results = []
    for line in raw.split("\n"):
        line = line.strip().lstrip("0123456789.、)-） *-")
        if not line or len(line) < 8:
            continue
        if any(line.startswith(p) for p in _SKIP_PHRASES):
            continue
        parts = line.split("|", 1)
        title = parts[-1].strip() if len(parts) > 1 else line
        if title and len(title) >= 8:
            results.append(NewsItem(
                title=title, source=source,
                symbol=symbol, timestamp=time.time(),
                category="news",
            ))
    return results


# ═══════════════════════════════════════════════════
#  Tiger API 数据源
# ═══════════════════════════════════════════════════

class TigerNewsSource:
    """从Tiger API获取公司事件（财报/分红/拆股）"""

    def __init__(self, get_quote_client_fn):
        self._get_client = get_quote_client_fn

    def fetch(self, symbols: list[str], days_back: int = 30) -> list[NewsItem]:
        items = []
        try:
            qc = self._get_client()
            from tigeropen.common.consts import Market

            now = datetime.now()
            begin = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
            end = (now + timedelta(days=7)).strftime("%Y-%m-%d")

            # 财报日历
            try:
                earnings = qc.get_corporate_earnings_calendar(
                    market=Market.HK, begin_date=begin, end_date=end
                )
                if earnings is not None and len(earnings) > 0:
                    for _, row in earnings.iterrows():
                        sym = str(row.get("symbol", ""))
                        if symbols and sym not in symbols:
                            continue
                        date_str = str(row.get("date", row.get("earning_date", "")))
                        items.append(NewsItem(
                            title=f"{sym} 财报发布日: {date_str}",
                            source="tiger", symbol=sym,
                            timestamp=time.time(), category="earnings",
                            content=f"预计EPS: {row.get('eps_estimate', 'N/A')}, "
                                    f"实际EPS: {row.get('eps_actual', 'N/A')}",
                        ))
            except Exception as e:
                logger.debug(f"Tiger财报日历获取失败: {e}")

            # 分红信息
            if symbols:
                try:
                    divs = qc.get_corporate_dividend(
                        symbols=symbols, market=Market.HK,
                        begin_date=begin, end_date=end
                    )
                    if divs is not None and len(divs) > 0:
                        for _, row in divs.iterrows():
                            sym = str(row.get("symbol", ""))
                            amount = row.get("amount", 0)
                            ex_date = str(row.get("ex_date", row.get("execute_date", "")))
                            items.append(NewsItem(
                                title=f"{sym} 派息 {amount}/股, 除息日 {ex_date}",
                                source="tiger", symbol=sym,
                                timestamp=time.time(), category="dividend",
                            ))
                except Exception as e:
                    logger.debug(f"Tiger分红数据获取失败: {e}")

                # 拆股信息
                try:
                    splits = qc.get_corporate_split(
                        symbols=symbols, market=Market.HK,
                        begin_date=begin, end_date=end
                    )
                    if splits is not None and len(splits) > 0:
                        for _, row in splits.iterrows():
                            sym = str(row.get("symbol", ""))
                            ratio = row.get("to_factor", "")
                            items.append(NewsItem(
                                title=f"{sym} 拆股 比例 {ratio}",
                                source="tiger", symbol=sym,
                                timestamp=time.time(), category="split",
                            ))
                except Exception as e:
                    logger.debug(f"Tiger拆股数据获取失败: {e}")

        except Exception as e:
            logger.warning(f"Tiger数据源整体失败: {e}")

        logger.info(f"[Tiger源] 获取到 {len(items)} 条公司事件")
        return items


# ═══════════════════════════════════════════════════
#  LLM 搜索数据源（统一基类，消除DeepSeek/Perplexity重复代码）
# ═══════════════════════════════════════════════════

class LLMNewsSource:
    """LLM搜索新闻基类 — DeepSeek和Perplexity共用"""

    def __init__(self, api_key_env: str, base_url: str, model: str,
                 source_name: str, system_prompt: str, user_prompt_template: str,
                 temperature: float = 0.3):
        self._api_key = os.getenv(api_key_env)
        self._base_url = base_url
        self._model = model
        self._source_name = source_name
        self._system_prompt = system_prompt
        self._user_prompt_template = user_prompt_template
        self._temperature = temperature

    def _is_available(self) -> bool:
        return bool(self._api_key)

    def fetch(self, symbols: list[str], max_per_symbol: int = 5) -> list[NewsItem]:
        if not self._is_available():
            return []

        from openai import OpenAI
        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        items = []
        source_name = self._source_name

        def _fetch_one(symbol: str) -> list[NewsItem]:
            try:
                prompt = self._user_prompt_template.format(
                    symbol=symbol, max_per_symbol=max_per_symbol
                )
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self._temperature,
                    max_tokens=600,
                )
                raw = response.choices[0].message.content.strip()
                return _parse_llm_lines(raw, symbol, source_name)
            except Exception as e:
                logger.warning(f"[{source_name}源] {symbol} 新闻获取失败: {e}")
                return []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_fetch_one, s): s for s in symbols}
            for future in as_completed(futures):
                items.extend(future.result())

        logger.info(f"[{source_name}源] 获取到 {len(items)} 条新闻")
        return items


def _create_deepseek_source() -> LLMNewsSource:
    return LLMNewsSource(
        api_key_env="DEEPSEEK_API_KEY",
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model="deepseek-chat",
        source_name="deepseek",
        system_prompt="你是金融新闻助手，专注港股市场。简洁列出新闻标题。",
        user_prompt_template=(
            "请列出 {symbol} 这只港股最近7天内最重要的{max_per_symbol}条新闻标题。\n"
            "要求：\n"
            "1. 每条新闻一行，格式：日期 | 标题\n"
            "2. 只列标题，不要分析\n"
            "3. 如果没有最新新闻，列出最近的重要新闻\n"
            "4. 包括：财报、业务进展、管理层变动、行业政策、分析师评级等\n"
            "5. 日期格式：YYYY-MM-DD"
        ),
        temperature=0.3,
    )


class OpenAIWebSearchSource:
    """用OpenAI Responses API + web_search工具获取实时新闻"""

    def __init__(self):
        self._api_key = os.getenv("OPENAI_API_KEY")

    def _is_available(self) -> bool:
        return bool(self._api_key)

    def fetch(self, symbols: list[str], max_per_symbol: int = 5) -> list[NewsItem]:
        if not self._is_available():
            return []

        from openai import OpenAI
        client = OpenAI(api_key=self._api_key, timeout=60.0)
        items = []

        def _fetch_one(symbol: str) -> list[NewsItem]:
            try:
                prompt = (
                    f"请列出 {symbol} 这只港股最近7天内最重要的{max_per_symbol}条新闻标题。\n"
                    f"要求：\n"
                    f"1. 每条新闻一行，格式：日期 | 标题\n"
                    f"2. 只列标题，不要分析\n"
                    f"3. 包括：财报、业务进展、管理层变动、行业政策、分析师评级等\n"
                    f"4. 日期格式：YYYY-MM-DD"
                )
                response = client.responses.create(
                    model="gpt-4o-mini",
                    tools=[{"type": "web_search"}],
                    input=prompt,
                )
                raw = response.output_text.strip()
                return _parse_llm_lines(raw, symbol, "openai")
            except Exception as e:
                logger.warning(f"[OpenAI源] {symbol} 新闻获取失败: {e}")
                return []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_fetch_one, s): s for s in symbols}
            for future in as_completed(futures):
                items.extend(future.result())

        logger.info(f"[OpenAI源] 获取到 {len(items)} 条新闻")
        return items


# ═══════════════════════════════════════════════════
#  新闻聚合器（主入口）
# ═══════════════════════════════════════════════════

class NewsFetcher:
    """
    多源新闻聚合器
    - 自动从Tiger API、DeepSeek、Perplexity获取新闻
    - 内存缓存 + TTL过期 + 最大条目限制
    - 后台定时刷新
    - 去重合并
    """

    def __init__(self, get_quote_client_fn=None, cache_ttl: int = 1800):
        self._cache: dict[str, list[NewsItem]] = {}
        self._cache_time: dict[str, float] = {}
        self._cache_ttl = cache_ttl
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._shutdown = False
        self._watch_symbols: list[str] = []

        # 初始化数据源
        self._sources = []
        if get_quote_client_fn:
            self._sources.append(TigerNewsSource(get_quote_client_fn))
        self._sources.append(OpenAIWebSearchSource())
        self._sources.append(_create_deepseek_source())

        source_names = []
        if get_quote_client_fn:
            source_names.append("Tiger")
        if os.getenv("OPENAI_API_KEY"):
            source_names.append("OpenAI")
        if os.getenv("DEEPSEEK_API_KEY"):
            source_names.append("DeepSeek")
        logger.info(f"新闻聚合器初始化，可用数据源: {', '.join(source_names) or '无'}")

    def _is_cache_valid(self, symbol: str) -> bool:
        if symbol not in self._cache_time:
            return False
        return (time.time() - self._cache_time[symbol]) < self._cache_ttl

    def _deduplicate(self, items: list[NewsItem]) -> list[NewsItem]:
        """按标题去重，保留最新的（前12字符匹配，兼顾中英文）"""
        seen = {}
        for item in items:
            key = item.title[:12].lower()
            if key not in seen or item.timestamp > seen[key].timestamp:
                seen[key] = item
        return list(seen.values())

    def _evict_cache_if_needed(self):
        """淘汰最老的缓存条目，保持缓存大小在限制内"""
        if len(self._cache) <= MAX_CACHE_SYMBOLS:
            return
        # 按最后更新时间排序，淘汰最老的
        sorted_syms = sorted(self._cache_time.keys(), key=lambda s: self._cache_time[s])
        to_remove = sorted_syms[:len(self._cache) - MAX_CACHE_SYMBOLS]
        for sym in to_remove:
            self._cache.pop(sym, None)
            self._cache_time.pop(sym, None)

    def fetch_news(self, symbols: list[str], force: bool = False) -> dict[str, list[NewsItem]]:
        """获取多个股票的新闻，带缓存"""
        result = {}
        symbols_to_fetch = []

        with self._lock:
            for sym in symbols:
                if not force and self._is_cache_valid(sym):
                    result[sym] = self._cache.get(sym, [])
                else:
                    symbols_to_fetch.append(sym)

        if not symbols_to_fetch:
            return result

        # 并发从所有数据源获取
        all_items: list[NewsItem] = []
        with ThreadPoolExecutor(max_workers=len(self._sources)) as executor:
            futures = []
            for source in self._sources:
                futures.append(executor.submit(source.fetch, symbols_to_fetch))
            for future in as_completed(futures):
                try:
                    all_items.extend(future.result())
                except Exception as e:
                    logger.warning(f"数据源获取异常: {e}")

        # 按symbol分组
        grouped: dict[str, list[NewsItem]] = {s: [] for s in symbols_to_fetch}
        for item in all_items:
            if item.symbol in grouped:
                grouped[item.symbol].append(item)

        # 去重并更新缓存
        with self._lock:
            for sym, items in grouped.items():
                deduped = self._deduplicate(items)
                deduped.sort(key=lambda x: x.timestamp, reverse=True)
                self._cache[sym] = deduped
                self._cache_time[sym] = time.time()
                result[sym] = deduped
            self._evict_cache_if_needed()

        total = sum(len(v) for v in result.values())
        logger.info(f"新闻抓取完成: {len(symbols)} 只股票, 共 {total} 条新闻")
        return result

    def get_cached_headlines(self, symbol: str, max_count: int = 10) -> list[str]:
        """
        仅从缓存获取新闻标题（不触发网络请求，适合热路径调用）

        Returns:
            标题字符串列表，缓存未命中时返回空列表
        """
        with self._lock:
            items = self._cache.get(symbol, [])
            return [item.title for item in items[:max_count]]

    def get_headlines(self, symbol: str, max_count: int = 10) -> list[str]:
        """
        获取某只股票的新闻标题列表（会触发fetch，适合API调用）

        Returns:
            标题字符串列表
        """
        news = self.fetch_news([symbol])
        items = news.get(symbol, [])
        return [item.title for item in items[:max_count]]

    def get_all_news(self, symbol: str) -> list[dict]:
        """获取某只股票缓存中的所有新闻（含详情，不触发fetch）"""
        with self._lock:
            items = self._cache.get(symbol, [])
            return [item.to_dict() for item in items]

    # ── 后台定时抓取 ──

    def start_auto_fetch(self, symbols: list[str], interval: int = 1800):
        with self._lock:
            # 取消旧timer，防止重复调用导致多个timer泄漏
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._watch_symbols = list(symbols)
            self._shutdown = False
        logger.info(f"启动新闻自动抓取: {symbols}, 间隔 {interval}秒")
        self._schedule_fetch(interval)

    def _schedule_fetch(self, interval: int):
        with self._lock:
            if self._shutdown:
                return
            self._timer = threading.Timer(interval, self._auto_fetch_task, args=[interval])
            self._timer.daemon = True
            self._timer.start()

    def _auto_fetch_task(self, interval: int):
        with self._lock:
            if self._shutdown:
                return
            symbols = list(self._watch_symbols)
        try:
            logger.info(f"[自动抓取] 刷新 {len(symbols)} 只股票新闻...")
            self.fetch_news(symbols, force=True)
        except Exception as e:
            logger.error(f"[自动抓取] 失败: {e}")
        self._schedule_fetch(interval)

    def stop_auto_fetch(self):
        """停止后台定时抓取"""
        with self._lock:
            self._shutdown = True
            if self._timer:
                self._timer.cancel()
                self._timer = None
        logger.info("新闻自动抓取已停止")

    def add_watch_symbol(self, symbol: str):
        with self._lock:
            if symbol not in self._watch_symbols:
                self._watch_symbols.append(symbol)
                logger.info(f"新增监控股票: {symbol}")

    def remove_watch_symbol(self, symbol: str):
        with self._lock:
            if symbol in self._watch_symbols:
                self._watch_symbols.remove(symbol)
                logger.info(f"移除监控股票: {symbol}")

    def get_status(self) -> dict:
        with self._lock:
            return {
                "sources": [type(s).__name__ for s in self._sources],
                "watch_symbols": list(self._watch_symbols),
                "cached_symbols": list(self._cache.keys()),
                "cache_ttl": self._cache_ttl,
                "auto_fetch_active": not self._shutdown and self._timer is not None,
                "cache_stats": {
                    sym: {
                        "count": len(items),
                        "age_seconds": int(time.time() - self._cache_time[sym]),
                    }
                    for sym, items in self._cache.items()
                    if sym in self._cache_time
                },
            }


# ═══════════════════════════════════════════════════
#  全局单例
# ═══════════════════════════════════════════════════

_fetcher: Optional[NewsFetcher] = None


def get_news_fetcher() -> Optional[NewsFetcher]:
    return _fetcher


def init_news_fetcher(get_quote_client_fn=None, cache_ttl: int = 1800) -> NewsFetcher:
    global _fetcher
    _fetcher = NewsFetcher(get_quote_client_fn, cache_ttl)
    return _fetcher
