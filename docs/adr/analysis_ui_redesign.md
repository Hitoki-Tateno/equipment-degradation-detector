# ADR: 分析・可視化・特徴量エンジニアリングの大規模再設計

- 日付: 2026-02-25
- ステータス: 承認済み
- 関連ADR: architecture_minutes.md, tech_selection_minutes.md

## 背景

Step 1（データ可視化）完了後、Step 2（モデル定義）の実装過程で以下の課題が明確になった。

### 課題1: トレンド分析の判定ロジックの冗長性
- WARNING_THRESHOLD(0.5)のハードコード判定は、異常検知（IsolationForest）と役割が重複
- ダッシュボードの「トレンド警告」列は異常検知が導入された現在、実質的に不要
- バックエンドの回帰計算・永続化・API配信の仕組み自体は、プロット描画に必要なため維持する

### 課題2: 異常値通知のUX問題
- 散布図のポイント色分け（青→赤）による通知は、数値的な重大度が伝わらない
- 感度スライダーの効果が間接的（色が変わるだけ）で、閾値の意味が視覚的に不明
- 「どの程度異常か」のスコア値をユーザーが確認できない

### 課題3: 特徴量の固定化
- RawWorkTimeFeatureBuilder（生値のみ）しか存在せず、分析精度の向上手段がない
- 時系列データに有効な特徴量（移動平均、変化率等）を試す手段がユーザーにない
- FeatureBuilder ABCは拡張可能な設計だが、活用されていない

## 決定事項

### 決定1: トレンド分析の簡素化（判定ロジック廃止、描画特化）

**方針**: バックエンドの回帰計算・永続化・APIは維持する。WARNING_THRESHOLD/is_warning判定ロジックを廃止し、slope/interceptをAPIで返してフロントエンドで描画するだけのシンプルな構成にする。ダッシュボードへのトレンド表示は不要。

**理由**:
- 回帰計算はバックエンドの責務として維持（フロントエンドに計算ロジックを持たせない）
- WARNING_THRESHOLDの判定は異常検知に統合することで役割の重複を解消
- ダッシュボードからトレンド列を削除し、異常検出数で代替

**変更対象**:
- `TrendResult` dataclass: `is_warning` フィールドを削除（slope/interceptは維持）
- `compute_trend()`: `WARNING_THRESHOLD` 定数を削除、戻り値から `is_warning` を除去
- `trend_results` テーブル: `is_warning` 列を削除
- API: `TrendResultResponse` から `is_warning` を削除
- Dashboard: トレンド警告・傾き列を削除、「異常検出数」列を追加

### 決定2: 異常スコアサブチャートによる数値通知

**方針**: メイン散布図のポイント色分けを廃止し、異常スコアを独立したサブチャートで数値表示する。感度スライダーに連動する動的閾値ラインで判定基準を視覚化する。

**UIデザイン**:
```
┌──────────────────────────────────────────┐
│  作業時間 散布図 + トレンド直線           │  ← メイン（全ポイント同色）
│  yaxis domain: [0.33, 1.0]              │
├──────────────────────────────────────────┤
│  異常スコア (0-1) + 閾値ライン           │  ← サブチャート
│  yaxis2 domain: [0.0, 0.23]            │
│  ─ ─ ─ ─ 閾値 ─ ─ ─ ─ (感度連動)       │
└──────────────────────────────────────────┘
         共有X軸（ズーム/パン同期）
```

**技術選択**:
- サブチャートのトレースタイプ: `scattergl`（`plotly.js-gl2d-dist`にbar未含有のため）
- 閾値ライン: `layout.shapes`（`xref: 'paper'`で全幅、ズーム追従）
- X軸共有: `yaxis2.anchor: 'x'` でPlotlyネイティブの同期
- 閾値計算式: 決定5 で絶対値に変更

**理由**:
- 異常スコアの数値が直接可視化され、相対的な重大度が明確
- 閾値ラインが動的に動くことで、感度調整の効果が直感的に理解可能
- メイン散布図がシンプルになり、データの全体傾向に集中できる

### 決定3: 特徴量アセットシステム

**方針**: 複数の特徴量ビルダーを提供し、ユーザーがチェックボックスで自由に組み合わせ可能にする。選択された特徴量はModelDefinitionの一部として永続化し、分析実行時に動的にCompositeFeatureBuilderを構成する。具体的な特徴量の種類・数は今後選定する。

**特徴量の候補例**（確定ではない、今後の選定で決定）:
- 時系列統計量系: 移動平均、移動標準偏差、変化率、差分、ラグ特徴量 等
- 時間情報系: 曜日エンコーディング、時刻エンコーディング 等
- その他、ドメイン知識に基づく特徴量

**アーキテクチャ**:
- `FeatureBuilder.build()` に `timestamps` 引数を追加（後方互換: デフォルトNone）
- `FeatureConfig` / `FeatureSpec` dataclassでユーザー設定を型安全に表現
- `FEATURE_REGISTRY` dictと `create_feature_builder()` ファクトリで動的構築
- `CompositeFeatureBuilder` で複数特徴量を `np.hstack` で結合
- `ModelDefinition.feature_config` に永続化（SQLiteのJSON列）
- AnalysisEngineが `model_def.feature_config` を参照して特徴量ビルダーを動的生成

**ユーザージャーニー**:
```
[1. チュートリアルで学ぶ]
   チュートリアルページ → 各特徴量の説明・サンプルデータで効果を確認
                          → 「この特徴量はこういう場面で有効」を理解
                                    ↓
[2. プロットで適用]
   プロットページ → カテゴリ選択 → ベースライン範囲をドラッグ選択
                  → BaselineControlsパネル内で:
                      ・感度スライダー（既存）
                      ・特徴量チェックボックス（新規）
                      ・パラメータ入力（該当する特徴量のみ展開）
                  → 「設定を保存」ボタンで一括保存
                                    ↓
[3. 結果を確認]
   バックエンド再分析 → 異常スコアサブチャートが更新
                      → 特徴量の効果を異常スコアの変化で判断
                      → 必要に応じて特徴量を変更して再保存
```

**チュートリアルページ**:
- フロントエンドに「チュートリアル」ビューを新設
- 各特徴量の説明 + プリコンピュートしたサンプルデータでの変換前後をPlotlyミニチャートで可視化
- 「いつ使うか」「どういうデータに有効か」のガイダンステキスト付き
- プレビューAPIは不要（チュートリアルは学習用、プロットは実践用）

**理由**:
- FeatureBuilder ABCの設計意図（拡張可能な特徴量エンジニアリング）を実現
- Composite Patternによる自由な組み合わせで、ユーザーが分析精度を自己最適化可能
- チュートリアルページにより、ML知識が限定的なユーザーでも特徴量を理解して選択可能
- ベースライン設定と特徴量選択を同じパネル・同じ保存アクションで行うことで操作の一貫性を確保

### 決定4: Isolation Forest ハイパーパラメータの抽象化

**方針**: `anomaly.py` にハードコードされていた IsolationForest のハイパーパラメータ（`n_estimators`, `contamination`, `max_samples`）を `ModelDefinition` に `anomaly_params` フィールドとして持たせ、内部的に設定可能にする。UIへの露出は本決定のスコープ外。

**対象パラメータ**:

| パラメータ | デフォルト値 | 説明 |
|-----------|-------------|------|
| `n_estimators` | 100 | 決定木の数 |
| `contamination` | 0.01 | 想定される異常割合 |
| `max_samples` | "auto" | 各木に使うサンプル数 |

`random_state=42` は再現性のため常に固定し、ユーザー設定不可。

**データフロー**:
```
ModelDefinition.anomaly_params (dict|None)
  → AnalysisEngine.run()
    → train_and_score(baseline_feat, all_feat, anomaly_params=model_def.anomaly_params)
      → _DEFAULTS とマージ: {**_DEFAULTS, **(anomaly_params or {})}
        → IsolationForest(n_estimators=..., contamination=..., max_samples=..., random_state=42)
```

**実装詳細**:

1. **`backend/interfaces/result_store.py`** — `ModelDefinition` に `anomaly_params: dict | None = None` を追加。`feature_config` と同じパターン（オプショナル、Noneでデフォルト動作）。

2. **`backend/analysis/anomaly.py`** — ハードコード値を `_DEFAULTS` モジュール定数に抽出。`train_and_score()` に `anomaly_params: dict | None = None` 引数を追加。`None` の場合は `_DEFAULTS` をそのまま使用し、指定された場合は部分上書きマージ（`{**_DEFAULTS, **(anomaly_params or {})}`）。

3. **`backend/analysis/engine.py`** — `train_and_score()` 呼び出しに `anomaly_params=model_def.anomaly_params` を追加。

4. **`backend/result_store/sqlite.py`** — `model_definitions` テーブルに `anomaly_params TEXT DEFAULT NULL` 列を追加。v3→v4 マイグレーション（`ALTER TABLE ADD COLUMN`）。JSON でシリアライズ/デシリアライズ（`feature_config` と同一パターン）。

5. **API層は変更なし** — `PUT /api/models/{category_id}` のリクエスト/レスポンスモデルは変更せず、バックエンド内部の抽象化に留める。将来的にUIからの設定が必要になった時点でAPI層を拡張する。

**後方互換性**:
- `anomaly_params=None` → 既存デフォルト値がそのまま適用（動作変更なし）
- 既存DBレコードは `anomaly_params=NULL` のままで正常動作
- 部分指定（例: `{"n_estimators": 50}` のみ）→ 未指定パラメータはデフォルト値で補完

**理由**:
- `feature_config` の実装パターンに合わせることで一貫性を維持
- ハードコード値をモジュール定数に抽出し、デフォルト値を明示的に管理
- API層を変更しないことで、フロントエンドへの影響ゼロで内部拡張性を確保

### 決定5: 異常スコア閾値の絶対値化

**方針**: フロントエンドの閾値計算を相対値（min/maxベース）から絶対値（`threshold = 1.0 - sensitivity`）に変更する。

**背景**:
- `computeThreshold()` が `max - sensitivity * (max - min)` で閾値を算出しており、スコアの min/max に対する相対値になっている
- 全データが正常（スコア ≈ 0.4-0.5）でも min/max の差分に基づいて必ず一部が閾値を超え、誤検知が発生する
- 異常スコアは `-score_samples()` により原論文準拠の 0-1 スケールで保存済み（`sw_architecture_minutes.md` L211-218）
- 正規化済みのスコアを絶対値として直接判定すべき

**閾値の計算式変更**:

| | 旧（相対値） | 新（絶対値） |
|---|---|---|
| 計算式 | `max - sensitivity * (max - min)` | `1.0 - sensitivity` |
| 入力 | スコアの min/max に依存 | sensitivity のみ |
| sensitivity=0.25 (低) | データ依存 | threshold = 0.75（スコア > 0.75 のみ異常） |
| sensitivity=0.50 (中) | データ依存 | threshold = 0.50（原論文の正常/異常境界） |
| sensitivity=0.75 (高) | データ依存 | threshold = 0.25（広く異常を検出） |

**UXへの影響**:
- 感度スライダーのラベル・範囲・方向は変更なし（「低/中/高」、0.25-0.75）
- 「高い感度 = より多くの異常を検出」のUX方向を維持
- 全データが正常な場合、閾値ラインがスコア群の上方に位置し、誤検知が発生しない

**変更対象**:
- `frontend/src/components/WorkTimePlot.jsx`: `computeThreshold()` を `return 1.0 - sensitivity;` に簡素化

**理由**:
- 原論文準拠の 0-1 スケールを既に採用しているため、絶対閾値が最も直接的かつ解釈可能
- 相対閾値は全データ正常時にも誤検知を生むため、異常検知システムとして不適切

## 影響範囲

### 破壊的変更
- `TrendResult`: `is_warning` フィールド削除
- `FeatureBuilder`: build()シグネチャ変更（後方互換あり）
- API: `GET /api/dashboard/summary` のレスポンスから `trend` 削除
- DB: `trend_results` の `is_warning` 列削除、`model_definitions` に `feature_config` 列追加

### 非破壊的変更（決定4）
- `ModelDefinition`: `anomaly_params` フィールド追加（デフォルトNone、既存動作に影響なし）
- `train_and_score()`: `anomaly_params` 引数追加（デフォルトNone、後方互換）
- DB: `model_definitions` に `anomaly_params` 列追加（`ALTER TABLE ADD COLUMN`、NULL許容）

### 依存ルール
変更後も以下を維持する（`test_dependency_rules.py` で強制）:
- analysis/ → interfaces/ のみ依存
- ingestion/ → interfaces/ のみ依存（具象はdependencies.py経由）

## リスク

| リスク | 影響度 | 緩和策 |
|--------|--------|--------|
| Plotly.js gl2d-distでサブプロットが正常動作しない可能性 | 中 | 事前にPoC実施。yaxis2はlayoutレベル機能のためtrace typeに依存しない |
| 特徴量組み合わせで次元爆発 | 低 | UI側でパラメータ上限を設定 |
| DB migration（既存データ） | 低 | ALTER TABLE ADD COLUMNで対応。SQLiteの制約内 |
| anomaly_params に不正な値が渡される可能性 | 低 | scikit-learnがバリデーションしてエラーを返す。API層拡張時にPydanticバリデーション追加 |
