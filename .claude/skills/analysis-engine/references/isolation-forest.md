# Isolation Forest 実装仕様

## scikit-learnのメソッドとcontamination依存性

| メソッド | contamination依存 |
|---|---|
| fit() | しない（木の構築） |
| score_samples() | しない（生スコア） |
| offset_ | する（閾値） |
| decision_function() | する（score_samples - offset_） |
| predict() | する（decision_functionの符号） |

## 設計上の帰結

1. **-score_samples()で原論文準拠の正規化スコア(0〜1)に変換して結果ストアに保存する**（anomaly_score: REAL、1に近いほど異常）
2. **感度スライダーはフロントエンドで閾値を適用するだけ** → API不要、再学習不要
3. **再学習が必要なのはベースライン期間または除外点が変更されたときのみ**

## 実装パターン

```python
from sklearn.ensemble import IsolationForest
import numpy as np

def train_and_score(
    baseline_data: np.ndarray,
    all_data: np.ndarray,
    n_estimators: int = 100,
    random_state: int = 42,
) -> np.ndarray:
    """ベースラインで学習し、全データのスコアを算出する。

    Returns:
        anomaly_scores: 原論文準拠の異常スコア (0〜1, 1に近いほど異常)
    """
    model = IsolationForest(
        n_estimators=n_estimators,
        random_state=random_state,
        contamination="auto",  # offset計算のみ。スコア自体には影響しない
    )
    model.fit(baseline_data)
    return -model.score_samples(all_data)
```

## 固定パラメータ（ユーザー非公開）

| パラメータ | 値 | 理由 |
|---|---|---|
| n_estimators | 100 | デフォルトで実用十分 |
| max_samples | "auto" | アルゴリズム内部調整 |
| max_features | 1.0 | 全特徴量使用 |
| random_state | 42 | 再現性確保 |
| contamination | "auto" | スコア算出には影響しない |

## ベースラインデータの構築

1. モデル定義からbaseline_start, baseline_endを取得
2. Store層から該当期間のwork_recordsを取得
3. excluded_pointsに含まれるrecorded_atのレコードを除外
4. FeatureBuilderで特徴量行列に変換
5. 上記をbaseline_dataとしてfit()に渡す
