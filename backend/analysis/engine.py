"""分析エンジン — トレンド分析と異常検知のオーケストレーター."""

import numpy as np

from backend.analysis.trend import compute_trend
from backend.interfaces.data_store import CategoryNode, DataStoreInterface
from backend.interfaces.result_store import ResultStoreInterface, TrendResult


class AnalysisEngine:
    """分析エンジン.

    DataStore からデータを取得し、トレンド分析を実行し、
    結果を ResultStore に保存する。
    """

    def __init__(
        self,
        data_store: DataStoreInterface,
        result_store: ResultStoreInterface,
    ) -> None:
        self._data_store = data_store
        self._result_store = result_store

    def run(self, category_id: int) -> None:
        """指定カテゴリのトレンド分析を実行する.

        1. Store から全期間データを取得
        2. レコードが存在すればトレンド分析を実行し結果保存
        3. モデル定義の有無を確認（異常検知は #7 で実装予定）
        """
        records = self._data_store.get_records(category_id)
        if not records:
            return

        records = sorted(records, key=lambda r: r.recorded_at)
        n_values = np.arange(1, len(records) + 1)
        work_times = np.array([r.work_time for r in records])

        slope, intercept, is_warning = compute_trend(n_values, work_times)

        self._result_store.save_trend_result(
            TrendResult(
                category_id=category_id,
                slope=slope,
                intercept=intercept,
                is_warning=is_warning,
            )
        )

        # モデル定義チェック（異常検知は #7 で実装）
        model_def = self._result_store.get_model_definition(category_id)
        if model_def is not None:
            pass  # TODO: #7 Isolation Forest

    def run_all(self) -> None:
        """全末端カテゴリに対してトレンド分析を実行する."""
        tree = self._data_store.get_category_tree()
        for leaf in self._collect_leaves(tree):
            self.run(leaf.id)

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
