from __future__ import annotations

from app.collectors.fleet import FleetSimulator
from app.models import METRICS, NodeStatus


def test_fleet_is_deterministic_for_seed() -> None:
    a = FleetSimulator(5, seed=7)
    b = FleetSimulator(5, seed=7)
    for t in range(20):
        sa = a.collect(float(t))
        sb = b.collect(float(t))
        assert [s.metrics for s in sa] == [s.metrics for s in sb]


def test_fleet_snapshots_have_all_metrics_in_bounds() -> None:
    sim = FleetSimulator(10, seed=1)
    for t in range(200):
        for snap in sim.collect(float(t)):
            assert set(snap.metrics) == set(METRICS)
            assert 0 <= snap.metrics["cpu"] <= 100
            assert 0 <= snap.metrics["memory"] <= 100
            assert 0 <= snap.metrics["disk"] <= 100
            assert snap.metrics["net_rx"] >= 0


def test_fleet_produces_incidents_over_time() -> None:
    sim = FleetSimulator(8, seed=3, incident_rate=0.2)
    statuses = set()
    for t in range(300):
        for snap in sim.collect(float(t)):
            statuses.add(snap.status)
    assert NodeStatus.DOWN in statuses
    assert NodeStatus.DEGRADED in statuses


def test_down_node_reports_zero_metrics() -> None:
    sim = FleetSimulator(3, seed=5, incident_rate=1.0)
    for t in range(50):
        for snap in sim.collect(float(t)):
            if snap.status == NodeStatus.DOWN:
                assert all(v == 0.0 for v in snap.metrics.values())
                return
    raise AssertionError("expected at least one DOWN node with incident_rate=1.0")
