"""Доменные модели предметной области CRM."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    """Приоритеты выполнения заявок."""

    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
    CRITICAL = "Наивысший"


class Status(str, Enum):
    """Жизненный цикл заявки."""

    NEW = "Новая"
    IN_PROGRESS = "В работе"
    WAITING_CLIENT = "Ожидает ответа клиента"
    RESOLVED = "Решена"
    CLOSED = "Закрыта"


class Role(str, Enum):
    """Роли пользователей в системе."""

    CLIENT = "Клиент"
    OPERATOR = "Оператор"
    ADMIN = "Администратор"


@dataclass
class User:
    """Модель пользователя системы."""

    id: int
    name: str
    email: str
    role: Role


@dataclass(frozen=True)
class TicketDraft:
    """Данные новой заявки до сохранения и присвоения идентификатора."""

    title: str
    description: str
    client_name: str
    client_email: str
    priority: Priority
    confidence_score: float


@dataclass(kw_only=True)
class TicketAdd:
    """Данные заявки без идентификатора."""

    title: str
    description: str
    client_name: str
    client_email: str | None = None
    priority: Priority
    confidence_score: float
    status: Status = Status.NEW
    operator_name: str | None = None
    manual_priority_override: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(kw_only=True)
class Ticket(TicketAdd):
    """Сохранённая заявка: данные заявки плюс идентификатор."""

    id: int


@dataclass(frozen=True)
class TicketAuditLog:
    """Запись журнала аудита ручного изменения приоритета."""

    id: int
    ticket_id: int
    changed_by_name: str
    old_priority: Priority
    new_priority: Priority
    reason: str | None
    created_at: datetime
