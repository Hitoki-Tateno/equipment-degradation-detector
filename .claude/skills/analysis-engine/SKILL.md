---
name: analysis-engine
description: 分析層（Isolation Forest + 線形回帰）の実装。異常検知モデル、トレンド分析、特徴量構築の戦略パターン、スコア算出、スケジューラーの実装時に使用する。「Isolation Forest」「回帰分析」「トレンド」「異常検知」「分析層」「スケジューラー」「特徴量」に関するタスクで発動する。
---

# 分析層実装

## 概要

`backend/analysis/` に分析エンジンを実装する。2つの独立した検知アプローチを併用する。

| 検知対象 | アプローチ | 対象期間 | 定義者 |
|---|---|---|---|
| 緩やかな経年劣化 | 線形回帰 | 全期間 | システム固定 |
| 突発的な異常値 | Isolation Forest | ベースライン期間 | ユーザー定義 |

## 依存方向

分析層は `backend/interfaces/` にのみ依存する。Store層の実装を直接importしない。

```python
from backend.interfaces.data_store import DataStoreInterface
from backend.interfaces.result_store import ResultStoreInterface

class AnalysisEngine:
    def __init__(self, data_store: DataStoreInterface, result_store: ResultStoreInterface):
        ...
```

## 特徴量構築（戦略パターン）

特徴ベクトルの構築方法は差し替え可能な構造にする:

```python
from abc import ABC, abstractmethod
import numpy as np

class FeatureStrategy(ABC):
    @abstractmethod
    def extract(self, work_times: list[float], timestamps: list[datetime]) -> np.ndarray:
        ...

class RawWorkTimeStrategy(FeatureStrategy):
    """生の作業時間を特徴量として使用（デフォルト）。"""
    def extract(self, work_times, timestamps):
        return np.array(work_times).reshape(-1, 1)
```

ユーザーには公開しない。変更は運用判断でシステム側が行う。

## Isolation Forestの仕様

[references/isolation-forest.md](references/isolation-forest.md) に詳細を記載。

## 判定フロー（Step 3: 継続監視）

[references/analysis-flow.md](references/analysis-flow.md) に判定フロー全体を記載。

## TDD

分析層のロジックにはTDDを適用する。既知のデータセット（作業時間が線形に増加するデータ、明らかな外れ値を含むデータ等）に対して期待される結果をテストで先に定義する。
