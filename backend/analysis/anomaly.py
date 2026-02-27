"""IsolationForest による異常検知."""

import numpy as np
from sklearn.ensemble import IsolationForest

_DEFAULTS: dict = {
    "n_estimators": 100,
    "contamination": "auto",
    "max_samples": "auto",
}


def train_and_score(
    baseline_data: np.ndarray,
    all_data: np.ndarray,
    anomaly_params: dict | None = None,
) -> np.ndarray:
    """ベースラインで学習し全データのスコアを返す.

    -score_samples() で原論文準拠の異常スコア (0〜1) を返す。
    1 に近いほど異常、0.5 付近が正常。バッチ非依存。

    Args:
        baseline_data: ベースライン特徴量 (n_baseline, d).
        all_data: 全期間特徴量 (n_all, d).
        anomaly_params: IsolationForest パラメータ（省略時はデフォルト値）.

    Returns:
        原論文準拠の異常スコア (n_all,). 0〜1, 1 = 最異常.
    """
    params = {**_DEFAULTS, **(anomaly_params or {})}
    model = IsolationForest(
        n_estimators=params["n_estimators"],
        max_samples=params["max_samples"],
        contamination=params["contamination"],
        random_state=42,
    )
    model.fit(baseline_data)
    return -model.score_samples(all_data)
