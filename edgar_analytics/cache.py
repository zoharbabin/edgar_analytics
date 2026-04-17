"""Optional disk caching for filing data.

Requires the ``cache`` extra::

    pip install edgar-analytics[cache]

When ``diskcache`` is unavailable, the cache layer is a transparent no-op.
Past-period filings are immutable and cached forever.  Current-period data
uses a 24-hour TTL.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Optional

from .logging_utils import get_logger

logger = get_logger(__name__)

try:
    import diskcache
    HAS_DISKCACHE = True
except ImportError:
    HAS_DISKCACHE = False

_DEFAULT_DIR = ".edgar_cache"
_CURRENT_PERIOD_TTL = 86400  # 24 hours


class CacheLayer:
    """SQLite-backed disk cache with TTL support.

    When ``diskcache`` is not installed, all operations are no-ops and
    :meth:`get` always returns ``None``.
    """

    def __init__(self, directory: str = _DEFAULT_DIR, enabled: bool = True) -> None:
        self._enabled = enabled and HAS_DISKCACHE
        self._cache: Optional[Any] = None
        if self._enabled:
            self._cache = diskcache.Cache(directory)
            logger.debug("Disk cache initialized at %s", directory)

    @staticmethod
    def _key(namespace: str, *parts: str) -> str:
        raw = ":".join([namespace] + list(parts))
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, namespace: str, *parts: str) -> Optional[Any]:
        if not self._enabled:
            return None
        key = self._key(namespace, *parts)
        return self._cache.get(key)

    def set(self, value: Any, namespace: str, *parts: str, ttl: Optional[int] = None) -> None:
        if not self._enabled:
            return
        key = self._key(namespace, *parts)
        if ttl is None:
            self._cache.set(key, value)
        else:
            self._cache.set(key, value, expire=ttl)

    def set_immutable(self, value: Any, namespace: str, *parts: str) -> None:
        """Cache a value forever (no TTL). Use for past-period filings."""
        self.set(value, namespace, *parts, ttl=None)

    def set_current(self, value: Any, namespace: str, *parts: str) -> None:
        """Cache a value with the current-period TTL (24h)."""
        self.set(value, namespace, *parts, ttl=_CURRENT_PERIOD_TTL)

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()

    @property
    def enabled(self) -> bool:
        return self._enabled
