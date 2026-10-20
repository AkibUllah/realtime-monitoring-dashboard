"""In-memory ring-buffer time-series store with optional SQLite persistence."""

from __future__ import annotations

import bisect
import logging
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from app.models import NodeSnapshot, Sample

log = logging.getLogger("store")


@dataclass(frozen=True)
class Point:
    ts: float
    value: float


class RingBuffer:
    """Fixed-capacity, append-only, time-ordered buffer of (ts, value)."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._ts: deque[float] = deque(maxlen=capacity)
        self._values: deque[float] = deque(maxlen=capacity)

    def __len__(self) -> int:
        return len(self._ts)

    def append(self, ts: float, value: float) -> None:
        if self._ts and ts < self._ts[-1]:
            # out-of-order sample (e.g. replay from persistence); drop rather than corrupt order
            return
        self._ts.append(ts)
        self._values.append(value)

    def latest(self) -> Point | None:
        return Point(self._ts[-1], self._values[-1]) if self._ts else None

    def query(
        self, since: float, until: float | None = None, step: float | None = None
    ) -> list[Point]:
        """Points with since <= ts <= until. ``step`` downsamples by averaging buckets."""
        ts = list(self._ts)
        values = list(self._values)
        lo = bisect.bisect_left(ts, since)
        hi = bisect.bisect_right(ts, until) if until is not None else len(ts)
        pts = [Point(ts[i], values[i]) for i in range(lo, hi)]
        if not step or step <= 0 or len(pts) < 2:
            return pts
        buckets: dict[int, list[float]] = {}
        order: list[int] = []
        for p in pts:
            key = int(p.ts // step)
            if key not in buckets:
                buckets[key] = []
                order.append(key)
            buckets[key].append(p.value)
        return [Point(key * step, round(sum(buckets[key]) / len(buckets[key]), 3)) for key in order]


class TimeSeriesStore:
    def __init__(self, capacity: int = 1800) -> None:
        self.capacity = capacity
        self._series: dict[tuple[str, str], RingBuffer] = {}
        self._nodes: dict[str, NodeSnapshot] = {}
        self._lock = threading.Lock()

    def _buf(self, node_id: str, metric: str) -> RingBuffer:
        key = (node_id, metric)
        buf = self._series.get(key)
        if buf is None:
            buf = self._series[key] = RingBuffer(self.capacity)
        return buf

    def append(self, sample: Sample) -> None:
        with self._lock:
            self._buf(sample.node_id, sample.metric).append(sample.ts, sample.value)

    def record(self, snapshot: NodeSnapshot) -> None:
        with self._lock:
            self._nodes[snapshot.node_id] = snapshot
            for s in snapshot.samples():
                self._buf(s.node_id, s.metric).append(s.ts, s.value)

    def nodes(self) -> list[NodeSnapshot]:
        with self._lock:
            return sorted(self._nodes.values(), key=lambda n: n.node_id)

    def node(self, node_id: str) -> NodeSnapshot | None:
        return self._nodes.get(node_id)

    def metrics_for(self, node_id: str) -> list[str]:
        return sorted(m for (n, m) in self._series if n == node_id)

    def latest(self, node_id: str, metric: str) -> Point | None:
        buf = self._series.get((node_id, metric))
        return buf.latest() if buf else None

    def history(
        self,
        node_id: str,
        metric: str,
        since: float,
        until: float | None = None,
        step: float | None = None,
    ) -> list[Point]:
        with self._lock:
            buf = self._series.get((node_id, metric))
            return buf.query(since, until, step) if buf else []

    def mark_stale(self, now: float, timeout: float) -> list[str]:
        """Return node ids whose last snapshot is older than ``timeout`` seconds."""
        return [n.node_id for n in self.nodes() if now - n.ts > timeout]


class SqlitePersistence:
    """Append-only sample log in SQLite. Used to warm the ring buffers after a restart."""

    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS samples (ts REAL NOT NULL, node_id TEXT NOT NULL, "
            "metric TEXT NOT NULL, value REAL NOT NULL)"
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS ix_samples_ts ON samples(ts)")
        self._conn.commit()
        self._lock = threading.Lock()

    def write(self, samples: list[Sample]) -> None:
        if not samples:
            return
        with self._lock:
            self._conn.executemany(
                "INSERT INTO samples (ts, node_id, metric, value) VALUES (?, ?, ?, ?)",
                [(s.ts, s.node_id, s.metric, s.value) for s in samples],
            )
            self._conn.commit()

    def load_recent(self, seconds: float, now: float | None = None) -> list[Sample]:
        now = now or time.time()
        with self._lock:
            rows = self._conn.execute(
                "SELECT node_id, metric, value, ts FROM samples WHERE ts >= ? ORDER BY ts",
                (now - seconds,),
            ).fetchall()
        return [Sample(node_id=r[0], metric=r[1], value=r[2], ts=r[3]) for r in rows]

    def prune(self, older_than_seconds: float, now: float | None = None) -> int:
        now = now or time.time()
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM samples WHERE ts < ?", (now - older_than_seconds,)
            )
            self._conn.commit()
            return cur.rowcount

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0])

    def close(self) -> None:
        self._conn.close()
