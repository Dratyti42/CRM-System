"""ИИ-агент приоритизации: абстрактный класс + реализации ."""

from __future__ import annotations

from abc import ABC, abstractmethod

from models import ClassificationResult, Priority


class PriorityClassifier(ABC):
    """Абстрактный классификатор приоритета заявок."""

    @abstractmethod
    def classify(self, title: str, description: str) -> ClassificationResult:
        """Возвращает рассчитанный приоритет заявки и уверенность модели."""
        ...


class KeywordPriorityClassifier(PriorityClassifier):
    """Классификатор на основе анализа ключевых слов в тексте заявки."""

    KEYWORDS: dict[Priority, tuple[str, ...]] = {
        Priority.CRITICAL: (
            "авария",
            "сбой",
            "не работает",
            "критично",
            "остановка",
            "падение",
            "недоступен",
        ),
        Priority.HIGH: (
            "срочно",
            "важно",
            "ошибка",
            "проблема",
            "нарушение",
        ),
        Priority.MEDIUM: (
            "запрос",
            "уточнение",
            "вопрос",
            "помощь",
            "настройка",
        ),
        Priority.LOW: (
            "информация",
            "консультация",
            "предложение",
            "пожелание",
            "документация",
        ),
    }

    def classify(self, title: str, description: str) -> ClassificationResult:
        """Определяет приоритет по числу совпавших ключевых слов."""
        text = f"{title} {description}".lower()
        for priority in (Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW):
            matches = sum(1 for keyword in self.KEYWORDS[priority] if keyword in text)
            if matches > 0:
                confidence = min(0.6 + matches * 0.1, 0.99)
                return ClassificationResult(priority=priority, confidence=confidence)
        return ClassificationResult(priority=Priority.MEDIUM, confidence=0.5)


class FallbackPriorityClassifier(PriorityClassifier):
    """Резервный классификатор: применяется при недоступности ИИ-сервиса."""

    def classify(self, title: str, description: str) -> ClassificationResult:
        """Всегда возвращает средний приоритет с нулевой уверенностью."""
        return ClassificationResult(priority=Priority.MEDIUM, confidence=0.0)


class SafePriorityClassifier(PriorityClassifier):
    """Обёртка, использующая резервный классификатор при сбое основного."""

    def __init__(self, primary: PriorityClassifier, fallback: PriorityClassifier) -> None:
        """Принимает основной и резервный классификаторы."""
        self._primary = primary
        self._fallback = fallback

    def classify(self, title: str, description: str) -> ClassificationResult:
        """Пытается вызвать основной классификатор, при ошибке — резервный."""
        try:
            return self._primary.classify(title, description)
        except Exception:
            return self._fallback.classify(title, description)