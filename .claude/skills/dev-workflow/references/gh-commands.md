# gh CLI コマンドリファレンス

## 初期認証

```bash
gh auth login
```

## リポジトリ操作

```bash
# リモートリポジトリの作成・接続
gh repo create {org/repo-name} --private --source=. --push

# 既存リポジトリのクローン
gh repo clone {org/repo-name}
```

## ラベル初期セットアップ

プロジェクト初回に実行:

```bash
# ステータスラベル
gh label create "status:todo" --color "E4E669" --description "未着手"
gh label create "status:in-progress" --color "0075CA" --description "作業中"
gh label create "status:in-review" --color "D876E3" --description "レビュー待ち"
gh label create "status:done" --color "0E8A16" --description "完了"

# カテゴリラベル
gh label create "layer:store" --color "BFDADC" --description "Store層・結果ストア"
gh label create "layer:api" --color "F9D0C4" --description "FastAPI"
gh label create "layer:analysis" --color "C5DEF5" --description "分析層"
gh label create "layer:frontend" --color "FEF2C0" --description "フロントエンド"
gh label create "layer:infra" --color "E6E6E6" --description "CI/CD・コンテナ・デプロイ"
```

## Issue操作

```bash
# Issue一覧（ラベルフィルタ）
gh issue list --label "status:todo"
gh issue list --label "layer:store"

# Issue作成
gh issue create --title "Store層: SqliteDataStore実装" \
  --body "契約テストをパスするSQLite実装を作成する" \
  --label "status:todo,layer:store"

# アサイン + ステータス変更
gh issue edit <番号> --add-assignee @me
gh issue edit <番号> --remove-label "status:todo" --add-label "status:in-progress"
```

## PR操作

```bash
# PR作成（Issueと紐付け）
gh pr create \
  --title "feat(store): SQLite DataStore実装" \
  --body "Closes #<番号>" \
  --base main

# PR一覧
gh pr list

# CIステータス確認
gh pr checks

# マージ（squash + ブランチ削除）
gh pr merge --squash --delete-branch
```

## worktreeとの組み合わせ例

```bash
# 1. Issueを確認・アサイン
gh issue list --label "status:todo"
gh issue edit 42 --add-assignee @me
gh issue edit 42 --remove-label "status:todo" --add-label "status:in-progress"

# 2. worktree作成
git worktree add ../worktrees/issue-42-store-impl -b feature/issue-42-store-impl
cd ../worktrees/issue-42-store-impl
uv sync

# 3. 実装 → PR作成
gh pr create --title "feat(store): SQLite DataStore実装" --body "Closes #42"
gh issue edit 42 --remove-label "status:in-progress" --add-label "status:in-review"

# 4. マージ後にworktree削除
gh pr merge --squash --delete-branch
cd <ベースリポジトリ>
git worktree remove ../worktrees/issue-42-store-impl
git pull origin main
```
