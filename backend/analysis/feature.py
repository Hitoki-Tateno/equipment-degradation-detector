"""特徴量構築の戦略パターン."""

from abc import ABC, abstractmethod
from datetime import datetime

import numpy as np


class FeatureStrategy(ABC):
    """特徴量抽出の抽象基底クラス."""

    @abstractmethod
    def extract(self, work_times: list[float], timestamps: list[datetime]) -> np.ndarray:
        """作業時間とタイムスタンプから特徴量ベクトルを構築する."""


class RawWorkTimeStrategy(FeatureStrategy):
    """生の作業時間をそのまま特徴量として使用（デフォルト）."""

    def extract(self, work_times: list[float], timestamps: list[datetime]) -> np.ndarray:
        return np.array(work_times).reshape(-1, 1)
