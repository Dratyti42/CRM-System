"""Модуль классификации заявок (паттерны GoF: Strategy, Decorator, Factory)."""

import logging
import time
from abc import ABC, abstractmethod
from typing import ClassVar

from .models import Priority

logger = logging.getLogger(__name__)


class BasePriorityClassifier(ABC):
    """Абстрактная стратегия классификации клиентских обращений."""

    @abstractmethod
    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Определить приоритет заявки и уровень уверенности модели."""


class KeywordPriorityStrategy(BasePriorityClassifier):
    """Стратегия классификации заявок на основе анализа ключевых слов."""

    CRITICAL_KEYWORDS: tuple[str, ...] = (
        "авария",
        "упал",
        "лежит",
        "блокирует",
        "критично",
    )
    HIGH_KEYWORDS: tuple[str, ...] = (
        "ошибка",
        "не работает",
        "срочно",
        "сбой",
    )
    LOW_KEYWORDS: tuple[str, ...] = (
        "вопрос",
        "консультация",
        "уточнить",
        "информация",
    )

    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Выполнить оценку текста и вернуть приоритет с коэффициентом уверенности."""
        text = f"{title} {description}".lower()

        if any(word in text for word in self.CRITICAL_KEYWORDS):
            return Priority.CRITICAL, 0.95

        if any(word in text for word in self.HIGH_KEYWORDS):
            return Priority.HIGH, 0.85

        if any(word in text for word in self.LOW_KEYWORDS):
            return Priority.LOW, 0.90

        return Priority.MEDIUM, 0.50


class StrictCriticalStrategy(BasePriorityClassifier):
    """Строгая стратегия с повышенной чувствительностью к инцидентам безопасности и оплат."""

    CRITICAL_KEYWORDS: tuple[str, ...] = (
        "авария",
        "упал",
        "лежит",
        "блокирует",
        "критично",
        "взлом",
        "утечка",
        "оплата",
        "деньги",
    )
    HIGH_KEYWORDS: tuple[str, ...] = (
        "ошибка",
        "не работает",
        "срочно",
        "сбой",
        "тормозит",
        "доступ",
    )
    LOW_KEYWORDS: tuple[str, ...] = (
        "вопрос",
        "консультация",
        "уточнить",
        "информация",
        "подскажите",
    )

    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Определить приоритет с акцентом на критические бизнес-инциденты."""
        text = f"{title} {description}".lower()

        if any(word in text for word in self.CRITICAL_KEYWORDS):
            return Priority.CRITICAL, 0.96

        if any(word in text for word in self.HIGH_KEYWORDS):
            return Priority.HIGH, 0.88

        if any(word in text for word in self.LOW_KEYWORDS):
            return Priority.LOW, 0.85

        return Priority.MEDIUM, 0.55


class FallbackPriorityStrategy(BasePriorityClassifier):
    """Резервная стратегия, всегда назначающая средний приоритет."""

    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Вернуть приоритет по умолчанию с пониженной уверенностью."""
        return Priority.MEDIUM, 0.50


class ClassifierDecorator(BasePriorityClassifier):
    """Базовый декоратор для расширения поведения классификатора."""

    def __init__(self, wrapped: BasePriorityClassifier) -> None:
        """Сохранить ссылку на оборачиваемый классификатор."""
        self._wrapped = wrapped

    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Делегировать классификацию вложенному объекту."""
        return self._wrapped.predict(title, description)


class FallbackClassifierDecorator(ClassifierDecorator):
    """Декоратор отказоустойчивости: возвращает средний приоритет при сбое модели."""

    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Выполнить классификацию с перехватом сбоев и переходом в режим Fallback."""
        try:
            return self._wrapped.predict(title, description)
        except Exception:
            logger.exception(
                "Сбой классификатора заявок; применен резервный приоритет '%s'.",
                Priority.MEDIUM.value,
            )
            return Priority.MEDIUM, 0.50


class LoggingClassifierDecorator(ClassifierDecorator):
    """Декоратор логирования результатов и времени работы классификатора."""

    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Замерить время инференса и зафиксировать прогноз в журнале."""
        start = time.perf_counter()
        priority, confidence = self._wrapped.predict(title, description)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Классификация завершена за %.2f мс: priority=%s, confidence=%.2f",
            elapsed_ms,
            priority.value,
            confidence,
        )
        return priority, confidence


class ClassifierFactory:
    """Фабрика для создания настроенного классификатора с декораторами."""

    _STRATEGIES: ClassVar[dict[str, type[BasePriorityClassifier]]] = {
        "keyword": KeywordPriorityStrategy,
        "strict": StrictCriticalStrategy,
        "fallback": FallbackPriorityStrategy,
    }

    @classmethod
    def create(
        cls,
        strategy_name: str = "keyword",
        *,
        enable_fallback: bool = True,
        enable_logging: bool = True,
    ) -> BasePriorityClassifier:
        """Собрать экземпляр классификатора по имени стратегии и флагам декораторов."""
        strategy_cls = cls._STRATEGIES.get(
            strategy_name.lower(), KeywordPriorityStrategy
        )
        classifier: BasePriorityClassifier = strategy_cls()
        if enable_fallback:
            classifier = FallbackClassifierDecorator(classifier)
        if enable_logging:
            classifier = LoggingClassifierDecorator(classifier)
        return classifier


KeywordAIAgent = KeywordPriorityStrategy
