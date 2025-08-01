from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Review
from django.db import models


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
    
    def get_queryset(self, request):
        """Оптимизируем запросы с prefetch_related"""
        return super().get_queryset(request).select_related(
            'app_platform_data__app'
        )
    
    # Настройки для лучшего отображения
    list_per_page = 25
    list_max_show_all = 1000
    
    # Дополнительные действия
    actions = ['mark_as_important', 'export_reviews', 'mark_high_rating_reviews']
    
    def mark_as_important(self, request, queryset):
        """Action to mark reviews as important"""
        updated = queryset.update(metadata=models.F('metadata') + {'important': True})
        self.message_user(
            request,
            f'Marked as important: {updated} reviews'
        )
    mark_as_important.short_description = 'Mark as important'
    
    def mark_high_rating_reviews(self, request, queryset):
        """Action to mark high rating reviews"""
        high_rating_reviews = queryset.filter(rating__gte=4)
        updated = high_rating_reviews.update(metadata=models.F('metadata') + {'high_rating': True})
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
    
    def get_queryset(self, request):
        """Optimize queries with select_related for better performance"""
        return super().get_queryset(request).select_related(
            'app_platform_data__app'
        )
    
    def changelist_view(self, request, extra_context=None):
        """Custom changelist view without global statistics"""
        return super().changelist_view(request, extra_context=extra_context)


# Импортируем AppPlatformData для использования в choices
from apps.app.models import AppPlatformData
