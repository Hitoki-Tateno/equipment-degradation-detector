"""FastAPIアプリケーション。

取り込みAPI + データ提供API + 分析結果APIを統合。
"""

from fastapi import FastAPI

app = FastAPI(
    title="設備劣化検知システム API",
    version="0.1.0",
)


@app.get("/api/health")
async def health_check():
    """ヘルスチェック。"""
    return {"status": "ok"}


# TODO: Step 1 で実装
# - POST /api/records       (取り込みAPI)
# - GET  /api/records       (データ提供API)
# - GET  /api/categories    (分類ツリーAPI)

# TODO: Step 2 で実装
# - GET  /api/results/{category_id}  (分析結果API)
# - GET  /api/models/{category_id}   (モデル定義取得)
# - PUT  /api/models/{category_id}   (モデル定義更新)

# TODO: Step 3 / 開発用
# - POST /api/analysis/run  (手動トリガー)
