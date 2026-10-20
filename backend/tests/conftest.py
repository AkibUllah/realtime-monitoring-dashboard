from __future__ import annotations

import os
from collections.abc import Iterator

os.environ["COLLECTOR_ENABLED"] = "false"
os.environ["HOST_COLLECTOR_ENABLED"] = "false"
os.environ["FLEET_SIZE"] = "4"
os.environ["SQLITE_PATH"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
