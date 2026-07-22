import json

import pytest

from app.api import health


@pytest.mark.asyncio
async def test_health_is_healthy_when_milvus_is_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health.milvus_manager, "health_check", lambda: True)

    response = await health.health_check()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["data"]["status"] == "healthy"
    assert payload["data"]["milvus"]["status"] == "connected"


@pytest.mark.asyncio
async def test_health_is_unhealthy_when_milvus_is_disconnected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health.milvus_manager, "health_check", lambda: False)

    response = await health.health_check()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["data"]["status"] == "unhealthy"
    assert payload["data"]["milvus"]["status"] == "disconnected"
