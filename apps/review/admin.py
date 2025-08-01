from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Review
from django.db import models
from django.db.models import F
from apps.app.models import AppPlatformData
from apps.review_analysis.admin import AnalysisResultInline


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'get_app_name',
        'get_platform',
        'get_rating_stars',
        'author',
        'title_preview',
        'version',
        'get_app_owner',
        'get_analysis_status',
        'platform_updated_at',
        'created_at'
    ]
    
    list_filter = [
        'app_platform_data__platform',
        'app_platform_data__app__name',
        'app_platform_data__app__owner',
        'rating',
        'platform_updated_at',
        'created_at',
        ('app_platform_data__app__competitors', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'app_platform_data__app__name',
        'author',
        'title',
        'content',
        'review_id'
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'get_app_name',
        'get_platform',
        'get_rating_stars'
    ]
    
    inlines = [AnalysisResultInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'app_platform_data',
                'review_id',
                'author',
                'rating',
                'get_rating_stars',
            )
        }),
        ('Content', {
            'fields': (
                'title',
                'content',
                'version',
            )
        }),
        ('Metadata', {
            'fields': (
                'platform_updated_at',
                'metadata',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def get_app_name(self, obj):
        """Displays app name"""
        return obj.app_platform_data.app.name
    get_app_name.short_description = 'App'
    get_app_name.admin_order_field = 'app_platform_data__app__name'
    
    def get_platform(self, obj):
        """Displays platform with icon"""
        platform_icons = {
            'appstore': '🍎',
            'play_market': '🤖',
            'product_hunt': '🔍',
        }
        icon = platform_icons.get(obj.app_platform_data.platform, '📱')
        platform_name = dict(AppPlatformData.PLATFORM_CHOICES).get(
            obj.app_platform_data.platform, obj.app_platform_data.platform
        )
        return format_html('{} {}', icon, platform_name)
    get_platform.short_description = 'Platform'
    get_platform.admin_order_field = 'app_platform_data__platform'
    
    def get_rating_stars(self, obj):
        """Displays rating with stars"""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="font-size: 16px;">{}</span> <span style="font-weight: bold;">({})</span>',
            stars, obj.rating
        )
    get_rating_stars.short_description = 'Rating'
    get_rating_stars.admin_order_field = 'rating'
    
    def title_preview(self, obj):
        """Shows title preview"""
        if obj.title:
            return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
        return '-'
    title_preview.short_description = 'Title'
    
    def content_preview(self, obj):
        """Shows content preview"""
        if obj.content:
            return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        return '-'
    content_preview.short_description = 'Content'
    
    def get_app_owner(self, obj):
        """Shows app owner"""
        return obj.app_platform_data.app.owner.email
    get_app_owner.short_description = 'App Owner'
    get_app_owner.admin_order_field = 'app_platform_data__app__owner__email'
    
    def get_analysis_status(self, obj):
        """Shows analysis status"""
        if hasattr(obj, 'analysis_result'):
            tone = obj.analysis_result.tone
            if tone == 'very_negative':
                color = 'darkred'
            elif tone == 'negative':
                color = 'red'
            elif tone == 'neutral':
                color = 'gray'
            elif tone == 'positive':
                color = 'green'
            else:  # very_positive
                color = 'darkgreen'
            return format_html(
                '<span style="color: {};">✓ Analyzed</span>',
                color
            )
        return format_html('<span style="color: orange;">⚠ Pending</span>')
    get_analysis_status.short_description = 'Analysis'
    
    def get_queryset(self, request):
        """Оптимизируем запросы с prefetch_related"""
        return super().get_queryset(request).select_related(
            'app_platform_data__app'
        )
    
    # Настройки для лучшего отображения
    list_per_page = 25
    list_max_show_all = 1000
    
    # Дополнительные действия
    actions = ['mark_as_important', 'export_reviews', 'mark_high_rating_reviews', 'run_analysis']
    
    def mark_as_important(self, request, queryset):
        """Action to mark reviews as important"""
        updated = queryset.update(metadata=F('metadata') + {'important': True})
        self.message_user(
            request,
            f'Marked as important: {updated} reviews'
        )
    mark_as_important.short_description = 'Mark as important'
    
    def mark_high_rating_reviews(self, request, queryset):
        """Action to mark high rating reviews"""
        high_rating_reviews = queryset.filter(rating__gte=4)
        updated = high_rating_reviews.update(metadata=F('metadata') + {'high_rating': True})
        self.message_user(
            request,
            f'Marked as high rating: {updated} reviews (rating 4-5)'
        )
    mark_high_rating_reviews.short_description = 'Mark high rating reviews'
    
    def export_reviews(self, request, queryset):
        """Action to export reviews"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reviews_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'App', 'Platform', 'Rating', 'Author', 'Title', 
            'Content', 'Version', 'Updated At', 'Created At'
        ])
        
        for review in queryset.select_related('app_platform_data__app'):
            writer.writerow([
                review.app_platform_data.app.name,
                review.app_platform_data.get_platform_display(),
                review.rating,
                review.author,
                review.title,
                review.content,
                review.version,
                review.platform_updated_at,
                review.created_at,
            ])
        
        return response
    export_reviews.short_description = 'Export reviews to CSV'
    
    def run_analysis(self, request, queryset):
        """Action to run analysis on selected reviews"""
        from apps.review_analysis.tasks import reanalyze_reviews
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Преобразуем UUID в строки для Celery
        review_ids = [str(id) for id in queryset.values_list('id', flat=True)]
        
        logger.info(f"Starting analysis for reviews: {review_ids}")
        
        try:
            result = reanalyze_reviews.apply_async(args=[review_ids], queue='analysis')
            logger.info(f"Task submitted with ID: {result.id}")
            
            self.message_user(
                request,
                f'Analysis started for {len(review_ids)} reviews. Results will be available soon.',
                level='SUCCESS'
            )
        except Exception as e:
            logger.error(f"Failed to submit analysis task: {str(e)}")
            self.message_user(
                request,
                f'Failed to start analysis: {str(e)}',
                level='ERROR'
            )
    run_analysis.short_description = 'Run analysis on selected reviews'
    
    def get_queryset(self, request):
        """Optimize queries with select_related for better performance"""
        return super().get_queryset(request).select_related(
            'app_platform_data__app'
        ).prefetch_related('analysis_result')
    
    def changelist_view(self, request, extra_context=None):
        """Custom changelist view without global statistics"""
        return super().changelist_view(request, extra_context=extra_context)
