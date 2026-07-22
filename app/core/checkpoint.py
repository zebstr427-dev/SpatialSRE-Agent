"""PostgreSQL lifecycle and security boundary for LangGraph checkpoints."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from loguru import logger
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import Settings


def build_checkpoint_serializer() -> JsonPlusSerializer:
    """Create a serializer that never reconstructs unapproved Python types."""

    return JsonPlusSerializer(
        pickle_fallback=False,
        allowed_msgpack_modules=None,
    )


def create_checkpoint_pool(settings: Settings) -> AsyncConnectionPool:
    """Build a closed pool with the connection semantics required by LangGraph."""

    return AsyncConnectionPool(
        conninfo=settings.checkpoint_database_url.get_secret_value(),
        min_size=settings.checkpoint_pool_min_size,
        max_size=settings.checkpoint_pool_max_size,
        timeout=settings.checkpoint_pool_timeout,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        check=AsyncConnectionPool.check_connection,
        name="langgraph-checkpoints",
        open=False,
    )


@dataclass(slots=True)
class CheckpointRuntime:
    """Resources owned by the FastAPI application lifespan."""

    pool: AsyncConnectionPool
    saver: AsyncPostgresSaver

    async def health_check(self) -> bool:
        try:
            async with self.pool.connection() as connection:
                await connection.execute("SELECT 1")
            return True
        except Exception as exc:
            logger.warning(f"Checkpoint store health check failed: {type(exc).__name__}")
            return False


@asynccontextmanager
async def open_checkpoint_runtime(settings: Settings) -> AsyncIterator[CheckpointRuntime]:
    """Open, initialize, and always close the checkpoint connection pool."""

    pool = create_checkpoint_pool(settings)
    try:
        await pool.open(wait=True, timeout=settings.checkpoint_pool_timeout)
        saver = AsyncPostgresSaver(pool, serde=build_checkpoint_serializer())
        if settings.checkpoint_auto_setup:
            await saver.setup()
        logger.info("PostgreSQL checkpoint runtime initialized")
        yield CheckpointRuntime(pool=pool, saver=saver)
    finally:
        await pool.close()
        logger.info("PostgreSQL checkpoint runtime closed")
