"""結果ストアの抽象インターフェース（境界③）。

分析結果の永続化と提供を担う。
分析層が書き込み、表示層が読み取る。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from backend.interfaces.feature import FeatureConfig


@dataclass(frozen=True)
class TrendResult:
    """トレンド分析結果。"""

    category_id: int
    slope: float
    intercept: float


@dataclass(frozen=True)
class AnomalyResult:
    """異常スコア結果。

    anomaly_score は原論文準拠の正規化スコア (0〜1, 1に近いほど異常)。
    scikit-learn の -score_samples() で算出。
    booleanではなくfloat。閾値判定はフロントエンド側で実行する。
    """

    category_id: int
    recorded_at: datetime
    anomaly_score: float


@dataclass
class ModelDefinition:
    """モデル定義（末端ノードごとに1つ保持）。

    ユーザーがStep 2でGUI上で定義するもの:
    1. ベースライン期間（baseline_start, baseline_end）
    2. ベースライン内の除外点（excluded_points）
    3. 感度（sensitivity → contamination相当の閾値にマッピング）
    """

    category_id: int
    baseline_start: datetime
    baseline_end: datetime
    sensitivity: float
    excluded_points: list[datetime] = field(default_factory=list)
    feature_config: FeatureConfig | None = None


class ResultStoreInterface(ABC):
    """結果ストアの抽象インターフェース。"""

    @abstractmethod
    def save_trend_result(self, result: TrendResult) -> None:
        """トレンド分析結果を保存する（上書き）。"""
        ...

    @abstractmethod
    def get_trend_result(self, category_id: int) -> TrendResult | None:
        """トレンド分析結果を取得する。"""
        ...

    @abstractmethod
    def save_anomaly_results(self, results: list[AnomalyResult]) -> None:
        """異常スコア結果をバッチ保存する（既存は上書き）。"""
        ...

    @abstractmethod
    def get_anomaly_results(self, category_id: int) -> list[AnomalyResult]:
        """指定分類の全異常スコア結果を取得する。"""
        ...

    @abstractmethod
    def save_model_definition(self, definition: ModelDefinition) -> None:
        """モデル定義を保存する（上書き）。"""
        ...

    @abstractmethod
    def get_model_definition(self, category_id: int) -> ModelDefinition | None:
        """モデル定義を取得する。"""
        ...

    @abstractmethod
    def delete_model_definition(self, category_id: int) -> None:
        """指定カテゴリのモデル定義を削除する。存在しない場合もエラーにしない。"""
        ...

    @abstractmethod
    def delete_anomaly_results(self, category_id: int) -> None:
        """指定カテゴリの全異常スコア結果を削除する。存在しない場合もエラーにしない。"""
        ...

    @abstractmethod
    def delete_all_data(self) -> None:
        """全データを削除する（デバッグ用）。"""
        ...
