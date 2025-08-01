"""
Django Admin для управления анализом отзывов
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count, Q
from django import forms
from django_json_widget.widgets import JSONEditorWidget

from .models import (
    PipelineStepType, PipelineStepConfig, PromptTemplate,
    AnalysisResult, ReviewTicket
)
from .tasks import run_review_pipeline, reanalyze_reviews


class ReadOnlyAdminMixin:
    """Миксин для read-only полей"""
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PipelineStepType)
class PipelineStepTypeAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """
    Read-only справочник типов шагов
    """
    list_display = ['key', 'label', 'description', 'created_at']
    list_filter = ['key']
    search_fields = ['label', 'description']
    readonly_fields = ['id', 'key', 'label', 'description', 'created_at', 'updated_at']
    
    def has_add_permission(self, request):
        # Разрешаем добавление только суперпользователям
        return request.user.is_superuser


class PipelineStepConfigForm(forms.ModelForm):
    """Форма с JSON виджетом для параметров"""
    class Meta:
        model = PipelineStepConfig
        fields = '__all__'
        widgets = {
            'params': JSONEditorWidget(attrs={
                'style': 'height: 300px;',
            })
        }


@admin.register(PipelineStepConfig)
class PipelineStepConfigAdmin(admin.ModelAdmin):
    """
    Конфигурация шагов пайплайна с drag-and-drop сортировкой
    """
    form = PipelineStepConfigForm
    list_display = ['get_status_icon', 'order', 'step_type', 'get_params_preview', 'updated_at']
    list_filter = ['enabled', 'step_type__key']
    list_editable = ['order']
    ordering = ['order']
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('step_type', 'enabled', 'order')
        }),
        ('Parameters', {
            'fields': ('params',),
            'description': 'Configure step-specific parameters. See help text for available options.'
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_status_icon(self, obj):
        """Иконка статуса"""
        if obj.enabled:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    get_status_icon.short_description = 'Status'
    
    def get_params_preview(self, obj):
        """Превью параметров"""
        if not obj.params:
            return '-'
        preview = str(obj.params)[:50]
        if len(str(obj.params)) > 50:
            preview += '...'
        return preview
    get_params_preview.short_description = 'Parameters'
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        """Добавляем help_text для params"""
        field = super().formfield_for_dbfield(db_field, **kwargs)
        
        if db_field.name == 'params':
            field.help_text = """
            Available parameters by step type:
            - tone_detection: {} (no parameters needed)
            - issue_detection: {} (no parameters needed)
            - complexity_check: {} (no parameters needed)
            - gpt_analysis: {
                "api_key": "sk-...",  # Optional, uses OPENAI_API_KEY from settings if not provided
                "model": "gpt-4o-mini",  # GPT model to use
                "prompt_id": "default_review_analysis",  # Prompt template ID
                "skip_if_simple": true  # Skip simple reviews if ComplexityCheck marked them (default: true)
              }
            - persistence: {
                "auto_ticket_for_problems": true,  # Create tickets for problems
                "auto_ticket_for_complex": true,  # Create tickets for complex reviews
                "ticket_only_for_negative": false  # If true, create tickets only for negative reviews (rating <= 3)
              }
            
            Note: Each step works independently. You can enable/disable any combination of steps.
            """
        
        return field


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    """
    Управление шаблонами промптов
    """
    list_display = ['prompt_id', 'version', 'get_active_status', 'get_text_preview', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['prompt_id', 'text']
    
    fieldsets = (
        ('Identification', {
            'fields': ('prompt_id', 'version', 'is_active')
        }),
        ('Content', {
            'fields': ('text',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def get_active_status(self, obj):
        """Статус активности"""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: gray;">Inactive</span>')
    get_active_status.short_description = 'Status'
    
    def get_text_preview(self, obj):
        """Превью текста промпта"""
        preview = obj.text[:100]
        if len(obj.text) > 100:
            preview += '...'
        return preview
    get_text_preview.short_description = 'Text Preview'
    
    @admin.action(description='Mark selected prompts as active')
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
    
    @admin.action(description='Mark selected prompts as inactive')
    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)


class AnalysisResultInline(admin.TabularInline):
    """Inline для результатов анализа в Review"""
    model = AnalysisResult
    extra = 0
    readonly_fields = [
        'tone', 'raw_polarity', 'raw_subjectivity', 'issues',
        'complex_review', 'confidence', 'analysis_source', 'analysis_timestamp'
    ]
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    """
    Результаты анализа отзывов
    """
    list_display = [
        'get_review_preview', 'get_tone_display', 'get_issues_count',
        'analysis_source', 'get_executed_steps', 'confidence', 'analysis_timestamp'
    ]
    list_filter = ['tone', 'analysis_source', 'analysis_timestamp', 'complex_review']
    search_fields = ['review__content', 'review__title', 'issues', 'notes']
    readonly_fields = [
        'id', 'review', 'tone', 'raw_polarity', 'raw_subjectivity',
        'issues', 'complex_review', 'notes', 'confidence',
        'analysis_source', 'analysis_timestamp', 'full_payload', 'flag_support',
        'created_at', 'updated_at', 'get_review_link', 'get_executed_steps'
    ]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('review', 'get_review_link')
        }),
        ('Analysis Results', {
            'fields': (
                'tone', 'raw_polarity', 'raw_subjectivity',
                'issues', 'complex_review', 'notes', 'confidence'
            )
        }),
        ('Analysis Metadata', {
            'fields': (
                'analysis_source', 'analysis_timestamp', 'get_executed_steps', 'flag_support'
            )
        }),
        ('Debug Information', {
            'fields': ('full_payload',),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_review_preview(self, obj):
        """Превью отзыва"""
        content = obj.review.content[:50]
        if len(obj.review.content) > 50:
            content += '...'
        return f"{obj.review.rating}★ - {content}"
    get_review_preview.short_description = 'Review'
    
    def get_tone_display(self, obj):
        """Отображение тональности с цветом"""
        colors = {
            'very_negative': 'darkred',
            'negative': 'red',
            'neutral': 'gray',
            'positive': 'green',
            'very_positive': 'darkgreen',
        }
        color = colors.get(obj.tone, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_tone_display()
        )
    get_tone_display.short_description = 'Tone'
    
    def get_issues_count(self, obj):
        """Количество проблем/запросов"""
        if not obj.issues or obj.issues == ["No specific issue or request detected"]:
            return '-'
        
        problems = sum(1 for i in obj.issues if "Problem:" in i)
        requests = sum(1 for i in obj.issues if "Request:" in i)
        
        result = []
        if problems:
            result.append(f'🐛 {problems}')
        if requests:
            result.append(f'💡 {requests}')
        
        return ' '.join(result) or '-'
    get_issues_count.short_description = 'Issues'
    
    def get_review_link(self, obj):
        """Ссылка на отзыв в админке"""
        url = reverse('admin:review_review_change', args=[obj.review.id])
        return format_html('<a href="{}">View Review →</a>', url)
    get_review_link.short_description = 'Review Link'
    
    def get_executed_steps(self, obj):
        """Показывает выполненные шаги анализа"""
        if obj.full_payload:
            steps = obj.full_payload.get('executed_steps', [])
            if steps:
                return ', '.join(steps)
        return '-'
    get_executed_steps.short_description = 'Executed Steps'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Разрешаем удаление только суперпользователям
        return request.user.is_superuser


@admin.register(ReviewTicket)
class ReviewTicketAdmin(admin.ModelAdmin):
    """
    Управление тикетами для проблемных отзывов
    """
    list_display = [
        'get_ticket_number', 'get_review_preview', 'get_status_badge',
        'assignee', 'priority', 'created_at'
    ]
    list_filter = ['status', 'priority', 'assignee', 'created_at']
    list_editable = ['assignee']
    search_fields = [
        'review__content', 'review__title', 'notes',
        'analysis_result__issues'
    ]
    raw_id_fields = ['review', 'analysis_result']
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('status', 'assignee', 'priority')
        }),
        ('Review Details', {
            'fields': ('review', 'get_review_content', 'get_analysis_summary')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('System Fields', {
            'fields': ('id', 'analysis_result', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'get_review_content',
        'get_analysis_summary'
    ]
    
    actions = [
        'mark_as_in_progress', 'mark_as_closed',
        'reanalyze_and_reopen', 'assign_to_me'
    ]
    
    def get_ticket_number(self, obj):
        """Номер тикета"""
        return format_html('Ticket #{}', str(obj.id)[:8])
    get_ticket_number.short_description = '#'
    
    def get_review_preview(self, obj):
        """Превью отзыва"""
        app_name = obj.review.app_platform_data.app.name
        rating = obj.review.rating
        content = obj.review.content[:50]
        if len(obj.review.content) > 50:
            content += '...'
        return f"{app_name} | {rating}★ | {content}"
    get_review_preview.short_description = 'Review'
    
    def get_status_badge(self, obj):
        """Бейдж статуса"""
        colors = {
            'open': '#dc3545',  # red
            'in_progress': '#ffc107',  # yellow
            'closed': '#28a745',  # green
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display().upper()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'
    
    def get_review_content(self, obj):
        """Полный контент отзыва"""
        return format_html(
            '<div style="background-color: #f8f9fa; padding: 10px; '
            'border-radius: 5px; margin: 10px 0;">'
            '<strong>Rating:</strong> {}★<br>'
            '<strong>Title:</strong> {}<br>'
            '<strong>Content:</strong> {}<br>'
            '<strong>Author:</strong> {}'
            '</div>',
            obj.review.rating,
            obj.review.title or '-',
            obj.review.content,
            obj.review.author or 'Anonymous'
        )
    get_review_content.short_description = 'Review Content'
    
    def get_analysis_summary(self, obj):
        """Сводка анализа"""
        analysis = obj.analysis_result
        issues_html = '<ul>'
        for issue in analysis.issues:
            if "Problem:" in issue:
                issues_html += f'<li>🐛 {issue}</li>'
            elif "Request:" in issue:
                issues_html += f'<li>💡 {issue}</li>'
        issues_html += '</ul>'
        
        return format_html(
            '<div style="background-color: #e9ecef; padding: 10px; '
            'border-radius: 5px; margin: 10px 0;">'
            '<strong>Tone:</strong> {}<br>'
            '<strong>Issues:</strong> {}<br>'
            '<strong>Complex:</strong> {}<br>'
            '<strong>Support Flag:</strong> {}'
            '</div>',
            analysis.get_tone_display(),
            mark_safe(issues_html) if analysis.issues else '-',
            analysis.complex_review or '-',
            analysis.flag_support or '-'
        )
    get_analysis_summary.short_description = 'Analysis Summary'
    
    @admin.action(description='Mark as In Progress')
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
        self.message_user(request, f"{queryset.count()} tickets marked as in progress.")
    
    @admin.action(description='Mark as Closed')
    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
        self.message_user(request, f"{queryset.count()} tickets closed.")
    
    @admin.action(description='Re-run Analysis and Reopen')
    def reanalyze_and_reopen(self, request, queryset):
        review_ids = list(queryset.values_list('review_id', flat=True))
        reanalyze_reviews.delay(review_ids)
        queryset.update(status='open')
        self.message_user(
            request,
            f"Re-analysis started for {len(review_ids)} reviews. Tickets reopened."
        )
    
    @admin.action(description='Assign to Me')
    def assign_to_me(self, request, queryset):
        queryset.update(assignee=request.user)
        self.message_user(request, f"{queryset.count()} tickets assigned to you.")
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'review__app_platform_data__app',
            'analysis_result',
            'assignee'
        )