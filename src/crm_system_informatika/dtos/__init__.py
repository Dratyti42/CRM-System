"""Пакет Pydantic-схем запросов и ответов (DTO)."""

from .requests import (
    TicketCreateRequest,
    TicketPriorityOverrideRequest,
    TicketStatusUpdateRequest,
    TicketTakeRequest,
)
from .responses import (
    AuditLogResponse,
    HealthResponse,
    TicketDetailResponse,
    TicketListResponse,
    TicketResponse,
)

__all__ = [
    "AuditLogResponse",
    "HealthResponse",
    "TicketCreateRequest",
    "TicketDetailResponse",
    "TicketListResponse",
    "TicketPriorityOverrideRequest",
    "TicketResponse",
    "TicketStatusUpdateRequest",
    "TicketTakeRequest",
]
