"""分析エンジンのユニットテスト（FeatureBuilder + トレンド分析 + オーケストレータ）."""

from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.analysis.engine import AnalysisEngine
from backend.analysis.feature import RawWorkTimeFeatureBuilder
from backend.analysis.trend import WARNING_THRESHOLD, compute_trend
from backend.interfaces.data_store import CategoryNode, DataStoreInterface, WorkRecord
from backend.interfaces.feature import FeatureBuilder
from backend.interfaces.result_store import ResultStoreInterface, TrendResult


class TestRawWorkTimeFeatureBuilder:
    """RawWorkTimeFeatureBuilder の特徴量構築テスト."""

    def test_build_returns_2d_array(self):
        """既知データで構築 → shape が (n, 1) であること."""
        builder = RawWorkTimeFeatureBuilder()
        result = builder.build([10.0, 20.0, 30.0])
        assert result.shape == (3, 1)
        np.testing.assert_array_equal(result.flatten(), [10.0, 20.0, 30.0])

    def test_build_empty(self):
        """空リスト → shape (0, 1)."""
        builder = RawWorkTimeFeatureBuilder()
        result = builder.build([])
        assert result.shape == (0, 1)

    def test_build_accepts_tuple(self):
        """tuple 入力も受け付けること."""
        builder = RawWorkTimeFeatureBuilder()
        result = builder.build((5.0, 10.0))
        assert result.shape == (2, 1)

    def test_build_rejects_non_2d(self):
        """_build_impl が1次元を返した場合 ValueError."""

        class BadBuilder(FeatureBuilder):
            def _build_impl(self, work_times):
                return np.array(list(work_times))

        with pytest.raises(ValueError, match="2D array"):
            BadBuilder().build([1.0, 2.0])


class TestComputeTrend:
    """compute_trend のトレンド分析テスト."""

    def test_linear_increase_positive_slope(self):
        """線形増加データ → slope > 0."""
        n = np.array([1, 2, 3, 4, 5])
        wt = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        slope, intercept, _ = compute_trend(n, wt)
        assert slope > 0

    def test_flat_data_near_zero_slope(self):
        """平坦データ → slope ≈ 0."""
        n = np.array([1, 2, 3, 4, 5])
        wt = np.array([10.0, 10.0, 10.0, 10.0, 10.0])
        slope, _, _ = compute_trend(n, wt)
        assert abs(slope) < 1e-9

    def test_warning_when_slope_exceeds_threshold(self):
        """WARNING_THRESHOLD 超過 → is_warning = True."""
        n = np.array([1, 2])
        wt = np.array([0.0, WARNING_THRESHOLD * 10])
        _, _, is_warning = compute_trend(n, wt)
        assert is_warning is True

    def test_no_warning_below_threshold(self):
        """平坦データ → is_warning = False."""
        n = np.array([1, 2, 3])
        wt = np.array([10.0, 10.0, 10.0])
        _, _, is_warning = compute_trend(n, wt)
        assert is_warning is False


# --- AnalysisEngine オーケストレータテスト (issue #23) ---


@pytest.fixture
def mock_data_store():
    """DataStoreInterface のモック."""
    return MagicMock(spec=DataStoreInterface)


@pytest.fixture
def mock_result_store():
    """ResultStoreInterface のモック."""
    return MagicMock(spec=ResultStoreInterface)


@pytest.fixture
def engine(mock_data_store, mock_result_store):
    """テスト用 AnalysisEngine."""
    return AnalysisEngine(mock_data_store, mock_result_store)


class TestCollectLeaves:
    """_collect_leaves のユニットテスト."""

    def test_flat_list(self):
        """全ノードが末端 → 全て返す."""
        nodes = [
            CategoryNode(id=1, name="A", parent_id=None, children=[]),
            CategoryNode(id=2, name="B", parent_id=None, children=[]),
        ]
        result = AnalysisEngine._collect_leaves(nodes)
        assert len(result) == 2
        assert {n.id for n in result} == {1, 2}

    def test_nested_tree(self):
        """ネストしたツリー → 末端のみ返す."""
        nodes = [
            CategoryNode(
                id=1,
                name="Root",
                parent_id=None,
                children=[
                    CategoryNode(
                        id=2,
                        name="Mid",
                        parent_id=1,
                        children=[
                            CategoryNode(id=3, name="Leaf", parent_id=2, children=[]),
                        ],
                    ),
                ],
            ),
        ]
        result = AnalysisEngine._collect_leaves(nodes)
        assert len(result) == 1
        assert result[0].id == 3

    def test_empty(self):
        """空リスト → 空リスト."""
        assert AnalysisEngine._collect_leaves([]) == []


class TestAnalysisEngineRun:
    """AnalysisEngine.run() のユニットテスト."""

    def test_computes_trend_and_saves(self, engine, mock_data_store, mock_result_store):
        """レコード有り → トレンド計算して結果保存."""
        records = [
            WorkRecord(category_id=1, work_time=10.0, recorded_at=datetime(2025, 1, 1)),
            WorkRecord(category_id=1, work_time=20.0, recorded_at=datetime(2025, 2, 1)),
            WorkRecord(category_id=1, work_time=30.0, recorded_at=datetime(2025, 3, 1)),
        ]
        mock_data_store.get_records.return_value = records
        mock_result_store.get_model_definition.return_value = None

        engine.run(1)

        mock_data_store.get_records.assert_called_once_with(1)
        mock_result_store.save_trend_result.assert_called_once()
        saved = mock_result_store.save_trend_result.call_args[0][0]
        assert isinstance(saved, TrendResult)
        assert saved.category_id == 1
        assert saved.slope > 0

    def test_no_records_does_not_save(self, engine, mock_data_store, mock_result_store):
        """レコード無し → save_trend_result 呼ばれない."""
        mock_data_store.get_records.return_value = []

        engine.run(1)

        mock_result_store.save_trend_result.assert_not_called()

    def test_checks_model_definition(self, engine, mock_data_store, mock_result_store):
        """run() は get_model_definition を呼ぶ."""
        records = [
            WorkRecord(category_id=1, work_time=10.0, recorded_at=datetime(2025, 1, 1)),
        ]
        mock_data_store.get_records.return_value = records
        mock_result_store.get_model_definition.return_value = None

        engine.run(1)

        mock_result_store.get_model_definition.assert_called_once_with(1)

    def test_sorts_by_recorded_at(self, engine, mock_data_store, mock_result_store):
        """逆順レコード → ソートされてトレンド計算."""
        records = [
            WorkRecord(category_id=1, work_time=30.0, recorded_at=datetime(2025, 3, 1)),
            WorkRecord(category_id=1, work_time=10.0, recorded_at=datetime(2025, 1, 1)),
            WorkRecord(category_id=1, work_time=20.0, recorded_at=datetime(2025, 2, 1)),
        ]
        mock_data_store.get_records.return_value = records
        mock_result_store.get_model_definition.return_value = None

        engine.run(1)

        saved = mock_result_store.save_trend_result.call_args[0][0]
        assert saved.slope > 0  # ソート後 [10, 20, 30] → 正の傾き

    def test_single_record(self, engine, mock_data_store, mock_result_store):
        """1件のみ → エラーなく保存される."""
        records = [
            WorkRecord(category_id=1, work_time=10.0, recorded_at=datetime(2025, 1, 1)),
        ]
        mock_data_store.get_records.return_value = records
        mock_result_store.get_model_definition.return_value = None

        engine.run(1)

        mock_result_store.save_trend_result.assert_called_once()
        saved = mock_result_store.save_trend_result.call_args[0][0]
        assert saved.category_id == 1


class TestAnalysisEngineRunAll:
    """AnalysisEngine.run_all() のユニットテスト."""

    def test_calls_run_for_each_leaf(self, engine, mock_data_store, mock_result_store):
        """末端カテゴリごとに run() が呼ばれる."""
        tree = [
            CategoryNode(
                id=1,
                name="ProcessA",
                parent_id=None,
                children=[
                    CategoryNode(id=2, name="Equip1", parent_id=1, children=[]),
                    CategoryNode(id=3, name="Equip2", parent_id=1, children=[]),
                ],
            ),
        ]
        mock_data_store.get_category_tree.return_value = tree
        mock_data_store.get_records.return_value = [
            WorkRecord(category_id=2, work_time=10.0, recorded_at=datetime(2025, 1, 1)),
        ]
        mock_result_store.get_model_definition.return_value = None

        result = engine.run_all()

        assert result == 2
        assert mock_data_store.get_records.call_count == 2
        mock_data_store.get_records.assert_any_call(2)
        mock_data_store.get_records.assert_any_call(3)

    def test_empty_tree(self, engine, mock_data_store, mock_result_store):
        """空ツリー → 何もしない."""
        mock_data_store.get_category_tree.return_value = []

        result = engine.run_all()

        assert result == 0
        mock_data_store.get_records.assert_not_called()

    def test_skips_non_leaf(self, engine, mock_data_store, mock_result_store):
        """親ノードは処理されない — 末端のみ."""
        tree = [
            CategoryNode(
                id=1,
                name="Root",
                parent_id=None,
                children=[
                    CategoryNode(id=2, name="Leaf", parent_id=1, children=[]),
                ],
            ),
        ]
        mock_data_store.get_category_tree.return_value = tree
        mock_data_store.get_records.return_value = []

        result = engine.run_all()

        assert result == 1
        mock_data_store.get_records.assert_called_once_with(2)
