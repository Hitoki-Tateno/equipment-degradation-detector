---
name: sqlite-store
description: Store層と結果ストアのSQLite実装。DataStoreInterfaceおよびResultStoreInterfaceに準拠するSQLite実装クラスの作成時に使用する。「SQLite」「Store実装」「結果ストア実装」「DB」「スキーマ」「マイグレーション」に関するタスクで発動する。
---

# SQLite Store実装

## 概要

Store層（`backend/store/`）と結果ストア（`backend/result_store/`）はそれぞれ独立したSQLiteファイルで実装する。

- Store層: `data/store.db`
- 結果ストア: `data/result_store.db`

両方とも `backend/interfaces/` の抽象クラスに準拠する実装を提供する。

## 実装手順

1. `contract-tdd` スキルに従い、契約テストのfixtureを実装クラスに接続
2. 初回接続時にスキーマを自動作成（`CREATE TABLE IF NOT EXISTS`）
3. 契約テストを全てパスさせる

## 実装パターン

```python
import sqlite3
from backend.interfaces.data_store import DataStoreInterface, WorkRecord, CategoryNode

class SqliteDataStore(DataStoreInterface):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._init_schema()

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
```

## 分類ツリーの実装

隣接リスト方式。ツリー全体の取得にはSQLiteの再帰CTEを使用:

```sql
WITH RECURSIVE tree AS (
    SELECT id, name, parent_id FROM categories WHERE parent_id IS NULL
    UNION ALL
    SELECT c.id, c.name, c.parent_id FROM categories c JOIN tree t ON c.parent_id = t.id
)
SELECT * FROM tree;
```

## スキーマの詳細

[references/schema.md](references/schema.md) を参照。

## 注意事項

- `PRAGMA foreign_keys = ON` を接続ごとに設定する（SQLiteはデフォルトで外部キー制約が無効）
- upsert は `INSERT ... ON CONFLICT ... DO UPDATE` で実装
- `excluded_points` は `json.dumps()` / `json.loads()` でシリアライズ
- テストでは `tmp_path` を使い、テスト間でDBファイルを共有しない
