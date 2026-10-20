from __future__ import annotations

import asyncio
import time

from fastapi.testclient import TestClient


def tick(client: TestClient, n: int = 1, start: float | None = None) -> None:
    """Run n collection ticks 2s apart, ending roughly at the current time."""
    svc = client.app.state.service  # type: ignore[attr-defined]
    start = start if start is not None else time.time() - 2 * n
    for i in range(n):
        asyncio.run(svc.tick(now=start + i * 2))


def test_health_and_summary(client: TestClient) -> None:
    tick(client, 2)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["nodes"] == 4 and body["ticks"] == 2


def test_nodes_and_metrics_catalogue(client: TestClient) -> None:
    tick(client)
    nodes = client.get("/api/nodes").json()
    assert [n["node_id"] for n in nodes] == ["node-01", "node-02", "node-03", "node-04"]
    assert set(nodes[0]["metrics"]) == {"cpu", "memory", "disk", "net_rx", "net_tx"}
    assert {m["name"] for m in client.get("/api/metrics").json()} == {
        "cpu",
        "memory",
        "disk",
        "net_rx",
        "net_tx",
    }


def test_history_endpoint_with_range_and_step(client: TestClient) -> None:
    tick(client, 30, start=time.time() - 60)  # 30 samples over the last minute
    r = client.get(
        "/api/metrics/history", params={"node": "node-01", "metric": "cpu", "range": "2m"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["unit"] == "%" and len(body["points"]) == 30
    r = client.get(
        "/api/metrics/history",
        params={"node": "node-01", "metric": "cpu", "range": "2m", "step": 10},
    )
    assert len(r.json()["points"]) <= 7
    assert (
        client.get("/api/metrics/history", params={"node": "nope", "metric": "cpu"}).status_code
        == 404
    )
    assert (
        client.get("/api/metrics/history", params={"node": "node-01", "metric": "gpu"}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/metrics/history", params={"node": "node-01", "metric": "cpu", "range": "soon"}
        ).status_code
        == 422
    )


def test_rule_crud(client: TestClient) -> None:
    initial = client.get("/api/alerts/rules").json()
    assert len(initial) == 5
    r = client.post(
        "/api/alerts/rules",
        json={
            "name": "Edge CPU",
            "metric": "cpu",
            "op": ">",
            "threshold": 70,
            "for_seconds": 4,
            "node_filter": "edge",
        },
    )
    assert r.status_code == 201
    rule = r.json()
    assert rule["severity"] == "warning" and rule["node_filter"] == "edge"
    r = client.patch(
        f"/api/alerts/rules/{rule['id']}", json={"threshold": 75, "severity": "critical"}
    )
    assert r.json()["threshold"] == 75 and r.json()["severity"] == "critical"
    assert (
        client.post(
            "/api/alerts/rules", json={"name": "bad", "metric": "cpu", "op": "!=", "threshold": 1}
        ).status_code
        == 422
    )
    assert client.delete(f"/api/alerts/rules/{rule['id']}").status_code == 204
    assert client.delete(f"/api/alerts/rules/{rule['id']}").status_code == 404
    assert len(client.get("/api/alerts/rules").json()) == 5


def test_alert_fires_through_api(client: TestClient) -> None:
    client.post(
        "/api/alerts/rules", json={"name": "Any CPU", "metric": "cpu", "op": ">=", "threshold": 0}
    )
    tick(client)
    active = client.get("/api/alerts").json()
    assert len([a for a in active if a["state"] == "firing"]) == 4
    notes = client.get("/api/notifications").json()
    assert len(notes) == 4 and notes[0]["rule_name"] == "Any CPU"


def test_websocket_snapshot_then_live_ticks(client: TestClient) -> None:
    tick(client, 3)
    with client.websocket_connect("/ws/metrics") as ws:
        first = ws.receive_json()
        assert first["type"] == "snapshot"
        assert len(first["nodes"]) == 4
        assert len(first["history"]["node-01"]["cpu"]) == 3
        assert len(first["rules"]) == 5
        assert client.app.state.service.broadcaster.client_count == 1  # type: ignore[attr-defined]

        svc = client.app.state.service  # type: ignore[attr-defined]
        now = time.time()
        client.portal.call(svc.tick, now)  # type: ignore[attr-defined]
        live = ws.receive_json()
        assert live["type"] == "tick" and live["ts"] == now
        assert [n["node_id"] for n in live["nodes"]] == ["node-01", "node-02", "node-03", "node-04"]

        ws.send_text('{"type":"ping"}')
        assert ws.receive_json()["type"] == "pong"
    assert client.app.state.service.broadcaster.client_count == 0  # type: ignore[attr-defined]
