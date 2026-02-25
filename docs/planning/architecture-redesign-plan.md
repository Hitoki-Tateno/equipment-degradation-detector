# 大規模アーキテクチャ変更 実装プラン

- 日付: 2026-02-25
- 関連ADR: [analysis_ui_redesign.md](../adr/analysis_ui_redesign.md)

## 変更概要

| # | 変更 | 方針 |
|---|------|------|
| 1 | トレンド分析の簡素化 | バックエンド計算を廃止 → Plotly.jsフロントエンドOLSに移行 |
| 2 | 異常値通知の刷新 | ポイント色分け廃止 → 異常スコアサブチャート + 動的閾値ライン |
| 3 | 特徴量アセットシステム | 8種の特徴量ビルダー + ユーザー選択UI + チュートリアルページ |

---

## Step 1: トレンド分析の簡素化

Plotly.jsにはPython版のような `trendline='ols'` オプションがないため、フロントエンドでOLS計算を行いtraceとして追加する。

### 1-1. バックエンド: インターフェースからTrend削除

| ファイル | 変更内容 |
|----------|----------|
| `backend/interfaces/result_store.py` | `TrendResult` dataclass、`save_trend_result()`、`get_trend_result()` を削除 |
| `backend/result_store/sqlite.py` | `trend_results`テーブル・関連メソッド削除、`DROP TABLE IF EXISTS trend_results` マイグレーション追加 |
| `backend/analysis/trend.py` | **ファイル丸ごと削除** |
| `backend/analysis/engine.py` | `run()` からトレンド計算部分を削除 |

### 1-2. API: Trend関連レスポンス削除

| ファイル | 変更内容 |
|----------|----------|
| `backend/ingestion/main.py` | `TrendResultResponse` モデル削除 |
| 同上 | `GET /api/results/{category_id}` レスポンスから`trend`フィールド削除 |
| 同上 | `GET /api/dashboard/summary` の `DashboardCategorySummary` から`trend`フィールド削除 |

### 1-3. フロントエンド: OLS計算をWorkTimePlotに移動

| ファイル | 変更内容 |
|----------|----------|
| `frontend/src/components/WorkTimePlot.jsx` | `trend` prop削除、`useMemo`でOLS回帰をJS内で計算、トレンドtrace描画は維持（赤い点線） |
| `frontend/src/hooks/useBaselineManager.js` | state・dispatchからtrend関連を全削除 |
| `frontend/src/components/PlotView.jsx` | trend propの受け渡し削除 |
| `frontend/src/components/Dashboard.jsx` | 「トレンド警告」「傾き(slope)」列を削除、「異常検出数」列を追加 |
| `frontend/src/services/api.js` | TrendResult typedef削除 |

**OLS計算（JavaScript）**:
```javascript
// xValues=[1,2,...,n], yValues=work_times
const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
const intercept = (sumY - slope * sumX) / n;
```

### 1-4. テスト修正

| ファイル | 変更内容 |
|----------|----------|
| `tests/unit/test_analysis_engine.py` | `TestComputeTrend` クラス削除、エンジンテストからtrend assertion削除 |
| `tests/unit/test_result_store_contract.py` | `TestTrendResults` クラス削除 |
| `tests/integration/test_analysis_flow.py` | trend関連assertion更新 |

### 1-5. スキルドキュメント更新

- `.claude/skills/analysis-engine/references/analysis-flow.md`
- `.claude/skills/sqlite-store/references/schema.md`
- `.claude/skills/fastapi-api/references/endpoints.md`
- `.claude/skills/react-plotly/references/interactive-plots.md`
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

### 3-1. バックエンドインターフェース拡張

| ファイル | 変更内容 |
|----------|----------|
| `backend/interfaces/feature.py` | `build()`/`_build_impl()` に `timestamps: Sequence[datetime] \| None = None` 追加 |
| 同上 | `FeatureSpec(feature_type: str, params: dict)` dataclass追加 |
| 同上 | `FeatureConfig(features: list[FeatureSpec])` dataclass追加 |

### 3-2. 8種の特徴量ビルダー実装

`backend/analysis/feature.py` に追加:

| ビルダー | 出力次元 | パラメータ | timestamps必要 |
|----------|---------|-----------|---------------|
| `RawWorkTimeFeatureBuilder`（既存） | (n, 1) | なし | No |
| `MovingAverageFeatureBuilder` | (n, 1) | window: int | No |
| `MovingStdFeatureBuilder` | (n, 1) | window: int | No |
| `RateOfChangeFeatureBuilder` | (n, 1) | なし | No |
| `LagFeatureBuilder` | (n, len(lags)) | lags: list[int] | No |
| `DifferenceFeatureBuilder` | (n, 1) | なし | No |
| `DayOfWeekFeatureBuilder` | (n, 2) | なし | Yes |
| `HourOfDayFeatureBuilder` | (n, 2) | なし | Yes |

追加クラス:
- `CompositeFeatureBuilder`: 複数ビルダーを `np.hstack` で結合
- `FEATURE_REGISTRY` dict + `create_feature_builder(config)` ファクトリ関数

### 3-3. ModelDefinition拡張

| ファイル | 変更内容 |
|----------|----------|
| `backend/interfaces/result_store.py` | `ModelDefinition` に `feature_config: FeatureConfig \| None = None` 追加 |
| `backend/result_store/sqlite.py` | `model_definitions` に `feature_config TEXT DEFAULT NULL` 列追加（JSON） |

### 3-4. AnalysisEngine統合

| ファイル | 変更内容 |
|----------|----------|
| `backend/analysis/engine.py` | `model_def.feature_config` で動的ビルダー生成、timestampsもビルダーに渡す |

### 3-5. API追加・変更

| エンドポイント | 変更内容 |
|----------------|----------|
| `PUT /api/models/{category_id}` | リクエストに `feature_config` フィールド追加 |
| `GET /api/models/{category_id}` | レスポンスに `feature_config` フィールド追加 |
| **新規** `GET /api/features/registry` | 利用可能な特徴量一覧（型、ラベル、パラメータスキーマ、説明） |
| **新規** `GET /api/features/preview` | 指定特徴量でカテゴリデータを変換してプレビュー返却 |

### 3-6. フロントエンド: 特徴量選択UI

| ファイル | 変更内容 |
|----------|----------|
| **新規** `frontend/src/components/FeatureSelector.jsx` | Checkbox.Group で特徴量チェックボックス選択 + パラメータ入力 |
| `frontend/src/components/BaselineControls.jsx` | `FeatureSelector` をCollapse内に配置 |
| `frontend/src/hooks/useBaselineManager.js` | `featureConfig` state追加、save時にAPIへ送信 |
| `frontend/src/services/api.js` | `fetchFeatureRegistry()`, `fetchFeaturePreview()` 追加 |

### 3-7. フロントエンド: チュートリアルページ

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
| `tests/integration/test_analysis_flow.py` | registry/previewエンドポイントテスト |

---

## ファイル影響一覧

### 削除
| ファイル | 理由 |
|----------|------|
| `backend/analysis/trend.py` | トレンド計算をフロントエンドへ移行 |

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
| `backend/interfaces/result_store.py` | TrendResult削除、ModelDefinitionにfeature_config追加 |
| `backend/interfaces/feature.py` | timestamps引数追加、FeatureSpec/FeatureConfig追加 |
| `backend/analysis/feature.py` | 7種ビルダー + Composite + Registry + Factory追加 |
| `backend/analysis/engine.py` | trend計算削除、feature_config対応 |
| `backend/result_store/sqlite.py` | trend_results削除、feature_config列追加 |
| `backend/ingestion/main.py` | trend API削除、feature系API追加 |
| `frontend/src/components/WorkTimePlot.jsx` | OLS計算追加、色分け廃止、サブチャート追加 |
| `frontend/src/components/Dashboard.jsx` | trend列→異常検出数列 |
| `frontend/src/components/BaselineControls.jsx` | FeatureSelector統合 |
| `frontend/src/hooks/useBaselineManager.js` | trend削除、featureConfig追加 |
| `frontend/src/services/api.js` | trend型削除、feature系API追加 |
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
5. プロット: トレンド直線（赤点線）が表示されること（フロントエンドOLS）
6. ベースライン設定後: サブチャートに異常スコアが表示されること
7. 感度スライダー操作: 閾値ラインがリアルタイムで移動すること
8. 特徴量選択: チェックボックスで特徴量を変更→保存→再分析されること
9. チュートリアルページ: 各特徴量の説明とサンプルグラフが表示されること
