"""Store層のSQLite実装。

DataStoreInterfaceに準拠したSQLite実装を提供する。
"""

import sqlite3
from datetime import datetime

from backend.interfaces.data_store import CategoryNode, DataStoreInterface, WorkRecord

# スキーマ定義
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    parent_id   INTEGER REFERENCES categories(id),
    UNIQUE(name, parent_id)
);

CREATE TABLE IF NOT EXISTS work_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    work_time   REAL NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    UNIQUE(category_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_work_records_category_time
    ON work_records(category_id, recorded_at);
"""


class SqliteDataStore(DataStoreInterface):
    """SQLiteによるStore層実装。"""

    def __init__(self, db_path: str):
        """初期化。

        Args:
            db_path: SQLiteデータベースファイルのパス
        """
        self._db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """スキーマを初期化する。"""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """データベース接続を取得する。

        Returns:
            sqlite3.Connection
        """
        conn = sqlite3.connect(
            self._db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.execute("PRAGMA foreign_keys = ON")
        # datetimeをISO形式でシリアライズ
        sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
        sqlite3.register_converter("TIMESTAMP", lambda b: datetime.fromisoformat(b.decode()))
        return conn

    def upsert_records(self, records: list[WorkRecord]) -> int:
        """作業記録をバッチ投入する。

        Args:
            records: 投入するレコードのリスト

        Returns:
            投入されたレコード数
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            for record in records:
                cursor.execute(
                    """
                    INSERT INTO work_records (category_id, work_time, recorded_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(category_id, recorded_at)
                    DO UPDATE SET work_time = excluded.work_time
                    """,
                    (record.category_id, record.work_time, record.recorded_at),
                )
            conn.commit()
            return len(records)

    def ensure_category_path(self, path: list[str]) -> int:
        """分類パスに対応するカテゴリを取得または作成する。

        Args:
            path: 分類パス（例: ["プロセスA", "設備1"]）

        Returns:
            末端ノードのcategory_id
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            parent_id = None

            for name in path:
                # 既存のカテゴリを検索
                cursor.execute(
                    "SELECT id FROM categories WHERE name = ? AND parent_id IS ?",
                    (name, parent_id),
                )
                row = cursor.fetchone()

                if row:
                    # 既存カテゴリを使用
                    parent_id = row[0]
                else:
                    # 新規カテゴリを作成
                    cursor.execute(
                        "INSERT INTO categories (name, parent_id) VALUES (?, ?)",
                        (name, parent_id),
                    )
                    parent_id = cursor.lastrowid

            conn.commit()
            return parent_id

    def get_records(
        self,
        category_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[WorkRecord]:
        """指定分類の作業記録を取得する。

        Args:
            category_id: 分類ID
            start: 期間開始（省略時は全期間）
            end: 期間終了（省略時は全期間）

        Returns:
            作業記録のリスト（recorded_at昇順）
        """
        with self._connect() as conn:
            cursor = conn.cursor()

            # 期間フィルタリングのクエリ構築
            query = """
                SELECT category_id, work_time, recorded_at
                FROM work_records
                WHERE category_id = ?
            """
            params = [category_id]

            if start is not None:
                query += " AND recorded_at >= ?"
                params.append(start)

            if end is not None:
                query += " AND recorded_at <= ?"
                params.append(end)

            query += " ORDER BY recorded_at ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                WorkRecord(category_id=row[0], work_time=row[1], recorded_at=row[2]) for row in rows
            ]

    def get_category_tree(self, root_id: int | None = None) -> list[CategoryNode]:
        """分類ツリーを取得する。

        Args:
            root_id: ルートノードID（省略時はツリー全体）

        Returns:
            分類ノードのリスト
        """
        with self._connect() as conn:
            cursor = conn.cursor()

            # 再帰CTEでツリー全体を取得
            if root_id is None:
                cursor.execute(
                    """
                    WITH RECURSIVE tree AS (
                        SELECT id, name, parent_id
                        FROM categories
                        WHERE parent_id IS NULL
                        UNION ALL
                        SELECT c.id, c.name, c.parent_id
                        FROM categories c
                        JOIN tree t ON c.parent_id = t.id
                    )
                    SELECT id, name, parent_id FROM tree
                    """
                )
            else:
                cursor.execute(
                    """
                    WITH RECURSIVE tree AS (
                        SELECT id, name, parent_id
                        FROM categories
                        WHERE id = ?
                        UNION ALL
                        SELECT c.id, c.name, c.parent_id
                        FROM categories c
                        JOIN tree t ON c.parent_id = t.id
                    )
                    SELECT id, name, parent_id FROM tree
                    """,
                    (root_id,),
                )

            rows = cursor.fetchall()

            # ノードデータを格納
            node_data = {}
            for row in rows:
                node_id, name, parent_id = row
                node_data[node_id] = {"id": node_id, "name": name, "parent_id": parent_id}

            # 再帰的にツリーを構築する関数
            def build_node(node_id: int) -> CategoryNode:
                data = node_data[node_id]
                # 子ノードを検索して再帰的に構築
                children = [
                    build_node(child_id)
                    for child_id, child_data in node_data.items()
                    if child_data["parent_id"] == node_id
                ]
                return CategoryNode(
                    id=data["id"],
                    name=data["name"],
                    parent_id=data["parent_id"],
                    children=children,
                )

            # ルートノードを構築
            root_nodes = []
            for node_id, data in node_data.items():
                if data["parent_id"] is None or (root_id is not None and node_id == root_id):
                    root_nodes.append(build_node(node_id))

            return root_nodes
