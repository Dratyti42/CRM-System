"""Паттерн Unit of Work на базе Session SQLAlchemy."""

from abc import ABC, abstractmethod
from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker
from typing_extensions import Self

from ..repository import (
    BaseTicketRepository,
    SQLAlchemyTicketRepository,
    TicketRepository,
)


class BaseUnitOfWork(ABC):
    """Абстрактная единица работы для атомарного управления транзакциями."""

    tickets: BaseTicketRepository

    @abstractmethod
    def __enter__(self) -> Self:
        """Открыть контекст единицы работы."""

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Завершить контекст и выполнить откат при ошибке."""

    @abstractmethod
    def commit(self) -> None:
        """Зафиксировать все накопленные изменения."""

    @abstractmethod
    def rollback(self) -> None:
        """Откатить все незафиксированные изменения."""


class SQLAlchemyUnitOfWork(BaseUnitOfWork):
    """Реализация Unit of Work, использующая SQLAlchemy Session."""

    def __init__(
        self,
        session: Session | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        """Инициализировать Unit of Work готовой сессией или фабрикой сессий."""
        if session is None and session_factory is None:
            raise ValueError("Необходимо передать session или session_factory.")
        self._external_session = session
        self._session_factory = session_factory
        self._session: Session | None = session
        if session is not None:
            self.tickets = SQLAlchemyTicketRepository(session)

    def __enter__(self) -> Self:
        """Подготовить сессию и репозиторий к выполнению транзакции."""
        if self._external_session is not None:
            self._session = self._external_session
        elif self._session_factory is not None:
            self._session = self._session_factory()
        if self._session is None:
            raise RuntimeError("Сессия базы данных не инициализирована.")
        self.tickets = SQLAlchemyTicketRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Выполнить rollback при исключении и закрыть внутреннюю сессию."""
        if self._session is None:
            return
        if exc_type is not None:
            self._session.rollback()
        if self._external_session is None:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        """Зафиксировать транзакцию в PostgreSQL."""
        if self._session is not None:
            self._session.commit()

    def rollback(self) -> None:
        """Откатить текущую транзакцию в PostgreSQL."""
        if self._session is not None:
            self._session.rollback()


class InMemoryUnitOfWork(BaseUnitOfWork):
    """In-memory реализация Unit of Work для автономного запуска и тестов."""

    def __init__(self, repo: TicketRepository | None = None) -> None:
        """Инициализировать Unit of Work локальным репозиторием."""
        self.tickets: BaseTicketRepository = repo or TicketRepository()

    def __enter__(self) -> Self:
        """Войти в контекст единицы работы."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Завершить контекст без действий."""

    def commit(self) -> None:
        """Зафиксировать изменения в памяти."""

    def rollback(self) -> None:
        """Откатить изменения в памяти."""
