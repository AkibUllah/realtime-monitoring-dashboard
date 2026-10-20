"""Shared data types."""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field

METRICS: tuple[str, ...] = ("cpu", "memory", "disk", "net_rx", "net_tx")
METRIC_UNITS: dict[str, str] = {
    "cpu": "%",
    "memory": "%",
    "disk": "%",
    "net_rx": "kbps",
    "net_tx": "kbps",
}


class NodeStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass(frozen=True)
class Sample:
    """One metric reading. ``ts`` is a Unix timestamp in seconds (float)."""

    node_id: str
    metric: str
    value: float
    ts: float


@dataclass
class NodeSnapshot:
    node_id: str
    name: str
    region: str
    role: str
    status: NodeStatus
    ts: float
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    def samples(self) -> list[Sample]:
        return [Sample(self.node_id, m, v, self.ts) for m, v in self.metrics.items()]
