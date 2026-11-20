"""Консольный пользовательский интерфейс CRM-системы."""

import re
from enum import IntEnum

from .classifier import ClassifierFactory
from .configs.settings import settings
from .database.session import SessionFactory
from .database.uow import SQLAlchemyUnitOfWork
from .exceptions import CRMError
from .models import Priority, Status
from .observers import (
    ActivityLogObserver,
    HighPriorityAlertObserver,
    TicketEventPublisher,
)
from .service import CRMService

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


class MainMenuChoice(IntEnum):
    """Пункты главного меню консольного интерфейса."""

    EXIT = 0
    CREATE_TICKET = 1
    LIST_TICKETS = 2
    TAKE_TICKET = 3
    OVERRIDE_PRIORITY = 4
    CHANGE_STATUS = 5


class PriorityChoice(IntEnum):
    """Выбор приоритета в консоли."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class StatusChoice(IntEnum):
    """Выбор статуса в консоли."""

    IN_PROGRESS = 1
    WAITING_CLIENT = 2
    RESOLVED = 3
    CLOSED = 4


PRIORITY_MAP: dict[PriorityChoice, Priority] = {
    PriorityChoice.LOW: Priority.LOW,
    PriorityChoice.MEDIUM: Priority.MEDIUM,
    PriorityChoice.HIGH: Priority.HIGH,
    PriorityChoice.CRITICAL: Priority.CRITICAL,
}

STATUS_MAP: dict[StatusChoice, Status] = {
    StatusChoice.IN_PROGRESS: Status.IN_PROGRESS,
    StatusChoice.WAITING_CLIENT: Status.WAITING_CLIENT,
    StatusChoice.RESOLVED: Status.RESOLVED,
    StatusChoice.CLOSED: Status.CLOSED,
}


class ConsoleUI:
    """Консольный пользовательский интерфейс для работы с CRM."""

    def __init__(self, service: CRMService) -> None:
        """Инициализировать интерфейс сервисом прикладной логики."""
        self._service = service

    def run(self) -> None:
        """Запустить главный цикл взаимодействия с пользователем."""
        while True:
            print("\n" + "=" * 45)
            print("  CRM-СИСТЕМА С ИИ-ПРИОРИТИЗАЦИЕЙ")
            print("=" * 45)
            print("1. [Клиент] Подать новую заявку")
            print("2. [Оператор] Показать очередь заявок (сортировка по приоритету)")
            print("3. [Оператор] Взять заявку в работу")
            print("4. [Оператор] Вручную изменить приоритет")
            print("5. [Оператор] Изменить статус заявки")
            print("0. Выход")

            try:
                raw_input = int(input("\nВыберите действие: ").strip())
                choice = MainMenuChoice(raw_input)
            except ValueError:
                print("Неверный ввод, попробуйте еще раз.")
                continue

            if choice == MainMenuChoice.CREATE_TICKET:
                self._create_ticket()
            elif choice == MainMenuChoice.LIST_TICKETS:
                self._list_tickets()
            elif choice == MainMenuChoice.TAKE_TICKET:
                self._take_ticket()
            elif choice == MainMenuChoice.OVERRIDE_PRIORITY:
                self._override_priority()
            elif choice == MainMenuChoice.CHANGE_STATUS:
                self._change_status()
            elif choice == MainMenuChoice.EXIT:
                print("Выход из системы. До свидания!")
                break

    def _create_ticket(self) -> None:
        """Обработать диалог подачи обращения с перехватом ошибок валидации."""
        print("\n--- СОЗДАНИЕ ЗАЯВКИ ---")
        client_name = input("Ваше имя: ").strip()
        while True:
            client_email = input("Введите ваш Email: ").strip()
            if re.match(EMAIL_REGEX, client_email):
                break
            print("Ошибка: неверный формат почты.")

        title = input("Тема обращения: ").strip()
        desc = input("Описание проблемы: ").strip()

        try:
            ticket = self._service.create_ticket(
                title=title,
                description=desc,
                client_name=client_name,
                client_email=client_email,
            )
        except CRMError as err:
            print(f"\n[ОШИБКА ВАЛИДАЦИИ] {err}")
            return

        print(
            f"\n[УСПЕХ] Заявка #{ticket.id} создана со статусом '{ticket.status.value}'!"
        )
        print(
            f"-> ИИ определил приоритет: [{ticket.priority.value}] "
            f"(Уверенность: {ticket.confidence_score * 100:.0f}%)"
        )
        if ticket.confidence_score < settings.confidence_threshold:
            print(
                "-> Примечание: Требуется подтверждение приоритета оператором "
                "(низкая уверенность ИИ)."
            )

    def _list_tickets(self) -> None:
        """Отобразить упорядоченный список обращений для оператора."""
        tickets = self._service.get_tickets_for_operator()
        if not tickets:
            print("\nОчередь заявок пуста.")
            return

        print("\n--- ОЧЕРЕДЬ ЗАЯВОК (СОРТИРОВКА ПО ПРИОРИТЕТУ) ---")
        for t in tickets:
            override_flag = " [РУЧНОЙ ПРИОРИТЕТ]" if t.manual_priority_override else ""
            print(
                f"#{t.id} | Приоритет: {t.priority.value:<9}{override_flag} | "
                f"Статус: {t.status.value:<12} | Клиент: {t.client_name}"
            )
            print(f"    Тема: {t.title}")
            print(f"    Оператор: {t.operator_name or 'Не назначен'}")
            print("-" * 45)

    def _take_ticket(self) -> None:
        """Передать обращение в работу указанному оператору."""
        try:
            t_id = int(input("\nВведите ID заявки: "))
            operator = input("Имя оператора: ").strip()
            ticket = self._service.take_ticket_to_work(t_id, operator)
            print(
                f"[УСПЕХ] Заявка #{ticket.id} переведена в статус "
                f"'{ticket.status.value}', оператор: {ticket.operator_name}"
            )
        except (ValueError, CRMError) as err:
            print(f"[ОШИБКА] {err}")

    def _override_priority(self) -> None:
        """Изменить категорию приоритета вручную."""
        try:
            t_id = int(input("\nВведите ID заявки: "))
            print(
                "Доступные приоритеты: 1. Низкий | 2. Средний | 3. Высокий | 4. Наивысший"
            )
            p_input = int(input("Выберите новый приоритет (1-4): ").strip())
            p_choice = PriorityChoice(p_input)
            reason = input("Причина корректировки (опционально): ").strip()
            ticket = self._service.override_priority(
                ticket_id=t_id,
                new_priority=PRIORITY_MAP[p_choice],
                reason=reason or None,
            )
            print(
                f"[УСПЕХ] Приоритет заявки #{ticket.id} изменен на "
                f"'{ticket.priority.value}' вручную (зафиксировано в логе)."
            )
        except (ValueError, CRMError) as err:
            print(f"[ОШИБКА] {err}")

    def _change_status(self) -> None:
        """Обновить статус текущей заявки с обработкой бизнес-правил перехода."""
        try:
            t_id = int(input("\nВведите ID заявки: "))
            print("Статусы: 1. В работе | 2. Ожидает ответа | 3. Решена | 4. Закрыта")
            s_input = int(input("Выберите новый статус (1-4): ").strip())
            s_choice = StatusChoice(s_input)
            ticket = self._service.change_status(t_id, STATUS_MAP[s_choice])
            print(
                f"[УСПЕХ] Статус заявки #{ticket.id} обновлен на '{ticket.status.value}'."
            )
        except (ValueError, CRMError) as err:
            print(f"[ОШИБКА] {err}")


def run_cli() -> None:
    """Собрать зависимости и запустить консольный интерфейс."""
    uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)
    classifier = ClassifierFactory.create(settings.classifier_strategy)
    publisher = TicketEventPublisher(
        observers=[ActivityLogObserver(), HighPriorityAlertObserver()]
    )
    service = CRMService(uow=uow, classifier=classifier, publisher=publisher)
    ConsoleUI(service=service).run()
