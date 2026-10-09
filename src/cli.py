from enum import IntEnum

from src.models import Priority, Status
from src.service import CRMService


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
        self.service = service

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
        """Обработать диалог подачи обращения клиентом."""
        print("\n--- СОЗДАНИЕ ЗАЯВКИ ---")
        client_name = input("Ваше имя / Email: ").strip()
        title = input("Тема обращения: ").strip()
        desc = input("Описание проблемы: ").strip()

        ticket = self.service.create_ticket(title, desc, client_name)
        print(f"\n[УСПЕХ] Заявка #{ticket.id} создана со статусом '{ticket.status.value}'!")
        print(f"-> ИИ определил приоритет: [{ticket.priority.value}] (Уверенность: {ticket.confidence_score * 100:.0f}%)")
        if ticket.confidence_score < 0.6:
            print("-> Примечание: Требуется подтверждение приоритета оператором (низкая уверенность ИИ).")

    def _list_tickets(self) -> None:
        """Отобразить упорядоченный список обращений для оператора."""
        tickets = self.service.get_tickets_for_operator()
        if not tickets:
            print("\nОчередь заявок пуста.")
            return

        print("\n--- ОЧЕРЕДЬ ЗАЯВОК (СОРТИРОВКА ПО ПРИОРИТЕТУ) ---")
        for t in tickets:
            override_flag = " [РУЧНОЙ ПРИОРИТЕТ]" if t.manual_priority_override else ""
            print(f"#{t.id} | Приоритет: {t.priority.value:<9}{override_flag} | Статус: {t.status.value:<12} | Клиент: {t.client_name}")
            print(f"    Тема: {t.title}")
            print(f"    Оператор: {t.operator_name or 'Не назначен'}")
            print("-" * 45)

    def _take_ticket(self) -> None:
        """Передать обращение в работу указанному оператору."""
        try:
            t_id = int(input("\nВведите ID заявки: "))
            operator = input("Имя оператора: ").strip()
            ticket = self.service.take_ticket_to_work(t_id, operator)
            if ticket:
                print(f"[УСПЕХ] Заявка #{ticket.id} переведена в статус '{ticket.status.value}', оператор: {operator}")
            else:
                print("Заявка с таким ID не найдена.")
        except ValueError:
            print("Ошибка: введите корректный числовой ID.")

    def _override_priority(self) -> None:
        """Изменить категорию приоритета вручную."""
        try:
            t_id = int(input("\nВведите ID заявки: "))
            print("Доступные приоритеты: 1. Низкий | 2. Средний | 3. Высокий | 4. Наивысший")
            p_input = int(input("Выберите новый приоритет (1-4): ").strip())
            p_choice = PriorityChoice(p_input)
            ticket = self.service.override_priority(t_id, PRIORITY_MAP[p_choice])
            if ticket:
                print(f"[УСПЕХ] Приоритет заявки #{ticket.id} изменен на '{ticket.priority.value}' вручную (зафиксировано в логе).")
            else:
                print("Заявка не найдена.")
        except ValueError:
            print("Ошибка: выбран некорректный вариант.")

    def _change_status(self) -> None:
        """Обновить статус текущей заявки."""
        try:
            t_id = int(input("\nВведите ID заявки: "))
            print("Статусы: 1. В работе | 2. Ожидает ответа | 3. Решена | 4. Закрыта")
            s_input = int(input("Выберите новый статус (1-4): ").strip())
            s_choice = StatusChoice(s_input)
            ticket = self.service.change_status(t_id, STATUS_MAP[s_choice])
            if ticket:
                print(f"[УСПЕХ] Статус заявки #{ticket.id} обновлен на '{ticket.status.value}'.")
            else:
                print("Заявка не найдена.")
        except ValueError:
            print("Ошибка: выбран некорректный вариант.")
