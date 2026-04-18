"""Optional disk caching for filing data.

Requires the ``cache`` extra::

    pip install edgar-analytics[cache]

When ``diskcache`` is unavailable, the cache layer is a transparent no-op.
Past-period filings are immutable and cached forever.  Current-period data
uses a 24-hour TTL.

**Security note**: diskcache uses pickle internally. The cache directory
is restricted to owner-only permissions (0o700) on creation to mitigate
tampered-payload risks.
"""

from __future__ import annotations

import hashlib
import os
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
            os.makedirs(directory, mode=0o700, exist_ok=True)
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
        try:
            return self._cache.get(key)  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("Cache deserialization failed for key %s: %s", key[:12], exc)
            return None

    def set(self, value: Any, namespace: str, *parts: str, ttl: Optional[int] = None) -> None:
        if not self._enabled:
            return
        key = self._key(namespace, *parts)
        if ttl is None:
            self._cache.set(key, value)  # type: ignore[union-attr]
        else:
            self._cache.set(key, value, expire=ttl)  # type: ignore[union-attr]

    def set_immutable(self, value: Any, namespace: str, *parts: str) -> None:
        """Cache a value forever (no TTL). Use for past-period filings."""
        self.set(value, namespace, *parts, ttl=None)

    def set_current(self, value: Any, namespace: str, *parts: str) -> None:
        """Cache a value with the current-period TTL (24h)."""
        self.set(value, namespace, *parts, ttl=_CURRENT_PERIOD_TTL)

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()
            self._cache = None

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> CacheLayer:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @property
    def enabled(self) -> bool:
        return self._enabled
