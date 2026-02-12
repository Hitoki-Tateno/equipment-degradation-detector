# ResultStoreInterface 契約仕様

## ドメインモデル

```python
@dataclass(frozen=True)
class TrendResult:
    category_id: int
    slope: float           # 回帰直線の傾き
    intercept: float       # 切片
    is_warning: bool       # 警告フラグ

@dataclass(frozen=True)
class AnomalyResult:
    category_id: int
    recorded_at: datetime
    anomaly_score: float   # score_samples()の生スコア（boolean不可）

@dataclass
class ModelDefinition:
    category_id: int
    baseline_start: datetime
    baseline_end: datetime
    sensitivity: float     # UIスライダー値（contamination相当）
    excluded_points: list[datetime]  # ベースラインから除外する点
```

## メソッド契約

### save_trend_result / get_trend_result

- category_idで一意。保存は上書き
- 存在しないcategory_idに対してはNoneを返す

### save_anomaly_results / get_anomaly_results

- category_id × recorded_atで一意。バッチ保存は上書き
- anomaly_scoreはREAL値（booleanではない）
- 存在しないcategory_idに対しては空リスト

### save_model_definition / get_model_definition

- category_idで一意。保存は上書き
- excluded_pointsはJSON配列としてTEXTカラムに保存
- 存在しないcategory_idに対してはNoneを返す

## 重要: anomaly_scoreについて

scikit-learnのIsolation Forestの`score_samples()`が返す生スコアを保存する。このスコアはcontamination（感度）に依存しない。閾値判定はフロントエンド側で実行するため、結果ストアにはスコア値のみを保持する。
