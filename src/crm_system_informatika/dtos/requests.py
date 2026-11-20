"""Pydantic-схемы входящих запросов API."""

import re

from pydantic import BaseModel, Field, field_validator

from ..models import Priority, Status

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class TicketCreateRequest(BaseModel):
    """Схема запроса на создание новой клиентской заявки."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Краткая тема обращения",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Подробное описание проблемы",
    )
    client_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Имя клиента",
    )
    client_email: str = Field(
        ...,
        max_length=255,
        description="Электронная почта клиента",
    )

    @field_validator("client_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Проверить корректность формата электронной почты."""
        cleaned = value.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Неверный формат электронной почты.")
        return cleaned


class TicketTakeRequest(BaseModel):
    """Схема запроса на назначение оператора и взятие заявки в работу."""

    operator_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Имя оператора поддержки",
    )
    operator_email: str | None = Field(
        default=None,
        max_length=255,
        description="Опциональный email оператора",
    )


class TicketPriorityOverrideRequest(BaseModel):
    """Схема запроса на ручное переопределение приоритета заявки."""

    priority: Priority = Field(..., description="Новый уровень приоритета")
    operator_name: str | None = Field(
        default=None,
        max_length=255,
        description="Имя оператора, выполнившего корректировку",
    )
    reason: str | None = Field(
        default=None,
        max_length=255,
        description="Причина ручного изменения приоритета",
    )


class TicketStatusUpdateRequest(BaseModel):
    """Схема запроса на обновление статуса заявки."""

    status: Status = Field(..., description="Новый статус жизненного цикла")
