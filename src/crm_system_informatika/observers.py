"""Событийная подсистема уведомлений (паттерн GoF: Observer)."""

import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .models import Priority, Ticket

logger = logging.getLogger(__name__)


class TicketEventType(str, Enum):
    """Типы доменных событий жизненного цикла заявки."""

    CREATED = "created"
    ASSIGNED = "assigned"
    PRIORITY_OVERRIDDEN = "priority_overridden"
    STATUS_CHANGED = "status_changed"


@dataclass(frozen=True)
class TicketEvent:
    """Событие, публикуемое при изменении состояния заявки."""

    event_type: TicketEventType
    ticket: Ticket
    details: str = ""


@dataclass(frozen=True)
class OperatorAlert:
    """Визуальное оповещение оператора о критичной заявке."""

    ticket_id: int
    title: str
    priority: Priority
    message: str
    created_at: datetime


class BaseTicketObserver(ABC):
    """Абстрактный наблюдатель за событиями заявок."""

    @abstractmethod
    def update(self, event: TicketEvent) -> None:
        """Обработать поступившее событие заявки."""


class ActivityLogObserver(BaseTicketObserver):
    """Наблюдатель для журналирования всех событий по заявкам."""

    def update(self, event: TicketEvent) -> None:
        """Записать событие в системный журнал."""
        logger.info(
            "Событие [%s] для заявки #%d (%s): %s",
            event.event_type.value,
            event.ticket.id,
            event.ticket.priority.value,
            event.details,
        )


class HighPriorityAlertObserver(BaseTicketObserver):
    """Наблюдатель, формирующий оповещения операторов о срочных заявках."""

    ALERT_PRIORITIES: frozenset[Priority] = frozenset(
        {Priority.HIGH, Priority.CRITICAL}
    )

    def __init__(self, max_alerts: int = 10) -> None:
        """Инициализировать буфер последних оповещений."""
        self._alerts: deque[OperatorAlert] = deque(maxlen=max_alerts)

    def update(self, event: TicketEvent) -> None:
        """Сохранить оповещение при создании или повышении приоритета до высокого."""
        if event.event_type not in {
            TicketEventType.CREATED,
            TicketEventType.PRIORITY_OVERRIDDEN,
        }:
            return
        if event.ticket.priority not in self.ALERT_PRIORITIES:
            return

        alert = OperatorAlert(
            ticket_id=event.ticket.id,
            title=event.ticket.title,
            priority=event.ticket.priority,
            message=(
                f"Заявка #{event.ticket.id} требует внимания: "
                f"приоритет «{event.ticket.priority.value}»."
            ),
            created_at=datetime.now(timezone.utc),
        )
        self._alerts.appendleft(alert)

    def get_recent_alerts(self) -> list[OperatorAlert]:
        """Вернуть актуальный список оповещений для панели оператора."""
        return list(self._alerts)


class TicketEventPublisher:
    """Издатель событий заявок, управляющий подписками наблюдателей."""

    def __init__(self, observers: list[BaseTicketObserver] | None = None) -> None:
        """Инициализировать издатель начальным списком наблюдателей."""
        self._observers: list[BaseTicketObserver] = list(observers or [])

    def subscribe(self, observer: BaseTicketObserver) -> None:
        """Подписать наблюдателя на события заявок."""
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: BaseTicketObserver) -> None:
        """Отписать наблюдателя от событий заявок."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: TicketEvent) -> None:
        """Оповестить всех подписанных наблюдателей о событии."""
        for observer in self._observers:
            observer.update(event)
