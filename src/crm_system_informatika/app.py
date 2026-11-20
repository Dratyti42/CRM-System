"""Фабрика FastAPI-приложения с регистрацией роутеров и обработчиков ошибок."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .api.routes import router as api_router
from .configs.settings import settings
from .exceptions import (
    DomainValidationError,
    InvalidStatusTransitionError,
    TicketNotFoundError,
)
from .web.routes import router as web_router


def create_app() -> FastAPI:
    """Создать и сконфигурировать экземпляр FastAPI-приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    application = FastAPI(
        title=settings.app_title,
        version="0.2.0",
        description="REST API и веб-интерфейс CRM-системы с ИИ-приоритизацией заявок.",
    )

    @application.exception_handler(TicketNotFoundError)
    async def handle_not_found(
        request: Request, exc: TicketNotFoundError
    ) -> JSONResponse:
        """Вернуть HTTP 404 при обращении к несуществующей заявке."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @application.exception_handler(InvalidStatusTransitionError)
    async def handle_invalid_transition(
        request: Request, exc: InvalidStatusTransitionError
    ) -> JSONResponse:
        """Вернуть HTTP 400 при нарушении жизненного цикла статуса."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(DomainValidationError)
    async def handle_validation_error(
        request: Request, exc: DomainValidationError
    ) -> JSONResponse:
        """Вернуть HTTP 422 при ошибке доменной валидации."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    application.include_router(api_router)
    application.include_router(web_router)
    return application
