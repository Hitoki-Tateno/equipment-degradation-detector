# DataStoreInterface 契約仕様

## ドメインモデル

```python
@dataclass(frozen=True)
class CategoryNode:
    id: int
    name: str
    parent_id: int | None
    children: list["CategoryNode"]

@dataclass(frozen=True)
class WorkRecord:
    category_id: int
    work_time: float       # 秒
    recorded_at: datetime
```

## メソッド契約

### upsert_records(records: list[WorkRecord]) -> int

- 作業記録をバッチ投入
- 一意性キー: `category_id × recorded_at`
- 既存と一致 → 上書き（work_timeを更新）
- 一致しない → 新規追加
- 戻り値: 投入レコード数

### ensure_category_path(path: list[str]) -> int

- 分類パス（例: `["溶接プロセス", "溶接機A"]`）に対応するカテゴリを取得または作成
- 存在しないノードは自動作成
- 同じパスに対しては常に同じIDを返す
- 戻り値: 末端ノードのcategory_id

### get_records(category_id, start?, end?) -> list[WorkRecord]

- 指定分類の作業記録を取得
- start/end省略時は全期間
- 結果はrecorded_at昇順
- データがなければ空リスト

### get_category_tree(root_id?) -> list[CategoryNode]

- 分類ツリーを取得
- root_id省略時はツリー全体（ルートノードのリスト）
- 各ノードのchildrenに子ノードがネスト
