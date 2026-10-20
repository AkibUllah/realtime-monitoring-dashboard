"""Real host metrics via psutil."""

from __future__ import annotations

import logging
import platform
import time

import psutil

from app.models import NodeSnapshot, NodeStatus

log = logging.getLogger("collector.host")


class HostCollector:
    node_id = "host"

    def __init__(self) -> None:
        self._last_net = psutil.net_io_counters()
        self._last_ts = time.time()
        psutil.cpu_percent(interval=None)  # prime the non-blocking cpu meter

    def collect(self, now: float | None = None) -> NodeSnapshot:
        now = now or time.time()
        net = psutil.net_io_counters()
        dt = max(now - self._last_ts, 1e-3)
        rx_kbps = (net.bytes_recv - self._last_net.bytes_recv) * 8 / 1000 / dt
        tx_kbps = (net.bytes_sent - self._last_net.bytes_sent) * 8 / 1000 / dt
        self._last_net, self._last_ts = net, now

        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        status = NodeStatus.HEALTHY
        if cpu > 90 or mem > 90 or disk > 95:
            status = NodeStatus.DEGRADED
        return NodeSnapshot(
            node_id=self.node_id,
            name=platform.node() or "localhost",
            region="local",
            role="host",
            status=status,
            ts=now,
            metrics={
                "cpu": round(cpu, 2),
                "memory": round(mem, 2),
                "disk": round(disk, 2),
                "net_rx": round(max(rx_kbps, 0.0), 2),
                "net_tx": round(max(tx_kbps, 0.0), 2),
            },
        )
