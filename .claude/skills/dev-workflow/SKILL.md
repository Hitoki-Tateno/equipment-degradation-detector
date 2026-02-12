---
name: dev-workflow
description: 開発ワークフロー、ブランチ戦略、git worktree運用、Issue管理の手順。ブランチ作成、Issue操作、PR作成、worktree操作、並行開発、カンバン運用に関するタスクで発動する。「ブランチ」「PR」「Issue」「worktree」「マージ」「レビュー」「カンバン」「開発フロー」に関するタスクで発動する。
---

# 開発ワークフロー

## ブランチ戦略: GitHub Flow

- `main` と `feature/*` ブランチのみ
- `main` は常にデプロイ可能な状態を維持
- 全ての変更は feature ブランチからPRを経由して `main` にマージ

## git worktree による並行開発

複数のタスクを同一ワークスペースで並行作業するため **git worktree** を使用する:

```bash
# worktree作成（新規featureブランチ）
git worktree add ../worktrees/issue-42-store-impl -b feature/issue-42-store-impl

# worktree一覧
git worktree list

# マージ後に削除
git worktree remove ../worktrees/issue-42-store-impl
```

### worktree配置ルール

```
projects/
├── equipment-detector/                # main（ベースリポジトリ）
└── worktrees/
    ├── issue-42-store-impl/           # feature/issue-42-store-impl
    ├── issue-43-api-endpoints/        # feature/issue-43-api-endpoints
    └── issue-44-react-base/           # feature/issue-44-react-base
```

- 配置先: ベースリポジトリの隣に `worktrees/` ディレクトリを作成
- ディレクトリ名: `issue-{番号}-{簡潔な説明}`
- 各worktree初回に `uv sync` と `cd frontend && npm install` を実行
- マージ後は速やかに `git worktree remove` で削除

## Issue駆動開発（カンバン）

GitHub IssueをKanbanボードとして使用する。

### ラベル体系

ステータス:

| ラベル | 意味 | 色 |
|--------|------|----|
| `status:todo` | 未着手 | 黄 |
| `status:in-progress` | 作業中 | 青 |
| `status:in-review` | レビュー待ち | 紫 |
| `status:done` | 完了 | 緑 |

カテゴリ:

| ラベル | 対象 |
|--------|------|
| `layer:store` | Store層・結果ストア |
| `layer:api` | FastAPI |
| `layer:analysis` | 分析層 |
| `layer:frontend` | フロントエンド |
| `layer:infra` | CI/CD・コンテナ・デプロイ |

### Issueの粒度

1 Issue = 1 PR = **1〜3日**で完了する単位。

## 1タスクの開発フロー（要約）

1. `gh issue list --label "status:todo"` でIssueを取る
2. ラベルを `status:in-progress` に変更
3. worktree + feature ブランチを作成
4. TDD対象ならテストを先に書く（Red → Green → Refactor）
5. PR作成（本文に `Closes #番号`）→ CI自動実行
6. ラベルを `status:in-review` に変更
7. レビュー → マージ（squash）→ worktree削除
8. Issueが自動クローズ

詳細: [references/task-flow.md](references/task-flow.md)

## gh CLIコマンド

ラベルの初期セットアップ、Issue/PR操作の具体的なコマンド: [references/gh-commands.md](references/gh-commands.md)

## CI/CD

| タイミング | 実行内容 |
|---|---|
| PR時（マージ前） | `uv run ruff check` + `uv run pytest` |
| mainマージ後 | フロントエンドビルド + コンテナイメージビルド |
| デプロイ | 手動（`oc apply -k k8s/`） |
