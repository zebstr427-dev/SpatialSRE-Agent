"""Event-loop compatibility required by Psycopg async connections on Windows."""

import asyncio
import sys


def configure_asyncio_event_loop() -> None:
    """Install a Selector policy on Windows before an event loop is created."""

    if sys.platform != "win32":
        return

    selector_policy = asyncio.WindowsSelectorEventLoopPolicy
    if not isinstance(asyncio.get_event_loop_policy(), selector_policy):
        asyncio.set_event_loop_policy(selector_policy())
