"""IsolationForest 異常検知のユニットテスト."""

import numpy as np

from backend.analysis.anomaly import train_and_score


class TestTrainAndScore:
    """train_and_score() のテスト."""

    def test_outlier_scores_lower_than_normal_mean(self):
        """明確な外れ値 → スコアが正常点の平均より低い."""
        rng = np.random.default_rng(0)
        normal = 10.0 + rng.normal(0, 0.3, size=200)
        baseline = normal.reshape(-1, 1)

        all_values = np.append(normal, [1000.0])
        all_data = all_values.reshape(-1, 1)

        scores = train_and_score(baseline, all_data)

        assert scores.shape == (201,)
        normal_mean = scores[:200].mean()
        assert scores[200] < normal_mean

    def test_baseline_only_returns_finite_scores(self):
        """ベースラインのみ → 全スコアが有限."""
        data = np.array([10.0, 11.0, 10.5, 10.8, 10.2]).reshape(-1, 1)

        scores = train_and_score(data, data)

        assert scores.shape == (5,)
        assert np.all(np.isfinite(scores))

    def test_returns_1d_float_array(self):
        """戻り値は1次元 float 配列."""
        baseline = np.array([1.0, 2.0, 3.0]).reshape(-1, 1)
        all_data = np.array([1.0, 2.0, 3.0, 50.0]).reshape(-1, 1)

        scores = train_and_score(baseline, all_data)

        assert scores.ndim == 1
        assert np.issubdtype(scores.dtype, np.floating)

    def test_deterministic_with_random_state(self):
        """同一データ → 同一スコア（再現性）."""
        baseline = np.array([10.0, 11.0, 10.5, 10.8, 10.2]).reshape(-1, 1)
        all_data = np.array([10.0, 11.0, 50.0]).reshape(-1, 1)

        scores1 = train_and_score(baseline, all_data)
        scores2 = train_and_score(baseline, all_data)

        np.testing.assert_array_equal(scores1, scores2)
