"""Monitoring service: ties collectors, store, alert engine and WebSocket broadcaster together."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import WebSocket

from app.alerts.engine import AlertEngine, default_rules
from app.collectors.fleet import FleetSimulator
from app.collectors.host import HostCollector
from app.config import Settings
from app.models import NodeSnapshot, NodeStatus, Sample
from app.store.ring import SqlitePersistence, TimeSeriesStore

log = logging.getLogger("service")


class Broadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def publish(self, message: dict[str, Any]) -> None:
        if not self._clients:
            return
        payload = json.dumps(message, separators=(",", ":"))
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001 - a broken client must not break the loop
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


class MonitoringService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = TimeSeriesStore(capacity=settings.ring_capacity)
        self.alerts = AlertEngine()
        default_rules(self.alerts)
        self.broadcaster = Broadcaster()
        self.fleet = FleetSimulator(settings.fleet_size, seed=settings.fleet_seed)
        self.host: HostCollector | None = None
        if settings.host_collector_enabled:
            try:
                self.host = HostCollector()
            except Exception:  # noqa: BLE001 - e.g. restricted container
                log.exception("host collector unavailable; continuing with fleet only")
        self.persistence: SqlitePersistence | None = (
            SqlitePersistence(settings.sqlite_path) if settings.sqlite_path else None
        )
        self.started_at = time.time()
        self.tick_count = 0
        self._task: asyncio.Task | None = None
        if self.persistence:
            self._warm_from_persistence()

    # ---- lifecycle -------------------------------------------------------------------
    def _warm_from_persistence(self) -> None:
        assert self.persistence is not None
        window = self.settings.ring_capacity * self.settings.collect_interval_seconds
        samples = self.persistence.load_recent(window)
        for s in samples:
            self.store.append(s)
        if samples:
            log.info("restored %d samples from %s", len(samples), self.settings.sqlite_path)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="collector-loop")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self.persistence:
            self.persistence.close()

    async def _loop(self) -> None:
        interval = self.settings.collect_interval_seconds
        while True:
            started = time.monotonic()
            try:
                await self.tick()
            except Exception:  # noqa: BLE001
                log.exception("collector tick failed")
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(interval - elapsed, 0.05))

    # ---- one collection cycle --------------------------------------------------------
    def collect(self, now: float) -> list[NodeSnapshot]:
        snapshots = self.fleet.collect(now)
        if self.host is not None:
            try:
                snapshots.insert(0, self.host.collect(now))
            except Exception:  # noqa: BLE001
                log.exception("host collection failed")
        return snapshots

    async def tick(self, now: float | None = None) -> dict[str, Any]:
        now = now or time.time()
        snapshots = self.collect(now)
        samples: list[Sample] = []
        for snap in snapshots:
            self.store.record(snap)
            samples.extend(snap.samples())
        notifications = self.alerts.evaluate(snapshots, now)
        if self.persistence:
            self.persistence.write(samples)
            if self.tick_count % 300 == 0:
                self.persistence.prune(
                    self.settings.ring_capacity * self.settings.collect_interval_seconds * 2, now
                )
        self.tick_count += 1
        message = {
            "type": "tick",
            "ts": now,
            "nodes": [s.to_dict() for s in snapshots],
            "alerts": [a.to_dict() for a in self.alerts.active()],
            "notifications": [n.to_dict() for n in notifications],
        }
        await self.broadcaster.publish(message)
        return message

    # ---- read side -------------------------------------------------------------------
    def snapshot(self, history_seconds: float = 300, step: float | None = None) -> dict[str, Any]:
        now = time.time()
        nodes = self.store.nodes()
        history: dict[str, dict[str, list[list[float]]]] = {}
        for node in nodes:
            history[node.node_id] = {
                metric: [
                    [p.ts, p.value]
                    for p in self.store.history(
                        node.node_id, metric, now - history_seconds, step=step
                    )
                ]
                for metric in self.store.metrics_for(node.node_id)
            }
        return {
            "type": "snapshot",
            "ts": now,
            "nodes": [n.to_dict() for n in nodes],
            "history": history,
            "alerts": [a.to_dict() for a in self.alerts.active()],
            "rules": [r.to_dict() for r in self.alerts.rules.values()],
            "notifications": [n.to_dict() for n in list(self.alerts.notifications)[-50:]],
        }

    def summary(self) -> dict[str, Any]:
        nodes = self.store.nodes()
        by_status = {s.value: 0 for s in NodeStatus}
        for n in nodes:
            by_status[n.status.value] += 1
        return {
            "nodes": len(nodes),
            "by_status": by_status,
            "firing_alerts": self.alerts.firing_count(),
            "ws_clients": self.broadcaster.client_count,
            "ticks": self.tick_count,
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "persistence": bool(self.persistence),
        }
