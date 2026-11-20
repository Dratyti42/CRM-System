"""Классы-мапперы (Data Mapper) между ORM-моделями и доменными датаклассами."""

from ..models import Priority, Status, Ticket, TicketAuditLog, TicketDraft
from .models import TicketAuditLogModel, TicketModel, UserModel


class TicketMapper:
    """Маппер для преобразования сущностей заявок."""

    @staticmethod
    def to_domain(model: TicketModel) -> Ticket:
        """Преобразовать ORM-модель TicketModel в доменный датакласс Ticket."""
        client_name = model.client.full_name if model.client else "Неизвестный клиент"
        client_email = model.client.email if model.client else None
        operator_name = model.operator.full_name if model.operator else None

        return Ticket(
            id=model.id,
            title=model.title,
            description=model.description,
            client_name=client_name,
            client_email=client_email,
            priority=Priority(model.priority),
            confidence_score=model.confidence_score,
            status=Status(model.status),
            operator_name=operator_name,
            manual_priority_override=model.manual_priority_override,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_orm(draft: TicketDraft, client: UserModel) -> TicketModel:
        """Преобразовать черновик TicketDraft в новую ORM-модель TicketModel."""
        return TicketModel(
            title=draft.title,
            description=draft.description,
            priority=draft.priority.value,
            confidence_score=draft.confidence_score,
            status=Status.NEW.value,
            manual_priority_override=False,
            client_id=client.id,
        )


class AuditLogMapper:
    """Маппер для преобразования записей журнала аудита."""

    @staticmethod
    def to_domain(model: TicketAuditLogModel) -> TicketAuditLog:
        """Преобразовать ORM-модель TicketAuditLogModel в доменную запись аудита."""
        actor_name = (
            model.changed_by_user.full_name
            if model.changed_by_user
            else "Неизвестный пользователь"
        )
        return TicketAuditLog(
            id=model.id,
            ticket_id=model.ticket_id,
            changed_by_name=actor_name,
            old_priority=Priority(model.old_priority),
            new_priority=Priority(model.new_priority),
            reason=model.reason,
            created_at=model.created_at,
        )
