from dataclasses import dataclass

from psycopg.rows import dict_row

from app.config import Settings
from app.core.checkpoint import build_checkpoint_serializer, create_checkpoint_pool


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
