"""Isolation Forest 用の特徴量構築インターフェース."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass(frozen=True)
class FeatureSpec:
    """1つの特徴量ビルダーの指定。

    feature_type は FEATURE_REGISTRY のキーに対応する。
    params はビルダー固有のパラメータ（例: window=5）。
    """

    feature_type: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FeatureConfig:
    """ユーザーが選択した特徴量の組み合わせ。

    ModelDefinition に永続化され、分析実行時に
    create_feature_builder() で CompositeFeatureBuilder を動的構築する。
    """

    features: list[FeatureSpec] = field(default_factory=list)


class FeatureBuilder(ABC):
    """Isolation Forest に渡す特徴量行列を構築する抽象基底クラス.

    サブクラスは _build_impl を実装する。build() が shape の
    ポスト条件（2次元配列）を検証する Template Method パターン。

    空の入力に対しては shape (0, d) の2次元配列を返すこと。
    d（特徴量の次元数）は実装依存。
    """

    def build(
        self,
        work_times: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> np.ndarray:
        """特徴量行列を構築し、shape を検証して返す.

        Args:
            work_times: 作業時間のシーケンス（長さ n）
            timestamps: 各レコードの記録日時（長さ n）。
                        時間情報系特徴量で使用。None の場合は未使用。

        Returns:
            shape (n, d) の2次元配列。d は実装依存。

        Raises:
            ValueError: サブクラスが2次元配列を返さなかった場合
        """
        result = self._build_impl(work_times, timestamps)
        if result.ndim != 2:
            raise ValueError(
                f"FeatureBuilder must return 2D array, got {result.ndim}D"
            )
        return result

    @abstractmethod
    def _build_impl(
        self,
        work_times: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> np.ndarray:
        """サブクラスが実装する特徴量構築ロジック.

        Args:
            work_times: 作業時間のシーケンス（長さ n）
            timestamps: 各レコードの記録日時（長さ n, optional）

        Returns:
            shape (n, d) の2次元配列
        """
