---
name: fastapi-api
description: FastAPIによるAPIエンドポイント実装。取り込みAPI、データ提供API、分析結果API、モデル定義API、手動トリガーAPIの実装時に使用する。「API」「エンドポイント」「FastAPI」「ルーティング」「リクエスト」「レスポンス」に関するタスクで発動する。
---

# FastAPI エンドポイント実装

## 概要

`backend/ingestion/main.py` にFastAPIアプリケーションを構築する。取り込みAPIとデータ提供APIを同一アプリに統合する。

## 依存性注入パターン

Store層と結果ストアの実装はFastAPIのDependency Injectionで注入する。エンドポイントのコードから直接importしない:

```python
from backend.interfaces.data_store import DataStoreInterface

def get_data_store() -> DataStoreInterface:
    from backend.store.sqlite import SqliteDataStore
    return SqliteDataStore("data/store.db")

@app.post("/api/records")
async def create_records(
    body: RecordsBatchRequest,
    store: DataStoreInterface = Depends(get_data_store),
):
    ...
```

`get_data_store` と `get_result_store` のみが実装クラスを知る。エンドポイント関数はインターフェースにのみ依存する。

## Pydanticモデル

リクエスト/レスポンスはPydanticモデルで型定義する:

```python
from pydantic import BaseModel
from datetime import datetime

class RecordItem(BaseModel):
    category_path: list[str]
    work_time: float
    recorded_at: datetime

class RecordsBatchRequest(BaseModel):
    records: list[RecordItem]
```

## エンドポイント仕様

[references/endpoints.md](references/endpoints.md) に全エンドポイントの詳細仕様を記載。

## 取り込み時同期分析

POST /api/records および POST /api/records/csv の処理末尾で、対象カテゴリの分析を**同期的に**実行する:

```python
# POST /api/records の末尾
engine = get_analysis_engine()
for category_id in affected_category_ids:
    engine.run(category_id)
```

## モデルのライフサイクル

モデルは「未定義」と「定義済み」の2状態のみ。「更新」は存在しない（削除→再作成で対応）。

- **PUT /api/models/{category_id}**: モデルを新規作成（既存があれば上書き）。IsolationForestの学習を実行
- **DELETE /api/models/{category_id}**: モデルを削除。異常検知結果もカスケード削除
- **GET /api/models/{category_id}**: モデル定義を取得。未定義なら404

## 注意事項

- `category_path` で指定された分類がツリーに存在しなければ `ensure_category_path` で自動作成
- ヘルスチェック `GET /api/health` は実装済み
