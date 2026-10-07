from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Priority(str, Enum):
    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
    CRITICAL = "Наивысший"


class Status(str, Enum):
    NEW = "Новая"
    IN_PROGRESS = "В работе"
    WAITING_CLIENT = "Ожидает ответа клиента"
    RESOLVED = "Решена"
    CLOSED = "Закрыта"


class Role(str, Enum):
    CLIENT = "Клиент"
    OPERATOR = "Оператор"
    ADMIN = "Администратор"


@dataclass
class User:
    id: int
    name: str
    role: Role


@dataclass
class Ticket:
    id: int
    title: str
    description: str
    client_name: str
    priority: Priority
    confidence_score: float
    status: Status = Status.NEW
    operator_name: Optional[str] = None
    manual_priority_override: bool = False