"""DI用ファクトリ関数。

backend/ 直下に配置することで、ingestion/ から store/ への
直接依存を避けつつ、FastAPI の Depends() で注入できる。
"""

from backend.interfaces.data_store import DataStoreInterface

_data_store: DataStoreInterface | None = None


def get_data_store() -> DataStoreInterface:
    """DataStoreのシングルトンインスタンスを返す。"""
    global _data_store
    if _data_store is None:
        from backend.store.sqlite import SqliteDataStore

        _data_store = SqliteDataStore("data/store.db")
    return _data_store
