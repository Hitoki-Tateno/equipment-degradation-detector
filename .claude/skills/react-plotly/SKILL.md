---
name: react-plotly
description: React + Plotly.js + Ant Designによるフロントエンド実装。散布図プロット、分類ツリー表示、ベースライン範囲選択、除外点操作、感度スライダー、監視ダッシュボードの実装時に使用する。「フロントエンド」「React」「Plotly」「プロット」「グラフ」「ダッシュボード」「UI」「スライダー」「Ant Design」「antd」に関するタスクで発動する。
---

# React + Plotly.js + Ant Design フロントエンド実装

## 技術スタック

- **React 18** — UIフレームワーク
- **Plotly.js** (plotly.js-gl2d-dist + react-plotly.js/factory) — WebGL描画（scattergl）、軽量バンドル
- **Ant Design 5** — UIコンポーネント（Tree, Slider, Table, Layout, Segmented等）

## Ant Design: インポートルール（重要）

バンドルサイズ削減のため、**コンポーネント単位でインポートする**。一括インポート禁止:

```jsx
// ✅ 正しい: コンポーネント単位
import { Tree } from "antd";
import { Slider } from "antd";
import { Layout, Menu } from "antd";

// ❌ 禁止: 全体インポート
import antd from "antd";
```

アイコンも個別インポート:

```jsx
// ✅ 正しい
import { SettingOutlined } from "@ant-design/icons";

// ❌ 禁止
import * as Icons from "@ant-design/icons";
```

## コンポーネント構成

```
App.js                          # レイアウト + ビュー切替（dashboard / plot / tutorial）
├── Dashboard.jsx               # 監視ダッシュボード（カテゴリ一覧テーブル）
├── CategoryTree.jsx            # 分類ツリー（サイドバー内、プロットビュー時のみ表示）
├── PlotView.jsx                # プロットビューコンテナ
│   ├── WorkTimePlot.jsx        # Plotly散布図 + 異常スコアサブチャート（メモ化済み）
│   └── BaselineControls.jsx    # ベースライン設定操作パネル
│       └── FeatureSelector.jsx # 特徴量チェックボックス選択（Checkbox.Group）
└── TutorialPage.jsx            # 特徴量チュートリアルページ（学習専用）

hooks/
├── useBaselineManager.js       # ベースライン状態管理 + API操作
└── useResizable.js             # サイドバーリサイズ（ドラッグ操作）

services/api.js                 # axios APIクライアント
utils/categoryUtils.js          # カテゴリツリーのフラット化ユーティリティ
utils/featureTransforms.js      # JS版特徴量変換（チュートリアル表示専用）
```

### 状態管理の責務分担

| 状態 | 管理場所 | 説明 |
|------|---------|------|
| `currentView` | App.js | `'dashboard'` / `'plot'` / `'tutorial'` ビュー切替 |
| `categories` | App.js | カテゴリツリー（初回マウント時に取得） |
| `selectedCategoryId` | App.js | 選択中のカテゴリID |
| `siderWidth` / `isDragging` | useResizable hook | サイドバー幅のドラッグリサイズ |
| `records` / `trend` / `anomalies` | useBaselineManager | 分析データ（categoryId変更時に取得） |
| `baselineStatus` / `baselineRange` | useBaselineManager | ベースライン設定状態 |
| `interactionMode` | useBaselineManager | `'select'` / `'operate'` モード |
| `sensitivity` / `excludedIndices` | useBaselineManager | 感度・除外点設定 |
| `featureConfig` | useBaselineManager | 特徴量設定（save時にベースライン設定と一括送信） |
| `axisRange` | PlotView.jsx | ズーム/パン状態の保持（モード切替時に維持） |

## Ant Designコンポーネントの対応

| UI要素 | Ant Designコンポーネント | 使用箇所 |
|---|---|---|
| 分類ツリー | `Tree` | CategoryTree.jsx |
| 感度スライダー | `Slider` | BaselineControls.jsx |
| モード切替 | `Segmented` | PlotView.jsx |
| データ一覧テーブル | `Table` | Dashboard.jsx |
| 画面レイアウト | `Layout` (`Sider`, `Content`, `Header`) | App.js |
| ナビゲーション | `Menu` (horizontal) | App.js |
| 警告表示 | `Alert` / `Tag` | Dashboard.jsx, BaselineControls.jsx |
| 確認ダイアログ | `Modal.confirm` | BaselineControls.jsx, Dashboard.jsx |
| 読み込み中 | `Spin` / `Empty` | PlotView.jsx, App.js |
| 特徴量チェックボックス | `Checkbox.Group` | FeatureSelector.jsx |
| 特徴量カード | `Card` | TutorialPage.jsx |

## 用語規約（重要）

フロントエンドでは「モデル」という用語を使わない。Isolation Forestの設定は「ベースライン設定」として扱う:

| ❌ 旧用語 | ✅ 現用語 |
|-----------|----------|
| `modelStatus`, `'defined'`/`'undefined'` | `baselineStatus`, `'configured'`/`'unconfigured'` |
| `ModelControls` | `BaselineControls` |
| `fetchModelDefinition` | `fetchBaselineConfig` |
| `saveModelDefinition` | `saveBaselineConfig` |
| `deleteModelDefinition` | `deleteBaselineConfig` |
| 「モデル保存」「モデル削除」 | 「設定を保存」「設定をリセット」 |
| 「定義済み」「未定義」 | 「設定済み」「未設定」 |

※ バックエンドAPIエンドポイントは `/api/models/{category_id}` のまま維持。

## インタラクションモード

`Segmented` トグルで2つのモードを明示的に切り替える:

| モード | `interactionMode` | Plotly `dragmode` | 動作 |
|--------|-------------------|-------------------|------|
| 選択モード | `'select'` | `'select'` | ベースライン範囲選択（ドラッグ） + 除外点トグル（クリック） |
| 操作モード | `'operate'` | `'zoom'` | ズーム・パン操作 |

- デフォルト: `baselineStatus === 'configured'` → `'operate'`、`'unconfigured'` → `'select'`
- `baselineStatus` 変更時に自動切替（`useBaselineManager` 内の `useEffect`）
- ユーザーはいつでもトグルで手動切替可能

## ベースライン設定のライフサイクル

`'unconfigured'` ⇔ `'configured'` の2状態。「更新」は削除→再作成:

```
unconfigured → [範囲選択 + 感度調整 + 設定を保存] → configured
configured   → [設定をリセット]                    → unconfigured
```

- 保存: PUT `/api/models/{category_id}` → Isolation Forest学習 → 異常スコア取得
- 削除: DELETE `/api/models/{category_id}` → 異常検知結果カスケード削除

## 感度スライダーのリアルタイム反映

APIを叩かずにフロントエンドだけで完結する:

```
GET /api/results/{category_id} → anomaly_scores取得
  → Slider操作 → sensitivity値から閾値計算
  → 異常スコアサブチャートの動的閾値ラインが移動（layout.shapes更新）
  → サブチャートのポイント色が閾値で切り替わる（useMemo → React.memo で差分レンダリング）
```

※ メイン散布図のポイント色分け（anomaly→赤）は廃止済み。異常の可視化はサブチャートで行う（ADR: analysis_ui_redesign.md 決定2）。

## レイアウト

- **ヘッダー**: 固定上部。ナビゲーションMenu（ダッシュボード / プロット / チュートリアル切替）
- **サイドバー**: プロットビュー時のみ表示。折りたたみ可能。**ドラッグでリサイズ可能**（200px〜500px、デフォルト280px）
- **独立スクロール**: サイドバーとメインコンテンツは個別にスクロール（`overflow-y: auto` + `height: calc(100vh - 64px)`）
- **ビュー切替**: 条件付きレンダリング（`currentView` に応じて `<Dashboard />` / `<PlotView />` / `<TutorialPage />` を表示）

## メモ化の規約

全コンポーネントに `React.memo` を適用済み。新規コンポーネントも必ず適用する:

```jsx
// 全コンポーネント共通パターン
function MyComponent({ prop1, prop2 }) { ... }
export default React.memo(MyComponent);
```

- **inline style**: モジュールレベル定数に抽出（`const STYLE_XXX = { ... };`）
- **イベントハンドラ**: `useCallback` でラップ
- **算出値**: `useMemo` でメモ化（特にPlotlyの `traces`, `layout`, `shapes`）
- **配列/オブジェクトのprops**: 毎レンダリングで新規参照を生成しないこと

## Plotly.jsのインタラクション詳細

[references/interactive-plots.md](references/interactive-plots.md) を参照。

## ダッシュボードのデータ取得パターン（SSE + バッチAPI）

Dashboard はバッチAPI + SSE（Server-Sent Events）でデータを取得・更新する。個別カテゴリごとのフェッチは行わない:

### バッチAPI

`GET /api/dashboard/summary` で全リーフカテゴリのサマリーを1リクエストで一括取得:

```javascript
import { fetchDashboardSummary } from '../services/api';

const loadDashboardData = useCallback(async () => {
  const summaries = await fetchDashboardSummary();
  setDashboardData(summaries.map((s) => ({
    key: s.category_id,
    categoryId: s.category_id,
    categoryPath: s.category_path,
    // trend はダッシュボードから廃止（ADR: analysis_ui_redesign.md 決定1）
    anomalyCount: s.anomaly_count,
    baselineStatus: s.baseline_status,
  })));
}, []);
```

### SSE 接続（EventSource）

`GET /api/events` に `EventSource` で接続し、バックエンドのデータ変更をリアルタイム検知:

```javascript
const SSE_DEBOUNCE_MS = 2000;

useEffect(() => {
  const es = new EventSource('/api/events');
  let debounceTimer = null;

  const handleUpdate = () => {
    if (active) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => loadDashboardData(), SSE_DEBOUNCE_MS);
    } else {
      staleRef.current = true;
    }
  };

  es.addEventListener('dashboard-updated', handleUpdate);
  return () => {
    clearTimeout(debounceTimer);
    es.removeEventListener('dashboard-updated', handleUpdate);
    es.close();
  };
}, [active, loadDashboardData]);
```

### staleRef パターン

Dashboard が非アクティブ（プロットビュー表示中）に SSE イベントを受信した場合、`staleRef.current = true` を設定。`active` に復帰した時点で再取得する:

```javascript
const staleRef = useRef(false);

useEffect(() => {
  if (!active) return;
  if (dashboardData.length === 0 || staleRef.current) {
    if (categories && categories.length > 0) loadDashboardData();
  }
}, [active, categories, loadDashboardData, dashboardData.length]);
```

### 注意事項

- `flattenLeafCategories` は Dashboard では使用しない（バッチAPI がサーバー側でパス文字列を組み立てる）
- `updateSingleRow` はダッシュボード上のインライン削除用に維持（削除した行のみ差分更新）
- デバウンス（2秒）はデータ連続投入時の SSE イベント連打を集約するため

## 開発コマンド

```bash
cd frontend
npm install
npm start      # http://localhost:3000（APIはproxy経由でlocalhost:8000）
npm run build  # 本番ビルド → build/
```
