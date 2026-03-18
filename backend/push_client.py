"""
实时行情推送客户端 v2.0
使用老虎证券 Push API 订阅实时价格，替代部分轮询操作。
主要用途：止损/止盈的实时价格监控（不需要等下一个轮询周期）

v2.0 改进：
- 自动重连（连接断开后5秒重试）
- 价格更新超时警告（30秒无推送）
"""
import threading
import logging
import time
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class RealTimePriceCache:
    """
    实时价格缓存。
    通过 Tiger Push Client 订阅行情推送，维护所有交易标的的最新价格。
    策略引擎可用此价格做实时止损检查，无需等待下一次 K 线拉取。
    """

    def __init__(self):
        self._prices: dict[str, float] = {}   # symbol -> 最新价格
        self._lock = threading.Lock()
        self._push_client = None
        self._subscribed: set[str] = set()
        self._connected = False
        self._on_price_update: Optional[Callable] = None   # 价格更新回调
        self._config = None                                 # 保存config用于重连
        self._last_update: dict[str, datetime] = {}        # 每个symbol最后更新时间
        self._reconnect_thread: Optional[threading.Thread] = None
        self._subscribed_account: Optional[str] = None     # Bug6修复: 记录账户号，重连后恢复
        self._shutdown = False                              # 守护线程退出标志

    def setup(self, config) -> bool:
        """
        初始化并连接推送客户端。
        返回 True 表示成功，False 表示失败（降级为轮询）。
        v2.0：保存config用于自动重连
        """
        self._config = config
        return self._connect()

    def _connect(self) -> bool:
        """内部连接逻辑，供setup和重连调用"""
        try:
            from tigeropen.push.push_client import PushClient
            _, host, port = self._config.socket_host_port
            self._push_client = PushClient(host, port, use_ssl=True, client_config=self._config)
            self._push_client.quote_changed = self._on_quote_changed
            self._push_client.disconnect_callback = self._on_disconnect
            self._push_client.connect(self._config.tiger_id, self._config.private_key)
            self._connected = True
            logger.info("Tiger 实时推送客户端连接成功")
            # 重连后重新订阅之前的标的
            if self._subscribed:
                try:
                    self._push_client.subscribe_quote(list(self._subscribed))
                    logger.info(f"重连后恢复行情订阅: {list(self._subscribed)}")
                except Exception as e:
                    logger.warning(f"重连后恢复行情订阅失败: {e}")
            # Bug6修复: 重连后恢复账户推送订阅（持仓/订单/资产）
            if self._subscribed_account:
                try:
                    self._push_client.subscribe_position(self._subscribed_account)
                    self._push_client.subscribe_order(self._subscribed_account)
                    self._push_client.subscribe_asset(self._subscribed_account)
                    logger.info(f"重连后恢复账户推送订阅: {self._subscribed_account}")
                except Exception as e:
                    logger.warning(f"重连后恢复账户推送订阅失败: {e}")
            return True
        except Exception as e:
            logger.warning(f"Tiger 推送客户端连接失败（将降级为轮询）: {e}")
            self._connected = False
            return False

    def _start_reconnect_watchdog(self):
        """启动后台重连守护线程（连接断开后自动重试）"""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        def watchdog():
            while not self._shutdown:
                time.sleep(30)
                if self._shutdown:
                    break
                if not self._connected and self._config:
                    logger.info("推送客户端已断开，尝试自动重连...")
                    self._connect()
                # 检查价格更新是否超时（30秒无更新则警告）
                if self._connected:
                    now = datetime.now()
                    for sym, last_t in list(self._last_update.items()):
                        elapsed = (now - last_t).total_seconds()
                        if elapsed > 60:
                            logger.warning(f"[推送] {sym} 已{elapsed:.0f}秒无价格更新，可能连接异常")

        self._reconnect_thread = threading.Thread(target=watchdog, daemon=True)
        self._reconnect_thread.start()

    def subscribe_account(self, account: str):
        """
        订阅账户级推送：持仓变动 + 订单状态 + 资产变动
        基于 Tiger push_client 账户订阅 API（持仓变动约实时，订单成交秒级）
        """
        if not self._connected or not self._push_client:
            logger.warning("推送客户端未连接，账户订阅将在重连后自动恢复")
            return
        try:
            self._push_client.subscribe_position(account)
            self._push_client.subscribe_order(account)
            self._push_client.subscribe_asset(account)
            self._subscribed_account = account   # Bug6修复: 记录账户，重连后恢复
            logger.info(f"已订阅账户推送（持仓/订单/资产变动）: {account}")
        except Exception as e:
            logger.warning(f"账户推送订阅失败（不影响行情推送）: {e}")

    def set_price_callback(self, callback: Callable):
        """设置价格更新回调，引擎可用此触发实时止损检查"""
        self._on_price_update = callback

    def _on_disconnect(self):
        """连接断开回调，标记状态并触发重连"""
        self._connected = False
        logger.warning("Tiger 推送客户端连接已断开")
        self._start_reconnect_watchdog()

    def _on_quote_changed(self, frame):
        """处理行情推送数据"""
        try:
            symbol = getattr(frame, 'symbol', None)
            price = getattr(frame, 'latest_price', None)
            if symbol and price is not None:
                with self._lock:
                    self._prices[symbol] = float(price)
                    self._last_update[symbol] = datetime.now()
                # 触发引擎实时止损检查
                if self._on_price_update:
                    try:
                        self._on_price_update(symbol, float(price))
                    except Exception as cb_err:
                        logger.debug(f"价格回调异常: {cb_err}")
        except Exception as e:
            logger.debug(f"处理推送数据异常: {e}")

    def subscribe(self, symbols: list[str]):
        """订阅股票实时行情推送，并启动重连守护线程"""
        if not self._connected or not self._push_client:
            # 记录待订阅标的，重连后会恢复
            self._subscribed.update(symbols)
            return
        new = [s for s in symbols if s not in self._subscribed]
        if not new:
            return
        try:
            self._push_client.subscribe_quote(new)
            self._subscribed.update(new)
            logger.info(f"已订阅实时行情: {new}")
            # 启动重连守护（订阅后开始监控）
            self._start_reconnect_watchdog()
        except Exception as e:
            logger.warning(f"订阅行情失败: {e}")

    def unsubscribe(self, symbols: list[str]):
        """取消订阅"""
        if not self._connected or not self._push_client:
            return
        try:
            self._push_client.unsubscribe_quote(symbols)
            self._subscribed.difference_update(symbols)
        except Exception as e:
            logger.debug(f"取消订阅失败: {e}")

    def get_price(self, symbol: str) -> Optional[float]:
        """获取缓存的最新价格，无缓存返回 None"""
        with self._lock:
            return self._prices.get(symbol)

    def get_all_prices(self) -> dict:
        with self._lock:
            return dict(self._prices)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def disconnect(self):
        self._shutdown = True  # 先设置退出标志，让守护线程退出
        if self._push_client and self._connected:
            try:
                self._push_client.disconnect()
                logger.info("推送客户端已断开")
            except Exception:
                pass
        self._connected = False


# 全局单例
price_cache = RealTimePriceCache()
