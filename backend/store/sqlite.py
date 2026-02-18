"""Store層のSQLite実装。"""

import sqlite3
from datetime import datetime

from backend.interfaces.data_store import (
    CategoryNode,
    DataStoreInterface,
    WorkRecord,
)

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

# datetime adapter/converter をモジュールレベルで一度だけ登録
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter(
    "TIMESTAMP", lambda b: datetime.fromisoformat(b.decode())
)


class SqliteDataStore(DataStoreInterface):
    """SQLiteによるStore層実装。"""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def upsert_records(self, records: list[WorkRecord]) -> int:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO work_records (category_id, work_time, recorded_at)
                VALUES (?, ?, ?)
                ON CONFLICT(category_id, recorded_at)
                DO UPDATE SET work_time = excluded.work_time
                """,
                [(r.category_id, r.work_time, r.recorded_at) for r in records],
            )
        return len(records)

    def ensure_category_path(self, path: list[str]) -> int:
        if not path:
            raise ValueError("path must not be empty")
        parent_id = None
        with self._conn:
            for name in path:
                row = self._conn.execute(
                    "SELECT id FROM categories"
                    " WHERE name = ? AND parent_id IS ?",
                    (name, parent_id),
                ).fetchone()
                if row:
                    parent_id = row[0]
                else:
                    cursor = self._conn.execute(
                        "INSERT INTO categories"
                        " (name, parent_id) VALUES (?, ?)",
                        (name, parent_id),
                    )
                    parent_id = cursor.lastrowid
        return parent_id

    def get_records(
        self,
        category_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[WorkRecord]:
        query = (
            "SELECT category_id, work_time, recorded_at"
            " FROM work_records WHERE category_id = ?"
        )
        params: list = [category_id]
        if start is not None:
            query += " AND recorded_at >= ?"
            params.append(start)
        if end is not None:
            query += " AND recorded_at <= ?"
            params.append(end)
        query += " ORDER BY recorded_at ASC"

        rows = self._conn.execute(query, params).fetchall()
        return [
            WorkRecord(category_id=r[0], work_time=r[1], recorded_at=r[2])
            for r in rows
        ]

    def get_category_tree(
        self, root_id: int | None = None
    ) -> list[CategoryNode]:
        if root_id is None:
            seed_where = "WHERE parent_id IS NULL"
            params: tuple = ()
        else:
            seed_where = "WHERE id = ?"
            params = (root_id,)

        rows = self._conn.execute(
            f"""
            WITH RECURSIVE tree AS (
                SELECT id, name, parent_id FROM categories {seed_where}
                UNION ALL
                SELECT c.id, c.name, c.parent_id
                FROM categories c JOIN tree t ON c.parent_id = t.id
            )
            SELECT id, name, parent_id FROM tree
            """,
            params,
        ).fetchall()

        # children_map で O(n) ツリー構築
        node_data: dict[int, tuple[int, str, int | None]] = {}
        children_map: dict[int | None, list[int]] = {}
        for node_id, name, parent_id in rows:
            node_data[node_id] = (node_id, name, parent_id)
            children_map.setdefault(parent_id, []).append(node_id)

        def build_node(node_id: int) -> CategoryNode:
            nid, name, pid = node_data[node_id]
            children = [
                build_node(cid) for cid in children_map.get(node_id, [])
            ]
            return CategoryNode(
                id=nid, name=name, parent_id=pid, children=children
            )

        if root_id is not None:
            return [build_node(root_id)] if root_id in node_data else []
        return [build_node(nid) for nid in children_map.get(None, [])]

    def delete_all_data(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM work_records")
            self._conn.execute("DELETE FROM categories")
