"""分析エンジンのユニットテスト（FeatureStrategy + トレンド分析）."""

from datetime import datetime

import numpy as np

from backend.analysis.feature import RawWorkTimeStrategy
from backend.analysis.trend import WARNING_THRESHOLD, compute_trend


class TestRawWorkTimeStrategy:
    """RawWorkTimeStrategy の特徴量抽出テスト."""

    def test_extract_returns_2d_array(self):
        """既知データで特徴量抽出 → shape が (n, 1) であること."""
        strategy = RawWorkTimeStrategy()
        timestamps = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3),
        ]
        result = strategy.extract([10.0, 20.0, 30.0], timestamps)
        assert result.shape == (3, 1)
        np.testing.assert_array_equal(result.flatten(), [10.0, 20.0, 30.0])

    def test_extract_empty(self):
        """空リスト → shape (0, 1)."""
        strategy = RawWorkTimeStrategy()
        result = strategy.extract([], [])
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
