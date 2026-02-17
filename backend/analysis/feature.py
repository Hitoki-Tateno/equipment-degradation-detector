"""FeatureBuilder の実装."""

import numpy as np

from backend.interfaces.feature import FeatureBuilder


class RawWorkTimeFeatureBuilder(FeatureBuilder):
    """生の作業時間をそのまま特徴量行列にする（デフォルト）."""

    def build(self, work_times: list[float]) -> np.ndarray:
        return np.array(work_times).reshape(-1, 1)
