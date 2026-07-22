from dataclasses import dataclass

import pytest
from psycopg.rows import dict_row

from app.config import Settings
from app.core import checkpoint
from app.core.checkpoint import (
    build_checkpoint_serializer,
    create_checkpoint_pool,
    open_checkpoint_runtime,
)


@dataclass
class UntrustedCheckpointValue:
    value: str


def test_checkpoint_serializer_does_not_recreate_untrusted_python_types() -> None:
    serializer = build_checkpoint_serializer()

    payload = serializer.dumps_typed(UntrustedCheckpointValue("payload"))
    restored = serializer.loads_typed(payload)

    assert restored == {"value": "payload"}
    assert not isinstance(restored, UntrustedCheckpointValue)


def test_checkpoint_pool_uses_langgraph_required_connection_options() -> None:
    settings = Settings(
        _env_file=None,
        checkpoint_pool_min_size=2,
        checkpoint_pool_max_size=4,
        checkpoint_pool_timeout=7.5,
    )

    pool = create_checkpoint_pool(settings)

    assert pool.min_size == 2
    assert pool.max_size == 4
    assert pool.timeout == 7.5
    assert pool.kwargs["autocommit"] is True
    assert pool.kwargs["prepare_threshold"] == 0
    assert pool.kwargs["row_factory"] is dict_row


@pytest.mark.asyncio
async def test_checkpoint_startup_failure_is_propagated_without_memory_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingPool:
        def __init__(self) -> None:
            self.closed = False

        async def open(self, *, wait: bool, timeout: float) -> None:
            raise ConnectionError("checkpoint database unavailable")

        async def close(self) -> None:
            self.closed = True

    pool = FailingPool()
    monkeypatch.setattr(checkpoint, "create_checkpoint_pool", lambda _settings: pool)

    with pytest.raises(ConnectionError, match="checkpoint database unavailable"):
        async with open_checkpoint_runtime(Settings(_env_file=None)):
            pytest.fail("runtime must not fall back to an in-memory checkpointer")

    assert pool.closed
