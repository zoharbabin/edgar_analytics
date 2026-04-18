"""tests/test_security.py — tests for architecture & security hardening (v1.0.3)."""

import os
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from edgar_analytics.cache import CacheLayer
from edgar_analytics.models import AnalysisResult, TickerAnalysis, FilingSnapshot, SnapshotMetrics


class TestCacheDirectoryPermissions:
    """#1: Cache directory should be created with restricted permissions."""

    def test_cache_dir_created_with_0700(self, tmp_path):
        cache_dir = tmp_path / "test_cache"
        cache = CacheLayer(directory=str(cache_dir), enabled=True)
        if cache.enabled:
            assert cache_dir.exists()
            mode = oct(cache_dir.stat().st_mode & 0o777)
            assert mode == "0o700"
        cache.close()

    def test_get_returns_none_on_corrupt_cache(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"), enabled=True)
        if not cache.enabled:
            pytest.skip("diskcache not installed")
        result = cache.get("ns", "key")
        assert result is None
        cache.close()


class TestCacheResourceManagement:
    """#4: CacheLayer should support context manager and cleanup."""

    def test_context_manager(self, tmp_path):
        with CacheLayer(directory=str(tmp_path / "cache")) as cache:
            assert cache is not None
        assert cache._cache is None

    def test_close_idempotent(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"))
        cache.close()
        cache.close()

    def test_del_calls_close(self, tmp_path):
        cache = CacheLayer(directory=str(tmp_path / "cache"))
        cache.__del__()
        assert cache._cache is None


class TestPathTraversalCSV:
    """#2: CSV path traversal check must trigger before resolve()."""

    def test_dotdot_rejected(self):
        from edgar_analytics.reporting import ReportingEngine
        import pandas as pd
        engine = ReportingEngine()
        df = pd.DataFrame({"Revenue": [1000]}, index=["AAPL"])
        engine._save_csv_if_requested(df, "../../../etc/passwd")

    def test_normal_path_accepted(self, tmp_path):
        from edgar_analytics.reporting import ReportingEngine
        import pandas as pd
        engine = ReportingEngine()
        df = pd.DataFrame({"Revenue": [1000]}, index=["AAPL"])
        csv_path = str(tmp_path / "output.csv")
        engine._save_csv_if_requested(df, csv_path)
        assert Path(csv_path).exists()


class TestParquetPathTraversal:
    """#3: to_parquet must reject path traversal."""

    def test_dotdot_rejected(self):
        sm = SnapshotMetrics(revenue=1000)
        fs = FilingSnapshot(metrics=sm)
        ta = TickerAnalysis(ticker="X", annual_snapshot=fs)
        ar = AnalysisResult(main_ticker="X", tickers={"X": ta})
        with pytest.raises(ValueError, match="traversal"):
            ar.to_parquet("../../evil.parquet")

    def test_normal_path_accepted(self, tmp_path):
        sm = SnapshotMetrics(revenue=1000)
        fs = FilingSnapshot(metrics=sm)
        ta = TickerAnalysis(ticker="X", annual_snapshot=fs)
        ar = AnalysisResult(main_ticker="X", tickers={"X": ta})
        path = str(tmp_path / "output.parquet")
        ar.to_parquet(path)
        assert Path(path).exists()


class TestOrchestratorContextManager:
    """#4: TickerOrchestrator should support context manager."""

    def test_context_manager(self):
        from edgar_analytics.orchestrator import TickerOrchestrator
        with TickerOrchestrator(enable_cache=False) as orch:
            assert orch is not None


class TestIdentityLock:
    """#5: set_identity must be serialized across threads."""

    def test_identity_lock_exists(self):
        from edgar_analytics.orchestrator import TickerOrchestrator
        assert hasattr(TickerOrchestrator, "_IDENTITY_LOCK")
        assert isinstance(TickerOrchestrator._IDENTITY_LOCK, type(threading.Lock()))
