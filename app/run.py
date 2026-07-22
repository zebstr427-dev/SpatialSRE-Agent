"""Platform-aware Uvicorn launcher."""

from app.config import config
from app.core.asyncio_compat import configure_asyncio_event_loop, get_uvicorn_loop


def main() -> None:
    configure_asyncio_event_loop()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info",
        loop=get_uvicorn_loop(),
    )


if __name__ == "__main__":
    main()
