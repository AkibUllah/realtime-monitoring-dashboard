from __future__ import annotations

import pytest

from app.alerts.engine import AlertEngine, AlertState, Severity
from app.models import NodeSnapshot, NodeStatus


def snap(node_id: str, cpu: float, ts: float, role: str = "api") -> NodeSnapshot:
    return NodeSnapshot(
        node_id, node_id, "dhaka-1", role, NodeStatus.HEALTHY, ts, {"cpu": cpu, "memory": 40.0}
    )


def test_rule_without_duration_fires_immediately_and_resolves() -> None:
    eng = AlertEngine()
    rule = eng.add_rule(name="cpu", metric="cpu", op=">", threshold=80)
    assert eng.evaluate([snap("a", 50, 0)], now=0) == []
    fired = eng.evaluate([snap("a", 95, 1)], now=1)
    assert len(fired) == 1 and fired[0].state == AlertState.FIRING and fired[0].rule_id == rule.id
    assert eng.statuses[(rule.id, "a")].state == AlertState.FIRING
    resolved = eng.evaluate([snap("a", 20, 2)], now=2)
    assert len(resolved) == 1 and resolved[0].state == AlertState.RESOLVED
    assert eng.firing_count() == 0


def test_duration_must_be_sustained_before_firing() -> None:
    eng = AlertEngine()
    eng.add_rule(name="cpu", metric="cpu", op=">", threshold=80, for_seconds=10)
    assert eng.evaluate([snap("a", 90, 0)], now=0) == []
    assert eng.evaluate([snap("a", 91, 5)], now=5) == []
    fired = eng.evaluate([snap("a", 92, 10)], now=10)
    assert len(fired) == 1
    # still firing on later ticks, no duplicate notification
    assert eng.evaluate([snap("a", 93, 12)], now=12) == []
    assert len(eng.notifications) == 1


def test_breach_interrupted_resets_duration_timer() -> None:
    eng = AlertEngine()
    eng.add_rule(name="cpu", metric="cpu", op=">", threshold=80, for_seconds=10)
    eng.evaluate([snap("a", 90, 0)], now=0)
    eng.evaluate([snap("a", 10, 5)], now=5)  # dips below -> timer resets
    assert eng.evaluate([snap("a", 90, 12)], now=12) == []
    assert eng.evaluate([snap("a", 90, 22)], now=22) != []


def test_resolved_state_returns_to_ok_after_ttl() -> None:
    eng = AlertEngine(resolved_ttl=30)
    eng.add_rule(name="cpu", metric="cpu", op=">", threshold=80)
    eng.evaluate([snap("a", 90, 0)], now=0)
    eng.evaluate([snap("a", 10, 1)], now=1)
    assert eng.active()[0].state == AlertState.RESOLVED
    eng.evaluate([snap("a", 10, 31)], now=31)
    assert eng.active() == []


def test_rules_track_state_per_node() -> None:
    eng = AlertEngine()
    eng.add_rule(name="cpu", metric="cpu", op=">", threshold=80)
    fired = eng.evaluate([snap("a", 90, 0), snap("b", 10, 0), snap("c", 99, 0)], now=0)
    assert sorted(n.node_id for n in fired) == ["a", "c"]
    assert eng.firing_count() == 2


def test_node_filter_matches_id_role_or_region() -> None:
    eng = AlertEngine()
    eng.add_rule(name="db cpu", metric="cpu", op=">", threshold=50, node_filter="db")
    fired = eng.evaluate([snap("a", 90, 0, role="api"), snap("b", 90, 0, role="db")], now=0)
    assert [n.node_id for n in fired] == ["b"]


def test_disabled_rule_is_skipped_and_update_clears_state() -> None:
    eng = AlertEngine()
    rule = eng.add_rule(name="cpu", metric="cpu", op=">", threshold=80)
    eng.evaluate([snap("a", 90, 0)], now=0)
    assert eng.firing_count() == 1
    eng.update_rule(rule.id, enabled=False)
    assert eng.firing_count() == 0
    assert eng.evaluate([snap("a", 95, 1)], now=1) == []


def test_invalid_operator_rejected() -> None:
    with pytest.raises(ValueError):
        AlertEngine().add_rule(name="x", metric="cpu", op="!=", threshold=1)


def test_notification_message_and_severity() -> None:
    eng = AlertEngine()
    eng.add_rule(name="Disk full", metric="cpu", op=">=", threshold=90, severity=Severity.CRITICAL)
    (n,) = eng.evaluate([snap("db-1", 95.5, 0)], now=0)
    assert n.message == "[CRITICAL] Disk full FIRING on db-1: cpu=95.5 >= 90"
    assert n.severity == Severity.CRITICAL
    assert n.to_dict()["state"] == "firing"


def test_delete_rule_removes_statuses() -> None:
    eng = AlertEngine()
    rule = eng.add_rule(name="cpu", metric="cpu", op=">", threshold=80)
    eng.evaluate([snap("a", 90, 0)], now=0)
    eng.delete_rule(rule.id)
    assert eng.rules == {} and eng.statuses == {}
