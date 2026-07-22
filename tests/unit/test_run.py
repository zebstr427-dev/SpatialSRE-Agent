import sys
from types import SimpleNamespace
from typing import Any

from app import run


def test_launcher_passes_platform_compatible_loop_factory(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda *args, **kwargs: captured.update(kwargs)
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    run.main()

    assert captured["loop"] == (
        "app.core.asyncio_compat:create_selector_event_loop"
    )
