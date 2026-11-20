"""Pydantic-схемы исходящих ответов API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..configs.settings import settings
from ..models import Priority, Status, Ticket, TicketAuditLog


class TicketResponse(BaseModel):
    """Схема представления заявки в ответах API."""

    id: int
    title: str
    description: str
    client_name: str
    client_email: str | None = None
    priority: Priority
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    needs_review: bool
    status: Status
    operator_name: str | None = None
    manual_priority_override: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(
        cls,
        ticket: Ticket,
        confidence_threshold: float | None = None,
    ) -> "TicketResponse":
        """Построить DTO ответа из доменной сущности Ticket."""
        threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.confidence_threshold
        )
        return cls(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            client_name=ticket.client_name,
            client_email=ticket.client_email,
            priority=ticket.priority,
            confidence_score=ticket.confidence_score,
            needs_review=(
                ticket.confidence_score < threshold
                and not ticket.manual_priority_override
            ),
            status=ticket.status,
            operator_name=ticket.operator_name,
            manual_priority_override=ticket.manual_priority_override,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )


class TicketListResponse(BaseModel):
    """Схема ответа со списком заявок и общим количеством."""

    items: list[TicketResponse]
    total: int


class AuditLogResponse(BaseModel):
    """Схема записи журнала аудита изменений приоритета."""

    id: int
    ticket_id: int
    changed_by_name: str
    old_priority: Priority
    new_priority: Priority
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, log: TicketAuditLog) -> "AuditLogResponse":
        """Построить DTO ответа из доменной записи TicketAuditLog."""
        return cls(
            id=log.id,
            ticket_id=log.ticket_id,
            changed_by_name=log.changed_by_name,
            old_priority=log.old_priority,
            new_priority=log.new_priority,
            reason=log.reason,
            created_at=log.created_at,
        )


class TicketDetailResponse(TicketResponse):
    """Расширенная схема карточки заявки с историей аудита."""

    audit_logs: list[AuditLogResponse] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Схема ответа диагностики состояния сервиса."""

    status: str
    database: str
    classifier_strategy: str
