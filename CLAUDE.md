# CLAUDE.md

## プロジェクト概要

設備の作業時間の伸びから劣化・異常を事前検知するシステム。

## 依存ルール（絶対）

```
backend/interfaces/   ← 全ての層はここにのみ依存する
backend/store/        ← analysis/ や ingestion/ から直接import禁止
backend/result_store/ ← analysis/ や ingestion/ から直接import禁止
```

違反は `tests/unit/test_dependency_rules.py` で自動検出される。

## アーキテクチャ

```
[コンテナ外]                     [コンテナ内]

  RDB --> アダプター --> 取り込みAPI --> Store層(SQLite)
  CSV --> アダプター --/                  |     |
  JSON -> アダプター -/                分析層  | データ提供API
                                  |        |
                                  v        v
                              結果ストア --> データ提供API --> 表示層(React)
```

## ディレクトリ構成

```
backend/
  interfaces/       # 抽象クラス（ABC）— 全層の契約
  ingestion/        # FastAPI（取り込みAPI + データ提供API）
  store/            # Store層（SQLite実装）
  analysis/         # 分析層（scikit-learn）
  result_store/     # 結果ストア（SQLite実装）
  scheduler/        # 定期実行 + 手動トリガー
frontend/           # React + Plotly.js
tests/unit/         # ユニットテスト（契約テスト含む）
tests/integration/  # 統合テスト
k8s/                # OpenShift マニフェスト
.claude/skills/     # 各作業領域のスキル定義
```

## 技術スタック

Python(uv) / FastAPI / SQLite / scikit-learn / React / Plotly.js / Podman / OpenShift

## コマンド

```bash
uv sync                          # 依存インストール
uv run pytest                    # テスト
uv run ruff check backend/       # リント
uv run ruff format backend/      # フォーマット
uv run uvicorn backend.ingestion.main:app --reload  # API起動
```

## スキル一覧

各作業領域の詳細な手順・仕様は `.claude/skills/` に定義されている。

| スキル | 用途 |
|--------|------|
| dev-workflow | ブランチ戦略、git worktree、Issue管理、開発フロー |
| contract-tdd | 契約テストの実装とTDDワークフロー |
| sqlite-store | Store層・結果ストアのSQLite実装 |
| fastapi-api | APIエンドポイントの実装 |
| analysis-engine | 分析層（Isolation Forest + 回帰分析）の実装 |
| react-plotly | フロントエンド（React + Plotly.js + Ant Design）の実装 |
| k8s-deploy | OpenShiftへのデプロイ |
