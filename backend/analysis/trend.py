"""線形回帰によるトレンド分析."""

import numpy as np
from sklearn.linear_model import LinearRegression

WARNING_THRESHOLD: float = 0.5
"""slope がこの値を超えた場合に警告フラグを立てる（仮値）."""


def compute_trend(
    n_values: np.ndarray, work_times: np.ndarray
) -> tuple[float, float, bool]:
    """線形回帰でトレンドを算出する.

    Args:
        n_values: 連番（タイムスタンプ昇順ソートから導出）
        work_times: 作業時間の配列

    Returns:
        (slope, intercept, is_warning)
    """
    model = LinearRegression()
    model.fit(n_values.reshape(-1, 1), work_times)
    slope = float(model.coef_[0])
    intercept = float(model.intercept_)
    is_warning = slope > WARNING_THRESHOLD
    return slope, intercept, is_warning
