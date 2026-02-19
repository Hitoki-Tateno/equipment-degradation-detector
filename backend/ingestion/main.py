"""FastAPIアプリケーション。

取り込みAPI + データ提供API + 分析結果APIを統合。
"""

import io
from datetime import datetime
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from pydantic import BaseModel, field_validator

from backend.analysis.engine import AnalysisEngine
from backend.dependencies import (
    get_analysis_engine,
    get_data_store,
    get_result_store,
)
from backend.interfaces.data_store import (
    CategoryNode,
    DataStoreInterface,
    WorkRecord,
)
from backend.interfaces.result_store import (
    ModelDefinition,
    ResultStoreInterface,
)

StoreDep = Annotated[DataStoreInterface, Depends(get_data_store)]
ResultStoreDep = Annotated[ResultStoreInterface, Depends(get_result_store)]
EngineDep = Annotated[AnalysisEngine, Depends(get_analysis_engine)]

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

    @field_validator("recorded_at", mode="after")
    @classmethod
    def strip_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


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

    @field_validator("baseline_start", "baseline_end", mode="after")
    @classmethod
    def strip_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

    @field_validator("excluded_points", mode="after")
    @classmethod
    def strip_tz_list(cls, v: list[datetime]) -> list[datetime]:
        return [
            dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
            for dt in v
        ]


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
    engine: EngineDep,
):
    """作業記録をバッチ投入する。"""
    work_records: list[WorkRecord] = []
    affected_category_ids: set[int] = set()
    for item in body.records:
        category_id = store.ensure_category_path(item.category_path)
        affected_category_ids.add(category_id)
        work_records.append(
            WorkRecord(
                category_id=category_id,
                work_time=item.work_time,
                recorded_at=item.recorded_at,
            )
        )
    inserted = store.upsert_records(work_records)

    for cid in affected_category_ids:
        engine.run(cid)

    return {"inserted": inserted}


@app.post("/api/records/csv")
async def post_records_csv(
    file: UploadFile,
    store: StoreDep,
    engine: EngineDep,
):
    """CSVファイルから作業記録をバッチ投入する（デバッグ用）。"""
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    if "work_time" not in df.columns or "recorded_at" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="work_time and recorded_at columns are required",
        )

    ts = pd.to_datetime(df["recorded_at"])
    if ts.dt.tz is not None:
        ts = ts.dt.tz_localize(None)
    df["recorded_at"] = ts
    category_columns = [
        c for c in df.columns if c not in ("work_time", "recorded_at")
    ]

    work_records: list[WorkRecord] = []
    affected_category_ids: set[int] = set()
    skipped = 0
    for _, row in df.iterrows():
        path = [
            str(row[c])
            for c in category_columns
            if pd.notna(row[c]) and str(row[c]).strip()
        ]
        if not path:
            skipped += 1
            continue
        category_id = store.ensure_category_path(path)
        affected_category_ids.add(category_id)
        work_records.append(
            WorkRecord(
                category_id=category_id,
                work_time=float(row["work_time"]),
                recorded_at=row["recorded_at"].to_pydatetime(),
            )
        )

    inserted = store.upsert_records(work_records)

    for cid in affected_category_ids:
        engine.run(cid)

    return {"inserted": inserted, "skipped": skipped}


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
        raise HTTPException(
            status_code=404, detail="Model definition not found"
        )
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
    engine: EngineDep,
):
    """モデル定義を保存し、異常検知を実行する."""
    existing = result_store.get_model_definition(category_id)
    baseline_changed = existing is None or (
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
    engine.run(category_id)
    return {"retrained": baseline_changed}


@app.delete("/api/models/{category_id}")
async def delete_model_definition_endpoint(
    category_id: int,
    result_store: ResultStoreDep,
):
    """モデル定義を削除する。異常検知結果もカスケード削除。未定義なら404。"""
    existing = result_store.get_model_definition(category_id)
    if existing is None:
        raise HTTPException(
            status_code=404, detail="Model definition not found"
        )
    result_store.delete_anomaly_results(category_id)
    result_store.delete_model_definition(category_id)
    return {"deleted": True}


@app.post("/api/analysis/run")
async def run_analysis(engine: EngineDep):
    """全末端カテゴリに対して分析を手動トリガーする。"""
    count = engine.run_all()
    return {"processed_categories": count}


# ---------- デバッグ用エンドポイント ----------


@app.delete("/api/debug/data", tags=["debug"])
async def delete_all_data(store: StoreDep):
    """【デバッグ用】作業記録・カテゴリを全削除する。"""
    store.delete_all_data()
    return {"deleted": "data"}


@app.delete("/api/debug/results", tags=["debug"])
async def delete_all_results(result_store: ResultStoreDep):
    """【デバッグ用】分析結果・モデル定義を全削除する。"""
    result_store.delete_all_data()
    return {"deleted": "results"}


@app.delete("/api/debug/all", tags=["debug"])
async def delete_all(store: StoreDep, result_store: ResultStoreDep):
    """【デバッグ用】全データを一括削除する。"""
    result_store.delete_all_data()
    store.delete_all_data()
    return {"deleted": "all"}
