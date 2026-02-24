"""EventBus のユニットテスト。"""

import asyncio

from backend.ingestion.event_bus import EventBus


def _run(coro):
    """async テストを同期的に実行するヘルパー。"""
    return asyncio.run(coro)


class TestEventBus:
    """EventBus の pub/sub 動作を検証する。"""

    def test_publish_delivers_to_subscriber(self):
        """publish したイベントが subscriber に届く。"""

        async def _test():
            bus = EventBus()
            async with bus.subscribe() as queue:
                bus.publish("test-event", {"key": "value"})
                msg = await asyncio.wait_for(queue.get(), timeout=1)
                assert msg["event"] == "test-event"
                assert msg["data"] == {"key": "value"}

        _run(_test())

    def test_publish_delivers_to_multiple_subscribers(self):
        """複数 subscriber に同じイベントが届く。"""

        async def _test():
            bus = EventBus()
            async with bus.subscribe() as q1, bus.subscribe() as q2:
                bus.publish("multi", {"n": 1})
                m1 = await asyncio.wait_for(q1.get(), timeout=1)
                m2 = await asyncio.wait_for(q2.get(), timeout=1)
                assert m1["event"] == "multi"
                assert m2["event"] == "multi"

        _run(_test())

    def test_unsubscribe_stops_delivery(self):
        """subscribe コンテキスト離脱後はイベントが届かない。"""

        async def _test():
            bus = EventBus()
            async with bus.subscribe() as queue:
                bus.publish("before", None)
                msg = await asyncio.wait_for(queue.get(), timeout=1)
                assert msg["event"] == "before"

            # コンテキスト離脱後
            assert len(bus._subscribers) == 0
            bus.publish("after", None)  # エラーなく完了する

        _run(_test())

    def test_publish_with_no_data(self):
        """data=None でも正常に配信される。"""

        async def _test():
            bus = EventBus()
            async with bus.subscribe() as queue:
                bus.publish("no-data")
                msg = await asyncio.wait_for(queue.get(), timeout=1)
                assert msg["event"] == "no-data"
                assert msg["data"] is None

        _run(_test())

    def test_multiple_events_queued(self):
        """複数イベントが順序通りにキューに入る。"""

        async def _test():
            bus = EventBus()
            async with bus.subscribe() as queue:
                bus.publish("first")
                bus.publish("second")
                bus.publish("third")
                events = []
                for _ in range(3):
                    msg = await asyncio.wait_for(queue.get(), timeout=1)
                    events.append(msg["event"])
                assert events == ["first", "second", "third"]

        _run(_test())
