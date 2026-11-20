# Применённые паттерны проектирования (GoF и Мартин Фаулер)

## 1. Паттерны Gang of Four (GoF)

### 1.1 Strategy (Стратегия) — поведенческий паттерн
* **Где реализован:** `src/crm_system_informatika/classifier.py` (`BasePriorityClassifier`, `KeywordPriorityStrategy`, `StrictCriticalStrategy`, `FallbackPriorityStrategy`).
* **Обоснование:** В CRM-системе алгоритм определения приоритета заявок должен заменяться (эвристика по ключевым словам, строгая бизнес-эвристика, резервная стратегия, а в будущем — HTTP-клиент к ML-модели) без изменения кода `CRMService`.

### 1.2 Decorator (Декоратор) — структурный паттерн
* **Где реализован:** `src/crm_system_informatika/classifier.py` (`ClassifierDecorator`, `FallbackClassifierDecorator`, `LoggingClassifierDecorator`).
* **Обоснование:** Динамически добавляет сквозную функциональность к любой стратегии классификации без дублирования кода:
  * `FallbackClassifierDecorator` реализует требование ТЗ (п. 4.2.1 и 5.1) — при сбое классификатора заявке назначается приоритет «Средний» (`0.50`).
  * `LoggingClassifierDecorator` замеряет время инференса и логирует результат.

### 1.3 Factory (Фабрика) — порождающий паттерн
* **Где реализован:** `src/crm_system_informatika/classifier.py` (`ClassifierFactory.create`) и `src/crm_system_informatika/app.py` (`create_app`).
* **Обоснование:** Инкапсулирует выбор нужной стратегии по переменной окружения `CLASSIFIER_STRATEGY` и её оборачивание декораторами, освобождая API и CLI от создания конкретных классов вручную.

### 1.4 Observer (Наблюдатель) — поведенческий паттерн
* **Где реализован:** `src/crm_system_informatika/observers.py` (`TicketEventPublisher`, `BaseTicketObserver`, `HighPriorityAlertObserver`, `ActivityLogObserver`).
* **Обоснование:** Слабо связывает `CRMService` с подсистемой оповещений. При создании или изменении заявки публикуется `TicketEvent`: `HighPriorityAlertObserver` формирует срочные оповещения в панели оператора для приоритетов `Высокий`/`Наивысший` (ТЗ п. 4.1.4), а `ActivityLogObserver` ведет системный журнал.

---

## 2. Паттерны Мартина Фаулера (PoEAA)

### 2.1 Repository
* **Где реализован:** `src/crm_system_informatika/repository.py` (`BaseTicketRepository`, `SQLAlchemyTicketRepository`, `TicketRepository`).
* **Обоснование:** Изолирует SQLAlchemy-запросы от бизнес-логики. Репозиторий работает с переданной `Session` и не вызывает `commit()` самостоятельно.

### 2.2 Unit of Work
* **Где реализован:** `src/crm_system_informatika/database/uow.py` (`BaseUnitOfWork`, `SQLAlchemyUnitOfWork`, `InMemoryUnitOfWork`).
* **Обоснование:** Использует `Session` SQLAlchemy для атомарной фиксации нескольких операций в одной транзакции (например, при ручной смене приоритета одновременно обновляется `tickets`, находится/создаётся оператор в `users` и добавляется запись в `ticket_audit_logs` с общим `commit()` / `rollback()`).

### 2.3 Service Layer
* **Где реализован:** `src/crm_system_informatika/service.py` (`CRMService`).
* **Обоснование:** Содержит все бизнес-правила (валидацию, сортировку очереди, допустимые переходы статусов, аудит) и переиспользуется сразу в трёх точках: FastAPI REST API, Jinja2 Web UI и CLI.

### 2.4 Data Mapper и DTO
* **Где реализованы:** `src/crm_system_informatika/database/mappers.py` (`TicketMapper`, `AuditLogMapper`) и `src/crm_system_informatika/dtos/` (`requests.py`, `responses.py`).
* **Обоснование:** Полностью отделяют ORM-модели БД, доменные датаклассы и контракты HTTP API на Pydantic.