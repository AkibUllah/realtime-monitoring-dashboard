"""Synthetic node fleet.

Each node follows a bounded random walk around a per-role baseline, with occasional
incidents (CPU/memory saturation, a node going down) so alerting has something to do.
Deterministic for a given seed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.models import NodeSnapshot, NodeStatus

REGIONS = ("dhaka-1", "dhaka-2", "ctg-1")
ROLES = ("api", "worker", "db", "cache", "edge")

BASELINES: dict[str, dict[str, float]] = {
    "api": {"cpu": 35, "memory": 55, "disk": 40, "net_rx": 4200, "net_tx": 6800},
    "worker": {"cpu": 60, "memory": 65, "disk": 55, "net_rx": 900, "net_tx": 700},
    "db": {"cpu": 25, "memory": 78, "disk": 72, "net_rx": 2600, "net_tx": 3100},
    "cache": {"cpu": 15, "memory": 70, "disk": 20, "net_rx": 5100, "net_tx": 5400},
    "edge": {"cpu": 30, "memory": 45, "disk": 30, "net_rx": 9800, "net_tx": 7200},
}

BOUNDS: dict[str, tuple[float, float]] = {
    "cpu": (0.5, 100.0),
    "memory": (5.0, 100.0),
    "disk": (5.0, 100.0),
    "net_rx": (0.0, 50_000.0),
    "net_tx": (0.0, 50_000.0),
}


@dataclass
class Incident:
    kind: str  # cpu_spike | memory_leak | down
    remaining: int


@dataclass
class FakeNode:
    node_id: str
    name: str
    region: str
    role: str
    values: dict[str, float]
    incident: Incident | None = None
    disk_drift: float = field(default=0.002)


class FleetSimulator:
    def __init__(self, size: int, seed: int = 42, incident_rate: float = 0.02) -> None:
        self._rng = random.Random(seed)
        self.incident_rate = incident_rate
        self.nodes: list[FakeNode] = []
        for i in range(size):
            role = ROLES[i % len(ROLES)]
            region = REGIONS[i % len(REGIONS)]
            base = BASELINES[role]
            values = {m: base[m] * self._rng.uniform(0.85, 1.15) for m in base}
            self.nodes.append(
                FakeNode(
                    node_id=f"node-{i + 1:02d}",
                    name=f"{role}-{region}-{i + 1:02d}",
                    region=region,
                    role=role,
                    values=values,
                )
            )

    def _step(self, node: FakeNode) -> None:
        base = BASELINES[node.role]
        for metric, value in node.values.items():
            lo, hi = BOUNDS[metric]
            spread = (hi - lo) * 0.02
            # mean-reverting random walk
            drift = (base[metric] - value) * 0.05
            new = value + drift + self._rng.gauss(0, spread)
            if metric == "disk":
                new = value + node.disk_drift  # disks only fill up
            node.values[metric] = min(max(new, lo), hi)

        if node.incident is None and self._rng.random() < self.incident_rate:
            kind = self._rng.choice(["cpu_spike", "cpu_spike", "memory_leak", "down"])
            node.incident = Incident(kind=kind, remaining=self._rng.randint(8, 25))
        if node.incident is not None:
            inc = node.incident
            if inc.kind == "cpu_spike":
                node.values["cpu"] = min(100.0, node.values["cpu"] + self._rng.uniform(25, 45))
            elif inc.kind == "memory_leak":
                node.values["memory"] = min(100.0, node.values["memory"] + 2.5)
            inc.remaining -= 1
            if inc.remaining <= 0:
                node.incident = None
                if inc.kind == "memory_leak":
                    node.values["memory"] = BASELINES[node.role]["memory"]

    def _status(self, node: FakeNode) -> NodeStatus:
        if node.incident is not None and node.incident.kind == "down":
            return NodeStatus.DOWN
        v = node.values
        if v["cpu"] > 90 or v["memory"] > 90 or v["disk"] > 95:
            return NodeStatus.DEGRADED
        return NodeStatus.HEALTHY

    def collect(self, now: float) -> list[NodeSnapshot]:
        out: list[NodeSnapshot] = []
        for node in self.nodes:
            self._step(node)
            status = self._status(node)
            metrics = {m: round(v, 2) for m, v in node.values.items()}
            if status == NodeStatus.DOWN:
                metrics = {m: 0.0 for m in metrics}
            out.append(
                NodeSnapshot(
                    node_id=node.node_id,
                    name=node.name,
                    region=node.region,
                    role=node.role,
                    status=status,
                    ts=now,
                    metrics=metrics,
                )
            )
        return out
