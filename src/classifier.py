from abc import ABC, abstractmethod
from typing import Tuple
from src.models import Priority


class BasePriorityClassifier(ABC):
    # Абстрактный интерфейс классификатора

    @abstractmethod
    def predict(self, title: str, description: str) -> Tuple[Priority, float]:
        pass


class KeywordAIAgent(BasePriorityClassifier):
    # Имитация ИИ-агента с анализом ключевых слов и расчетом уверенности (Confidence Score)

    def predict(self, title: str, description: str) -> Tuple[Priority, float]:
        text = f"{title} {description}".lower()

        # Проверка на критические сбои
        if any(word in text for word in ["авария", "упал", "лежит", "блокирует", "критично"]):
            return Priority.CRITICAL, 0.95

        # Проверка на высокий приоритет
        if any(word in text for word in ["ошибка", "не работает", "срочно", "сбой"]):
            return Priority.HIGH, 0.85

        # Проверка на низкий приоритет
        if any(word in text for word in ["вопрос", "консультация", "уточнить", "информация"]):
            return Priority.LOW, 0.90

        # Если ИИ не уверен - ставится средний приоритет с низким коэффициентом
        return Priority.MEDIUM, 0.50
