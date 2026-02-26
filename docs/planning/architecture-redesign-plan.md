# 大規模アーキテクチャ変更 実装プラン

- 日付: 2026-02-25
- 関連ADR: [analysis_ui_redesign.md](../adr/analysis_ui_redesign.md)

## 変更概要

| # | 変更 | 方針 |
|---|------|------|
| 1 | トレンド分析の簡素化 | バックエンド計算は維持、WARNING_THRESHOLD/is_warning廃止、ダッシュボード表示削除 |
| 2 | 異常値通知の刷新 | ポイント色分け廃止 → 異常スコアサブチャート + 動的閾値ライン |
| 3 | 特徴量アセットシステム | 複数特徴量を組み合わせ可能なアーキテクチャ + ユーザー選択UI + チュートリアルページ（具体的な特徴量は今後選定） |

---

## Step 1: トレンド分析の簡素化（判定ロジック廃止、描画特化）

**方針**: バックエンドの回帰計算・永続化・APIは維持する。WARNING_THRESHOLD/is_warning判定ロジックを廃止し、slope/interceptをAPIで返してフロントエンドで描画するだけのシンプルな構成にする。ダッシュボードへのトレンド表示は不要。

### 1-1. バックエンド: 判定ロジック削除

| ファイル | 変更内容 |
|----------|----------|
| `backend/analysis/trend.py` | `WARNING_THRESHOLD` 定数を削除、`compute_trend()` の戻り値から `is_warning` を除去し `(slope, intercept)` のみ返す |
| `backend/interfaces/result_store.py` | `TrendResult` dataclassから `is_warning` フィールドを削除 |
| `backend/result_store/sqlite.py` | `trend_results` テーブルの `is_warning` 列を削除 |
| `backend/analysis/engine.py` | `TrendResult` 構築時の `is_warning` 引数を削除 |

### 1-2. API: ダッシュボードからトレンド除去

| ファイル | 変更内容 |
|----------|----------|
| `backend/ingestion/main.py` | `TrendResultResponse` から `is_warning` フィールドを削除（slope/interceptは維持） |
| 同上 | `GET /api/results/{category_id}`: `trend` フィールドは維持（slope/interceptのみ） |
| 同上 | `GET /api/dashboard/summary`: `DashboardCategorySummary` から `trend` フィールドを削除 |

### 1-3. フロントエンド: ダッシュボード列削除、プロット描画は維持

| ファイル | 変更内容 |
|----------|----------|
| `frontend/src/components/Dashboard.jsx` | 「トレンド警告」「傾き(slope)」列を削除、「異常検出数」列を追加 |
| `frontend/src/components/WorkTimePlot.jsx` | 変更なし（APIからslope/interceptを受けて赤い点線を描画する現行の仕組みを維持） |
| `frontend/src/hooks/useBaselineManager.js` | trend stateは維持（APIレスポンスを受け渡すのみ） |
| `frontend/src/services/api.js` | TrendResult typedefから `is_warning` を削除 |

### 1-4. テスト修正

| ファイル | 変更内容 |
|----------|----------|
| `tests/unit/test_analysis_engine.py` | `TestComputeTrend` の `is_warning` 関連テストを削除・修正 |
| `tests/unit/test_result_store_contract.py` | `TestTrendResults` から `is_warning` assertionを削除 |
| `tests/integration/test_analysis_flow.py` | `is_warning` 関連assertionを削除 |

### 1-5. スキルドキュメント更新

- `.claude/skills/analysis-engine/references/analysis-flow.md`
- `.claude/skills/sqlite-store/references/schema.md`
- `.claude/skills/fastapi-api/references/endpoints.md`
- `.claude/skills/contract-tdd/references/result-store-contract.md`

---

## Step 2: 異常値通知の刷新

**制約**: `plotly.js-gl2d-dist` v3.3.1は `bar` トレースを含まない → `scattergl` markerで代替。

### 2-1. WorkTimePlot.jsx の大幅改修

**メイン散布図**:
- 全ポイントを同一色（青 #1890ff）に統一
- 除外点のみグレー (#bfbfbf)
- anomalyによる色分けを廃止

**異常スコアサブチャート**:
- Plotlyサブプロットとして下部に配置
- 共有X軸（`yaxis2.anchor: 'x'`）でズーム/パン同期
- `scattergl` + `mode: 'markers'` でスコアをプロット
- 閾値超過ポイント: 赤 (#ff4d4f)、以下: 青 (#1890ff)

**動的閾値ライン**:
- `layout.shapes` で水平線描画（`xref: 'paper'`, `yref: 'y2'`）
- 感度スライダー変更時にリアルタイムで移動

**レイアウト**:
```javascript
yaxis:  { domain: [0.33, 1.0] }   // メインチャート（上部67%）
yaxis2: { domain: [0.0, 0.23], range: [0, 1.05], anchor: 'x' } // サブチャート（下部23%）
```

**その他**:
- プロット高さ: サブチャート表示時 560px、非表示時 400px
- クリックガード: `handleClick` で `curveNumber === 0`（メインtrace）のみ除外操作を許可
- `computeThreshold` 関数の計算式 `max - sensitivity * (max - min)` は維持

### 2-2. 変更不要なファイル

- `BaselineControls.jsx`: 感度スライダーはそのまま
- `PlotView.jsx`: prop interfaceに変更なし
- `useBaselineManager.js`: state構造に変更なし
- バックエンド全般: スコアは既に0-1で返却済み

---

## Step 3: 特徴量アセットシステム

**注意**: 具体的な特徴量の選定は今後行う。ここではアーキテクチャ（仕組み）の方向性のみ定める。

### ユーザージャーニー

```
[1. チュートリアルで学ぶ]
   チュートリアルページ → 各特徴量の説明・サンプルデータで効果を確認
                          → 「この特徴量はこういう場面で有効」を理解
                                    ↓
[2. プロットで適用]
   プロットページ → カテゴリ選択 → ベースライン範囲をドラッグ選択
                  → BaselineControlsパネル内で:
                      ・感度スライダー（既存）
                      ・特徴量チェックボックス（新規）← ベースライン設定と同じパネル
                      ・パラメータ入力（該当する特徴量のみ展開）
                  → 「設定を保存」ボタンで一括保存
                                    ↓
[3. 結果を確認]
   バックエンド再分析 → 異常スコアサブチャートが更新
                      → 特徴量の効果を異常スコアの変化で判断
                      → 必要に応じて特徴量を変更して再保存
```

**ポイント**:
- 特徴量のプレビューAPIは不要（チュートリアルはサンプルデータ、プロットは保存後の結果で確認）
- ベースライン設定と特徴量選択は同じ「保存」アクションで一括送信
- チュートリアルは学習用、プロットは実践用という明確な役割分担

### 3-1. バックエンドインターフェース拡張

| ファイル | 変更内容 |
|----------|----------|
| `backend/interfaces/feature.py` | `build()`/`_build_impl()` に `timestamps: Sequence[datetime] \| None = None` 追加 |
| 同上 | `FeatureSpec(feature_type: str, params: dict)` dataclass追加 |
| 同上 | `FeatureConfig(features: list[FeatureSpec])` dataclass追加 |

### 3-2. 特徴量ビルダーの追加

`backend/analysis/feature.py` に追加:
- 個別の特徴量ビルダークラス（具体的な種類・数は今後選定）
- `CompositeFeatureBuilder`: 複数ビルダーを `np.hstack` で結合し、ユーザーが自由に組み合わせ可能にする
- `FEATURE_REGISTRY` dict + `create_feature_builder(config)` ファクトリ関数

**特徴量の候補例**（確定ではない、今後の選定で決定）:
- 時系列統計量系: 移動平均、移動標準偏差、変化率、差分、ラグ特徴量 等
- 時間情報系: 曜日エンコーディング、時刻エンコーディング 等
- その他、ドメイン知識に基づく特徴量

### 3-3. ModelDefinition拡張

| ファイル | 変更内容 |
|----------|----------|
| `backend/interfaces/result_store.py` | `ModelDefinition` に `feature_config: FeatureConfig \| None = None` 追加 |
| `backend/result_store/sqlite.py` | `model_definitions` に `feature_config TEXT DEFAULT NULL` 列追加（JSON） |

### 3-4. AnalysisEngine統合

| ファイル | 変更内容 |
|----------|----------|
| `backend/analysis/engine.py` | `model_def.feature_config` で動的ビルダー生成、timestampsもビルダーに渡す |

### 3-5. API変更

| エンドポイント | 変更内容 |
|----------------|----------|
| `PUT /api/models/{category_id}` | リクエストに `feature_config` フィールド追加（ベースライン設定と一括送信） |
| `GET /api/models/{category_id}` | レスポンスに `feature_config` フィールド追加 |
| **新規** `GET /api/features/registry` | 利用可能な特徴量一覧（型、ラベル、パラメータスキーマ、説明） |

### 3-6. フロントエンド: 特徴量選択UI（BaselineControlsに統合）

| ファイル | 変更内容 |
|----------|----------|
| **新規** `frontend/src/components/FeatureSelector.jsx` | Checkbox.Group で特徴量チェックボックス選択 + パラメータ入力 |
| `frontend/src/components/BaselineControls.jsx` | 既存の感度スライダーの下に `FeatureSelector` を配置 |
| `frontend/src/hooks/useBaselineManager.js` | `featureConfig` state追加、save時に既存のベースライン設定と一緒にAPIへ送信 |
| `frontend/src/services/api.js` | `fetchFeatureRegistry()` 追加 |

### 3-7. フロントエンド: チュートリアルページ（学習専用）

| ファイル | 変更内容 |
|----------|----------|
| **新規** `frontend/src/components/TutorialPage.jsx` | 各特徴量のカード表示 + Plotlyミニチャートで変換前後を可視化 |
| **新規** `frontend/src/utils/featureTransforms.js` | JS版特徴量変換（チュートリアル表示専用） |
| `frontend/src/App.js` | メニューに「チュートリアル」ビュー追加 |

### 3-8. テスト

| ファイル | 変更内容 |
|----------|----------|
| **新規** `tests/unit/test_feature_builders.py` | 各ビルダーの入出力、CompositeBuilder、ファクトリ |
| `tests/unit/test_result_store_contract.py` | feature_config付きModelDefinitionの保存・読込テスト |
| `tests/unit/test_analysis_engine.py` | feature_config利用時のengine.run()テスト |
| `tests/integration/test_analysis_flow.py` | registryエンドポイント、feature_config付きモデル保存のテスト |

---

## ファイル影響一覧

### 新規作成
| ファイル | 内容 |
|----------|------|
| `docs/adr/analysis_ui_redesign.md` | 本変更のADR |
| `frontend/src/components/FeatureSelector.jsx` | 特徴量チェックボックスUI |
| `frontend/src/components/TutorialPage.jsx` | チュートリアルページ |
| `frontend/src/utils/featureTransforms.js` | JS版特徴量変換（チュートリアル用） |
| `tests/unit/test_feature_builders.py` | 特徴量ビルダーユニットテスト |

### 主要変更
| ファイル | 変更内容 |
|----------|----------|
| `backend/analysis/trend.py` | WARNING_THRESHOLD削除、compute_trend()からis_warning除去 |
| `backend/interfaces/result_store.py` | TrendResultからis_warning削除、ModelDefinitionにfeature_config追加 |
| `backend/interfaces/feature.py` | timestamps引数追加、FeatureSpec/FeatureConfig追加 |
| `backend/analysis/feature.py` | 特徴量ビルダー群 + Composite + Registry + Factory追加 |
| `backend/analysis/engine.py` | is_warning除去、feature_config対応 |
| `backend/result_store/sqlite.py` | trend_resultsからis_warning列削除、feature_config列追加 |
| `backend/ingestion/main.py` | TrendResultResponseからis_warning削除、ダッシュボードからtrend除去、feature系API追加 |
| `frontend/src/components/WorkTimePlot.jsx` | 色分け廃止、サブチャート追加（トレンド描画は維持） |
| `frontend/src/components/Dashboard.jsx` | trend列削除→異常検出数列追加 |
| `frontend/src/components/BaselineControls.jsx` | FeatureSelector統合 |
| `frontend/src/hooks/useBaselineManager.js` | featureConfig追加 |
| `frontend/src/services/api.js` | TrendResultからis_warning削除、fetchFeatureRegistry()追加 |
| `frontend/src/App.js` | チュートリアルビュー追加 |

---

## 検証方法

### バックエンドテスト
```bash
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run ruff check backend/
uv run ruff format --check backend/
```

### 依存ルール検証
```bash
uv run pytest tests/unit/test_dependency_rules.py -v
```

### フロントエンドテスト
```bash
cd frontend && npm run build
```

### E2E動作確認
1. API起動: `uv run uvicorn backend.ingestion.main:app --reload`
2. フロントエンド起動: `cd frontend && npm start`
3. CSVデータをアップロード
4. ダッシュボード: 「異常検出数」列が表示されること
5. プロット: トレンド直線（赤点線）が表示されること（バックエンドAPIからslope/interceptを取得して描画）
6. ベースライン設定後: サブチャートに異常スコアが表示されること
7. 感度スライダー操作: 閾値ラインがリアルタイムで移動すること
8. 特徴量選択: チェックボックスで特徴量を変更→保存→再分析されること
9. チュートリアルページ: 各特徴量の説明とサンプルグラフが表示されること
