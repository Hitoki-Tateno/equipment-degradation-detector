"""IsolationForest による異常検知."""

import numpy as np
from sklearn.ensemble import IsolationForest

_DEFAULTS: dict = {
    "n_estimators": 100,
    "contamination": 0.01,
    "max_samples": "auto",
}


def train_and_score(
    baseline_data: np.ndarray,
    all_data: np.ndarray,
    anomaly_params: dict | None = None,
) -> np.ndarray:
    """ベースラインで学習し全データのスコアを返す.

    decision_function を contamination 校正境界 (= 0.5) で正規化し、
    0〜1 のスコアを返す。contamination パラメータが実際にスコアに反映される。

    Args:
        baseline_data: ベースライン特徴量 (n_baseline, d).
        all_data: 全期間特徴量 (n_all, d).
        anomaly_params: IsolationForest パラメータ（省略時はデフォルト値）.

    Returns:
        正規化異常スコア (n_all,). 0〜1, 0.5 = contamination 境界, 1 = 最異常.
    """
    params = {**_DEFAULTS, **(anomaly_params or {})}
    model = IsolationForest(
        n_estimators=params["n_estimators"],
        max_samples=params["max_samples"],
        contamination=params["contamination"],
        random_state=42,
    )
    model.fit(baseline_data)

    # スケーリング基準をベースライン(学習データ)から算出（固定）
    baseline_raw = -model.decision_function(baseline_data)
    pos_max = baseline_raw.max() if baseline_raw.max() > 0 else 1.0
    neg_min = abs(baseline_raw.min()) if baseline_raw.min() < 0 else 1.0

    # 全データをスコアリング
    raw = -model.decision_function(all_data)
    scores = np.where(
        raw >= 0,
        0.5 + 0.5 * raw / pos_max,
        0.5 - 0.5 * np.abs(raw) / neg_min,
    )
    return np.clip(scores, 0.0, 1.0)
