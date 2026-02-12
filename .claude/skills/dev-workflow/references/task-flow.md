# 1タスクの開発フロー（詳細）

## Step 1: Issueを取る

```bash
# 未着手のIssueを確認
gh issue list --label "status:todo"

# 作業開始: ステータス変更 + アサイン
gh issue edit <番号> --remove-label "status:todo" --add-label "status:in-progress"
gh issue edit <番号> --add-assignee @me
```

## Step 2: worktree + featureブランチを作成

```bash
# mainを最新に更新
cd <ベースリポジトリ>
git pull origin main

# worktree作成（ブランチも同時に作成）
git worktree add ../worktrees/issue-<番号>-<説明> -b feature/issue-<番号>-<説明>

# worktreeに移動して依存インストール
cd ../worktrees/issue-<番号>-<説明>
uv sync
cd frontend && npm install && cd ..
```

命名規則:
- ブランチ名: `feature/issue-<番号>-<簡潔な説明>`
- ディレクトリ名: `issue-<番号>-<簡潔な説明>`
- 例: `feature/issue-42-store-sqlite-impl` → `issue-42-store-sqlite-impl`

## Step 3: TDD（対象の場合のみ）

TDD適用対象:
- 層間インターフェースの契約テスト
- 分析層のロジック

```bash
# Red: テストを書く（失敗する）
uv run pytest tests/unit/test_data_store_contract.py -v
# → FAILED

# Green: テストを通す最小実装
uv run pytest tests/unit/test_data_store_contract.py -v
# → PASSED

# Refactor: コード整理（テストは通ったまま）
uv run pytest tests/unit/test_data_store_contract.py -v
# → PASSED
```

## Step 4: 実装 + 品質チェック

```bash
# リント
uv run ruff check backend/ tests/
uv run ruff format backend/ tests/

# テスト全実行
uv run pytest

# 依存方向違反チェック（テストに含まれるが念のため）
uv run pytest tests/unit/test_dependency_rules.py -v
```

## Step 5: コミット + PR作成

```bash
# コミット
git add .
git commit -m "feat(store): SQLite DataStore実装"

# プッシュ
git push -u origin feature/issue-<番号>-<説明>

# PR作成（Issue番号をリンク）
gh pr create \
  --title "feat(store): SQLite DataStore実装" \
  --body "Closes #<番号>" \
  --base main

# ステータス変更
gh issue edit <番号> --remove-label "status:in-progress" --add-label "status:in-review"
```

### コミットメッセージ規約

```
<type>(<scope>): <説明>

type:
  feat     新機能
  fix      バグ修正
  test     テスト追加・修正
  refactor リファクタリング
  docs     ドキュメント
  ci       CI設定
  chore    その他

scope:
  store, result-store, api, analysis, frontend, infra, test
```

## Step 6: レビュー + CI

PRを作成するとCIが自動実行される:

```bash
# PRの状態確認
gh pr status

# CIの結果確認
gh pr checks
```

## Step 7: マージ + 後始末

```bash
# マージ（レビュー承認後）
gh pr merge --squash --delete-branch

# ベースリポジトリに戻ってworktree削除
cd <ベースリポジトリ>
git worktree remove ../worktrees/issue-<番号>-<説明>

# mainを更新
git pull origin main

# Issueは "Closes #番号" により自動クローズ
```
