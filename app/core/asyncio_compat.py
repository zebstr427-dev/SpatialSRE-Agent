"""Event-loop compatibility required by Psycopg async connections on Windows."""

import asyncio
import sys

UVICORN_SELECTOR_LOOP = "app.core.asyncio_compat:create_selector_event_loop"


def create_selector_event_loop() -> asyncio.AbstractEventLoop:
    """Build the loop Uvicorn must use for Psycopg async I/O on Windows."""

    return asyncio.SelectorEventLoop()


def get_uvicorn_loop() -> str:
    """Return a Uvicorn loop setting compatible with the current platform."""

    return UVICORN_SELECTOR_LOOP if sys.platform == "win32" else "auto"


def configure_asyncio_event_loop() -> None:
    """Install a Selector policy on Windows before an event loop is created."""

    if sys.platform != "win32":
        return

    selector_policy = asyncio.WindowsSelectorEventLoopPolicy
    if not isinstance(asyncio.get_event_loop_policy(), selector_policy):
        asyncio.set_event_loop_policy(selector_policy())
