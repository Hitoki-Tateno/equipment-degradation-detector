"""FeatureBuilder の実装."""

from collections.abc import Sequence

import numpy as np

from backend.interfaces.feature import FeatureBuilder


class RawWorkTimeFeatureBuilder(FeatureBuilder):
    """生の作業時間をそのまま特徴量行列にする（デフォルト）.

    特徴量次元数 d = 1。
    """

    def _build_impl(self, work_times: Sequence[float]) -> np.ndarray:
        return np.array(list(work_times)).reshape(-1, 1)
