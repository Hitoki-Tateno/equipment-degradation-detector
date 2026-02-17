"""特徴量構築のドメイン制約."""

from abc import ABC, abstractmethod

import numpy as np


class FeatureBuilder(ABC):
    """Isolation Forest に渡す特徴量行列を構築する契約."""

    @abstractmethod
    def build(self, work_times: list[float]) -> np.ndarray:
        """作業時間リストから特徴量行列 (n, d) を構築する."""
