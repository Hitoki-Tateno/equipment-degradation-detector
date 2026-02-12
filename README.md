# 設備劣化検知システム

設備の作業時間の伸びから劣化や異常を事前に検知し、ユーザーが兆候を確認できるシステム。

## 開発環境セットアップ

### Dev Container（推奨）

VS Code + Dev Containers拡張でワンクリック起動。プロキシ設定はホストの環境変数から自動引き継ぎ。

```bash
# ホスト側でプロキシ環境変数が設定されていれば自動的にコンテナに渡される
# HTTP_PROXY, HTTPS_PROXY, NO_PROXY
```

VS Codeで「Reopen in Container」を選択すれば、uv, Node.js, ruff等が全てプリインストール済みの環境が起動する。

### 手動セットアップ

```bash
# uv インストール（未導入の場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存インストール
uv sync

# テスト実行
uv run pytest

# リント
uv run ruff check backend/ tests/
uv run ruff format backend/ tests/

# API起動（開発用）
uv run uvicorn backend.ingestion.main:app --reload --port 8000
```

### フロントエンド開発

```bash
cd frontend
npm install
npm start    # http://localhost:3000 で起動。APIは localhost:8000 にプロキシ
```

## コンテナビルド・デプロイ

### ローカルビルド

```bash
podman build -t equipment-degradation-detector .
podman run -p 80:80 -p 8000:8000 -v ./data:/app/data equipment-degradation-detector
```

### OpenShift デプロイ

```bash
# 全リソースを一括適用
oc apply -k k8s/

# または個別適用
oc apply -f k8s/namespace.yaml
oc apply -f k8s/imagestream.yaml
oc apply -f k8s/buildconfig.yaml
oc apply -f k8s/pvc.yaml
oc apply -f k8s/deployment.yaml
oc apply -f k8s/service.yaml
oc apply -f k8s/route.yaml

# ビルド実行
oc start-build equipment-detector-build -n equipment-detector
```

## ディレクトリ構成

```
.devcontainer/        # Dev Container設定（Docker, プロキシ対応）
backend/
  interfaces/         # 抽象クラス（ABC）— 全層の契約
  ingestion/          # 取り込みAPI + データ提供API（FastAPI）
  store/              # Store層の実装（SQLite）
  analysis/           # 分析層（scikit-learn）
  result_store/       # 結果ストアの実装（SQLite）
  scheduler/          # 定期実行 + 手動トリガー
frontend/             # React + Plotly.js
tests/
  unit/               # ユニットテスト（契約テスト含む）
  integration/        # 統合テスト
k8s/                  # OpenShift / Kubernetes マニフェスト
```

## アーキテクチャ概要

詳細は [CLAUDE.md](./CLAUDE.md) を参照。

- **コアモノリス + 境界分離の混合型**
- 全ての層は `backend/interfaces/` の抽象クラスにのみ依存
- Store層・結果ストアは独立したSQLiteファイル
- 1コンテナ（Podman + supervisord）
- OpenShift（Kubernetes）にデプロイ

## 開発ロードマップ

| Step | 内容 |
|------|------|
| 1 | データ可視化（プロット表示） |
| 2 | 異常検知モデル定義（Isolation Forest + 回帰分析） |
| 3 | 継続監視（スケジューラー + ダッシュボード） |
