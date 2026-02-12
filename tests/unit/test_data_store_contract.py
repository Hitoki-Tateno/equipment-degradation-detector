"""Store層の契約テスト（TDD: Red phase）。

このテストは DataStoreInterface の契約を検証する。
どの実装（SQLite, PostgreSQL等）であっても、このテストが通ることを保証する。

使い方:
  1. DataStoreInterface の実装クラスを作成
  2. fixture `data_store` で実装インスタンスを返す
  3. 全テストがパスすることを確認
"""

from datetime import datetime

import pytest

from backend.interfaces.data_store import DataStoreInterface, WorkRecord


@pytest.fixture
def data_store(tmp_path):
    """Store層の実装インスタンスを返す。"""
    from backend.store.sqlite import SqliteDataStore

    db_path = tmp_path / "test.db"
    return SqliteDataStore(str(db_path))


class TestUpsertRecords:
    """バッチ投入の契約テスト。"""

    def test_insert_new_records(self, data_store: DataStoreInterface):
        """新規レコードが正しく投入される。"""
        category_id = data_store.ensure_category_path(["プロセスA", "設備1"])
        records = [
            WorkRecord(category_id=category_id, work_time=10.5, recorded_at=datetime(2025, 1, 1)),
            WorkRecord(category_id=category_id, work_time=11.0, recorded_at=datetime(2025, 1, 2)),
        ]
        count = data_store.upsert_records(records)
        assert count == 2

        result = data_store.get_records(category_id)
        assert len(result) == 2

    def test_upsert_overwrites_on_duplicate_key(self, data_store: DataStoreInterface):
        """分類×タイムスタンプが一致するレコードは上書きされる。"""
        category_id = data_store.ensure_category_path(["プロセスA", "設備1"])
        ts = datetime(2025, 1, 1)

        data_store.upsert_records(
            [WorkRecord(category_id=category_id, work_time=10.0, recorded_at=ts)]
        )
        data_store.upsert_records(
            [WorkRecord(category_id=category_id, work_time=20.0, recorded_at=ts)]
        )

        result = data_store.get_records(category_id)
        assert len(result) == 1
        assert result[0].work_time == 20.0


class TestGetRecords:
    """データ取得の契約テスト。"""

    def test_returns_empty_for_no_data(self, data_store: DataStoreInterface):
        """データがない分類では空リストを返す。"""
        category_id = data_store.ensure_category_path(["プロセスX", "設備Y"])
        result = data_store.get_records(category_id)
        assert result == []

    def test_filters_by_date_range(self, data_store: DataStoreInterface):
        """期間指定でフィルタされる。"""
        category_id = data_store.ensure_category_path(["プロセスA", "設備1"])
        records = [
            WorkRecord(category_id=category_id, work_time=10.0, recorded_at=datetime(2025, 1, 1)),
            WorkRecord(category_id=category_id, work_time=11.0, recorded_at=datetime(2025, 2, 1)),
            WorkRecord(category_id=category_id, work_time=12.0, recorded_at=datetime(2025, 3, 1)),
        ]
        data_store.upsert_records(records)

        result = data_store.get_records(
            category_id, start=datetime(2025, 1, 15), end=datetime(2025, 2, 15)
        )
        assert len(result) == 1
        assert result[0].work_time == 11.0

    def test_returns_sorted_by_recorded_at(self, data_store: DataStoreInterface):
        """結果はrecorded_at昇順でソートされる。"""
        category_id = data_store.ensure_category_path(["プロセスA", "設備1"])
        records = [
            WorkRecord(category_id=category_id, work_time=12.0, recorded_at=datetime(2025, 3, 1)),
            WorkRecord(category_id=category_id, work_time=10.0, recorded_at=datetime(2025, 1, 1)),
        ]
        data_store.upsert_records(records)

        result = data_store.get_records(category_id)
        assert result[0].recorded_at < result[1].recorded_at


class TestCategoryTree:
    """分類ツリーの契約テスト。"""

    def test_ensure_creates_hierarchy(self, data_store: DataStoreInterface):
        """分類パスの階層が自動作成される。"""
        category_id = data_store.ensure_category_path(["プロセスA", "設備1"])
        assert isinstance(category_id, int)

    def test_ensure_returns_same_id_for_same_path(self, data_store: DataStoreInterface):
        """同じパスに対しては同じIDが返る。"""
        id1 = data_store.ensure_category_path(["プロセスA", "設備1"])
        id2 = data_store.ensure_category_path(["プロセスA", "設備1"])
        assert id1 == id2

    def test_get_tree_returns_hierarchy(self, data_store: DataStoreInterface):
        """ツリー構造が正しく返される。"""
        data_store.ensure_category_path(["プロセスA", "設備1"])
        data_store.ensure_category_path(["プロセスA", "設備2"])

        tree = data_store.get_category_tree()
        assert len(tree) >= 1

        process_a = next((n for n in tree if n.name == "プロセスA"), None)
        assert process_a is not None
        assert len(process_a.children) == 2
