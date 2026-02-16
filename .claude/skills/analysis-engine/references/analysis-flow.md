# 分析実行フロー

## 取り込み時同期分析

データ取り込みエンドポイント（POST /api/records, POST /api/records/csv）の処理末尾で、対象カテゴリの分析を**同期的に**実行する。スケジューラーや定期実行は使用しない。

```
取り込みリクエスト受信
  ├── レコード保存
  ├── トレンド分析（常時実行）
  └── 異常検知
        ├── モデル定義済み → IsolationForest実行
        └── モデル未定義 → スキップ
```

### 実行トリガー

| トリガー | 対象 | 用途 |
|---------|------|------|
| POST /api/records | 取り込まれたカテゴリ | リアルタイム取り込み時 |
| POST /api/records/csv | 影響を受ける全カテゴリ | CSVバッチ取り込み時 |
| POST /api/analysis/run | 全末端カテゴリ | ダッシュボードの手動トリガーボタン |

### 各カテゴリに対する処理

1. Store層から全期間データを取得
2. **トレンド分析**: 線形回帰を全期間で実行。傾き・切片・警告有無を算出し結果ストアに保存
3. モデル定義が存在する場合:
   - Store層からベースライン期間データを取得
   - 除外点を除去
   - Isolation Forestで学習
   - 全期間データに対してscore_samples()を実行
   - anomaly_scoresを結果ストアに保存

## モデルのライフサイクル

```
未定義 ──(ユーザーがベースライン選択+保存)──→ 定義済み ──(ユーザーが削除)──→ 未定義
```

- **作成（PUT /api/models）**: ユーザーがGUI上でベースライン範囲・感度を指定して保存。IsolationForestの学習もこのタイミングで実行
- **削除（DELETE /api/models）**: モデルを削除し未定義状態に戻す。異常検知結果もカスケード削除
- **「更新」は存在しない**: 設備状況変化時はモデル削除→再作成。部分更新を排除し運用上の安全性を確保

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
