"""DI用ファクトリ関数。

backend/ 直下に配置することで、ingestion/ から store/ への
直接依存を避けつつ、FastAPI の Depends() で注入できる。
"""

from backend.analysis.engine import AnalysisEngine
from backend.interfaces.data_store import DataStoreInterface
from backend.interfaces.result_store import ResultStoreInterface

_data_store: DataStoreInterface | None = None
_result_store: ResultStoreInterface | None = None
_analysis_engine: AnalysisEngine | None = None


def get_data_store() -> DataStoreInterface:
    """DataStoreのシングルトンインスタンスを返す。"""
    global _data_store
    if _data_store is None:
        from backend.store.sqlite import SqliteDataStore

        _data_store = SqliteDataStore("data/store.db")
    return _data_store


def get_result_store() -> ResultStoreInterface:
    """ResultStoreのシングルトンインスタンスを返す。"""
    global _result_store
    if _result_store is None:
        from backend.result_store.sqlite import SqliteResultStore

        _result_store = SqliteResultStore("data/result_store.db")
    return _result_store


def get_analysis_engine() -> AnalysisEngine:
    """AnalysisEngineのシングルトンインスタンスを返す。"""
    global _analysis_engine
    if _analysis_engine is None:
        _analysis_engine = AnalysisEngine(get_data_store(), get_result_store())
    return _analysis_engine


def _reset_all() -> None:
    """全シングルトンをリセットする（テスト用）。"""
    global _data_store, _result_store, _analysis_engine
    _data_store = None
    _result_store = None
    _analysis_engine = None
