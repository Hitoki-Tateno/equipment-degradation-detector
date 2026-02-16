# 実装フェーズ進行計画 v2

## Context

設備劣化検知システムの開発において、Step 1（データ可視化）のインフラストラクチャが完成し、次のフェーズへ進む段階にある。v1計画をもとに、テックリードとの設計議論を行い、アーキテクチャ上の重要な判断を確定した。

**v1からの主要変更:**
- スケジューラー廃止 → データ取り込み時の同期分析に変更
- モデルのライフサイクル（状態遷移）を明確化
- IsolationForest実装を特徴量決定まで待ち回し
- 並行開発を前提としない順序実行に変更

変更の詳細な経緯は末尾の「設計判断ログ」を参照。

---

## 確定した設計判断

### 分析実行タイミング
データ取り込みエンドポイント（POST /api/records, POST /api/records/csv）の処理末尾で、対象カテゴリの分析を**同期的に**実行する。

- 1レコードずつのリアルタイム取り込みが主要ユースケース
- SQLiteの直列書き込み制約上、並列化の恩恵は限定的
- 数レコード×LinearRegressionはミリ秒単位で完了するためレイテンシ問題なし
- POST /api/analysis/run は手動トリガーとして残す（ダッシュボードの「分析実行」ボタン用）

### 分析フローの分割
```
取り込みリクエスト受信
  ├── レコード保存
  ├── トレンド分析（常時実行）
  └── 異常検知
        ├── モデル定義済み → IsolationForest実行
        └── モデル未定義 → スキップ
```

### モデルのライフサイクル
```
未定義 ──(ユーザーがベースライン選択+保存)──→ 定義済み ──(ユーザーが削除)──→ 未定義
```
- **作成**: ユーザーがGUI上でベースライン範囲・感度を指定して保存。IsolationForestの学習もこのタイミングで実行
- **削除**: モデルを削除、未定義状態に戻す。異常検知結果もカスケード削除
- **「更新」は存在しない**: 設備状況変化時はモデル削除→再作成。中途半端な部分更新を排除し、運用上の安全性を確保

### 廃止されるコンポーネント
- ~~`backend/scheduler/main.py`~~ → 不要。定期実行ループは持たない
- ~~APScheduler依存~~ → 不要

---

## 既存コードへの影響分析

### ResultStoreInterface（要拡張）
現在の `backend/interfaces/result_store.py` に以下の2メソッドが不足:
- `delete_model_definition(category_id: int) -> None`
- `delete_anomaly_results(category_id: int) -> None`

→ フェーズCで追加。契約テスト + SqliteResultStore実装も必要。

### DataStoreInterface
末端ノード（子なし）列挙メソッドは不要。`get_category_tree()` でツリー取得後、再帰的に子なしノードをフィルタすればよい（AnalysisEngine内のヘルパー）。

### backend/scheduler/main.py
スケルトンのみで実装なし。廃止しても影響なし（削除はフェーズC時）。

---

## 実装フェーズの進行順序

フロントエンド先行で画面の操作感を確認した後、バックエンドロジックを実装し接続する。

```
時系列 →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[A: Frontend Step 2] → [B: 回帰ロジック(TDD)] → [C: API接続+統合] → [D: ダッシュボード] → [E: 統合テスト]
                                                                                    ↑
                                                               IsolationForest実装はここ以降（特徴量決定後）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### フェーズ A: Frontend Step 2（モデル定義GUI）
**対象**: `frontend/src/`
**方針**: 分析結果はモック/ハードコードで暫定表示。画面の操作感をGUIで確認する。

1. **API関数追加** (`frontend/src/services/api.js`)
   - fetchResults, fetchModelDefinition, saveModelDefinition, deleteModelDefinition, triggerAnalysis

2. **WorkTimePlot拡張** (`frontend/src/components/WorkTimePlot.jsx`)
   - Box Select でベースライン範囲選択 (`dragmode: "select"`, `onSelected`)
   - クリックで除外点トグル (`onClick`)
   - 回帰直線オーバーレイ（**暫定: ハードコード値で表示確認**）

3. **感度スライダー** — 新コンポーネントまたはApp.jsに追加
   - Ant Design `Slider` (0〜1)
   - anomaly_scoresに閾値適用 → マーカー色更新（フロント完結）

4. **モデル定義 保存/読み込み/削除 フロー**
   - PUT /api/models/{category_id} で保存
   - DELETE /api/models/{category_id} で削除（カスケード削除）
   - カテゴリ選択時にGET /api/models/{category_id}で既存定義を読み込み

**参照**: `frontend/src/services/api.js`, `frontend/src/components/WorkTimePlot.jsx`, `.claude/skills/react-plotly/references/interactive-plots.md`

### フェーズ B: トレンド分析（厳密TDD）
**対象**: `backend/analysis/`
**方針**: テストを先に書き（Red）、最小実装で通し（Green）、リファクタリングする

1. **FeatureStrategy ABC + RawWorkTimeStrategy**
   - `backend/analysis/feature.py` に定義
   - テスト: 既知データで特徴量抽出結果を検証

2. **トレンド分析（LinearRegression）**
   - `backend/analysis/trend.py` に `compute_trend(records) → TrendResult`
   - テスト: 線形増加データ（slope > 0）、平坦データ（slope ≈ 0）、WARNING_THRESHOLD判定
   - WARNING_THRESHOLDは仮値で定義し、定数として管理

3. **AnalysisEngine オーケストレータ（トレンドのみ）**
   - `backend/analysis/engine.py` にDIパターンで実装
   - `run(category_id)`: 指定カテゴリのトレンド分析を実行
   - モデル定義有無を確認し、定義済みなら異常検知を実行（**異常検知は後日実装、現時点ではスキップ**）
   - テスト: モック Store/ResultStoreで呼び出しフローを検証

**成果物**: `backend/analysis/feature.py`, `backend/analysis/trend.py`, `backend/analysis/engine.py`, `tests/unit/test_analysis_engine.py`

**参照**: `backend/interfaces/data_store.py`, `backend/interfaces/result_store.py`, `.claude/skills/analysis-engine/references/analysis-flow.md`

### フェーズ C: API接続 + 取り込み時分析
**対象**: `backend/ingestion/main.py`, `backend/interfaces/result_store.py`, `backend/result_store/sqlite.py`

1. **ResultStoreInterface拡張**
   - `delete_model_definition(category_id)` 追加
   - `delete_anomaly_results(category_id)` 追加
   - 契約テスト追加 → SqliteResultStore実装

2. **取り込みエンドポイントへの分析組み込み**
   - POST /api/records の処理末尾で `AnalysisEngine.run(category_id)` を同期呼び出し
   - POST /api/records/csv では影響を受ける全カテゴリに対して実行

3. **POST /api/analysis/run 接続**
   - スケルトンを実装に置換
   - AnalysisEngine をDIで注入し `run(category_id)` または `run_all()` を呼び出す

4. **DELETE /api/models/{category_id} 実装**
   - モデル定義削除 + 異常検知結果のカスケード削除

5. **統合テスト**
   - `tests/integration/test_analysis_flow.py`
   - データ投入 → 分析自動実行 → 結果取得の一連フロー
   - モデル削除 → 結果がクリアされることの検証

6. **scheduler/main.py 廃止**

**成果物**: 取り込み→分析→結果保存の完全なバックエンドフロー

### フェーズ D: Frontend Step 3（監視ダッシュボード）
**対象**: `frontend/src/`

1. カテゴリ一覧ステータステーブル（Ant Design `Table`）
2. トレンド警告表示（`Tag` / `Alert`）
3. モデル状態表示（未定義 / 定義済み）
4. 手動分析トリガーボタン（POST /api/analysis/run呼び出し）
5. モデル削除ボタン + 確認ダイアログ
6. ダッシュボードとプロット画面の切り替え/統合

### フェーズ F: IsolationForest（特徴量決定後）
**前提**: 特徴量の選定が完了していること

1. **異常検知実装（TDD）**
   - `backend/analysis/anomaly.py` に `train_and_score(baseline, all_data) → anomaly_scores`
   - 固定パラメータ: n_estimators=100, random_state=42, contamination="auto"

2. **AnalysisEngine拡張**
   - `run()` 内のモデル定義済み分岐で異常検知を呼び出す

3. **モデル作成時の学習処理**
   - PUT /api/models/{category_id} でモデル保存時にIsolationForestの学習を実行

4. **フロントエンド接続**
   - 感度スライダーの閾値適用を実データに接続
   - 異常マーカーの表示

**参照**: `.claude/skills/analysis-engine/references/isolation-forest.md`

### フェーズ E: 統合テスト + デプロイ準備
1. E2E統合テスト（全フロー検証）
2. エッジケース対応（データ0件、モデル未定義時等）
3. OpenShiftデプロイ検証

---

## Issue分割案（8件）

| 仮# | タイトル | フェーズ | ラベル | 備考 |
|-----|---------|---------|--------|------|
| 1 | フロントエンド: API関数追加 + 回帰直線表示（モック） | A | `layer:frontend` | ハードコード/モック値で動作確認 |
| 2 | フロントエンド: ベースライン選択 + 除外点 + 感度スライダー | A | `layer:frontend` | #1に依存 |
| 3 | 分析エンジン: FeatureStrategy + トレンド分析（TDD） | B | `layer:analysis` | Red→Green→Refactor |
| 4 | 分析エンジン: AnalysisEngineオーケストレータ（TDD） | B | `layer:analysis` | #3に依存 |
| 5 | 取り込み時分析 + API接続 + モデル削除API | C | `layer:api` | #4に依存。Interface拡張含む |
| 6 | フロントエンド: 監視ダッシュボード | D | `layer:frontend` | #5に依存 |
| 7 | 異常検知: IsolationForest実装（TDD） | F | `layer:analysis` | 特徴量決定後、#4に依存 |
| 8 | 統合テスト + デプロイ検証 | E | `layer:infra` | 全完了後 |

### 実行順タイムライン
```
#1 (API関数+モック表示) → #2 (ベースライン+スライダー) → #3 (トレンドTDD) → #4 (オーケストレータ) → #5 (API接続) → #6 (ダッシュボード) → #8 (統合テスト)
                                                                                                                          ↑
                                                                                                #7 (IsolationForest) はここに合流（特徴量決定後）
```

---

## 検証方法

| フェーズ | 検証コマンド/手順 |
|---------|-----------------|
| A | ブラウザでBox Select → モデル保存/削除 → 感度スライダー → 暫定表示の目視確認 |
| B | `uv run pytest tests/unit/test_analysis_engine.py -v` 全PASS |
| B | `uv run pytest tests/unit/test_dependency_rules.py -v` PASS（依存方向違反なし） |
| C | `POST /api/records` → `GET /api/results/{id}` で自動分析結果を確認 |
| C | `DELETE /api/models/{id}` → 異常検知結果がクリアされることを確認 |
| D | ダッシュボードで全カテゴリのステータス + モデル状態が一覧表示 |
| F | IsolationForestユニットテスト全PASS |
| E | `uv run pytest` 全テストPASS + `uv run ruff check backend/` PASS |

---

## 設計判断ログ

### 判断1: スケジューラー廃止 → 取り込み時同期分析
- **v1**: APSchedulerまたはtime.sleepによる定期実行
- **問題**: ポーリングではなくイベント駆動が要件に合致
- **決定**: 取り込みエンドポイントの処理末尾で分析を同期呼び出し
- **根拠**: 1レコードずつのリアルタイム取り込みが主要ユースケース。SQLite単一Pod構成で並列化の恩恵なし

### 判断2: 同期実行の採用
- **検討**: 同期 / BackgroundTasks / 手動トリガーのみ
- **決定**: 同期実行
- **根拠**: 数レコード×LinearRegression=ミリ秒。HTTPレスポンスの遅延は無視できるレベル

### 判断3: モデルのライフサイクル定義
- **v1**: 状態遷移が明示されていなかった
- **決定**: 未定義⇔定義済みの2状態。更新は削除→再作成
- **根拠**: 部分更新を許すとベースラインと学習済みモデルの不整合が起きやすい

### 判断4: 分析フローの分割（トレンド常時 / 異常検知はモデル依存）
- **決定**: トレンド=常時実行、異常検知=モデル定義済みのみ
- **根拠**: トレンドは前提条件なし。異常検知はベースライン学習済みモデルが必要

### 判断5: カスケード削除
- **決定**: モデル削除時にanomaly結果も一緒に削除
- **根拠**: モデルが消えた以上、そのモデルに基づく検知結果は意味を失う

### 判断6: IsolationForest後回し
- **v1**: フェーズAでトレンドと連続実装
- **決定**: 特徴量が確定するまで実装しない
- **根拠**: 特徴量未定のまま実装しても手戻りになる

### 判断7: 順序実行（並行開発の撤回）
- **v1**: フロントエンドとバックエンドの並行開発
- **決定**: フロントエンド先行→バックエンドの順序実行
- **根拠**: IF後回しでバックエンド作業量が縮小。並行のコーディネーションコストに見合わない

### 判断8: レイテンシ・可用性は考慮対象外
- **決定**: 現段階では考慮しない
- **根拠**: SQLiteを選定した時点で単一Pod前提。高可用性は設計目標に含まれていない
