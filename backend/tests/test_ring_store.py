from __future__ import annotations

import pytest

from app.models import NodeSnapshot, NodeStatus, Sample
from app.store.ring import RingBuffer, SqlitePersistence, TimeSeriesStore


def test_ring_buffer_evicts_oldest_at_capacity() -> None:
    buf = RingBuffer(3)
    for i in range(5):
        buf.append(float(i), i * 10.0)
    assert len(buf) == 3
    assert [p.ts for p in buf.query(0)] == [2.0, 3.0, 4.0]
    assert buf.latest() is not None and buf.latest().value == 40.0


def test_ring_buffer_rejects_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        RingBuffer(0)


def test_ring_buffer_drops_out_of_order_samples() -> None:
    buf = RingBuffer(10)
    buf.append(10.0, 1.0)
    buf.append(5.0, 2.0)  # older than last -> ignored
    buf.append(11.0, 3.0)
    assert [p.ts for p in buf.query(0)] == [10.0, 11.0]


def test_query_window_is_inclusive() -> None:
    buf = RingBuffer(100)
    for i in range(10):
        buf.append(float(i), float(i))
    assert [p.ts for p in buf.query(3, 6)] == [3.0, 4.0, 5.0, 6.0]
    assert buf.query(100) == []


def test_query_downsamples_by_bucket_average() -> None:
    buf = RingBuffer(100)
    for i in range(10):
        buf.append(float(i), float(i))  # values 0..9 at 1s intervals
    pts = buf.query(0, step=5)
    assert [(p.ts, p.value) for p in pts] == [(0.0, 2.0), (5.0, 7.0)]


def test_store_records_snapshots_and_lists_nodes() -> None:
    store = TimeSeriesStore(capacity=50)
    for t in range(3):
        store.record(
            NodeSnapshot(
                "node-01",
                "api",
                "dhaka-1",
                "api",
                NodeStatus.HEALTHY,
                float(t),
                {"cpu": 10.0 + t, "memory": 50.0},
            )
        )
    assert [n.node_id for n in store.nodes()] == ["node-01"]
    assert store.metrics_for("node-01") == ["cpu", "memory"]
    assert store.latest("node-01", "cpu").value == 12.0
    assert [p.value for p in store.history("node-01", "cpu", since=1.0)] == [11.0, 12.0]
    assert store.history("nope", "cpu", since=0) == []


def test_store_marks_stale_nodes() -> None:
    store = TimeSeriesStore()
    store.record(NodeSnapshot("a", "a", "r", "api", NodeStatus.HEALTHY, 100.0, {"cpu": 1}))
    store.record(NodeSnapshot("b", "b", "r", "api", NodeStatus.HEALTHY, 130.0, {"cpu": 1}))
    assert store.mark_stale(now=140.0, timeout=20) == ["a"]


def test_sqlite_persistence_roundtrip_and_prune(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = SqlitePersistence(str(tmp_path / "m.db"))
    db.write(
        [
            Sample("n", "cpu", 1.0, 100.0),
            Sample("n", "cpu", 2.0, 200.0),
            Sample("n", "cpu", 3.0, 300.0),
        ]
    )
    assert db.count() == 3
    recent = db.load_recent(seconds=150, now=300.0)
    assert [s.value for s in recent] == [2.0, 3.0]
    assert db.prune(older_than_seconds=150, now=300.0) == 1
    assert db.count() == 2
    db.close()


def test_warm_start_restores_history(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.config import Settings
    from app.service import MonitoringService

    path = str(tmp_path / "warm.db")
    settings = Settings(
        sqlite_path=path, host_collector_enabled=False, fleet_size=2, collector_enabled=False
    )
    first = MonitoringService(settings)
    import asyncio
    import time

    base = time.time() - 10
    for t in range(5):
        asyncio.run(first.tick(now=base + t))
    first.persistence.close()  # type: ignore[union-attr]

    second = MonitoringService(settings)
    assert len(second.store.history("node-01", "cpu", since=0)) == 5
    second.persistence.close()  # type: ignore[union-attr]
