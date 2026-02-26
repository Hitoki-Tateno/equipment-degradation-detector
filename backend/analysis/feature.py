"""FeatureBuilder の実装."""

from collections.abc import Sequence
from datetime import datetime

import numpy as np

from backend.interfaces.feature import FeatureBuilder, FeatureConfig


class RawWorkTimeFeatureBuilder(FeatureBuilder):
    """生の作業時間をそのまま特徴量行列にする（デフォルト）.

    特徴量次元数 d = 1。
    """

    def _build_impl(
        self,
        work_times: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> np.ndarray:
        return np.array(list(work_times)).reshape(-1, 1)


class CompositeFeatureBuilder(FeatureBuilder):
    """複数の FeatureBuilder を結合する.

    各ビルダーの出力を np.hstack で水平結合し、
    ユーザーが自由に特徴量を組み合わせ可能にする。
    """

    def __init__(self, builders: list[FeatureBuilder]) -> None:
        if not builders:
            raise ValueError("At least one builder is required")
        self._builders = builders

    def _build_impl(
        self,
        work_times: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> np.ndarray:
        arrays = [b.build(work_times, timestamps) for b in self._builders]
        return np.hstack(arrays)


FEATURE_REGISTRY: dict[str, dict] = {
    "raw_work_time": {
        "builder": RawWorkTimeFeatureBuilder,
        "label": "作業時間（生値）",
        "description": "作業時間の生値をそのまま特徴量として使用する",
        "params_schema": {},
    },
}
"""利用可能な特徴量ビルダーのレジストリ。

キーは feature_type 文字列、値はメタデータ付き dict。
各エントリ: builder, label, description, params_schema。
新しい特徴量を追加する際はここに登録するだけで
API・ファクトリに自動反映される。
"""


def create_feature_builder(config: FeatureConfig) -> FeatureBuilder:
    """FeatureConfig から適切な FeatureBuilder を構築する.

    Args:
        config: ユーザーが選択した特徴量の組み合わせ

    Returns:
        単一ビルダーまたは CompositeFeatureBuilder

    Raises:
        ValueError: 未知の feature_type が指定された場合
    """
    if not config.features:
        return RawWorkTimeFeatureBuilder()

    builders: list[FeatureBuilder] = []
    for spec in config.features:
        entry = FEATURE_REGISTRY.get(spec.feature_type)
        if entry is None:
            raise ValueError(f"Unknown feature type: {spec.feature_type}")
        builders.append(entry["builder"](**spec.params))

    if len(builders) == 1:
        return builders[0]
    return CompositeFeatureBuilder(builders)
