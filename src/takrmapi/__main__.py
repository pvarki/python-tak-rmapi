"""Entrypoint module  `python -m takrmapi`."""

import uvicorn

from takrmapi.settings import settings


def main() -> None:
    """Entrypoint of the application."""
    uvicorn.run(
        "takrmapi.web.application:get_app",
        workers=settings.workers_count,
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.value.lower(),
        factory=True,
    )


if __name__ == "__main__":
    main()
