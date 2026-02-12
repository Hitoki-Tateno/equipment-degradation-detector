# 分析判定フロー

## 定期実行フロー（Step 3）

スケジューラー（`backend/scheduler/main.py`）が以下を実行:

1. 定期実行（またはPOST /api/analysis/runによる手動トリガー）で起動
2. 全カテゴリ（末端ノード）を列挙
3. 各カテゴリについて:
   a. Store層から全期間データを取得
   b. **トレンド分析**: 線形回帰を全期間で実行。傾き・切片・警告有無を算出し結果ストアに保存
   c. モデル定義が存在する場合:
      - Store層からベースライン期間データを取得
      - 除外点を除去
      - Isolation Forestで学習
      - 全期間データに対してscore_samples()を実行
      - anomaly_scoresを結果ストアに保存

## トレンド分析

```python
from sklearn.linear_model import LinearRegression
import numpy as np

def compute_trend(n_values: np.ndarray, work_times: np.ndarray) -> tuple[float, float, bool]:
    """線形回帰でトレンドを算出する。

    Args:
        n_values: 回数（連番。タイムスタンプから導出）
        work_times: 作業時間

    Returns:
        (slope, intercept, is_warning)
    """
    model = LinearRegression()
    model.fit(n_values.reshape(-1, 1), work_times)
    slope = model.coef_[0]
    intercept = model.intercept_
    # 警告閾値はシステム固定で定義（要調整）
    is_warning = slope > WARNING_THRESHOLD
    return slope, intercept, is_warning
```

`WARNING_THRESHOLD` はシステム設定として管理する。ユーザーには公開しない。

## 「回数n」の導出

回数はドメインモデルに含めない。分析時にタイムスタンプの昇順ソートで連番を振る:

```python
records = sorted(records, key=lambda r: r.recorded_at)
n_values = np.arange(1, len(records) + 1)
```
