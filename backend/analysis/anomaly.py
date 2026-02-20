"""IsolationForest による異常検知."""

import numpy as np
from sklearn.ensemble import IsolationForest


def train_and_score(
    baseline_data: np.ndarray,
    all_data: np.ndarray,
) -> np.ndarray:
    """ベースラインで学習し全データのスコアを返す.

    Args:
        baseline_data: ベースライン特徴量 (n_baseline, d).
        all_data: 全期間特徴量 (n_all, d).

    Returns:
        原論文準拠の異常スコア (n_all,). 0〜1, 1に近いほど異常.
    """
    model = IsolationForest(
        n_estimators=100,
        random_state=42,
        contamination="auto",
    )
    model.fit(baseline_data)
    return -model.score_samples(all_data)
