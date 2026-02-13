"""結果ストアの契約テスト（TDD: Red phase）。

ResultStoreInterface の契約を検証する。
"""

from datetime import datetime

import pytest

from backend.interfaces.result_store import (
    AnomalyResult,
    ModelDefinition,
    ResultStoreInterface,
    TrendResult,
)


@pytest.fixture
def result_store(tmp_path):
    """結果ストアの実装インスタンスを返す。"""
    from backend.result_store.sqlite import SqliteResultStore

    return SqliteResultStore(str(tmp_path / "test_result.db"))


class TestTrendResults:
    """トレンド分析結果の契約テスト。"""

    def test_save_and_get(self, result_store: ResultStoreInterface):
        result = TrendResult(category_id=1, slope=0.5, intercept=10.0, is_warning=False)
        result_store.save_trend_result(result)

        loaded = result_store.get_trend_result(1)
        assert loaded is not None
        assert loaded.slope == 0.5
        assert loaded.intercept == 10.0
        assert loaded.is_warning is False

    def test_overwrite_on_same_category(self, result_store: ResultStoreInterface):
        result_store.save_trend_result(
            TrendResult(category_id=1, slope=0.5, intercept=10.0, is_warning=False)
        )
        result_store.save_trend_result(
            TrendResult(category_id=1, slope=1.0, intercept=20.0, is_warning=True)
        )

        loaded = result_store.get_trend_result(1)
        assert loaded is not None
        assert loaded.slope == 1.0
        assert loaded.is_warning is True

    def test_returns_none_for_missing(self, result_store: ResultStoreInterface):
        assert result_store.get_trend_result(999) is None


class TestAnomalyResults:
    """異常スコア結果の契約テスト。"""

    def test_save_and_get(self, result_store: ResultStoreInterface):
        results = [
            AnomalyResult(category_id=1, recorded_at=datetime(2025, 1, 1), anomaly_score=-0.3),
            AnomalyResult(category_id=1, recorded_at=datetime(2025, 1, 2), anomaly_score=-0.8),
        ]
        result_store.save_anomaly_results(results)

        loaded = result_store.get_anomaly_results(1)
        assert len(loaded) == 2

    def test_returns_empty_for_missing(self, result_store: ResultStoreInterface):
        assert result_store.get_anomaly_results(999) == []


class TestModelDefinitions:
    """モデル定義の契約テスト。"""

    def test_save_and_get(self, result_store: ResultStoreInterface):
        defn = ModelDefinition(
            category_id=1,
            baseline_start=datetime(2025, 1, 1),
            baseline_end=datetime(2025, 6, 1),
            sensitivity=0.5,
            excluded_points=[datetime(2025, 3, 15)],
        )
        result_store.save_model_definition(defn)

        loaded = result_store.get_model_definition(1)
        assert loaded is not None
        assert loaded.sensitivity == 0.5
        assert len(loaded.excluded_points) == 1

    def test_returns_none_for_missing(self, result_store: ResultStoreInterface):
        assert result_store.get_model_definition(999) is None
