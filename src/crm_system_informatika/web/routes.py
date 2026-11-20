"""Маршруты веб-интерфейса на Jinja2, вызывающие сервисный слой CRM."""

from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..api.dependencies import get_alert_observer, get_crm_service
from ..configs.settings import settings
from ..dtos.responses import AuditLogResponse, TicketResponse
from ..exceptions import CRMError
from ..models import Priority, Status
from ..observers import HighPriorityAlertObserver
from ..service import CRMService

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["Web UI"])


def _redirect_with_message(
    url: str,
    *,
    message: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Сформировать редирект с сообщением о результате операции."""
    params: dict[str, str] = {}
    if message:
        params["message"] = message
    if error:
        params["error"] = error
    target = f"{url}?{urlencode(params)}" if params else url
    return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    service: Annotated[CRMService, Depends(get_crm_service)],
    alert_observer: Annotated[HighPriorityAlertObserver, Depends(get_alert_observer)],
    priority: Annotated[str | None, Query()] = None,
    ticket_status: Annotated[str | None, Query(alias="status")] = None,
    message: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> HTMLResponse:
    """Отобразить главную панель оператора и форму подачи новой заявки."""
    selected_priority = Priority(priority) if priority else None
    selected_status = Status(ticket_status) if ticket_status else None

    tickets = service.get_tickets_for_operator(
        priority=selected_priority,
        status=selected_status,
    )
    ticket_dtos = [TicketResponse.from_domain(t) for t in tickets]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_title": settings.app_title,
            "tickets": ticket_dtos,
            "alerts": alert_observer.get_recent_alerts()[:3],
            "priorities": list(Priority),
            "statuses": list(Status),
            "selected_priority": priority or "",
            "selected_status": ticket_status or "",
            "message": message,
            "error": error,
        },
    )


@router.post("/web/tickets", response_class=RedirectResponse)
def create_ticket_web(
    service: Annotated[CRMService, Depends(get_crm_service)],
    client_name: Annotated[str, Form()],
    client_email: Annotated[str, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
) -> RedirectResponse:
    """Обработать веб-форму создания клиентской заявки."""
    try:
        ticket = service.create_ticket(
            title=title,
            description=description,
            client_name=client_name,
            client_email=client_email,
        )
        return _redirect_with_message(
            "/",
            message=(
                f"Заявка #{ticket.id} создана. Приоритет ИИ: "
                f"«{ticket.priority.value}» ({ticket.confidence_score * 100:.0f}%)."
            ),
        )
    except CRMError as err:
        return _redirect_with_message("/", error=str(err))


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse, response_model=None)
def ticket_detail(
    ticket_id: int,
    request: Request,
    service: Annotated[CRMService, Depends(get_crm_service)],
    message: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> HTMLResponse | RedirectResponse:
    """Отобразить карточку заявки с управлением статусом, приоритетом и аудитом."""
    try:
        ticket = service.get_ticket_by_id(ticket_id)
        audit_logs = service.get_ticket_audit_logs(ticket_id)
    except CRMError as err:
        return _redirect_with_message("/", error=str(err))

    allowed_statuses = service.get_allowed_transitions(ticket.status)

    return templates.TemplateResponse(
        request=request,
        name="ticket_detail.html",
        context={
            "app_title": settings.app_title,
            "ticket": TicketResponse.from_domain(ticket),
            "audit_logs": [AuditLogResponse.from_domain(log) for log in audit_logs],
            "priorities": list(Priority),
            "allowed_statuses": allowed_statuses,
            "can_take": Status.IN_PROGRESS in allowed_statuses,
            "message": message,
            "error": error,
        },
    )


@router.post("/web/tickets/{ticket_id}/take", response_class=RedirectResponse)
def take_ticket_web(
    ticket_id: int,
    service: Annotated[CRMService, Depends(get_crm_service)],
    operator_name: Annotated[str, Form()],
) -> RedirectResponse:
    """Взять заявку в работу из веб-интерфейса."""
    try:
        ticket = service.take_ticket_to_work(
            ticket_id=ticket_id,
            operator_name=operator_name,
        )
        return _redirect_with_message(
            f"/tickets/{ticket_id}",
            message=f"Заявка взята в работу оператором {ticket.operator_name}.",
        )
    except CRMError as err:
        return _redirect_with_message(f"/tickets/{ticket_id}", error=str(err))


@router.post("/web/tickets/{ticket_id}/priority", response_class=RedirectResponse)
def override_priority_web(
    ticket_id: int,
    service: Annotated[CRMService, Depends(get_crm_service)],
    priority: Annotated[Priority, Form()],
    operator_name: Annotated[str, Form()] = "",
    reason: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """Вручную изменить приоритет заявки из веб-интерфейса."""
    try:
        ticket = service.override_priority(
            ticket_id=ticket_id,
            new_priority=priority,
            operator_name=operator_name or None,
            reason=reason or None,
        )
        return _redirect_with_message(
            f"/tickets/{ticket_id}",
            message=f"Приоритет изменен на «{ticket.priority.value}» (записано в аудит).",
        )
    except CRMError as err:
        return _redirect_with_message(f"/tickets/{ticket_id}", error=str(err))


@router.post("/web/tickets/{ticket_id}/status", response_class=RedirectResponse)
def change_status_web(
    ticket_id: int,
    service: Annotated[CRMService, Depends(get_crm_service)],
    new_status: Annotated[Status, Form(alias="status")],
) -> RedirectResponse:
    """Изменить статус заявки из веб-интерфейса."""
    try:
        ticket = service.change_status(
            ticket_id=ticket_id,
            new_status=new_status,
        )
        return _redirect_with_message(
            f"/tickets/{ticket_id}",
            message=f"Статус обновлен на «{ticket.status.value}».",
        )
    except CRMError as err:
        return _redirect_with_message(f"/tickets/{ticket_id}", error=str(err))
