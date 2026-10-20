"""REST + WebSocket endpoints."""

from __future__ import annotations

import re
import time

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)

from app.api.schemas import RuleIn, RuleUpdate
from app.models import METRIC_UNITS, METRICS
from app.service import MonitoringService

router = APIRouter()

_RANGE_RE = re.compile(r"^(\d+)([smh])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600}


def parse_range(value: str) -> float:
    """'30s' | '15m' | '1h' -> seconds."""
    m = _RANGE_RE.match(value.strip())
    if not m:
        raise HTTPException(422, detail="range must look like 30s, 15m or 1h")
    return int(m.group(1)) * _UNIT_SECONDS[m.group(2)]


def service(request: Request) -> MonitoringService:
    return request.app.state.service  # type: ignore[no-any-return]


@router.get("/health", tags=["ops"])
def health(request: Request) -> dict:
    svc = service(request)
    return {"status": "ok", "service": "realtime-monitoring", **svc.summary()}


@router.get("/api/summary", tags=["metrics"])
def summary(request: Request) -> dict:
    return service(request).summary()


@router.get("/api/nodes", tags=["metrics"])
def nodes(request: Request) -> list[dict]:
    return [n.to_dict() for n in service(request).store.nodes()]


@router.get("/api/metrics", tags=["metrics"])
def metrics() -> list[dict]:
    return [{"name": m, "unit": METRIC_UNITS[m]} for m in METRICS]


@router.get("/api/metrics/history", tags=["metrics"])
def history(
    request: Request,
    node: str = Query(..., description="node id, e.g. host or node-01"),
    metric: str = Query(..., description="cpu | memory | disk | net_rx | net_tx"),
    range: str = Query("15m", alias="range"),
    step: float | None = Query(None, gt=0, description="downsample bucket in seconds"),
) -> dict:
    svc = service(request)
    if metric not in METRICS:
        raise HTTPException(422, detail=f"unknown metric '{metric}'")
    if svc.store.node(node) is None:
        raise HTTPException(404, detail=f"unknown node '{node}'")
    seconds = parse_range(range)
    now = time.time()
    points = svc.store.history(node, metric, now - seconds, step=step)
    return {
        "node": node,
        "metric": metric,
        "unit": METRIC_UNITS[metric],
        "range_seconds": seconds,
        "step": step,
        "points": [[p.ts, p.value] for p in points],
    }


@router.get("/api/snapshot", tags=["metrics"])
def snapshot(request: Request, range: str = Query("5m")) -> dict:
    return service(request).snapshot(history_seconds=parse_range(range))


@router.get("/api/alerts", tags=["alerts"])
def active_alerts(request: Request) -> list[dict]:
    return [a.to_dict() for a in service(request).alerts.active()]


@router.get("/api/alerts/rules", tags=["alerts"])
def list_rules(request: Request) -> list[dict]:
    return [r.to_dict() for r in service(request).alerts.rules.values()]


@router.post("/api/alerts/rules", tags=["alerts"], status_code=201)
def create_rule(payload: RuleIn, request: Request) -> dict:
    return service(request).alerts.add_rule(**payload.model_dump()).to_dict()


@router.patch("/api/alerts/rules/{rule_id}", tags=["alerts"])
def update_rule(rule_id: int, payload: RuleUpdate, request: Request) -> dict:
    engine = service(request).alerts
    if rule_id not in engine.rules:
        raise HTTPException(404, detail="rule not found")
    return engine.update_rule(rule_id, **payload.model_dump(exclude_unset=True)).to_dict()


@router.delete(
    "/api/alerts/rules/{rule_id}",
    tags=["alerts"],
    status_code=204,
    response_class=Response,
    response_model=None,
)
def delete_rule(rule_id: int, request: Request):  # type: ignore[no-untyped-def]
    engine = service(request).alerts
    if rule_id not in engine.rules:
        raise HTTPException(404, detail="rule not found")
    engine.delete_rule(rule_id)
    return Response(status_code=204)


@router.get("/api/notifications", tags=["alerts"])
def notifications(request: Request, limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    items = list(service(request).alerts.notifications)[-limit:]
    return [n.to_dict() for n in reversed(items)]


@router.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket) -> None:
    svc: MonitoringService = websocket.app.state.service
    await svc.broadcaster.connect(websocket)
    try:
        await websocket.send_json(svc.snapshot(history_seconds=300))
        while True:
            # Clients may send {"type": "ping"}; anything else is ignored. Disconnect ends the loop.
            msg = await websocket.receive_text()
            if msg == '{"type":"ping"}' or msg == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})
    except WebSocketDisconnect:
        pass
    finally:
        await svc.broadcaster.disconnect(websocket)
