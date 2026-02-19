"""統合テスト — データ投入→分析自動実行→結果取得の一連フロー."""

import io

import pytest
from fastapi.testclient import TestClient

from backend.analysis.engine import AnalysisEngine
from backend.dependencies import (
    _reset_all,
    get_analysis_engine,
    get_data_store,
    get_result_store,
)
from backend.ingestion.main import app
from backend.result_store.sqlite import SqliteResultStore
from backend.store.sqlite import SqliteDataStore


@pytest.fixture(autouse=True)
def _override_deps(tmp_path):
    """テスト用に tmp_path の SQLite インスタンスを注入する。"""
    data_store = SqliteDataStore(str(tmp_path / "store.db"))
    result_store = SqliteResultStore(str(tmp_path / "result.db"))
    engine = AnalysisEngine(data_store, result_store)

    app.dependency_overrides[get_data_store] = lambda: data_store
    app.dependency_overrides[get_result_store] = lambda: result_store
    app.dependency_overrides[get_analysis_engine] = lambda: engine

    yield

    app.dependency_overrides.clear()
    _reset_all()


@pytest.fixture
def client():
    return TestClient(app)


class TestRecordsPostTriggersAnalysis:
    """POST /api/records → 分析結果が自動生成される。"""

    def test_trend_computed_after_post(self, client):
        """レコード投入後に GET /api/results でトレンド結果が取得できる。"""
        resp = client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["ProcessA", "Equip1"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                    {
                        "category_path": ["ProcessA", "Equip1"],
                        "work_time": 20.0,
                        "recorded_at": "2025-02-01T00:00:00",
                    },
                    {
                        "category_path": ["ProcessA", "Equip1"],
                        "work_time": 30.0,
                        "recorded_at": "2025-03-01T00:00:00",
                    },
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["inserted"] == 3

        # カテゴリツリーから category_id を取得
        tree_resp = client.get("/api/categories")
        leaf_id = tree_resp.json()["categories"][0]["children"][0]["id"]

        results_resp = client.get(f"/api/results/{leaf_id}")
        assert results_resp.status_code == 200
        data = results_resp.json()
        assert data["trend"] is not None
        assert data["trend"]["slope"] > 0

    def test_multiple_categories(self, client):
        """複数カテゴリのレコード → 各カテゴリの分析結果が生成される。"""
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["A", "X"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                    {
                        "category_path": ["A", "Y"],
                        "work_time": 20.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                ]
            },
        )
        tree_resp = client.get("/api/categories")
        children = tree_resp.json()["categories"][0]["children"]
        for child in children:
            results_resp = client.get(f"/api/results/{child['id']}")
            assert results_resp.json()["trend"] is not None


class TestCsvPostTriggersAnalysis:
    """POST /api/records/csv → 分析結果が自動生成される。"""

    def test_csv_triggers_analysis(self, client):
        """CSV投入後にトレンド結果が取得できる。"""
        csv_content = (
            "category,work_time,recorded_at\n"
            "EquipA,10.0,2025-01-01\n"
            "EquipA,20.0,2025-02-01\n"
            "EquipA,30.0,2025-03-01\n"
        )
        resp = client.post(
            "/api/records/csv",
            files={
                "file": (
                    "test.csv",
                    io.BytesIO(csv_content.encode()),
                    "text/csv",
                )
            },
        )
        assert resp.status_code == 200
        assert resp.json()["inserted"] == 3

        tree_resp = client.get("/api/categories")
        leaf_id = tree_resp.json()["categories"][0]["id"]

        results_resp = client.get(f"/api/results/{leaf_id}")
        assert results_resp.json()["trend"] is not None
        assert results_resp.json()["trend"]["slope"] > 0


class TestAnalysisRunEndpoint:
    """POST /api/analysis/run → 全カテゴリ分析。"""

    def test_processes_all_categories(self, client):
        """手動トリガーで全末端カテゴリが処理される。"""
        # まずデータを投入
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["P", "E1"],
                        "work_time": 5.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                    {
                        "category_path": ["P", "E2"],
                        "work_time": 15.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                ]
            },
        )

        resp = client.post("/api/analysis/run")
        assert resp.status_code == 200
        assert resp.json()["processed_categories"] == 2

    def test_empty_store_returns_zero(self, client):
        """データ無し → processed_categories: 0。"""
        resp = client.post("/api/analysis/run")
        assert resp.status_code == 200
        assert resp.json()["processed_categories"] == 0


class TestDeleteModelClearsAnomalies:
    """DELETE /api/models/{id} → 異常結果がクリアされる。"""

    def test_delete_clears_model(self, client):
        """モデル定義削除 → 取得で 404。"""
        # データ投入
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["X", "Y"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                ]
            },
        )
        tree_resp = client.get("/api/categories")
        leaf_id = tree_resp.json()["categories"][0]["children"][0]["id"]

        # モデル定義を作成
        client.put(
            f"/api/models/{leaf_id}",
            json={
                "baseline_start": "2025-01-01T00:00:00",
                "baseline_end": "2025-12-31T00:00:00",
                "sensitivity": 0.5,
                "excluded_points": [],
            },
        )

        # モデル定義を削除
        del_resp = client.delete(f"/api/models/{leaf_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        # 削除後は 404
        get_resp = client.get(f"/api/models/{leaf_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        """未定義モデルの削除 → 404。"""
        resp = client.delete("/api/models/9999")
        assert resp.status_code == 404


class TestModelCreationTriggersAnomaly:
    """PUT /api/models → IsolationForest学習 → 異常スコア。"""

    def test_put_model_triggers_anomaly_scores(self, client):
        """モデル保存後に anomaly スコアが取得できる。"""
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["P", "E"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                    {
                        "category_path": ["P", "E"],
                        "work_time": 10.5,
                        "recorded_at": "2025-02-01T00:00:00",
                    },
                    {
                        "category_path": ["P", "E"],
                        "work_time": 10.2,
                        "recorded_at": "2025-03-01T00:00:00",
                    },
                    {
                        "category_path": ["P", "E"],
                        "work_time": 100.0,
                        "recorded_at": "2025-04-01T00:00:00",
                    },
                ]
            },
        )
        tree = client.get("/api/categories")
        leaf = tree.json()["categories"][0]["children"][0]
        leaf_id = leaf["id"]

        resp = client.put(
            f"/api/models/{leaf_id}",
            json={
                "baseline_start": "2025-01-01T00:00:00",
                "baseline_end": "2025-03-31T00:00:00",
                "sensitivity": 0.5,
                "excluded_points": [],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["retrained"] is True

        results = client.get(f"/api/results/{leaf_id}")
        data = results.json()
        assert len(data["anomalies"]) == 4
        for a in data["anomalies"]:
            assert "anomaly_score" in a
            assert isinstance(a["anomaly_score"], float)

    def test_delete_model_clears_anomalies(self, client):
        """モデル削除 → 異常スコアもクリア。"""
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["Q", "F"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                    {
                        "category_path": ["Q", "F"],
                        "work_time": 10.5,
                        "recorded_at": "2025-02-01T00:00:00",
                    },
                ]
            },
        )
        tree = client.get("/api/categories")
        leaf_id = tree.json()["categories"][0]["children"][0]["id"]

        client.put(
            f"/api/models/{leaf_id}",
            json={
                "baseline_start": "2025-01-01T00:00:00",
                "baseline_end": "2025-12-31T00:00:00",
                "sensitivity": 0.5,
                "excluded_points": [],
            },
        )
        r1 = client.get(f"/api/results/{leaf_id}")
        assert len(r1.json()["anomalies"]) == 2

        client.delete(f"/api/models/{leaf_id}")

        r2 = client.get(f"/api/results/{leaf_id}")
        assert len(r2.json()["anomalies"]) == 0

    def test_new_data_updates_anomalies(self, client):
        """モデル定義済み → 新データ投入 → スコア更新。"""
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["R", "G"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                    {
                        "category_path": ["R", "G"],
                        "work_time": 10.5,
                        "recorded_at": "2025-02-01T00:00:00",
                    },
                ]
            },
        )
        tree = client.get("/api/categories")
        leaf_id = tree.json()["categories"][0]["children"][0]["id"]

        client.put(
            f"/api/models/{leaf_id}",
            json={
                "baseline_start": "2025-01-01T00:00:00",
                "baseline_end": "2025-12-31T00:00:00",
                "sensitivity": 0.5,
                "excluded_points": [],
            },
        )

        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["R", "G"],
                        "work_time": 100.0,
                        "recorded_at": "2025-03-01T00:00:00",
                    },
                ]
            },
        )

        results = client.get(f"/api/results/{leaf_id}")
        assert len(results.json()["anomalies"]) == 3


class TestTimezoneAwareDatetimes:
    """offset-aware datetime の入力が正しく処理される。"""

    def test_aware_records_and_model_no_500(self, client):
        """TZ付きレコード + TZ付きモデル定義 → 500エラーにならない。"""
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["TZ", "A"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00+09:00",
                    },
                    {
                        "category_path": ["TZ", "A"],
                        "work_time": 10.5,
                        "recorded_at": "2025-02-01T00:00:00+09:00",
                    },
                    {
                        "category_path": ["TZ", "A"],
                        "work_time": 10.2,
                        "recorded_at": "2025-03-01T00:00:00+09:00",
                    },
                ]
            },
        )
        tree = client.get("/api/categories")
        leaf_id = tree.json()["categories"][0]["children"][0]["id"]

        resp = client.put(
            f"/api/models/{leaf_id}",
            json={
                "baseline_start": "2025-01-01T00:00:00+09:00",
                "baseline_end": "2025-03-31T00:00:00+09:00",
                "sensitivity": 0.5,
                "excluded_points": [],
            },
        )
        assert resp.status_code == 200

        results = client.get(f"/api/results/{leaf_id}")
        assert results.status_code == 200
        data = results.json()
        assert len(data["anomalies"]) == 3

    def test_mixed_aware_naive_no_error(self, client):
        """naive レコード + aware モデル定義 → エラーにならない。"""
        client.post(
            "/api/records",
            json={
                "records": [
                    {
                        "category_path": ["TZ", "B"],
                        "work_time": 10.0,
                        "recorded_at": "2025-01-01T00:00:00",
                    },
                    {
                        "category_path": ["TZ", "B"],
                        "work_time": 10.5,
                        "recorded_at": "2025-02-01T00:00:00",
                    },
                ]
            },
        )
        tree = client.get("/api/categories")
        leaf_id = tree.json()["categories"][0]["children"][0]["id"]

        resp = client.put(
            f"/api/models/{leaf_id}",
            json={
                "baseline_start": "2025-01-01T00:00:00Z",
                "baseline_end": "2025-12-31T00:00:00Z",
                "sensitivity": 0.5,
                "excluded_points": ["2025-02-01T00:00:00Z"],
            },
        )
        assert resp.status_code == 200

        results = client.get(f"/api/results/{leaf_id}")
        assert results.status_code == 200
        assert len(results.json()["anomalies"]) == 2
