"""インメモリ EventBus。

単一プロセス（uvicorn）前提の軽量 pub/sub。
API エンドポイントがデータ変更時に publish し、
SSE エンドポイントが subscribe してフロントへ中継する。
"""

import asyncio
from contextlib import asynccontextmanager


class EventBus:
    """asyncio.Queue ベースのインメモリ pub/sub バス。"""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[dict]] = []

    def publish(self, event: str, data: dict | None = None) -> None:
        """全 subscriber にイベントを配信する。"""
        message = {"event": event, "data": data}
        for queue in self._subscribers:
            queue.put_nowait(message)

    @asynccontextmanager
    async def subscribe(self):
        """コンテキスト内で Queue を受け取り、イベントを待ち受ける。"""
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            yield queue
        finally:
            self._subscribers.remove(queue)
