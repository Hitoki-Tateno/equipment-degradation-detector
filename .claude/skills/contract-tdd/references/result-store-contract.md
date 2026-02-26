# ResultStoreInterface 契約仕様

## ドメインモデル

```python
@dataclass(frozen=True)
class TrendResult:
    category_id: int
    slope: float           # 回帰直線の傾き
    intercept: float       # 切片
    # is_warning は廃止済み（ADR: analysis_ui_redesign.md 決定1）

@dataclass(frozen=True)
class AnomalyResult:
    category_id: int
    recorded_at: datetime
    anomaly_score: float   # 原論文準拠の正規化スコア 0〜1（1=異常, boolean不可）

@dataclass
class ModelDefinition:
    category_id: int
    baseline_start: datetime
    baseline_end: datetime
    sensitivity: float     # UIスライダー値（contamination相当）
    excluded_points: list[datetime]  # ベースラインから除外する点
    feature_config: FeatureConfig | None = None  # 特徴量設定（JSONで永続化）
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
- feature_configはJSON文字列としてTEXTカラムに保存（NULLable）
- 存在しないcategory_idに対してはNoneを返す

### delete_model_definition

- 指定category_idのモデル定義を削除する
- 存在しないcategory_idに対してはエラーを発生させない（冪等）
- カスケード: 呼び出し元で delete_anomaly_results も合わせて呼ぶこと

### delete_anomaly_results

- 指定category_idの全異常スコア結果を削除する
- 存在しないcategory_idに対してはエラーを発生させない（冪等）
- 削除後、get_anomaly_results は空リストを返す

## 重要: anomaly_scoreについて

scikit-learnのIsolation Forestの`-score_samples()`で算出した原論文準拠の正規化スコア（0〜1、1に近いほど異常）を保存する。このスコアはcontamination（感度）に依存しない。閾値判定はフロントエンド側で実行するため、結果ストアにはスコア値のみを保持する。
