"""Слой репозиториев (паттерн Repository) для доступа к хранилищу заявок."""

from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .database.mappers import AuditLogMapper, TicketMapper
from .database.models import TicketAuditLogModel, TicketModel, UserModel
from .exceptions import TicketNotFoundError
from .models import Priority, Role, Status, Ticket, TicketAuditLog, TicketDraft


class BaseTicketRepository(ABC):
    """Абстрактный репозиторий для управления хранилищем заявок."""

    @abstractmethod
    def add(self, draft: TicketDraft) -> Ticket:
        """Сохранить новую заявку из черновика."""

    @abstractmethod
    def get_all(
        self,
        priority: Priority | None = None,
        status: Status | None = None,
    ) -> list[Ticket]:
        """Получить перечень заявок с опциональной фильтрацией."""

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по первичному ключу."""

    @abstractmethod
    def update(self, ticket: Ticket, operator_email: str | None = None) -> Ticket:
        """Сохранить обновленное состояние заявки."""

    @abstractmethod
    def add_audit_log(
        self,
        ticket_id: int,
        actor_name: str,
        old_priority: Priority,
        new_priority: Priority,
        reason: str | None = None,
    ) -> TicketAuditLog:
        """Добавить запись о ручном изменении приоритета в журнал аудита."""

    @abstractmethod
    def get_audit_logs(self, ticket_id: int) -> list[TicketAuditLog]:
        """Получить историю ручных изменений приоритета по заявке."""


class TicketRepository(BaseTicketRepository):
    """In-memory реализация репозитория заявок."""

    def __init__(self) -> None:
        """Инициализировать локальные хранилища заявок и записей аудита."""
        self._tickets: list[Ticket] = []
        self._audit_logs: list[TicketAuditLog] = []
        self._counter: int = 1
        self._audit_counter: int = 1

    def add(self, draft: TicketDraft) -> Ticket:
        """Добавить заявку в локальный список."""
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id=self._counter,
            created_at=now,
            updated_at=now,
            **asdict(draft),
        )
        self._tickets.append(ticket)
        self._counter += 1
        return ticket

    def get_all(
        self,
        priority: Priority | None = None,
        status: Status | None = None,
    ) -> list[Ticket]:
        """Вернуть список заявок с учетом фильтров."""
        result = list(self._tickets)
        if priority is not None:
            result = [t for t in result if t.priority == priority]
        if status is not None:
            result = [t for t in result if t.status == status]
        return result

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по ID в локальном списке."""
        for ticket in self._tickets:
            if ticket.id == ticket_id:
                return ticket
        return None

    def update(self, ticket: Ticket, operator_email: str | None = None) -> Ticket:
        """Обновить существующую запись в локальном списке."""
        for i, existing in enumerate(self._tickets):
            if existing.id == ticket.id:
                ticket.updated_at = datetime.now(timezone.utc)
                self._tickets[i] = ticket
                return ticket
        raise TicketNotFoundError(ticket.id)

    def add_audit_log(
        self,
        ticket_id: int,
        actor_name: str,
        old_priority: Priority,
        new_priority: Priority,
        reason: str | None = None,
    ) -> TicketAuditLog:
        """Записать событие ручного переопределения приоритета в память."""
        log = TicketAuditLog(
            id=self._audit_counter,
            ticket_id=ticket_id,
            changed_by_name=actor_name,
            old_priority=old_priority,
            new_priority=new_priority,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        self._audit_logs.append(log)
        self._audit_counter += 1
        return log

    def get_audit_logs(self, ticket_id: int) -> list[TicketAuditLog]:
        """Вернуть записи аудита для указанной заявки."""
        return [log for log in self._audit_logs if log.ticket_id == ticket_id]


class SQLAlchemyTicketRepository(BaseTicketRepository):
    """Репозиторий на базе SQLAlchemy, работающий в рамках внешней Session (Unit of Work)."""

    def __init__(self, session: Session) -> None:
        """Привязать репозиторий к активной сессии SQLAlchemy."""
        self._session = session

    def _get_or_create_user(
        self,
        full_name: str,
        role: Role,
        email: str | None = None,
    ) -> UserModel:
        """Найти пользователя по email или имени либо создать нового в текущей сессии."""
        clean_name = full_name.strip()
        normalized_email = (
            email.strip().lower()
            if email and email.strip()
            else f"{clean_name.lower().replace(' ', '.')}@crm.local"
        )

        stmt = select(UserModel).where(UserModel.email == normalized_email)
        user = self._session.scalars(stmt).first()

        if user is None and email is None:
            stmt_by_name = select(UserModel).where(UserModel.full_name == clean_name)
            user = self._session.scalars(stmt_by_name).first()

        if user is None:
            user = UserModel(
                email=normalized_email,
                full_name=clean_name,
                role=role.value,
            )
            self._session.add(user)
            self._session.flush()

        return user

    def add(self, draft: TicketDraft) -> Ticket:
        """Добавить новую заявку в текущую транзакцию."""
        client = self._get_or_create_user(
            full_name=draft.client_name,
            email=draft.client_email,
            role=Role.CLIENT,
        )
        ticket_model = TicketMapper.to_orm(draft, client)
        self._session.add(ticket_model)
        self._session.flush()
        self._session.refresh(ticket_model, ["client", "operator"])
        return TicketMapper.to_domain(ticket_model)

    def get_all(
        self,
        priority: Priority | None = None,
        status: Status | None = None,
    ) -> list[Ticket]:
        """Получить заявки из БД с жадной загрузкой связей и опциональными фильтрами."""
        stmt = (
            select(TicketModel)
            .options(
                joinedload(TicketModel.client),
                joinedload(TicketModel.operator),
            )
            .order_by(TicketModel.id.asc())
        )
        if priority is not None:
            stmt = stmt.where(TicketModel.priority == priority.value)
        if status is not None:
            stmt = stmt.where(TicketModel.status == status.value)

        models = self._session.scalars(stmt).unique().all()
        return [TicketMapper.to_domain(m) for m in models]

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по ID в базе данных."""
        stmt = (
            select(TicketModel)
            .options(
                joinedload(TicketModel.client),
                joinedload(TicketModel.operator),
            )
            .where(TicketModel.id == ticket_id)
        )
        model = self._session.scalars(stmt).unique().first()
        return TicketMapper.to_domain(model) if model else None

    def update(self, ticket: Ticket, operator_email: str | None = None) -> Ticket:
        """Обновить состояние заявки в текущей сессии."""
        stmt = (
            select(TicketModel)
            .options(
                joinedload(TicketModel.client),
                joinedload(TicketModel.operator),
            )
            .where(TicketModel.id == ticket.id)
        )
        ticket_model = self._session.scalars(stmt).unique().first()
        if ticket_model is None:
            raise TicketNotFoundError(ticket.id)

        if ticket.operator_name:
            operator = self._get_or_create_user(
                full_name=ticket.operator_name,
                email=operator_email,
                role=Role.OPERATOR,
            )
            ticket_model.operator_id = operator.id

        ticket_model.status = ticket.status.value
        ticket_model.priority = ticket.priority.value
        ticket_model.manual_priority_override = ticket.manual_priority_override

        self._session.flush()
        self._session.refresh(ticket_model, ["client", "operator"])
        return TicketMapper.to_domain(ticket_model)

    def add_audit_log(
        self,
        ticket_id: int,
        actor_name: str,
        old_priority: Priority,
        new_priority: Priority,
        reason: str | None = None,
    ) -> TicketAuditLog:
        """Добавить запись аудита в текущую транзакцию."""
        actor = self._get_or_create_user(full_name=actor_name, role=Role.OPERATOR)
        audit_model = TicketAuditLogModel(
            ticket_id=ticket_id,
            changed_by_user_id=actor.id,
            old_priority=old_priority.value,
            new_priority=new_priority.value,
            reason=reason,
        )
        self._session.add(audit_model)
        self._session.flush()
        self._session.refresh(audit_model, ["changed_by_user"])
        return AuditLogMapper.to_domain(audit_model)

    def get_audit_logs(self, ticket_id: int) -> list[TicketAuditLog]:
        """Получить отсортированную историю изменений приоритета для заявки."""
        stmt = (
            select(TicketAuditLogModel)
            .options(joinedload(TicketAuditLogModel.changed_by_user))
            .where(TicketAuditLogModel.ticket_id == ticket_id)
            .order_by(TicketAuditLogModel.created_at.desc())
        )
        models = self._session.scalars(stmt).unique().all()
        return [AuditLogMapper.to_domain(m) for m in models]

