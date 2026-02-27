"""IsolationForest 異常検知のユニットテスト."""

import numpy as np

from backend.analysis.anomaly import train_and_score


class TestTrainAndScore:
    """train_and_score() のテスト."""

    def test_outlier_scores_higher_than_normal_mean(self):
        """明確な外れ値 → スコアが正常点の平均より高い (1に近い=異常)."""
        rng = np.random.default_rng(0)
        normal = 10.0 + rng.normal(0, 0.3, size=200)
        baseline = normal.reshape(-1, 1)

        all_values = np.append(normal, [1000.0])
        all_data = all_values.reshape(-1, 1)

        scores = train_and_score(baseline, all_data)

        assert scores.shape == (201,)
        normal_mean = scores[:200].mean()
        assert scores[200] > normal_mean

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


class TestTrainAndScoreAnomalyParams:
    """anomaly_params を指定した場合のテスト."""

    def test_none_params_uses_defaults(self):
        """anomaly_params=None → デフォルト値で正常動作."""
        baseline = np.array([10.0, 11.0, 10.5, 10.8, 10.2]).reshape(-1, 1)
        all_data = np.array([10.0, 11.0, 50.0]).reshape(-1, 1)

        scores_none = train_and_score(baseline, all_data, anomaly_params=None)
        scores_default = train_and_score(baseline, all_data)

        np.testing.assert_allclose(scores_none, scores_default)

    def test_custom_n_estimators(self):
        """n_estimators を変更 → スコア形状は正しい."""
        baseline = np.array([10.0, 11.0, 10.5, 10.8, 10.2]).reshape(-1, 1)
        all_data = np.array([10.0, 11.0, 50.0]).reshape(-1, 1)

        scores = train_and_score(
            baseline, all_data, anomaly_params={"n_estimators": 50}
        )

        assert scores.shape == (3,)
        assert np.all(np.isfinite(scores))

    def test_custom_contamination(self):
        """contamination を数値で指定 → 正常動作."""
        rng = np.random.default_rng(0)
        normal = 10.0 + rng.normal(0, 0.3, size=200)
        baseline = normal.reshape(-1, 1)
        all_data = np.append(normal, [1000.0]).reshape(-1, 1)

        scores = train_and_score(
            baseline, all_data, anomaly_params={"contamination": 0.1}
        )

        assert scores.shape == (201,)
        assert np.all(np.isfinite(scores))

    def test_custom_max_samples(self):
        """max_samples を整数で指定 → 正常動作."""
        baseline = np.array([10.0, 11.0, 10.5, 10.8, 10.2]).reshape(-1, 1)
        all_data = np.array([10.0, 11.0, 50.0]).reshape(-1, 1)

        scores = train_and_score(
            baseline, all_data, anomaly_params={"max_samples": 3}
        )

        assert scores.shape == (3,)
        assert np.all(np.isfinite(scores))

    def test_partial_params_merged_with_defaults(self):
        """一部のみ指定 → 未指定はデフォルト値が使われる."""
        baseline = np.array([10.0, 11.0, 10.5, 10.8, 10.2]).reshape(-1, 1)
        all_data = np.array([10.0, 11.0, 50.0]).reshape(-1, 1)

        scores = train_and_score(
            baseline, all_data, anomaly_params={"n_estimators": 200}
        )

        assert scores.shape == (3,)
        assert np.all(np.isfinite(scores))


class TestScoreNormalization:
    """decision_function 正規化のテスト."""

    def test_scores_in_zero_one_range(self):
        """全スコアが [0, 1] 範囲内."""
        rng = np.random.default_rng(0)
        normal = 10.0 + rng.normal(0, 0.3, size=200)
        baseline = normal.reshape(-1, 1)
        all_values = np.append(normal, [1000.0])
        all_data = all_values.reshape(-1, 1)

        scores = train_and_score(baseline, all_data)

        assert np.all(scores >= 0.0)
        assert np.all(scores <= 1.0)

    def test_contamination_affects_scores(self):
        """contamination 値が異なる → スコア分布が変わる."""
        rng = np.random.default_rng(42)
        normal = 10.0 + rng.normal(0, 0.3, size=200)
        baseline = normal.reshape(-1, 1)
        all_data = baseline.copy()

        scores_low = train_and_score(
            baseline, all_data, anomaly_params={"contamination": 0.01}
        )
        scores_high = train_and_score(
            baseline, all_data, anomaly_params={"contamination": 0.1}
        )

        # contamination が高い → 0.5 超のポイントが多い
        above_low = np.sum(scores_low > 0.5)
        above_high = np.sum(scores_high > 0.5)
        assert above_high > above_low

    def test_boundary_maps_to_half(self):
        """contamination 境界が概ね 0.5 にマッピングされる."""
        rng = np.random.default_rng(0)
        baseline = (10.0 + rng.normal(0, 0.3, size=500)).reshape(-1, 1)

        scores = train_and_score(
            baseline, baseline, anomaly_params={"contamination": 0.05}
        )

        # ベースライン内で 0.5 超の割合が contamination に近い
        ratio = np.sum(scores > 0.5) / len(scores)
        assert 0.01 <= ratio <= 0.15  # 0.05 の前後で許容

    def test_all_identical_data(self):
        """全データ同一 → エラーなし、全スコアが有限."""
        baseline = np.full((10, 1), 5.0)
        all_data = np.full((15, 1), 5.0)

        scores = train_and_score(baseline, all_data)

        assert scores.shape == (15,)
        assert np.all(np.isfinite(scores))
