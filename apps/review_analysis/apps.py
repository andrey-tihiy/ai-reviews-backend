from django.apps import AppConfig


class ReviewAnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.review_analysis"
    verbose_name = "Review Analysis"
    
    def ready(self):
        # Импортируем все шаги анализа для регистрации в StepRegistry
        from . import services  # noqa
        from .services import steps  # noqa
        # Явно импортируем все шаги чтобы они зарегистрировались
        from .services.steps import (  # noqa
            ToneDetectionStep,
            IssueDetectionStep,
            ComplexityCheckStep,
            GPTAnalysisStep,
            PersistenceStep,
        )
