from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.service.models import UUIDModel
from apps.review.models import Review

# ArrayField доступен только для PostgreSQL
try:
    from django.contrib.postgres.fields import ArrayField
except ImportError:
    ArrayField = None

User = get_user_model()


class PipelineStepType(UUIDModel):
    """
    Справочник всех возможных шагов пайплайна
    """
    STEP_KEYS = [
        ('tone_detection', 'Tone Detection'),
        ('issue_detection', 'Issue Detection'),
        ('complexity_check', 'Complexity Check'),
        ('gpt_analysis', 'GPT Analysis'),
        ('persistence', 'Persistence'),
    ]
    
    key = models.CharField(
        max_length=50,
        unique=True,
        choices=STEP_KEYS,
        help_text='Unique identifier for the pipeline step type'
    )
    label = models.CharField(
        max_length=100,
        help_text='Human-readable label for the step'
    )
    description = models.TextField(
        blank=True,
        help_text='Detailed description of what this step does'
    )
    
    class Meta:
        ordering = ['label']
        verbose_name = 'Pipeline Step Type'
        verbose_name_plural = 'Pipeline Step Types'
    
    def __str__(self):
        return f"{self.label} ({self.key})"


class PipelineStepConfig(UUIDModel):
    """
    Конфигурация шагов пайплайна анализа
    """
    step_type = models.ForeignKey(
        PipelineStepType,
        on_delete=models.CASCADE,
        related_name='configs',
        help_text='Type of pipeline step'
    )
    enabled = models.BooleanField(
        default=True,
        help_text='Whether this step is enabled'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='Order in which steps are executed (lower numbers first)'
    )
    params = models.JSONField(
        default=dict,
        blank=True,
        help_text='Parameters for the step (e.g., thresholds, model settings, prompt_id)'
    )
    
    class Meta:
        ordering = ['order', 'step_type__label']
        verbose_name = 'Pipeline Step Configuration'
        verbose_name_plural = 'Pipeline Step Configurations'
        indexes = [
            models.Index(fields=['enabled', 'order']),
        ]
    
    def __str__(self):
        status = "✓" if self.enabled else "✗"
        return f"{status} {self.order}. {self.step_type.label}"


class PromptTemplate(UUIDModel):
    """
    Шаблоны промптов для GPT анализа
    """
    prompt_id = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique identifier for the prompt template'
    )
    version = models.CharField(
        max_length=20,
        default='1.0',
        help_text='Version of the prompt template'
    )
    text = models.TextField(
        help_text='The actual prompt template text'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this prompt is currently active'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Prompt Template'
        verbose_name_plural = 'Prompt Templates'
        unique_together = [('prompt_id', 'version')]
        indexes = [
            models.Index(fields=['prompt_id', 'is_active']),
        ]
    
    def __str__(self):
        active = "✓" if self.is_active else ""
        return f"{self.prompt_id} v{self.version} {active}"


class AnalysisResult(UUIDModel):
    """
    Результаты анализа отзыва
    """
    TONE_CHOICES = [
        ('very_negative', 'Very Negative'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('positive', 'Positive'),
        ('very_positive', 'Very Positive'),
    ]
    
    ANALYSIS_SOURCE_CHOICES = [
        ('local', 'Local Analysis'),
        ('gpt', 'GPT Analysis'),
        ('manual', 'Manual Override'),
        ('none', 'No Analysis (All Steps Disabled)'),
    ]
    
    review = models.OneToOneField(
        Review,
        on_delete=models.CASCADE,
        related_name='analysis_result',
        help_text='The review that was analyzed'
    )
    
    # Основные результаты анализа
    tone = models.CharField(
        max_length=20,
        choices=TONE_CHOICES,
        help_text='Overall tone of the review'
    )
    raw_polarity = models.FloatField(
        help_text='Raw polarity score (-1 to 1)'
    )
    raw_subjectivity = models.FloatField(
        help_text='Raw subjectivity score (0 to 1)'
    )
    issues = models.JSONField(
        default=list,
        help_text='List of detected issues/requests'
    )
    complex_review = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Reason why this review needs manual attention'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Additional notes from analysis'
    )
    confidence = models.FloatField(
        default=1.0,
        help_text='Confidence score of the analysis (0-1)'
    )
    
    # Метаданные анализа
    analysis_source = models.CharField(
        max_length=20,
        choices=ANALYSIS_SOURCE_CHOICES,
        default='local',
        help_text='Source of the analysis'
    )
    analysis_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When the analysis was performed'
    )
    full_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text='Full analysis payload for debugging'
    )
    
    # Флаги для поддержки
    flag_support = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Support flag (e.g., hidden issue in positive review)'
    )
    
    class Meta:
        ordering = ['-analysis_timestamp']
        verbose_name = 'Analysis Result'
        verbose_name_plural = 'Analysis Results'
        indexes = [
            models.Index(fields=['tone', 'analysis_timestamp']),
            models.Index(fields=['analysis_source']),
            models.Index(fields=['complex_review']),
        ]
    
    def __str__(self):
        return f"{self.review} - {self.get_tone_display()}"
    
    def has_issues(self):
        """Check if review has any issues"""
        return bool(self.issues and any("Problem:" in issue for issue in self.issues))
    
    def has_requests(self):
        """Check if review has any feature requests"""
        return bool(self.issues and any("Request:" in issue for issue in self.issues))


class ReviewTicket(UUIDModel):
    """
    Тикеты для отзывов, требующих внимания
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]
    
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='tickets',
        help_text='The review associated with this ticket'
    )
    analysis_result = models.ForeignKey(
        AnalysisResult,
        on_delete=models.CASCADE,
        related_name='tickets',
        help_text='The analysis result that triggered this ticket'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        help_text='Current status of the ticket'
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        help_text='User assigned to handle this ticket'
    )
    
    # Дополнительные поля
    priority = models.IntegerField(
        default=0,
        help_text='Priority level (higher = more urgent)'
    )
    notes = models.TextField(
        blank=True,
        help_text='Internal notes about the ticket'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review Ticket'
        verbose_name_plural = 'Review Tickets'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assignee', 'status']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.review} ({self.get_status_display()})"


# Сигналы для автоматического запуска анализа
@receiver(post_save, sender=Review)
def trigger_review_analysis(sender, instance, created, **kwargs):
    """
    Автоматически запускает анализ при создании нового отзыва
    """
    if created:
        from .tasks import run_review_pipeline
        # Запускаем задачу в очереди 'analysis'
        run_review_pipeline.apply_async(
            args=[str(instance.id)],
            queue='analysis'
        )