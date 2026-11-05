"""Классы-мапперы для преобразования между ORM-моделями и датаклассами."""

from ..models import Priority, Status, Ticket, TicketDraft
from .models import TicketModel, UserModel


class TicketMapper:
    """Маппер для преобразования сущностей заявок."""

    @staticmethod
    def to_domain(model: TicketModel) -> Ticket:
        """Преобразовать ORM-модель TicketModel в датакласс предметной области Ticket."""
        client_name = model.client.full_name if model.client else "Неизвестный клиент"
        operator_name = model.operator.full_name if model.operator else None

        return Ticket(
            id=model.id,
            title=model.title,
            description=model.description,
            client_name=client_name,
            priority=Priority(model.priority),
            confidence_score=model.confidence_score,
            status=Status(model.status),
            operator_name=operator_name,
            manual_priority_override=model.manual_priority_override,
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
