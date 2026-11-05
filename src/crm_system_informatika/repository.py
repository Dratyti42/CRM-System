from abc import ABC, abstractmethod
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from .database.mappers import TicketMapper
from .database.models import TicketAuditLogModel, TicketModel, UserModel
from .models import Role, Ticket, TicketDraft


class BaseTicketRepository(ABC):
    """Абстрактный репозиторий для управления хранилищем заявок."""

    @abstractmethod
    def add(self, draft: TicketDraft) -> Ticket:
        """Сохранить новую заявку из черновика."""

    @abstractmethod
    def get_all(self) -> list[Ticket]:
        """Получить полный перечень заявок."""

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по первичному ключу."""

    @abstractmethod
    def update(self, ticket: Ticket) -> Ticket:
        """Явно сохранить обновленное состояние сущности в хранилище."""


class TicketRepository(BaseTicketRepository):
    """In-memory реализация репозитория заявок."""

    def __init__(self) -> None:
        """Инициализировать локальное хранилище и счетчик идентификаторов."""
        self._tickets: list[Ticket] = []
        self._counter: int = 1

    def add(self, draft: TicketDraft) -> Ticket:
        """Добавить заявку в локальный список без риска дублирования аргументов."""
        ticket = Ticket(id=self._counter, **asdict(draft))
        self._tickets.append(ticket)
        self._counter += 1
        return ticket

    def get_all(self) -> list[Ticket]:
        """Вернуть копию списка всех сохраненных заявок."""
        return list(self._tickets)

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по ID в текущем списке."""
        for ticket in self._tickets:
            if ticket.id == ticket_id:
                return ticket
        return None

    def update(self, ticket: Ticket) -> Ticket:
        """Обновить существующую запись в списке."""
        for i, existing in enumerate(self._tickets):
            if existing.id == ticket.id:
                self._tickets[i] = ticket
                return ticket
        raise ValueError(f"Заявка с ID {ticket.id} не найдена в репозитории.")


class SQLAlchemyTicketRepository(BaseTicketRepository):
    """Реализация репозитория на базе SQLAlchemy и PostgreSQL."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _get_or_create_user(
        self, session: Session, name_or_email: str, role: Role
    ) -> UserModel:
        """Найти пользователя по имени/email или автоматически создать нового."""
        clean_name = name_or_email.strip()
        email = clean_name if "@" in clean_name else f"{clean_name.lower()}@crm.local"

        stmt = select(UserModel).where(
            (UserModel.email == email) | (UserModel.full_name == clean_name)
        )
        user = session.scalars(stmt).first()

        if user is None:
            user = UserModel(
                email=email,
                full_name=clean_name,
                role=role.value,
            )
            session.add(user)
            session.flush()

        return user

    def add(self, draft: TicketDraft) -> Ticket:
        """Сохранить новую заявку в базе данных PostgreSQL."""
        with self._session_factory() as session, session.begin():
            client = self._get_or_create_user(session, draft.client_name, Role.CLIENT)
            ticket_model = TicketMapper.to_orm(draft, client)
            session.add(ticket_model)
            session.flush()

            session.refresh(ticket_model, ["client"])
            return TicketMapper.to_domain(ticket_model)

    def get_all(self) -> list[Ticket]:
        """Получить все заявки из БД с жадной загрузкой клиентов и операторов."""
        with self._session_factory() as session:
            stmt = (
                select(TicketModel)
                .options(
                    joinedload(TicketModel.client),
                    joinedload(TicketModel.operator),
                )
                .order_by(TicketModel.id.asc())
            )
            models = session.scalars(stmt).unique().all()
            return [TicketMapper.to_domain(m) for m in models]

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по ID в базе данных."""
        with self._session_factory() as session:
            stmt = (
                select(TicketModel)
                .options(
                    joinedload(TicketModel.client),
                    joinedload(TicketModel.operator),
                )
                .where(TicketModel.id == ticket_id)
            )
            model = session.scalars(stmt).unique().first()
            return TicketMapper.to_domain(model) if model else None

    def update(self, ticket: Ticket) -> Ticket:
        """Обновить статус или приоритет заявки в базе данных PostgreSQL."""
        with self._session_factory() as session, session.begin():
            stmt = (
                select(TicketModel)
                .options(
                    joinedload(TicketModel.client),
                    joinedload(TicketModel.operator),
                )
                .where(TicketModel.id == ticket.id)
            )
            ticket_model = session.scalars(stmt).unique().first()
            if ticket_model is None:
                raise ValueError(f"Заявка с ID #{ticket.id} не найдена в базе данных.")

            if (
                ticket_model.priority != ticket.priority.value
                and ticket.manual_priority_override
            ):
                operator = (
                    self._get_or_create_user(
                        session, ticket.operator_name, Role.OPERATOR
                    )
                    if ticket.operator_name
                    else ticket_model.client
                )
                audit_log = TicketAuditLogModel(
                    ticket_id=ticket_model.id,
                    changed_by_user_id=operator.id,
                    old_priority=ticket_model.priority,
                    new_priority=ticket.priority.value,
                    reason="Ручная корректировка оператором",
                )
                session.add(audit_log)

            if ticket.operator_name:
                operator = self._get_or_create_user(
                    session, ticket.operator_name, Role.OPERATOR
                )
                ticket_model.operator_id = operator.id

            ticket_model.status = ticket.status.value
            ticket_model.priority = ticket.priority.value
            ticket_model.manual_priority_override = ticket.manual_priority_override

            session.flush()
            session.refresh(ticket_model, ["client", "operator"])
            return TicketMapper.to_domain(ticket_model)
