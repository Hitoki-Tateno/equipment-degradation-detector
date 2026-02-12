# APIエンドポイント詳細仕様

## POST /api/records（取り込みAPI — 境界①）

```
リクエスト:
  { "records": [{ "category_path": ["大分類", "中分類"], "work_time": 123.4, "recorded_at": "2025-01-01T00:00:00" }] }

レスポンス:
  { "inserted": 2 }

振る舞い:
  - category_path から ensure_category_path でcategory_idを取得（未知なら自動作成）
  - category_id × recorded_at が既存と一致 → 上書き
  - それ以外 → 新規追加
```

## GET /api/records（データ提供API — 境界②）

```
パラメータ:
  - category_id: int（必須）
  - start: datetime（省略可）
  - end: datetime（省略可）

レスポンス:
  { "records": [{ "work_time": 10.5, "recorded_at": "2025-01-01T00:00:00" }] }

備考: start/end省略時は全期間
```

## GET /api/categories（分類ツリーAPI — 境界②）

```
パラメータ:
  - root: int（省略可）

レスポンス:
  { "categories": [{ "id": 1, "name": "プロセスA", "parent_id": null, "children": [{ "id": 2, "name": "設備1", "parent_id": 1, "children": [] }] }] }

備考: root省略時はツリー全体
```

## GET /api/results/{category_id}（分析結果API — 境界③）

```
レスポンス:
  {
    "trend": { "slope": 0.05, "intercept": 10.0, "is_warning": false },
    "anomalies": [{ "recorded_at": "2025-01-01T00:00:00", "anomaly_score": -0.35 }]
  }

備考: trend または anomalies が未計算の場合は null を返す
```

## GET /api/models/{category_id}（モデル定義取得）

```
レスポンス:
  { "baseline_start": "...", "baseline_end": "...", "sensitivity": 0.5, "excluded_points": ["2025-03-15T00:00:00"] }

備考: 未定義の場合は 404
```

## PUT /api/models/{category_id}（モデル定義更新）

```
リクエスト:
  { "baseline_start": "...", "baseline_end": "...", "sensitivity": 0.5, "excluded_points": ["2025-03-15T00:00:00"] }

レスポンス:
  { "retrained": true }

振る舞い:
  1. 既存のモデル定義を取得
  2. baseline_start, baseline_end, excluded_points のいずれかが変更されたか比較
  3. 変更あり → Isolation Forestを再学習し結果ストアを更新。retrained: true
  4. sensitivityのみ変更 → 再学習しない。retrained: false
```

## POST /api/analysis/run（手動トリガー — 開発用）

```
レスポンス:
  { "processed_categories": 5 }

振る舞い: 全分類に対して分析層の判定フローを実行
```
