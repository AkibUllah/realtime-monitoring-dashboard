"""FastAPI application entry point."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.service import MonitoringService


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s"))
        root.addHandler(handler)
    root.setLevel(level.upper())


settings = get_settings()
configure_logging(settings.log_level)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    service = MonitoringService(settings)
    app.state.service = service
    if settings.collector_enabled:
        await service.tick()  # populate immediately so the first client sees data
        await service.start()
        log.info(
            "collector started: %d fleet nodes + host=%s every %.1fs",
            settings.fleet_size,
            service.host is not None,
            settings.collect_interval_seconds,
        )
    yield
    await service.stop()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Host + fleet metrics, ring-buffer history, alert rules and a WebSocket stream.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(router)
