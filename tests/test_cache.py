"""tests/test_cache.py — unit tests for CacheLayer."""

import pytest
from edgar_analytics.cache import CacheLayer, HAS_DISKCACHE


class TestCacheLayerNoBackend:
    """Test CacheLayer when diskcache is not available or disabled."""

    def test_disabled_get_returns_none(self):
        cache = CacheLayer(enabled=False)
        assert cache.get("ns", "key") is None

    def test_disabled_set_is_noop(self):
        cache = CacheLayer(enabled=False)
        cache.set("value", "ns", "key")
        assert cache.get("ns", "key") is None

    def test_disabled_close_is_noop(self):
        cache = CacheLayer(enabled=False)
        cache.close()

    def test_enabled_property(self):
        cache = CacheLayer(enabled=False)
        assert cache.enabled is False


class TestCacheLayerKey:
    def test_key_deterministic(self):
        k1 = CacheLayer._key("ns", "a", "b")
        k2 = CacheLayer._key("ns", "a", "b")
        assert k1 == k2

    def test_key_different_for_different_inputs(self):
        k1 = CacheLayer._key("ns", "a")
        k2 = CacheLayer._key("ns", "b")
        assert k1 != k2


@pytest.mark.skipif(not HAS_DISKCACHE, reason="diskcache not installed")
class TestCacheLayerWithBackend:
    """Test CacheLayer with real diskcache backend."""

    def test_set_and_get(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"))
        cache.set("hello", "ns", "key1")
        assert cache.get("ns", "key1") == "hello"
        cache.close()

    def test_set_immutable(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"))
        cache.set_immutable({"data": 42}, "filings", "AAPL", "10-K")
        assert cache.get("filings", "AAPL", "10-K") == {"data": 42}
        cache.close()

    def test_set_current_with_ttl(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"))
        cache.set_current("recent", "ns", "current_key")
        assert cache.get("ns", "current_key") == "recent"
        cache.close()

    def test_get_missing_returns_none(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"))
        assert cache.get("ns", "nonexistent") is None
        cache.close()

    def test_enabled_property_true(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"))
        assert cache.enabled is True
        cache.close()
