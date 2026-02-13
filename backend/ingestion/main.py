"""FastAPIアプリケーション。

取り込みAPI + データ提供API + 分析結果APIを統合。
"""

from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_data_store, get_result_store
from backend.interfaces.data_store import CategoryNode, DataStoreInterface, WorkRecord
from backend.interfaces.result_store import ModelDefinition, ResultStoreInterface

StoreDep = Annotated[DataStoreInterface, Depends(get_data_store)]
ResultStoreDep = Annotated[ResultStoreInterface, Depends(get_result_store)]

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


class TrendResultResponse(BaseModel):
    """トレンド分析結果のレスポンス。"""

    slope: float
    intercept: float
    is_warning: bool


class AnomalyResultResponse(BaseModel):
    """異常スコア結果のレスポンス。"""

    recorded_at: datetime
    anomaly_score: float


class ModelDefinitionRequest(BaseModel):
    """モデル定義の更新リクエスト。"""

    baseline_start: datetime
    baseline_end: datetime
    sensitivity: float
    excluded_points: list[datetime] = []


class ModelDefinitionResponse(BaseModel):
    """モデル定義のレスポンス。"""

    category_id: int
    baseline_start: datetime
    baseline_end: datetime
    sensitivity: float
    excluded_points: list[datetime]


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


@app.get("/api/results/{category_id}")
async def get_results(
    category_id: int,
    result_store: ResultStoreDep,
):
    """分析結果を取得する。未計算なら null を返す。"""
    trend = result_store.get_trend_result(category_id)
    anomalies = result_store.get_anomaly_results(category_id)
    return {
        "trend": TrendResultResponse(
            slope=trend.slope,
            intercept=trend.intercept,
            is_warning=trend.is_warning,
        )
        if trend
        else None,
        "anomalies": [
            AnomalyResultResponse(
                recorded_at=a.recorded_at,
                anomaly_score=a.anomaly_score,
            )
            for a in anomalies
        ],
    }


@app.get("/api/models/{category_id}")
async def get_model_definition(
    category_id: int,
    result_store: ResultStoreDep,
):
    """モデル定義を取得する。未定義なら 404。"""
    definition = result_store.get_model_definition(category_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Model definition not found")
    return ModelDefinitionResponse(
        category_id=definition.category_id,
        baseline_start=definition.baseline_start,
        baseline_end=definition.baseline_end,
        sensitivity=definition.sensitivity,
        excluded_points=definition.excluded_points,
    )


@app.put("/api/models/{category_id}")
async def put_model_definition(
    category_id: int,
    body: ModelDefinitionRequest,
    result_store: ResultStoreDep,
):
    """モデル定義を保存する。ベースライン変更があれば retrained フラグを返す。"""
    existing = result_store.get_model_definition(category_id)
    retrained = False
    if existing is not None:
        retrained = (
            existing.baseline_start != body.baseline_start
            or existing.baseline_end != body.baseline_end
            or sorted(existing.excluded_points) != sorted(body.excluded_points)
        )

    definition = ModelDefinition(
        category_id=category_id,
        baseline_start=body.baseline_start,
        baseline_end=body.baseline_end,
        sensitivity=body.sensitivity,
        excluded_points=body.excluded_points,
    )
    result_store.save_model_definition(definition)
    return {"retrained": retrained}


@app.post("/api/analysis/run")
async def run_analysis():
    """分析を手動トリガーする（スケルトン）。"""
    return {"status": "not_implemented"}
