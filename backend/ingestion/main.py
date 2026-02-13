"""FastAPIアプリケーション。

取り込みAPI + データ提供API + 分析結果APIを統合。
"""

from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from backend.dependencies import get_data_store
from backend.interfaces.data_store import CategoryNode, DataStoreInterface, WorkRecord

StoreDep = Annotated[DataStoreInterface, Depends(get_data_store)]

app = FastAPI(
    title="設備劣化検知システム API",
    version="0.1.0",
)


# ---------- Pydantic モデル ----------


class RecordItem(BaseModel):
    """取り込みリクエスト内の1レコード。"""

    category_path: list[str]
    work_time: float
    recorded_at: datetime


class RecordsBatchRequest(BaseModel):
    """POST /api/records のリクエストボディ。"""

    records: list[RecordItem]


class RecordResponse(BaseModel):
    """1件の作業記録レスポンス。"""

    category_id: int
    work_time: float
    recorded_at: datetime


class CategoryNodeResponse(BaseModel):
    """カテゴリノードのレスポンス（再帰構造）。"""

    id: int
    name: str
    parent_id: int | None
    children: list["CategoryNodeResponse"]


# ---------- ヘルパー ----------


def _to_category_node_response(node: CategoryNode) -> CategoryNodeResponse:
    """CategoryNode → CategoryNodeResponse の再帰変換。"""
    return CategoryNodeResponse(
        id=node.id,
        name=node.name,
        parent_id=node.parent_id,
        children=[_to_category_node_response(c) for c in node.children],
    )


# ---------- エンドポイント ----------


@app.get("/api/health")
async def health_check():
    """ヘルスチェック。"""
    return {"status": "ok"}


@app.post("/api/records")
async def post_records(
    body: RecordsBatchRequest,
    store: StoreDep,
):
    """作業記録をバッチ投入する。"""
    work_records: list[WorkRecord] = []
    for item in body.records:
        category_id = store.ensure_category_path(item.category_path)
        work_records.append(
            WorkRecord(
                category_id=category_id,
                work_time=item.work_time,
                recorded_at=item.recorded_at,
            )
        )
    inserted = store.upsert_records(work_records)
    return {"inserted": inserted}


@app.get("/api/records")
async def get_records(
    category_id: int,
    store: StoreDep,
    start: datetime | None = None,
    end: datetime | None = None,
):
    """指定カテゴリの作業記録を取得する。"""
    records = store.get_records(category_id, start=start, end=end)
    return {
        "records": [
            RecordResponse(
                category_id=r.category_id,
                work_time=r.work_time,
                recorded_at=r.recorded_at,
            )
            for r in records
        ]
    }


@app.get("/api/categories")
async def get_categories(
    store: StoreDep,
    root: int | None = None,
):
    """分類ツリーを取得する。"""
    nodes = store.get_category_tree(root_id=root)
    return {"categories": [_to_category_node_response(n) for n in nodes]}


# TODO: Step 2 で実装
# - GET  /api/results/{category_id}  (分析結果API)
# - GET  /api/models/{category_id}   (モデル定義取得)
# - PUT  /api/models/{category_id}   (モデル定義更新)

# TODO: Step 3 / 開発用
# - POST /api/analysis/run  (手動トリガー)
