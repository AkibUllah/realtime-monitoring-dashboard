"""Threshold + duration alert rules with OK / FIRING / RESOLVED state."""

from __future__ import annotations

import enum
import itertools
import logging
import operator
from collections import deque
from dataclasses import asdict, dataclass, field

from app.models import NodeSnapshot

log = logging.getLogger("alerts")

_OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le}


class AlertState(str, enum.Enum):
    OK = "ok"
    FIRING = "firing"
    RESOLVED = "resolved"


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    id: int
    name: str
    metric: str
    op: str
    threshold: float
    for_seconds: float = 0.0
    severity: Severity = Severity.WARNING
    node_filter: str | None = None  # exact node id, role name, or None for all nodes
    enabled: bool = True

    def matches(self, node: NodeSnapshot) -> bool:
        if not self.node_filter:
            return True
        return self.node_filter in (node.node_id, node.role, node.region)

    def breached(self, value: float) -> bool:
        return _OPS[self.op](value, self.threshold)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class AlertStatus:
    rule_id: int
    node_id: str
    state: AlertState = AlertState.OK
    breach_since: float | None = None
    fired_at: float | None = None
    resolved_at: float | None = None
    last_value: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d


@dataclass
class Notification:
    id: int
    ts: float
    rule_id: int
    rule_name: str
    node_id: str
    state: AlertState
    severity: Severity
    value: float
    message: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        d["severity"] = self.severity.value
        return d


@dataclass
class AlertEngine:
    rules: dict[int, AlertRule] = field(default_factory=dict)
    statuses: dict[tuple[int, str], AlertStatus] = field(default_factory=dict)
    notifications: deque[Notification] = field(default_factory=lambda: deque(maxlen=500))
    resolved_ttl: float = 60.0
    _rule_ids: itertools.count = field(default_factory=lambda: itertools.count(1))
    _notif_ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    # ---- rule management -------------------------------------------------------------
    def add_rule(self, **kwargs) -> AlertRule:  # type: ignore[no-untyped-def]
        if kwargs.get("op") not in _OPS:
            raise ValueError(f"op must be one of {sorted(_OPS)}")
        rule = AlertRule(id=next(self._rule_ids), **kwargs)
        self.rules[rule.id] = rule
        return rule

    def update_rule(self, rule_id: int, **changes) -> AlertRule:  # type: ignore[no-untyped-def]
        rule = self.rules[rule_id]
        if "op" in changes and changes["op"] not in _OPS:
            raise ValueError(f"op must be one of {sorted(_OPS)}")
        for k, v in changes.items():
            if v is not None:
                setattr(rule, k, v)
        # state for this rule is no longer meaningful
        for key in [k for k in self.statuses if k[0] == rule_id]:
            del self.statuses[key]
        return rule

    def delete_rule(self, rule_id: int) -> None:
        del self.rules[rule_id]
        for key in [k for k in self.statuses if k[0] == rule_id]:
            del self.statuses[key]

    # ---- evaluation ------------------------------------------------------------------
    def evaluate(self, nodes: list[NodeSnapshot], now: float) -> list[Notification]:
        """Evaluate every enabled rule against the latest snapshots. Returns new notifications."""
        emitted: list[Notification] = []
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            for node in nodes:
                if not rule.matches(node) or rule.metric not in node.metrics:
                    continue
                value = node.metrics[rule.metric]
                key = (rule.id, node.node_id)
                status = self.statuses.get(key)
                if status is None:
                    status = self.statuses[key] = AlertStatus(rule_id=rule.id, node_id=node.node_id)
                status.last_value = value

                if rule.breached(value):
                    if status.breach_since is None:
                        status.breach_since = now
                    held_for = now - status.breach_since
                    if status.state != AlertState.FIRING and held_for >= rule.for_seconds:
                        status.state = AlertState.FIRING
                        status.fired_at = now
                        status.resolved_at = None
                        emitted.append(
                            self._notify(rule, node.node_id, AlertState.FIRING, value, now)
                        )
                else:
                    status.breach_since = None
                    if status.state == AlertState.FIRING:
                        status.state = AlertState.RESOLVED
                        status.resolved_at = now
                        emitted.append(
                            self._notify(rule, node.node_id, AlertState.RESOLVED, value, now)
                        )
                    elif (
                        status.state == AlertState.RESOLVED
                        and status.resolved_at is not None
                        and now - status.resolved_at >= self.resolved_ttl
                    ):
                        status.state = AlertState.OK
        return emitted

    def _notify(
        self, rule: AlertRule, node_id: str, state: AlertState, value: float, now: float
    ) -> Notification:
        verb = "FIRING" if state == AlertState.FIRING else "RESOLVED"
        message = (
            f"[{rule.severity.value.upper()}] {rule.name} {verb} on {node_id}: "
            f"{rule.metric}={value:g} {rule.op} {rule.threshold:g}"
        )
        n = Notification(
            id=next(self._notif_ids),
            ts=now,
            rule_id=rule.id,
            rule_name=rule.name,
            node_id=node_id,
            state=state,
            severity=rule.severity,
            value=value,
            message=message,
        )
        self.notifications.append(n)
        log.warning(message) if state == AlertState.FIRING else log.info(message)
        return n

    def active(self) -> list[AlertStatus]:
        return [s for s in self.statuses.values() if s.state != AlertState.OK]

    def firing_count(self) -> int:
        return sum(1 for s in self.statuses.values() if s.state == AlertState.FIRING)


def default_rules(engine: AlertEngine) -> None:
    engine.add_rule(
        name="High CPU",
        metric="cpu",
        op=">",
        threshold=85,
        for_seconds=10,
        severity=Severity.WARNING,
    )
    engine.add_rule(
        name="CPU saturated",
        metric="cpu",
        op=">=",
        threshold=97,
        for_seconds=20,
        severity=Severity.CRITICAL,
    )
    engine.add_rule(
        name="Memory pressure",
        metric="memory",
        op=">",
        threshold=90,
        for_seconds=15,
        severity=Severity.WARNING,
    )
    engine.add_rule(
        name="Disk almost full",
        metric="disk",
        op=">",
        threshold=92,
        for_seconds=0,
        severity=Severity.CRITICAL,
    )
    engine.add_rule(
        name="Node unreachable (no traffic)",
        metric="net_rx",
        op="<=",
        threshold=0,
        for_seconds=6,
        severity=Severity.CRITICAL,
    )
