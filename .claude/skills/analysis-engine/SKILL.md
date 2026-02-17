---
name: analysis-engine
description: 分析層（Isolation Forest + 線形回帰）の実装。異常検知モデル、トレンド分析、特徴量構築（FeatureBuilder）、スコア算出の実装時に使用する。「Isolation Forest」「回帰分析」「トレンド」「異常検知」「分析層」「特徴量」に関するタスクで発動する。
---

# 分析層実装

## 概要

`backend/analysis/` に分析エンジンを実装する。2つの独立した検知アプローチを併用する。

| 検知対象 | アプローチ | 対象期間 | 定義者 |
|---|---|---|---|
| 緩やかな経年劣化 | 線形回帰 | 全期間 | システム固定 |
| 突発的な異常値 | Isolation Forest | ベースライン期間 | ユーザー定義 |

## 分析実行タイミング

分析はデータ取り込みエンドポイント（POST /api/records, POST /api/records/csv）の処理末尾で**同期的に**実行する。スケジューラーや定期実行は使用しない。

- トレンド分析: レコードが存在すれば常時実行
- 異常検知: モデルが定義済みの場合のみ実行（未定義ならスキップ）

POST /api/analysis/run は手動トリガー（ダッシュボードの「分析実行」ボタン用）として残す。

## 依存方向

分析層は `backend/interfaces/` にのみ依存する。Store層の実装を直接importしない。

```python
from backend.interfaces.data_store import DataStoreInterface
from backend.interfaces.result_store import ResultStoreInterface

class AnalysisEngine:
    def __init__(self, data_store: DataStoreInterface, result_store: ResultStoreInterface):
        ...
```

## 特徴量構築（FeatureBuilder）

特徴ベクトルの構築方法は差し替え可能な構造にする:

- 契約: `backend/interfaces/feature.py` — `FeatureBuilder` ABC
- 実装: `backend/analysis/feature.py` — `RawWorkTimeFeatureBuilder`

```python
# backend/interfaces/feature.py
from abc import ABC, abstractmethod
from collections.abc import Sequence
import numpy as np

class FeatureBuilder(ABC):
    """Template Method: build() が ndim=2 を検証し、_build_impl() を呼ぶ。"""
    def build(self, work_times: Sequence[float]) -> np.ndarray: ...

    @abstractmethod
    def _build_impl(self, work_times: Sequence[float]) -> np.ndarray: ...

# backend/analysis/feature.py
class RawWorkTimeFeatureBuilder(FeatureBuilder):
    """生の作業時間を特徴量行列にする（デフォルト、d=1）。"""
    def _build_impl(self, work_times):
        return np.array(list(work_times)).reshape(-1, 1)
```

ユーザーには公開しない。変更は運用判断でシステム側が行う。

## Isolation Forestの仕様

[references/isolation-forest.md](references/isolation-forest.md) に詳細を記載。

**注意**: IsolationForestの実装は特徴量の選定が完了してから着手する。特徴量未定のまま実装すると手戻りが発生するため。

## 分析実行フロー

[references/analysis-flow.md](references/analysis-flow.md) に分析フロー全体を記載。

## TDD

分析層のロジックにはTDDを適用する。既知のデータセット（作業時間が線形に増加するデータ、明らかな外れ値を含むデータ等）に対して期待される結果をテストで先に定義する。
