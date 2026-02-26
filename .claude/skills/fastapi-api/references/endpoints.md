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
  - 処理末尾で AnalysisEngine.run(category_id) を同期実行（トレンド分析 + モデル定義済みなら異常検知）
```

## POST /api/records/csv（CSV取り込みAPI）

```
リクエスト: multipart/form-data (CSVファイル)

レスポンス:
  { "inserted": 10, "skipped": 0 }

振る舞い:
  - CSVの各行を解析し、category_pathを自動構築
  - 処理末尾で影響を受ける全カテゴリに対して AnalysisEngine.run(category_id) を同期実行
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
    "trend": { "slope": 0.05, "intercept": 10.0 },
    "anomalies": [{ "recorded_at": "2025-01-01T00:00:00", "anomaly_score": 0.65 }]
  }

備考: trend または anomalies が未計算の場合は null を返す
```

## GET /api/models/{category_id}（モデル定義取得）

```
レスポンス:
  { "baseline_start": "...", "baseline_end": "...", "sensitivity": 0.5, "excluded_points": ["2025-03-15T00:00:00"], "feature_config": { "features": [{ "feature_type": "raw_work_time", "params": {} }] } }

備考: 未定義の場合は 404。feature_config は null の場合あり（デフォルト特徴量を使用）
```

## PUT /api/models/{category_id}（モデル定義作成）

```
リクエスト:
  { "baseline_start": "...", "baseline_end": "...", "sensitivity": 0.5, "excluded_points": ["2025-03-15T00:00:00"], "feature_config": { "features": [{ "feature_type": "raw_work_time", "params": {} }] } }

レスポンス:
  { "created": true }

振る舞い:
  - モデル定義を保存（既存があれば上書き）
  - feature_config はオプション（null可、省略時はデフォルト特徴量）
  - IsolationForestの学習を実行し、anomaly_scoresを結果ストアに保存
  - 「更新」の概念はない。変更時はDELETE→PUTで再作成する
```

## DELETE /api/models/{category_id}（モデル定義削除）

```
レスポンス:
  { "deleted": true }

振る舞い:
  - モデル定義を削除
  - 該当カテゴリの異常検知結果（anomaly_results）もカスケード削除
  - 未定義の場合は 404
```

## POST /api/analysis/run（手動トリガー）

```
レスポンス:
  { "processed_categories": 5 }

振る舞い:
  - 全末端カテゴリに対してトレンド分析を実行
  - モデル定義済みのカテゴリには異常検知も実行
  - ダッシュボードの「分析実行」ボタンから呼び出す
```

## GET /api/dashboard/summary（ダッシュボードバッチAPI）

```
レスポンス:
  {
    "categories": [
      {
        "category_id": 1,
        "category_path": "大分類 > 中分類",
        "anomaly_count": 3,
        "baseline_status": "configured"
      },
      {
        "category_id": 2,
        "category_path": "大分類 > 別分類",
        "anomaly_count": 0,
        "baseline_status": "unconfigured"
      }
    ]
  }

振る舞い:
  - 全リーフカテゴリのサマリーを一括返却（中間ノードは含まない）
  - category_path はサーバー側で " > " 区切りで組み立て
  - trend フィールドは廃止（ADR: analysis_ui_redesign.md 決定1）
  - anomaly_count は異常スコアの件数（リスト全体ではなく件数のみ）
  - baseline_status は "configured"（モデル定義あり）/ "unconfigured"（なし）
```

## GET /api/features/registry（特徴量一覧API）

```
レスポンス:
  {
    "features": [
      {
        "feature_type": "raw_work_time",
        "label": "生の作業時間",
        "description": "作業時間をそのまま特徴量として使用（デフォルト）",
        "params_schema": {}
      }
    ]
  }

振る舞い:
  - FEATURE_REGISTRY に登録された全特徴量の一覧を返す
  - params_schema は各特徴量が受け付けるパラメータのスキーマ（空の場合はパラメータなし）
  - フロントエンドの FeatureSelector が起動時に取得し、チェックボックスUI を動的構築
  - ADR: analysis_ui_redesign.md 決定3
```

## GET /api/events（SSEストリーム）

```
Content-Type: text/event-stream

イベント形式:
  event: dashboard-updated
  data: {}

振る舞い:
  - Server-Sent Events ストリーム
  - データ変更エンドポイント（POST /api/records, PUT/DELETE /api/models, POST /api/analysis/run）の完了後に dashboard-updated イベントを配信
  - 30秒間隔で keepalive コメント（": keepalive\n\n"）を送信し、プロキシによるコネクション切断を防止
  - フロントエンドの EventSource API で購読
```
