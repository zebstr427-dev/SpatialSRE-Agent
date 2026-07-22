import asyncio
import sys

import pytest

from app.core import asyncio_compat


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific Psycopg compatibility")
def test_windows_uses_selector_event_loop_policy() -> None:
    previous_policy = asyncio.get_event_loop_policy()
    try:
        asyncio_compat.configure_asyncio_event_loop()

        assert isinstance(
            asyncio.get_event_loop_policy(),
            asyncio.WindowsSelectorEventLoopPolicy,
        )
    finally:
        asyncio.set_event_loop_policy(previous_policy)


def test_selector_event_loop_factory_returns_selector_loop() -> None:
    loop = asyncio_compat.create_selector_event_loop()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


def test_windows_uvicorn_uses_project_selector_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")

    assert asyncio_compat.get_uvicorn_loop() == (
        "app.core.asyncio_compat:create_selector_event_loop"
    )
