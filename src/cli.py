"""Меню терминала: взаимодействие с пользователем (S)."""

from __future__ import annotations

from service import AuthService, TicketService
from models import Priority, TicketStatus, UserRole

ROLE_MAP: dict[str, UserRole] = {
    "client": UserRole.CLIENT,
    "operator": UserRole.OPERATOR,
    "admin": UserRole.ADMIN,
}

PRIORITY_MAP: dict[str, Priority] = {
    "low": Priority.LOW,
    "medium": Priority.MEDIUM,
    "high": Priority.HIGH,
    "critical": Priority.CRITICAL,
}


class CLI:
    """Интерактивное меню для работы с CRM в терминале."""

    def __init__(self, auth: AuthService, tickets: TicketService) -> None:
        """Принимает сервисы аутентификации и заявок."""
        self._auth = auth
        self._tickets = tickets

    def run(self) -> None:
        """Запускает главный цикл интерфейса."""
        self._seed()
        while True:
            self._print_menu()
            choice = input("Выбор: ").strip()
            self._handle(choice)

    def _print_menu(self) -> None:
        """Печатает главное меню."""
        print("\n=== CRM-система (ИВТ-262) ===")
        print("1. Регистрация")
        print("2. Вход")
        print("3. Создать заявку (Клиент)")
        print("4. Очередь заявок (Оператор)")
        print("5. Взять заявку в работу (Оператор)")
        print("6. Изменить приоритет вручную (Оператор)")
        print("7. Журнал аудита (Администратор)")
        print("0. Выход")

    def _seed(self) -> None:
        """Создаёт демонстрационные учётные записи всех ролей."""
        self._auth.register("client@crm.ru", "1234", UserRole.CLIENT)
        self._auth.register("operator@crm.ru", "1234", UserRole.OPERATOR)
        self._auth.register("admin@crm.ru", "1234", UserRole.ADMIN)

    def _handle(self, choice: str) -> None:
        """Обрабатывает выбранный пункт меню."""
        handlers = {
            "1": self._register,
            "2": self._login,
            "3": self._create_ticket,
            "4": self._show_queue,
            "5": self._take_ticket,
            "6": self._override_priority,
            "7": self._show_audit,
            "0": self._exit,
        }
        handler = handlers.get(choice)
        if handler is None:
            print("Неизвестная команда.")
            return
        handler()

    def _register(self) -> None:
        """Регистрирует нового пользователя через терминал."""
        email = input("Email: ").strip()
        password = input("Пароль: ").strip()
        role = ROLE_MAP.get(input("Роль (client/operator/admin): ").strip().lower())
        if role is None:
            print("Неизвестная роль.")
            return
        self._auth.register(email, password, role)
        print("Пользователь зарегистрирован.")

    def _login(self) -> None:
        """Выполняет вход в систему по email и паролю."""
        email = input("Email: ").strip()
        password = input("Пароль: ").strip()
        if not self._auth.login(email, password):
            print("Неверные учётные данные.")
            return
        user = self._auth.current_user()
        if user is not None:
            print(f"Вход выполнен: {user.email} ({user.role.value})")

    def _create_ticket(self) -> None:
        """Создаёт заявку от имени авторизованного Клиента."""
        user = self._auth.current_user()
        if user is None or user.role != UserRole.CLIENT:
            print("Требуется вход как Клиент.")
            return
        title = input("Тема: ").strip()
        description = input("Описание: ").strip()
        ticket = self._tickets.create_ticket(title, description, user.email)
        print(
            f"Заявка #{ticket.ticket_id} создана. "
            f"Приоритет: {ticket.ai_priority.value} "
            f"(уверенность {ticket.confidence:.2f})"
        )

    def _show_queue(self) -> None:
        """Показывает очередь заявок Оператору."""
        if not self._auth.require_role(UserRole.OPERATOR):
            print("Требуется роль Оператор.")
            return
        queue = self._tickets.list_queue()
        if not queue:
            print("Очередь пуста.")
            return
        for ticket in queue:
            flag = "!" if ticket.manual_override else " "
            print(
                f"[{flag}] #{ticket.ticket_id} | "
                f"{ticket.ai_priority.value:11} | "
                f"{ticket.status.value} | {ticket.title}"
            )

    def _take_ticket(self) -> None:
        """Переводит заявку в статус «В работе»."""
        if not self._auth.require_role(UserRole.OPERATOR):
            print("Требуется роль Оператор.")
            return
        raw = input("ID заявки: ").strip()
        if not raw.isdigit():
            print("Некорректный ID.")
            return
        ticket = self._tickets.change_status(int(raw), TicketStatus.IN_PROGRESS)
        if ticket is None:
            print("Заявка не найдена.")
            return
        print(f"Заявка #{ticket.ticket_id} взята в работу.")

    def _override_priority(self) -> None:
        """Позволяет Оператору вручную сменить приоритет заявки."""
        user = self._auth.current_user()
        if user is None or user.role != UserRole.OPERATOR:
            print("Требуется роль Оператор.")
            return
        raw = input("ID заявки: ").strip()
        if not raw.isdigit():
            print("Некорректный ID.")
            return
        priority = PRIORITY_MAP.get(input("Новый приоритет (low/medium/high/critical): ").strip().lower())
        if priority is None:
            print("Неизвестный приоритет.")
            return
        ticket = self._tickets.override_priority(int(raw), priority, user.email)
        if ticket is None:
            print("Заявка не найдена.")
            return
        print(f"Приоритет заявки #{ticket.ticket_id} изменён на {ticket.ai_priority.value}.")

    def _show_audit(self) -> None:
        """Показывает журнал ручных корректировок Администратору."""
        if not self._auth.require_role(UserRole.ADMIN):
            print("Требуется роль Администратор.")
            return
        logs = self._tickets.history()
        if not logs:
            print("Журнал пуст.")
            return
        for log in logs:
            print(
                f"#{log.ticket_id} | {log.original.value} -> {log.new_value.value} "
                f"| {log.operator_email} | {log.changed_at:%Y-%m-%d %H:%M}"
            )

    def _exit(self) -> None:
        """Завершает работу программы."""
        print("Выход.")
        raise SystemExit(0)