from abc import ABC, abstractmethod

from src.models import Priority


class BasePriorityClassifier(ABC):
    """Абстрактный интерфейс сервиса классификации обращений."""

    @abstractmethod
    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Определить приоритет заявки и уровень уверенности модели."""
        pass


class KeywordAIAgent(BasePriorityClassifier):
    """Эвристический классификатор заявок на основе анализа ключевых слов."""

    def predict(self, title: str, description: str) -> tuple[Priority, float]:
        """Выполнить оценку текста и вернуть приоритет с коэффициентом уверенности."""
        text = f"{title} {description}".lower()

        if any(word in text for word in ["авария", "упал", "лежит", "блокирует", "критично"]):
            return Priority.CRITICAL, 0.95

        if any(word in text for word in ["ошибка", "не работает", "срочно", "сбой"]):
            return Priority.HIGH, 0.85

        if any(word in text for word in ["вопрос", "консультация", "уточнить", "информация"]):
            return Priority.LOW, 0.90

        return Priority.MEDIUM, 0.50
