from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.alerts.engine import Severity
from app.models import METRICS

Metric = Literal["cpu", "memory", "disk", "net_rx", "net_tx"]
Op = Literal[">", ">=", "<", "<="]


class RuleIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    metric: Metric
    op: Op
    threshold: float
    for_seconds: float = Field(default=0, ge=0, le=86400)
    severity: Severity = Severity.WARNING
    node_filter: str | None = Field(default=None, max_length=40)
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    metric: Metric | None = None
    op: Op | None = None
    threshold: float | None = None
    for_seconds: float | None = Field(default=None, ge=0, le=86400)
    severity: Severity | None = None
    node_filter: str | None = Field(default=None, max_length=40)
    enabled: bool | None = None


assert set(Metric.__args__) == set(METRICS)  # type: ignore[attr-defined]
