"""Единая точка входа CRM-системы."""

import sys

import uvicorn

from .app import create_app
from .cli import run_cli
from .configs.settings import settings

app = create_app()


def main() -> None:
    """Запустить веб-сервер FastAPI или консольный интерфейс при передаче --cli."""
    if "--cli" in sys.argv:
        run_cli()
        return

    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
    )


if __name__ == "__main__":
    main()
