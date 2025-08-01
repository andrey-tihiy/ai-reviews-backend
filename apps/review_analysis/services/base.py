"""
Base classes for review analysis pipeline
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from apps.review.models import Review


class BaseAnalysisStep(ABC):
    """
    Базовый класс для шагов анализа отзывов
    """
    
    def __init__(self, **params):
        """
        Инициализация с параметрами из PipelineStepConfig.params
        """
        self.params = params
    
    @abstractmethod
    def process(self, review: Review, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка отзыва и обновление контекста
        
        Args:
            review: Объект отзыва для анализа
            context: Контекст с накопленными данными анализа
            
        Returns:
            Обновленный контекст
        """
        pass
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """
        Получение параметра с дефолтным значением
        """
        return self.params.get(key, default)


class StepRegistry:
    """
    Реестр для регистрации и получения классов шагов анализа
    """
    _registry: Dict[str, type[BaseAnalysisStep]] = {}
    
    @classmethod
    def register(cls, key: str):
        """
        Декоратор для регистрации класса шага
        """
        def decorator(step_class: type[BaseAnalysisStep]):
            cls._registry[key] = step_class
            return step_class
        return decorator
    
    @classmethod
    def get_step_class(cls, key: str) -> Optional[type[BaseAnalysisStep]]:
        """
        Получение класса шага по ключу
        """
        return cls._registry.get(key)
    
    @classmethod
    def get_all_steps(cls) -> Dict[str, type[BaseAnalysisStep]]:
        """
        Получение всех зарегистрированных шагов
        """
        return cls._registry.copy()