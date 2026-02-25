# ADR: 分析・可視化・特徴量エンジニアリングの大規模再設計

- 日付: 2026-02-25
- ステータス: 承認済み
- 関連ADR: architecture_minutes.md, tech_selection_minutes.md

## 背景

Step 1（データ可視化）完了後、Step 2（モデル定義）の実装過程で以下の課題が明確になった。

### 課題1: トレンド分析の過剰実装
- LinearRegressionをバックエンドで計算し、DB保存・API配信・フロントエンド描画するフルスタックパイプラインが存在
- 実際のユーザー価値は「プロット上の回帰直線」だけであり、バックエンドでの計算・保存は不要
- WARNING_THRESHOLD(0.5)のハードコード判定は、異常検知（IsolationForest）と役割が重複

### 課題2: 異常値通知のUX問題
- 散布図のポイント色分け（青→赤）による通知は、数値的な重大度が伝わらない
- 感度スライダーの効果が間接的（色が変わるだけ）で、閾値の意味が視覚的に不明
- 「どの程度異常か」のスコア値をユーザーが確認できない

### 課題3: 特徴量の固定化
- RawWorkTimeFeatureBuilder（生値のみ）しか存在せず、分析精度の向上手段がない
- 時系列データに有効な特徴量（移動平均、変化率等）を試す手段がユーザーにない
- FeatureBuilder ABCは拡張可能な設計だが、活用されていない

## 決定事項

### 決定1: トレンド直線のフロントエンド移行

**方針**: バックエンドのトレンド分析パイプラインを全廃し、Plotly.js上でOLS回帰をフロントエンド計算する。

**理由**:
- トレンド直線の描画はプレゼンテーション層の責務
- バックエンドの計算・保存・配信の3層が不要になり、コードベースが大幅に簡素化
- WARNING_THRESHOLDの判定は異常検知に統合することで役割の重複を解消

**削除対象**:
- `backend/analysis/trend.py`（ファイル削除）
- `TrendResult` dataclass、`save/get_trend_result()` インターフェース
- `trend_results` SQLiteテーブル
- API: `TrendResultResponse`、レスポンスの`trend`フィールド
- Dashboard: トレンド警告・傾き列

**追加対象**:
- `WorkTimePlot.jsx` 内でのJavaScript OLS計算（useMemoで最適化）
- Dashboard: 「異常検出数」列（anomalyCountのTag色分け表示）

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
- 閾値計算式: 既存の `max - sensitivity * (max - min)` を維持

**理由**:
- 異常スコアの数値が直接可視化され、相対的な重大度が明確
- 閾値ラインが動的に動くことで、感度調整の効果が直感的に理解可能
- メイン散布図がシンプルになり、データの全体傾向に集中できる

### 決定3: 特徴量アセットシステム

**方針**: 8種の特徴量ビルダーを提供し、ユーザーがチェックボックスで自由に組み合わせ可能にする。選択された特徴量はModelDefinitionの一部として永続化し、分析実行時に動的にCompositeFeatureBuilderを構成する。

**特徴量一覧**:

| 特徴量 | 説明 | パラメータ |
|--------|------|-----------|
| 生値 | 作業時間をそのまま使用 | なし |
| 移動平均 | 直近N回の平均 | window |
| 移動標準偏差 | 直近N回のばらつき | window |
| 変化率 | (今回-前回)/前回 | なし |
| ラグ特徴量 | t-1, t-2等の過去データ | lags |
| 差分 | 今回-前回（1階差分） | なし |
| 曜日エンコーディング | sin/cosによる周期表現 | なし |
| 時刻エンコーディング | sin/cosによる周期表現 | なし |

**アーキテクチャ**:
- `FeatureBuilder.build()` に `timestamps` 引数を追加（後方互換: デフォルトNone）
- `FeatureConfig` / `FeatureSpec` dataclassでユーザー設定を型安全に表現
- `FEATURE_REGISTRY` dictと `create_feature_builder()` ファクトリで動的構築
- `ModelDefinition.feature_config` に永続化（SQLiteのJSON列）
- AnalysisEngineが `model_def.feature_config` を参照して特徴量ビルダーを動的生成

**チュートリアルページ**:
- フロントエンドに「チュートリアル」ビューを新設
- 各特徴量の説明 + プリコンピュートしたサンプルデータでの変換前後をPlotlyミニチャートで可視化
- 「いつ使うか」のガイダンステキスト付き

**理由**:
- FeatureBuilder ABCの設計意図（拡張可能な特徴量エンジニアリング）を実現
- Composite Patternによる自由な組み合わせで、ユーザーが分析精度を自己最適化可能
- チュートリアルページにより、ML知識が限定的なユーザーでも特徴量を理解して選択可能

## 影響範囲

### 破壊的変更
- `ResultStoreInterface`: TrendResult関連メソッド削除
- `FeatureBuilder`: build()シグネチャ変更（後方互換あり）
- API: `GET /api/results/{id}` と `GET /api/dashboard/summary` のレスポンス形式変更
- DB: `trend_results` テーブル削除、`model_definitions` に列追加

### 依存ルール
変更後も以下を維持する（`test_dependency_rules.py` で強制）:
- analysis/ → interfaces/ のみ依存
- ingestion/ → interfaces/ のみ依存（具象はdependencies.py経由）

## リスク

| リスク | 影響度 | 緩和策 |
|--------|--------|--------|
| Plotly.js gl2d-distでサブプロットが正常動作しない可能性 | 中 | 事前にPoC実施。yaxis2はlayoutレベル機能のためtrace typeに依存しない |
| フロントエンドOLS計算の精度 | 低 | 装置の作業時間データ規模（数百〜数千点）ではJS浮動小数点精度で十分 |
| 特徴量組み合わせで次元爆発 | 低 | UI側でパラメータ上限を設定（window最大50、lags最大5等） |
| DB migration（既存データ） | 低 | DROP TABLE IF EXISTS + ALTER TABLE ADD COLUMNで対応。SQLiteの制約内 |
