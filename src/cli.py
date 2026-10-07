from src.classifier import KeywordAIAgent
from src.models import Priority, Status
from src.repository import TicketRepository
from src.service import CRMService


class ConsoleUI:
    def __init__(self, service: CRMService):
        self.service = service

    def run(self):
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
            choice = input("\nВыберите действие: ").strip()

            if choice == "1":
                self._create_ticket()
            elif choice == "2":
                self._list_tickets()
            elif choice == "3":
                self._take_ticket()
            elif choice == "4":
                self._override_priority()
            elif choice == "5":
                self._change_status()
            elif choice == "0":
                print("Выход из системы. До свидания!")
                break
            else:
                print("Неверный ввод, попробуйте еще раз.")

    def _create_ticket(self):
        print("\n--- СОЗДАНИЕ ЗАЯВКИ ---")
        client_name = input("Ваше имя / Email: ").strip()
        title = input("Тема обращения: ").strip()
        desc = input("Описание проблемы: ").strip()

        ticket = self.service.create_ticket(title, desc, client_name)
        print(f"\n[УСПЕХ] Заявка #{ticket.id} создана со статусом '{ticket.status.value}'!")
        print(f"-> ИИ определил приоритет: [{ticket.priority.value}] (Уверенность: {ticket.confidence_score * 100:.0f}%)")
        if ticket.confidence_score < 0.6:
            print("-> Примечание: Требуется подтверждение приоритета оператором (низкая уверенность ИИ).")

    def _list_tickets(self):
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

    def _take_ticket(self):
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

    def _override_priority(self):
        try:
            t_id = int(input("\nВведите ID заявки: "))
            print("Доступные приоритеты: 1. Низкий | 2. Средний | 3. Высокий | 4. Наивысший")
            p_map = {"1": Priority.LOW, "2": Priority.MEDIUM, "3": Priority.HIGH, "4": Priority.CRITICAL}
            p_choice = input("Выберите новый приоритет (1-4): ").strip()
            if p_choice in p_map:
                ticket = self.service.override_priority(t_id, p_map[p_choice])
                if ticket:
                    print(f"[УСПЕХ] Приоритет заявки #{ticket.id} изменен на '{ticket.priority.value}' вручную (зафиксировано в логе).")
                else:
                    print("Заявка не найдена.")
            else:
                print("Неверный выбор приоритета.")
        except ValueError:
            print("Ошибка ввода.")

    def _change_status(self):
        try:
            t_id = int(input("\nВведите ID заявки: "))
            print("Статусы: 1. В работе | 2. Ожидает ответа | 3. Решена | 4. Закрыта")
            s_map = {
                "1": Status.IN_PROGRESS,
                "2": Status.WAITING_CLIENT,
                "3": Status.RESOLVED,
                "4": Status.CLOSED,
            }
            s_choice = input("Выберите новый статус (1-4): ").strip()
            if s_choice in s_map:
                ticket = self.service.change_status(t_id, s_map[s_choice])
                if ticket:
                    print(f"[УСПЕХ] Статус заявки #{ticket.id} обновлен на '{ticket.status.value}'.")
                else:
                    print("Заявка не найдена.")
            else:
                print("Неверный выбор статуса.")
        except ValueError:
            print("Ошибка ввода.")