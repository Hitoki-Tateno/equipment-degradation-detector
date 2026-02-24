# パフォーマンスレビューレポート

**対象プロジェクト:** equipment-degradation-detector
**レビュー日:** 2026-02-20
**技術スタック:** React 18.3.0 (CRA) + FastAPI >= 0.115.0 + SQLite + scikit-learn
**レビュー種別:** 静的コード分析（プロファイリングデータ: なし）

## サマリー

全体的にフロントエンド・バックエンドともに堅実な設計が施されている。最も影響度が高い問題は **バンドルサイズ**（単一JSバンドル 2.5MB / gzip 790KB）であり、Plotly.js GL2D が大部分を占める。Code Splitting が一切行われておらず、初期ロード時にダッシュボード画面のみ必要な場合でもプロットライブラリ全体がロードされる。バックエンドでは、`async def` エンドポイント内で同期的なSQLite操作を実行しており、同時接続数が増えた場合にイベントループをブロックするリスクがある。ダッシュボード画面のAPIコール数（カテゴリ数×2回）もデータ増加に伴いボトルネックとなる可能性がある。

## 評価

### 1. レンダリング効率（フロントエンド）

**評価: 🟢 良好**
**推定影響度: 低**

全体的にReactのベストプラクティスに沿った実装が行われている。

**良い点:**

- 全コンポーネント（`Dashboard`, `WorkTimePlot`, `PlotView`, `BaselineControls`, `CategoryTree`）に `React.memo` が適用されており、不要な再レンダリングが抑制されている
- `useCallback` / `useMemo` がイベントハンドラやデータ派生値に適切に使われている（`App.js:64-78`, `WorkTimePlot.jsx:40-191`）
- スタイルオブジェクトがモジュールレベルの定数として定義されており（例: `App.js:14-27`）、レンダリングごとの新規オブジェクト生成を回避している
- `useBaselineManager` で `useReducer` を使った集約的な状態管理が行われており、状態更新のバッチ処理が自然に効く設計になっている
- `Dashboard.jsx:26` で `categoriesRef` を使って `loadDashboardData` のコールバック依存を安定化しており、不要な再取得を防いでいる

**指摘事項:**

- **[軽微] `Dashboard.jsx:144` — ダッシュボードの常時マウント**
  `App.js:143-150` で `Dashboard` は `display: none` で非表示にしているがアンマウントしていない。ダッシュボードは `Table` コンポーネントのみで軽量なため現時点では問題ないが、将来的にデータが増加した場合はプロットビュー表示中の不要なメモリ占有につながる可能性がある。
  → **推定影響: 低**。現状のコンポーネント構成では問題にならない。

- **[軽微] `WorkTimePlot.jsx:76-89` — `excludedIndices.includes()` のO(n)走査**
  `markerColors` と `markerSymbols` の算出で各ポイントに対して `excludedIndices.includes(i)` を呼んでおり、除外ポイント数×全ポイント数の計算量になる。
  → **推定影響: 低**。通常のデータ量（数百〜数千点）では問題にならない。万点を超える場合は `Set` への変換を検討。

### 2. バンドルサイズとロード効率（フロントエンド）

**評価: 🔴 要改善**
**推定影響度: 高**

**現状の計測値:**
| アセット | Raw | gzip (推定) |
|----------|-----|-------------|
| `main.c84de2d3.js` | 2.5MB | 790KB |
| `main.9e7d2304.css` | 3.8KB | ~1.5KB |

単一のJavaScriptバンドルに全てのコードが含まれている。

**指摘事項:**

- **[重大] Code Splitting が未実装**
  `plotly.js-gl2d-dist` はWebGL2Dレンダリング対応版で、ライブラリ単体で推定1.5〜2MBを占める（バンドル全体2.5MBの大部分）。Ant Designも全コンポーネントが含まれている可能性がある。ダッシュボード画面（`Table` のみ）を最初に表示するユーザーにとって、プロットライブラリのロードは完全に不要。
  → **改善案:** `React.lazy()` + `Suspense` で `PlotView`（= `WorkTimePlot` = Plotly依存）を動的importに分離する。`App.js:6` の `import PlotView from './components/PlotView'` を `const PlotView = React.lazy(() => import('./components/PlotView'))` に変更し、ダッシュボード表示時にはPlotlyバンドルがロードされないようにする。これにより初期ロードを推定 1.5〜2MB（gzip 500〜600KB）削減可能。

- **[中] `plotly.js-gl2d-dist` の選択**
  `plotly.js-gl2d-dist` は GL2Dに特化したカスタムバンドルを使っておりフルビルド（3.5MB+）よりは小さいが、それでも大きい。現在使っているトレースタイプは `scattergl` と `scatter`（lines）のみ。
  → **改善案:** Plotlyのカスタムバンドルをさらに絞り込む（`plotly.js-basic-dist` で `scattergl` が含まれるか確認）か、最低限 Code Splitting で遅延ロードする。

- **[低] Create React App (CRA) の制約**
  CRAは `react-scripts 5.0.1` を使用しており、Webpackの設定カスタマイズがejectなしではできない。Viteへの移行でTree-shakingの改善やビルド速度向上が見込めるが、移行コストとの兼ね合い。
  → **推定影響: 低（現時点）**。Code Splitting は CRA でも `React.lazy` で実現可能なので、まずはそちらを優先。

- **[情報] nginxでのgzip圧縮が未設定**
  `nginx.conf` にgzip設定がない。デフォルトではgzipが無効の場合があり、2.5MBのバンドルがそのまま転送される可能性がある。
  → **改善案:** `nginx.conf` に以下を追加:
  ```nginx
  gzip on;
  gzip_types text/css application/javascript application/json;
  gzip_min_length 1000;
  ```

### 3. レスポンス効率（バックエンド）

**評価: 🟡 改善推奨**
**推定影響度: 中**

**指摘事項:**

- **[重要] `async def` エンドポイントで同期SQLite操作を実行**
  全エンドポイント（`main.py:152-388`）が `async def` で定義されているが、`StoreDep` と `ResultStoreDep` の実際の実装（`SqliteDataStore`, `SqliteResultStore`）は `sqlite3` モジュールを使った同期I/O。`async def` 内で同期I/Oを呼ぶと、FastAPIのイベントループがブロックされ、同時リクエスト処理能力が著しく低下する。

  FastAPIの仕様: `def`（非async）のエンドポイントは自動的にスレッドプールで実行されるため、同期I/Oを安全に扱える。`async def` はイベントループ上で直接実行されるため、同期I/Oは禁忌。

  → **改善案（推奨）:** 全エンドポイントの `async def` を `def` に変更する。SQLiteは同期ドライバであり、`async def` にする利点がない。FastAPIが自動的にスレッドプールで実行するため、イベントループのブロックを回避できる。
  → **改善案（代替）:** `aiosqlite` に移行し、非同期I/Oを実現する。ただし移行コストが大きく、SQLiteの同時書き込み制限を考えるとメリットは限定的。

- **[重要] `PUT /api/models/{category_id}` での同期分析実行**
  `main.py:339` で `engine.run(category_id)` を呼んでおり、IsolationForestの学習・推論がリクエスト処理中に同期実行される。`engine.run()` は `scikit-learn` のfit/scoreを含むCPUバウンドな処理であり、データ量に比例して応答時間が増加する。
  → **推定影響: 中**。少量データ（数百件）では問題にならないが、大量データでは秒単位のブロックが発生する可能性がある。
  → **改善案:** バックグラウンドタスク（`BackgroundTasks`）に分離するか、`run_in_executor` でスレッドプール実行する。ただし、現状のエンドポイントが `async def` のままだと `def` に変更するだけで自動的にスレッドプール実行される。

- **[低] `POST /api/records` での逐次分析実行**
  `main.py:179-180` で影響を受けたカテゴリごとに `engine.run(cid)` を逐次実行している。多数のカテゴリが影響を受ける場合に応答時間が線形に増加する。
  → **推定影響: 低**。通常のバッチ投入では少数カテゴリの影響のみ。

- **[情報] ページネーションが未実装**
  `GET /api/records` はカテゴリの全レコードを一度に返す。データが蓄積されると応答サイズが大きくなる可能性がある。
  → **推定影響: 低（現時点）**。作業時間レコードはプロット表示に全件必要なため、APIレベルのページネーションよりも将来的にはデータの間引きやサマリーAPIが有用。

### 4. 外部リソースとの通信（バックエンド）

**評価: 🟢 良好**
**推定影響度: 低**

**分析結果:**

- **外部HTTP通信なし:** このアプリケーションは外部APIへのHTTPリクエストを行っていない。全てのデータはSQLiteローカルファイルに保存されており、外部サービスへの依存がない。

- **DB接続の管理:** SQLiteの接続は `dependencies.py` のシングルトンパターンで管理されており、リクエストごとの接続生成オーバーヘッドがない。`check_same_thread=False` が設定されており、マルチスレッド環境（FastAPIの `def` エンドポイント）での使用に対応している。

- **キャッシュ:** 明示的なキャッシュ層はないが、SQLiteのファイルI/Oキャッシュ（OSレベル）が暗黙的に機能する。カテゴリツリーのような変更頻度の低いデータにインメモリキャッシュを追加する余地はあるが、現時点では過剰最適化。

**指摘事項:**

- **[情報] Uvicornの単一ワーカー実行**
  `supervisord.conf:7` で `uvicorn` がデフォルトの1ワーカーで起動している。SQLiteの同時書き込み制限（WALモードでなければ排他ロック）を考慮するとシングルワーカーは合理的だが、読み取りのみのエンドポイントのスループットが制限される。
  → **推定影響: 低**。設備監視システムの想定同時ユーザー数は少数であり、現状では問題にならない。

### 5. データフロー全体の効率

**評価: 🟡 改善推奨**
**推定影響度: 中**

**指摘事項:**

- **[重要] ダッシュボードのN+1 APIコールパターン**
  `Dashboard.jsx:35-51` でダッシュボード表示時に、全末端カテゴリに対して `fetchResults(leaf.id)` と `fetchBaselineConfig(leaf.id)` を並列発行している（`Promise.allSettled` で1カテゴリあたり2リクエスト）。カテゴリ数Nに対して 2N 回のHTTPリクエストが発生する。

  例: 末端カテゴリが50個の場合、100件のHTTPリクエストが同時発行される。

  → **改善案:** ダッシュボード用の集約API（`GET /api/dashboard/summary`）を新設し、全カテゴリのトレンド・ベースライン状態を1回のAPIコールで取得する。バックエンドでSQL JOINを使えばDBアクセスも1〜2回で済む。

- **[中] プロットビュー遷移時のAPIコール**
  `useBaselineManager.js:176-218` でカテゴリ選択時に `fetchRecords` と `fetchResults` を並列取得し、さらに `fetchBaselineConfig` を直列で取得している（合計3 APIコール、うち2は並列、1は直列）。
  → **推定影響: 中**。3回のAPIコールは許容範囲だが、`fetchBaselineConfig` が直列になっている点は改善余地がある。
  → **改善案:** 3つのAPIコールを全て `Promise.all` で並列化する。ただし、404のハンドリングが必要なため現在のtry/catchパターンには理由がある。`Promise.allSettled` で3つを並列化し、個別にハンドリングするのが最適。

- **[低] フロントエンドのAPIクライアント設定**
  `api.js:3` で `axios.create({ baseURL: '/api' })` を使用しており、セッション再利用やリクエストの重複排除は行われていない。同じカテゴリのデータを短時間に複数回取得する可能性がある（ダッシュボード⇔プロット切替時など）。
  → **改善案:** React Query / SWR などのデータフェッチングライブラリの導入で、キャッシュ・重複排除・バックグラウンド更新を一括対応可能。ただし、現在のアプリケーション規模では導入コストに見合わない可能性がある。

## 優先対応事項

| 優先度 | 問題 | 推定影響度 | 改修コスト | 推奨アクション |
|--------|------|-----------|-----------|----------------|
| P0 | Code Splitting 未実装（バンドル 2.5MB / gzip 790KB） | 高 | 低 | `PlotView` を `React.lazy()` で動的import化。ダッシュボード初期表示の転送量を推定60%以上削減 |
| P0 | `async def` + 同期SQLite（イベントループブロック） | 高 | 低 | 全エンドポイントの `async def` を `def` に変更 |
| P1 | nginx gzip 未設定 | 中 | 低 | `nginx.conf` に gzip 設定を追加 |
| P1 | ダッシュボードのN+1 APIコール（2N回） | 中 | 中 | 集約API `GET /api/dashboard/summary` を新設 |
| P2 | `PUT /api/models` での同期分析実行 | 中 | 中 | `BackgroundTasks` またはスレッドプール実行に変更（`def` 化で自動解決） |
| P2 | `useBaselineManager` の直列APIコール | 低 | 低 | `Promise.allSettled` で3コールを並列化 |

## 計測の推奨

- **初期ロード時間:** Code Splitting 実装前後で Lighthouse の FCP (First Contentful Paint) / LCP (Largest Contentful Paint) を比較計測。現状のバンドルサイズから、FCP が2〜3秒以上かかっている可能性が高い（低速ネットワーク環境下）
- **バンドル内訳:** `npx source-map-explorer frontend/build/static/js/main.c84de2d3.js` で各ライブラリのバンドル寄与率を可視化。Plotly.js と Ant Design のサイズ内訳を定量把握
- **APIレスポンス時間:** `/api/results/{category_id}` と `/api/models/{category_id}` の応答時間を、カテゴリ数が増加した環境で計測。ダッシュボードの体感速度に直結
- **イベントループブロック時間:** `async def` → `def` への変更前後で、同時リクエスト処理時のレスポンス時間分布を計測（`ab` や `wrk` で負荷テスト）。特に `PUT /api/models` の応答時間がデータ量に対してどう変化するかを確認
- **SQLite書き込み競合:** WALモード未設定の場合、同時書き込みで `database is locked` エラーが発生する可能性がある。`PRAGMA journal_mode=WAL` の設定を検討し、負荷テスト時のエラー率を監視
