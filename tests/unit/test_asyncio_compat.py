import asyncio
import sys

import pytest

from app.core.asyncio_compat import configure_asyncio_event_loop


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific Psycopg compatibility")
def test_windows_uses_selector_event_loop_policy() -> None:
    previous_policy = asyncio.get_event_loop_policy()
    try:
        configure_asyncio_event_loop()

        assert isinstance(
            asyncio.get_event_loop_policy(),
            asyncio.WindowsSelectorEventLoopPolicy,
        )
    finally:
        asyncio.set_event_loop_policy(previous_policy)
