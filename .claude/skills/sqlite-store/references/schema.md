# SQLiteスキーマ定義

## Store層 (`data/store.db`)

```sql
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
```

### upsert文

```sql
INSERT INTO work_records (category_id, work_time, recorded_at)
VALUES (?, ?, ?)
ON CONFLICT(category_id, recorded_at)
DO UPDATE SET work_time = excluded.work_time;
```

## 結果ストア (`data/result_store.db`)

```sql
CREATE TABLE IF NOT EXISTS trend_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id  INTEGER NOT NULL UNIQUE,
    slope        REAL NOT NULL,
    intercept    REAL NOT NULL,
    is_warning   BOOLEAN NOT NULL
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
```

### anomaly_resultsのupsert文

```sql
INSERT INTO anomaly_results (category_id, recorded_at, anomaly_score)
VALUES (?, ?, ?)
ON CONFLICT(category_id, recorded_at)
DO UPDATE SET anomaly_score = excluded.anomaly_score;
```

### model_definitionsのupsert文

```sql
INSERT INTO model_definitions (category_id, baseline_start, baseline_end, sensitivity, excluded_points)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(category_id)
DO UPDATE SET
    baseline_start = excluded.baseline_start,
    baseline_end = excluded.baseline_end,
    sensitivity = excluded.sensitivity,
    excluded_points = excluded.excluded_points;
```
