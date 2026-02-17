"""Isolation Forest 用の特徴量構築インターフェース."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

import numpy as np


class FeatureBuilder(ABC):
    """Isolation Forest に渡す特徴量行列を構築する抽象基底クラス.

    サブクラスは _build_impl を実装する。build() が shape の
    ポスト条件（2次元配列）を検証する Template Method パターン。

    空の入力に対しては shape (0, d) の2次元配列を返すこと。
    d（特徴量の次元数）は実装依存。
    """

    def build(self, work_times: Sequence[float]) -> np.ndarray:
        """特徴量行列を構築し、shape を検証して返す.

        Args:
            work_times: 作業時間のシーケンス（長さ n）

        Returns:
            shape (n, d) の2次元配列。d は実装依存。

        Raises:
            ValueError: サブクラスが2次元配列を返さなかった場合
        """
        result = self._build_impl(work_times)
        if result.ndim != 2:
            raise ValueError(f"FeatureBuilder must return 2D array, got {result.ndim}D")
        return result

    @abstractmethod
    def _build_impl(self, work_times: Sequence[float]) -> np.ndarray:
        """サブクラスが実装する特徴量構築ロジック.

        Args:
            work_times: 作業時間のシーケンス（長さ n）

        Returns:
            shape (n, d) の2次元配列
        """
