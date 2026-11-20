"""Провайдеры зависимостей FastAPI для внедрения через Depends."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from ..classifier import BasePriorityClassifier, ClassifierFactory
from ..configs.settings import settings
from ..database.session import get_session
from ..database.uow import BaseUnitOfWork, SQLAlchemyUnitOfWork
from ..observers import (
    ActivityLogObserver,
    HighPriorityAlertObserver,
    TicketEventPublisher,
)
from ..service import CRMService


@lru_cache
def get_classifier() -> BasePriorityClassifier:
    """Создать и закешировать классификатор заявок через фабрику."""
    return ClassifierFactory.create(
        strategy_name=settings.classifier_strategy,
        enable_fallback=True,
        enable_logging=True,
    )


@lru_cache
def get_alert_observer() -> HighPriorityAlertObserver:
    """Вернуть общий наблюдатель оповещений о срочных заявках."""
    return HighPriorityAlertObserver()


@lru_cache
def get_event_publisher() -> TicketEventPublisher:
    """Создать и закешировать издатель событий с подключенными наблюдателями."""
    return TicketEventPublisher(
        observers=[
            ActivityLogObserver(),
            get_alert_observer(),
        ]
    )


def get_uow(
    session: Annotated[Session, Depends(get_session)],
) -> BaseUnitOfWork:
    """Создать Unit of Work на базе SQLAlchemy Session текущего запроса."""
    return SQLAlchemyUnitOfWork(session=session)


def get_crm_service(
    uow: Annotated[BaseUnitOfWork, Depends(get_uow)],
    classifier: Annotated[BasePriorityClassifier, Depends(get_classifier)],
    publisher: Annotated[TicketEventPublisher, Depends(get_event_publisher)],
) -> CRMService:
    """Собрать экземпляр CRMService с внедренными зависимостями."""
    return CRMService(
        uow=uow,
        classifier=classifier,
        publisher=publisher,
    )
