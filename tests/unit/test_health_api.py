import json
from types import SimpleNamespace

import pytest

from app.api import health


class FakeCheckpointRuntime:
    def __init__(self, healthy: bool) -> None:
        self.healthy = healthy

    async def health_check(self) -> bool:
        return self.healthy


def _request(*, checkpoint_healthy: bool) -> SimpleNamespace:
    state = SimpleNamespace(
        checkpoint_runtime=FakeCheckpointRuntime(checkpoint_healthy)
    )
    return SimpleNamespace(app=SimpleNamespace(state=state))


@pytest.mark.asyncio
async def test_health_is_healthy_when_milvus_is_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health.milvus_manager, "health_check", lambda: True)

    response = await health.health_check(_request(checkpoint_healthy=True))
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["data"]["service"] == "SpatialSRE-Agent"
    assert payload["data"]["status"] == "healthy"
    assert payload["data"]["milvus"]["status"] == "connected"
    assert payload["data"]["checkpoint_store"]["status"] == "connected"


@pytest.mark.asyncio
async def test_health_is_unhealthy_when_milvus_is_disconnected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health.milvus_manager, "health_check", lambda: False)

    response = await health.health_check(_request(checkpoint_healthy=True))
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["data"]["status"] == "unhealthy"
    assert payload["data"]["milvus"]["status"] == "disconnected"


@pytest.mark.asyncio
async def test_health_is_unhealthy_when_checkpoint_store_is_disconnected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health.milvus_manager, "health_check", lambda: True)

    response = await health.health_check(_request(checkpoint_healthy=False))
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["data"]["status"] == "unhealthy"
    assert payload["data"]["checkpoint_store"]["status"] == "disconnected"
