"""結果ストアのSQLite実装。"""

import json
import sqlite3
from datetime import datetime

from backend.interfaces.result_store import (
    AnomalyResult,
    ModelDefinition,
    ResultStoreInterface,
    TrendResult,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trend_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id  INTEGER NOT NULL UNIQUE,
    slope        REAL NOT NULL,
    intercept    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS anomaly_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER NOT NULL,
    recorded_at   TIMESTAMP NOT NULL,
    anomaly_score REAL NOT NULL,
    UNIQUE(category_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_anomaly_results_category
    ON anomaly_results(category_id);

CREATE TABLE IF NOT EXISTS model_definitions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NOT NULL UNIQUE,
    baseline_start  TIMESTAMP NOT NULL,
    baseline_end    TIMESTAMP NOT NULL,
    sensitivity     REAL NOT NULL,
    excluded_points TEXT DEFAULT '[]'
);
"""

# offset-naive に統一: TZ付きdatetimeが入っても壁時計時刻を保持しTZを除去
sqlite3.register_adapter(
    datetime, lambda dt: dt.replace(tzinfo=None).isoformat()
)
sqlite3.register_converter(
    "TIMESTAMP",
    lambda b: datetime.fromisoformat(b.decode()).replace(tzinfo=None),
)


class SqliteResultStore(ResultStoreInterface):
    """SQLiteによる結果ストア実装。"""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """既存DBのスキーマをマイグレーションする。"""
        # v1→v2: trend_results から is_warning 列を削除
        cols = [
            row[1]
            for row in self._conn.execute("PRAGMA table_info(trend_results)")
        ]
        if "is_warning" in cols:
            self._conn.executescript("""
                CREATE TABLE trend_results_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL UNIQUE,
                    slope       REAL NOT NULL,
                    intercept   REAL NOT NULL
                );
                INSERT INTO trend_results_new
                    (id, category_id, slope, intercept)
                    SELECT id, category_id, slope, intercept
                    FROM trend_results;
                DROP TABLE trend_results;
                ALTER TABLE trend_results_new RENAME TO trend_results;
            """)
            self._conn.commit()

    def save_trend_result(self, result: TrendResult) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO trend_results
                    (category_id, slope, intercept)
                VALUES (?, ?, ?)
                ON CONFLICT(category_id)
                DO UPDATE SET slope = excluded.slope,
                              intercept = excluded.intercept
                """,
                (
                    result.category_id,
                    result.slope,
                    result.intercept,
                ),
            )

    def get_trend_result(self, category_id: int) -> TrendResult | None:
        row = self._conn.execute(
            "SELECT category_id, slope, intercept"
            " FROM trend_results WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        return TrendResult(
            category_id=row[0],
            slope=row[1],
            intercept=row[2],
        )

    def save_anomaly_results(self, results: list[AnomalyResult]) -> None:
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO anomaly_results
                    (category_id, recorded_at, anomaly_score)
                VALUES (?, ?, ?)
                ON CONFLICT(category_id, recorded_at)
                DO UPDATE SET anomaly_score = excluded.anomaly_score
                """,
                [
                    (r.category_id, r.recorded_at, r.anomaly_score)
                    for r in results
                ],
            )

    def get_anomaly_results(self, category_id: int) -> list[AnomalyResult]:
        rows = self._conn.execute(
            "SELECT category_id, recorded_at, anomaly_score"
            " FROM anomaly_results WHERE category_id = ?",
            (category_id,),
        ).fetchall()
        return [
            AnomalyResult(
                category_id=r[0], recorded_at=r[1], anomaly_score=r[2]
            )
            for r in rows
        ]

    def save_model_definition(self, definition: ModelDefinition) -> None:
        excluded_json = json.dumps(
            [
                dt.replace(tzinfo=None).isoformat()
                for dt in definition.excluded_points
            ]
        )
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO model_definitions
                    (category_id, baseline_start, baseline_end,
                     sensitivity, excluded_points)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(category_id)
                DO UPDATE SET baseline_start = excluded.baseline_start,
                              baseline_end = excluded.baseline_end,
                              sensitivity = excluded.sensitivity,
                              excluded_points = excluded.excluded_points
                """,
                (
                    definition.category_id,
                    definition.baseline_start,
                    definition.baseline_end,
                    definition.sensitivity,
                    excluded_json,
                ),
            )

    def get_model_definition(self, category_id: int) -> ModelDefinition | None:
        row = self._conn.execute(
            "SELECT category_id, baseline_start,"
            " baseline_end, sensitivity, excluded_points"
            " FROM model_definitions WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        excluded = [
            datetime.fromisoformat(s).replace(tzinfo=None)
            for s in json.loads(row[4])
        ]
        return ModelDefinition(
            category_id=row[0],
            baseline_start=row[1],
            baseline_end=row[2],
            sensitivity=row[3],
            excluded_points=excluded,
        )

    def delete_model_definition(self, category_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM model_definitions WHERE category_id = ?",
                (category_id,),
            )

    def delete_anomaly_results(self, category_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM anomaly_results WHERE category_id = ?",
                (category_id,),
            )

    def delete_all_data(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM anomaly_results")
            self._conn.execute("DELETE FROM trend_results")
            self._conn.execute("DELETE FROM model_definitions")
