"""DI用ファクトリ関数。

backend/ 直下に配置することで、ingestion/ から store/ への
直接依存を避けつつ、FastAPI の Depends() で注入できる。
"""

from backend.interfaces.data_store import DataStoreInterface
from backend.interfaces.result_store import ResultStoreInterface

_data_store: DataStoreInterface | None = None
_result_store: ResultStoreInterface | None = None


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
