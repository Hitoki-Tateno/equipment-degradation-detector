"""Store層の抽象インターフェース（境界②）。

Store層は正規化データの永続化と検索を担う。
分類階層の管理もこの層の責務。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CategoryNode:
    """分類ノード。"""

    id: int
    name: str
    parent_id: int | None
    children: list["CategoryNode"]


@dataclass(frozen=True)
class WorkRecord:
    """作業記録（ドメインモデル）。"""

    category_id: int
    work_time: float
    recorded_at: datetime


class DataStoreInterface(ABC):
    """Store層の抽象インターフェース。

    全ての層はこのインターフェースを介してデータにアクセスする。
    SQLiteを直接触るコードが他の層に漏洩してはならない。
    """

    @abstractmethod
    def upsert_records(self, records: list[WorkRecord]) -> int:
        """作業記録をバッチ投入する。

        分類×タイムスタンプが既存と一致するものは上書き、
        それ以外は新規追加。

        Returns:
            投入されたレコード数
        """
        ...

    @abstractmethod
    def ensure_category_path(self, path: list[str]) -> int:
        """分類パスに対応するカテゴリを取得または作成する。

        パスに存在しないノードは自動作成される。

        Returns:
            末端ノードのcategory_id
        """
        ...

    @abstractmethod
    def get_records(
        self,
        category_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[WorkRecord]:
        """指定分類の作業記録を取得する。期間省略時は全期間。"""
        ...

    @abstractmethod
    def get_category_tree(
        self, root_id: int | None = None
    ) -> list[CategoryNode]:
        """分類ツリーを取得する。root_id省略時はツリー全体。"""
        ...

    @abstractmethod
    def delete_all_data(self) -> None:
        """全データを削除する（デバッグ用）。"""
        ...
