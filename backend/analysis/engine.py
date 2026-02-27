"""分析エンジン — トレンド分析と異常検知のオーケストレーター."""

import numpy as np

from backend.analysis.anomaly import train_and_score
from backend.analysis.feature import (
    RawWorkTimeFeatureBuilder,
    create_feature_builder,
)
from backend.analysis.trend import compute_trend
from backend.interfaces.data_store import (
    CategoryNode,
    DataStoreInterface,
)
from backend.interfaces.feature import FeatureBuilder
from backend.interfaces.result_store import (
    AnomalyResult,
    ResultStoreInterface,
    TrendResult,
)


class AnalysisEngine:
    """分析エンジン.

    DataStore からデータを取得し、トレンド分析・異常検知を実行し、
    結果を ResultStore に保存する。
    """

    def __init__(
        self,
        data_store: DataStoreInterface,
        result_store: ResultStoreInterface,
        feature_builder: FeatureBuilder | None = None,
    ) -> None:
        self._data_store = data_store
        self._result_store = result_store
        if feature_builder is None:
            feature_builder = RawWorkTimeFeatureBuilder()
        self._feature_builder = feature_builder

    def run(self, category_id: int) -> None:
        """指定カテゴリの分析を実行する.

        1. Store から全期間データを取得
        2. トレンド分析を実行し結果保存
        3. モデル定義があれば IsolationForest で異常検知
        """
        records = self._data_store.get_records(category_id)
        if not records:
            return

        records = sorted(records, key=lambda r: r.recorded_at)
        n_values = np.arange(1, len(records) + 1)
        work_times = np.array([r.work_time for r in records])

        slope, intercept = compute_trend(n_values, work_times)

        self._result_store.save_trend_result(
            TrendResult(
                category_id=category_id,
                slope=slope,
                intercept=intercept,
            )
        )

        # 異常検知（IsolationForest）
        model_def = self._result_store.get_model_definition(category_id)
        if model_def is not None:
            bl_start = model_def.baseline_start.replace(tzinfo=None)
            bl_end = model_def.baseline_end.replace(tzinfo=None)
            baseline_records = [
                r
                for r in records
                if bl_start <= r.recorded_at.replace(tzinfo=None) <= bl_end
            ]
            excluded = {
                dt.replace(tzinfo=None) for dt in model_def.excluded_points
            }
            baseline_records = [
                r
                for r in baseline_records
                if r.recorded_at.replace(tzinfo=None) not in excluded
            ]
            if not baseline_records:
                return

            # feature_config で動的ビルダー生成
            if model_def.feature_config is not None:
                feature_builder = create_feature_builder(
                    model_def.feature_config
                )
            else:
                feature_builder = self._feature_builder

            baseline_wt = [r.work_time for r in baseline_records]
            all_wt = [r.work_time for r in records]
            baseline_ts = [r.recorded_at for r in baseline_records]
            all_ts = [r.recorded_at for r in records]
            baseline_feat = feature_builder.build(baseline_wt, baseline_ts)
            all_feat = feature_builder.build(all_wt, all_ts)

            scores = train_and_score(
                baseline_feat,
                all_feat,
                anomaly_params=model_def.anomaly_params,
            )

            anomaly_results = [
                AnomalyResult(
                    category_id=category_id,
                    recorded_at=records[i].recorded_at,
                    anomaly_score=float(scores[i]),
                )
                for i in range(len(records))
            ]
            self._result_store.save_anomaly_results(anomaly_results)

    def run_all(self) -> int:
        """全末端カテゴリに対してトレンド分析を実行する.

        Returns:
            処理した末端カテゴリ数。
        """
        tree = self._data_store.get_category_tree()
        leaves = self._collect_leaves(tree)
        for leaf in leaves:
            self.run(leaf.id)
        return len(leaves)

    @staticmethod
    def _collect_leaves(nodes: list[CategoryNode]) -> list[CategoryNode]:
        """カテゴリツリーから末端ノードを再帰的に収集する."""
        leaves: list[CategoryNode] = []
        for node in nodes:
            if not node.children:
                leaves.append(node)
            else:
                leaves.extend(AnalysisEngine._collect_leaves(node.children))
        return leaves
