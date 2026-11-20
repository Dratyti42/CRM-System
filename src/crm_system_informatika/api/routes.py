"""REST API маршруты CRM-системы на FastAPI."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..configs.settings import settings
from ..database.session import get_session
from ..dtos.requests import (
    TicketCreateRequest,
    TicketPriorityOverrideRequest,
    TicketStatusUpdateRequest,
    TicketTakeRequest,
)
from ..dtos.responses import (
    AuditLogResponse,
    HealthResponse,
    TicketDetailResponse,
    TicketListResponse,
    TicketResponse,
)
from ..models import Priority, Status
from ..service import CRMService
from .dependencies import get_crm_service

router = APIRouter(prefix="/api/v1", tags=["CRM API"])


@router.get("/health", response_model=HealthResponse)
def healthcheck(
    session: Annotated[Session, Depends(get_session)],
) -> HealthResponse:
    """Проверить работоспособность API и доступность базы данных."""
    session.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        database="connected",
        classifier_strategy=settings.classifier_strategy,
    )


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    service: Annotated[CRMService, Depends(get_crm_service)],
    priority: Annotated[Priority | None, Query()] = None,
    ticket_status: Annotated[Status | None, Query(alias="status")] = None,
) -> TicketListResponse:
    """Вернуть очередь заявок, отсортированную по приоритету."""
    tickets = service.get_tickets_for_operator(
        priority=priority,
        status=ticket_status,
    )
    items = [TicketResponse.from_domain(ticket) for ticket in tickets]
    return TicketListResponse(items=items, total=len(items))


@router.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    payload: TicketCreateRequest,
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> TicketResponse:
    """Создать новую заявку с автоматической ИИ-приоритизацией."""
    ticket = service.create_ticket(
        title=payload.title,
        description=payload.description,
        client_name=payload.client_name,
        client_email=payload.client_email,
    )
    return TicketResponse.from_domain(ticket)


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: int,
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> TicketDetailResponse:
    """Получить карточку заявки вместе с журналом аудита приоритета."""
    ticket = service.get_ticket_by_id(ticket_id)
    logs = service.get_ticket_audit_logs(ticket_id)
    base = TicketResponse.from_domain(ticket)
    return TicketDetailResponse(
        **base.model_dump(),
        audit_logs=[AuditLogResponse.from_domain(log) for log in logs],
    )


@router.patch("/tickets/{ticket_id}/take", response_model=TicketResponse)
def take_ticket(
    ticket_id: int,
    payload: TicketTakeRequest,
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> TicketResponse:
    """Назначить оператора и перевести заявку в статус «В работе»."""
    ticket = service.take_ticket_to_work(
        ticket_id=ticket_id,
        operator_name=payload.operator_name,
        operator_email=payload.operator_email,
    )
    return TicketResponse.from_domain(ticket)


@router.patch("/tickets/{ticket_id}/priority", response_model=TicketResponse)
def override_ticket_priority(
    ticket_id: int,
    payload: TicketPriorityOverrideRequest,
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> TicketResponse:
    """Вручную изменить приоритет заявки с записью в аудит-лог."""
    ticket = service.override_priority(
        ticket_id=ticket_id,
        new_priority=payload.priority,
        operator_name=payload.operator_name,
        reason=payload.reason,
    )
    return TicketResponse.from_domain(ticket)


@router.patch("/tickets/{ticket_id}/status", response_model=TicketResponse)
def change_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdateRequest,
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> TicketResponse:
    """Перевести заявку в следующий допустимый статус жизненного цикла."""
    ticket = service.change_status(
        ticket_id=ticket_id,
        new_status=payload.status,
    )
    return TicketResponse.from_domain(ticket)


@router.get(
    "/tickets/{ticket_id}/audit-logs",
    response_model=list[AuditLogResponse],
)
def list_ticket_audit_logs(
    ticket_id: int,
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> list[AuditLogResponse]:
    """Получить историю ручных изменений приоритета указанной заявки."""
    logs = service.get_ticket_audit_logs(ticket_id)
    return [AuditLogResponse.from_domain(log) for log in logs]
