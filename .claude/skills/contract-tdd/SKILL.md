---
name: contract-tdd
description: 層間インターフェースの契約テスト実装とTDDワークフロー。Store層やResult Storeの抽象クラス（ABC）に対するテストの作成・実行、およびそれに準拠した実装の開発時に使用する。「契約テスト」「TDD」「インターフェース実装」「ABCの実装」に関するタスクで発動する。
---

# 契約テストTDDワークフロー

## 概要

このプロジェクトでは、層間インターフェース（`backend/interfaces/`）の契約テストと分析層ロジックにTDDを適用する。

## TDDサイクル

1. **Red** — テストを先に書く。テストは失敗する状態
2. **Green** — テストを通す最小限の実装を書く
3. **Refactor** — コードを整理する。テストは通ったまま

## 契約テストの構造

契約テストは `tests/unit/test_data_store_contract.py` と `tests/unit/test_result_store_contract.py` に定義済み。

### 実装をテストに接続する方法

各契約テストにはfixtureがある。実装完了後、`pytest.skip()` を実装インスタンスの生成に置き換える:

```python
# Before (Red phase)
@pytest.fixture
def data_store():
    pytest.skip("Store層の実装が未完成")

# After (Green phase)
@pytest.fixture
def data_store(tmp_path):
    from backend.store.sqlite import SqliteDataStore
    db_path = tmp_path / "test.db"
    return SqliteDataStore(str(db_path))
```

### 新しい契約テストを追加する場合

1. インターフェースの抽象メソッドを `backend/interfaces/` に追加
2. 対応するテストケースを `tests/unit/test_*_contract.py` に追加（Red）
3. 実装を更新してテストをパスさせる（Green）
4. リファクタリング（Refactor）

## インターフェースの詳細

- DataStoreInterface の仕様: [references/data-store-contract.md](references/data-store-contract.md) を参照
- ResultStoreInterface の仕様: [references/result-store-contract.md](references/result-store-contract.md) を参照

## 注意事項

- テスト実行: `uv run pytest tests/unit/test_data_store_contract.py -v`
- 契約テストは実装技術（SQLite等）に依存しない。PostgreSQL等に移行しても同じテストがパスすること
- fixtureで `tmp_path` を使い、テスト間でDBファイルを共有しない
