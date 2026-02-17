"""分析エンジンのユニットテスト（FeatureBuilder + トレンド分析）."""

import numpy as np

from backend.analysis.feature import RawWorkTimeFeatureBuilder
from backend.analysis.trend import WARNING_THRESHOLD, compute_trend


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
