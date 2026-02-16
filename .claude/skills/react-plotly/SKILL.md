---
name: react-plotly
description: React + Plotly.js + Ant Designによるフロントエンド実装。散布図プロット、分類ツリー表示、ベースライン範囲選択、除外点操作、感度スライダー、監視ダッシュボードの実装時に使用する。「フロントエンド」「React」「Plotly」「プロット」「グラフ」「ダッシュボード」「UI」「スライダー」「Ant Design」「antd」に関するタスクで発動する。
---

# React + Plotly.js + Ant Design フロントエンド実装

## 技術スタック

- **React 18** — UIフレームワーク
- **Plotly.js** (react-plotly.js) — インタラクティブプロット
- **Ant Design 5** — UIコンポーネント（Tree, Slider, Table, Layout等）

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

## コンポーネントとAnt Designの対応

| UI要素 | Ant Designコンポーネント |
|---|---|
| 分類ツリーのサイドバー | `Tree` / `DirectoryTree` |
| 感度スライダー | `Slider` |
| データ一覧 | `Table` |
| 画面レイアウト | `Layout` (`Sider`, `Content`) |
| 警告表示 | `Alert` / `Tag` |
| 読み込み中 | `Spin` |

## Step別の実装内容

### Step 1: データ可視化
- `Layout` + `Sider` でサイドバー付きレイアウト
- `Tree` で分類階層を表示（GET /api/categories）
- `react-plotly.js` で散布図: 横軸=回数n、縦軸=作業時間t

### Step 2: モデル定義GUI
- Plotly Box Selectでベースライン期間選択
- Plotly clickイベントで除外点トグル
- `Slider` で感度調整 → リアルタイム閾値変更
- モデル保存ボタン（PUT /api/models）
- モデル削除ボタン + `Modal.confirm` 確認ダイアログ（DELETE /api/models → カスケード削除）
- モデルのライフサイクル: 「未定義」⇔「定義済み」の2状態のみ。「更新」は削除→再作成で対応

### Step 3: 監視ダッシュボード
- `Table` でカテゴリ別のステータス一覧
- `Tag` / `Alert` でトレンド警告・異常表示

## 感度スライダーのリアルタイム反映

APIを叩かずにフロントエンドだけで完結する:

```
GET /api/results/{category_id} → anomaly_scores取得
  → Slider操作 → sensitivity値から閾値計算
  → 各点のanomaly_scoreと閾値比較
  → プロット色分け更新（React re-render）
```

## Plotly.jsのインタラクション詳細

[references/interactive-plots.md](references/interactive-plots.md) を参照。

## 開発コマンド

```bash
cd frontend
npm install
npm start      # http://localhost:3000（APIはproxy経由でlocalhost:8000）
npm run build  # 本番ビルド → build/
```
