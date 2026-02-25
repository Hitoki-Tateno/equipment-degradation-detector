# 設備劣化検知プロジェクト — ソフトウェアアーキテクチャ要件 議事録

## アーキテクチャスタイル

### 採用方式: コアモノリス + 境界分離の混合型

現在の構成は純粋なモノリスではなく、以下の混合型である。

- **コア（モノリス）:** Store層、結果ストア、分析層はプロセス内の直接結合
- **境界分離:** 取り込み層はFastAPIで外部公開、表示層はReactで分離

**モノリスを採用した根拠：**

- 1コンテナ構成・SQLite（ファイルベースDB）と自然に整合する
- 小規模チームでの開発効率が高い。サービス間通信のプロトコル定義やエラーハンドリングが不要
- 可用性を重視しない方針のため、分散アーキテクチャの最大の強み（部分障害への耐性・スケーラビリティ）を享受しない
- 分散にする場合、SQLiteからネットワーク対応DBへの変更が必須となり、技術選定と矛盾する

**モノリスのリスクと対策：**

層間の境界が規約でしか守れないため、以下のガードレールを設ける。

---

## ガードレール

### 静的解析（linter / ruff）

- 依存方向の制約をlinter / ruffのルールとして定義し、CIで自動検出する
- importの方向違反（例: Store層が分析層に依存する等）をビルド時に検出・拒否
- Store層のインターフェースは抽象クラス（ABC）として定義し、SQLiteを直接触るコードが分析層や表示層に漏洩していないかを静的に検証

### テスト戦略

静的解析で網羅できない部分はテストで担保する。ただし全てを緻密にテストするのではなく、**対象を絞って集中投資**する。

| 対象 | テストの厚さ | 根拠 |
|---|---|---|
| 層間インターフェース（契約テスト） | 厚い | アーキテクチャの整合性の生命線。マイグレーション時の安全網。Store層の抽象クラスに対して「この入力→この出力」を保証し、実装がSQLiteからPostgreSQLに変わっても同じテストが通ることを確認する |
| 分析層のロジック | 厚い | システムのコアバリュー。Isolation Forestの学習・判定、回帰分析の結果が期待通りかを既知データセットで検証する。バグが検知精度に直結するため妥協しない |
| Store層の実装 | 中程度 | 契約テストが通れば内部の正しさはほぼ保証される |
| 取り込みAPI | 薄い | バリデーションはFastAPIの型定義に委ねる。統合テスト数ケースで十分 |
| 表示層 | 最小限 | 状態管理のロジック部分のみテスト。描画コンポーネントは目視確認の方が効率的 |

---

## ディレクトリ構成

### モノレポ

1コンテナ構成のため、モノレポ一択。分ける理由がない。

### トップレベル構成

```
/
├── backend/
│   ├── interfaces/       # 抽象クラス（Store層・結果ストア）
│   ├── ingestion/        # 取り込みAPI（FastAPI）
│   ├── store/            # Store層（SQLite実装）
│   ├── analysis/         # 分析層（scikit-learn）
│   ├── result_store/     # 結果ストア（SQLite実装）
│   └── scheduler/        # 定期実行 + 手動トリガー
├── frontend/             # React + Plotly.js
├── Containerfile
└── supervisord.conf
```

### 設計判断

**interfaces/ をトップレベルに配置（B案）を採用。**

検討した構成：

| 案 | 概要 | 評価 |
|---|---|---|
| A案: 各層ディレクトリ内に配置 | store/interface.py, result_store/interface.py | linterで「store/interface.pyへの依存はOK、store/sqlite.pyへの依存はNG」とファイル単位の制約になり管理が煩雑 |
| B案: 共通のinterfaces/に切り出し | interfaces/data_store.py, interfaces/result_store.py | ディレクトリ単位でlinterルールを書ける。依存性逆転の原則がディレクトリ構造に表現される |
| C案: store/の下にinterfaces/と各実装を同居 | store/interfaces/, store/data_store/, store/result_store/ | Store層と結果ストアの責務分離が曖昧になる。アーキテクチャ設計で別SQLiteファイルに分離した意図と矛盾。store/という名前がアーキテクチャ上の「Store層」と混同される |

**B案の採用理由：**

- 「analysis/やingestion/はinterfaces/にのみ依存可、store/やresult_store/への直接依存は禁止」とディレクトリ単位で明確にlinterルールを定義できる
- Store層と結果ストアの責務分離がディレクトリ構造に正しく反映される
- 依存性逆転の原則が物理構造として表現される

**各層の下層ディレクトリ構造は実装フェーズで決定する。** 下層は各層の内部実装の構造であり、層間の契約には影響しない。interfaces/の抽象クラスが変わらなければ他の層は一切影響を受けないため、今決めるコストに対してリターンがない。

---

## ブランチ戦略

### 採用方式: GitHub Flow

mainブランチとfeatureブランチのみ。featureブランチからmainへPRを出してマージする。

**候補の比較：**

| 方式 | 評価 |
|---|---|
| Git Flow | 3〜5人の小規模チームにはブランチ管理のオーバーヘッドが重い。リリース管理も厳密でないためrelease/hotfixブランチの管理コストが見合わない。消去 |
| GitHub Flow | PRベースでCIをマージ前に回せる。シンプルかつ安全。チーム規模とリリース方針に合致 |
| Trunk-based | CIが整っていない段階ではmainが壊れるリスクがある。CIをこれから構築するプロジェクトには時期尚早 |

**GitHub Flowの採用理由：**

- 3〜5人のチーム規模でPRレビューが十分回る
- featureブランチ上でCIを回してからマージできるため、CI/CDが育っていく過程でも安全を保てる
- リリース管理が厳密でない方針と整合する

---

## CI/CD

### CI（自動化範囲）

| タイミング | 対象 |
|---|---|
| PR時（マージ前） | 静的解析（linter/ruff） + テスト |
| mainマージ後 | ビルド（フロントエンド + コンテナイメージ） |

- 静的解析とテストはガードレールとして決定済みのため、PRマージ前に自動で回すことが必須
- ビルドはマージ後にmainで実行

### CD（デプロイ）

- デプロイは手動とする
- デプロイ先がオンプレ環境のため、自動デプロイの可否は環境に依存する
- 可用性を重視しない方針のため、手動デプロイで十分

---

## SQLiteスキーマ設計

### Store層

```sql
categories (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  parent_id   INTEGER REFERENCES categories(id)
)

work_records (
  id          INTEGER PRIMARY KEY,
  category_id INTEGER NOT NULL REFERENCES categories(id),
  work_time   REAL NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  UNIQUE(category_id, recorded_at)
)
```

**分類ツリーの表現方法：** 隣接リスト（Adjacency List）を採用。

検討した方式：

| 方式 | 評価 |
|---|---|
| 隣接リスト | 最もシンプル。parent_idで親子関係を表現。ツリー全体の取得にはSQLiteの再帰CTE（WITH RECURSIVE）を使用。分類ツリーの変更頻度は低く深さも2〜3階層のため十分 |
| 経路列挙 | パスのLIKE検索で配下ノードを取得可能だが、ノード移動時にpath全体を書き換える必要がある。過剰 |
| 閉包テーブル | 最も柔軟だがテーブルが増え、小規模には過剰 |

### 結果ストア

```sql
trend_results (
  id           INTEGER PRIMARY KEY,
  category_id  INTEGER NOT NULL UNIQUE,
  slope        REAL NOT NULL,
  intercept    REAL NOT NULL,
  is_warning   BOOLEAN NOT NULL
)

anomaly_results (
  id            INTEGER PRIMARY KEY,
  category_id   INTEGER NOT NULL,
  recorded_at   TIMESTAMP NOT NULL,
  anomaly_score REAL NOT NULL,
  UNIQUE(category_id, recorded_at)
)

model_definitions (
  id              INTEGER PRIMARY KEY,
  category_id     INTEGER NOT NULL UNIQUE,
  baseline_start  TIMESTAMP NOT NULL,
  baseline_end    TIMESTAMP NOT NULL,
  sensitivity     REAL NOT NULL,
  excluded_points TEXT
)
```

**anomaly_resultsにはbooleanではなく異常スコア（REAL）を保存する。**

scikit-learnのIsolation Forestの動作を調査した結果：

| メソッド | contamination（感度）に依存するか |
|---|---|
| fit()（木の構築） | しない |
| score_samples()（生スコア） | しない |
| offset_（閾値） | する |
| decision_function() | する（score_samples - offset_） |
| predict() | する（decision_functionの符号） |

`score_samples()`で得られる生の異常スコアはcontaminationに依存しない。したがって：

- 結果ストアには異常スコアを保存する
- 感度（contamination相当の閾値）の適用はフロントエンド側で行う
- 感度スライダーを動かしてもAPIを叩かずにリアルタイムで判定結果を変更できる
- **再学習が必要なのはベースライン期間または除外点が変わったときのみ**

**[2026-02-20追記] スコアの正規化:**

scikit-learnの`score_samples()`は原論文のスコアを符号反転した値（概ね-1〜0）を返す。
これを`-score_samples()`で原論文準拠のスケール（0〜1）に変換して保存する。

- 原論文の定義: $s(x,n) = 2^{-E(h(x))/c(n)}$
- **1に近い → 異常、0.5未満 → 正常**
- 変更理由: APIの二次配布時に「スコアが高い＝異常」という直感的な解釈を保証するため
- 変更対象: `backend/analysis/anomaly.py` の `train_and_score()` 戻り値

### 分析層の特徴量構築

- Isolation Forestに渡す特徴ベクトルの構築方法は、分析層の内部で差し替え可能な構造とする（戦略パターン等）
- ユーザーには公開せずシステム固定。変更は運用判断で行う
- ドメインモデル、Store層スキーマ、API、結果ストアには波及しない。分析層の内部設計として実装フェーズで対応する

---

**excluded_pointsはJSON配列（タイムスタンプのリスト）で保持。** SQLiteのJSON関数で検索可能。除外点を単独でクエリする要件がないため、正規化して別テーブルにする必要はない。

---

## APIエンドポイント仕様

### 取り込みAPI（境界①）

```
POST /api/records
  Body: {
    records: [{
      category_path: ["大分類", "中分類"],
      work_time: 123.4,
      recorded_at: "2025-01-01T00:00:00"
    }, ...]
  }
  振る舞い: 分類×タイムスタンプが既存と一致→上書き、それ以外→新規追加
  備考: category_pathで指定された分類がツリーに存在しなければ自動作成
```

### データ提供API（境界②）

```
GET /api/records?category_id={id}&start={datetime}&end={datetime}
  出力: { records: [{ work_time, recorded_at }, ...] }
  備考: start/end省略時は全期間

GET /api/categories?root={id}
  出力: { categories: [{ id, name, parent_id, children: [...] }, ...] }
  備考: root省略時はツリー全体
```

### 分析結果API（境界③）

```
GET /api/results/{category_id}
  出力: {
    trend: { slope, intercept, is_warning },
    anomalies: [{ recorded_at, anomaly_score }, ...]
  }
```

### モデル定義API（Step 2 GUI操作用）

```
GET /api/models/{category_id}
  出力: { baseline_start, baseline_end, sensitivity, excluded_points }

PUT /api/models/{category_id}
  Body: { baseline_start, baseline_end, sensitivity, excluded_points }
  振る舞い: 保存後、ベースライン期間または除外点が変更された場合のみ
           Isolation Forestを再学習し結果ストアのanomaly_scoreを更新。
           sensitivityのみの変更では再学習しない（スコアはcontamination非依存）。
```

### 手動トリガーAPI（開発用）

```
POST /api/analysis/run
  振る舞い: 全分類に対して分析層の判定フローを手動実行
```

---

## リアルタイム通知とダッシュボード最適化（Issue #75）

### 課題

ダッシュボードのタブ切替時に、全リーフカテゴリに対して 2N リクエスト（`GET /api/results/{id}` × N + `GET /api/models/{id}` × N）が発生し、体感で遅い。さらに、データは設備から動的に注入される（`POST /api/records`）ため、ユーザー操作とは無関係にバックエンド側でデータが更新される。ダッシュボードはこれを検知する手段がなかった。

### 採用方式: バッチAPI + SSE（Server-Sent Events）

| 最適化 | 効果 |
|--------|------|
| **バッチAPI** `GET /api/dashboard/summary` | 2N → 1 リクエストに集約。全リーフカテゴリのサマリーを一括返却 |
| **SSE** `GET /api/events` | バックエンドの全データ変更をリアルタイムにフロントへ通知 |

**検討した代替案と棄却理由：**

| 案 | 評価 |
|---|---|
| ダーティフラグ（フロント完結） | ユーザー操作の変更しか追跡できず、バックエンドからのデータ注入を検知できない。不採用 |
| WebSocket | 双方向通信は不要。SSEの方が軽量でHTTP/1.1で動作するため過剰。不採用 |
| ポーリング + バージョン番号 | インターバル分の遅延がある。SSEであればリアルタイム通知が可能で実装の複雑さも同程度。不採用 |

### EventBus 設計

単一プロセス（uvicorn）前提で `asyncio.Queue` ベースのインメモリ pub/sub を採用:

- `backend/ingestion/event_bus.py` にモジュールレベルの `EventBus` クラスを定義
- `backend/dependencies.py` で DI 経由（`get_event_bus()`）でシングルトン注入
- データ変更エンドポイント（`POST /api/records`, `PUT/DELETE /api/models`, `POST /api/analysis/run`）の処理完了後に `bus.publish("dashboard-updated")` を呼び出し
- SSE エンドポイント `GET /api/events` が subscribe し、`text/event-stream` でフロントに中継
- 30秒間隔の keepalive コメントでプロキシによるコネクション切断を防止

**ResultStoreInterface は変更しない。** バッチAPI のエンドポイント内で既存メソッドをループ呼び出しする。ダッシュボードサマリーは表示層の関心事であり、ドメインインターフェースに持ち込まない。SQLite は同プロセス内アクセスなのでループのオーバーヘッドは許容範囲。

### フロントエンド連携

- Dashboard コンポーネントは常時マウント（Issue #51 で採用済みの設計）のため、SSE 接続が維持される
- SSE `dashboard-updated` イベント受信時: アクティブなら 2秒デバウンスで `fetchDashboardSummary()` を呼び出し、非アクティブなら stale フラグを立て復帰時に再取得
- PlotView / useBaselineManager は変更不要（PlotView での save/delete もバックエンド経由で SSE 通知が発火する）

### ダッシュボードAPI

```
GET /api/dashboard/summary
  出力: {
    categories: [{
      category_id: 1,
      category_path: "大分類 > 中分類",
      trend: { slope, intercept, is_warning } | null,
      anomaly_count: 3,
      baseline_status: "configured" | "unconfigured"
    }, ...]
  }
  備考: 全リーフカテゴリのサマリーを一括返却

GET /api/events
  Content-Type: text/event-stream
  イベント: dashboard-updated
  備考: SSEストリーム。データ変更時に通知を配信。30秒間隔でkeepalive
```

---

*最終更新: 2026-02-24*
