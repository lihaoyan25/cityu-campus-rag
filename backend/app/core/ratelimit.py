"""进程内 IP 限流：滑动窗口计数，无需外部依赖。

注意：仅适用于单进程部署（当前架构）；多 worker 部署需换 Redis 等共享存储。
"""
import logging
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class SlidingWindowLimiter:
    """按 key(通常为 IP) 的滑动窗口限流器。"""

    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._last_cleanup = time.monotonic()

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        """窗口内第 limit+1 次请求返回 False。"""
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        self._maybe_cleanup(now)
        return True

    def _maybe_cleanup(self, now: float) -> None:
        """周期性清空已过期 key，防止长期运行内存增长。"""
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now
        for k in [k for k, v in self._hits.items() if not v]:
            self._hits.pop(k, None)
