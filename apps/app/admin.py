from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count, Avg, Q, F
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from .models import App, AppPlatformData


class AppPlatformDataInline(admin.TabularInline):
    model = AppPlatformData
    extra = 0
    fields = (
        'platform', 'name', 'current_version', 'price', 'currency', 
        'rating_average', 'rating_count', 'is_primary'
    )
    readonly_fields = ('platform_app_id', 'bundle_id')


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'owner', 'get_platforms_summary', 'get_total_reviews', 
        'get_avg_rating', 'get_primary_platform', 'competitors_count', 'created_at'
    ]
    list_filter = [
        'created_at', 'owner', 
        ('competitors', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'name', 'owner__email', 'owner__first_name', 'owner__last_name',
        'platform_data__name', 'platform_data__platform_app_id'
    ]
    inlines = [AppPlatformDataInline]
    filter_horizontal = ('competitors',)
    readonly_fields = [
        'id', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('id', 'name', 'owner', 'competitors')
        }),
        (_('Important Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_apps', 'mark_as_featured', 'update_ratings_summary']
    
    def get_platforms_summary(self, obj):
        """Показывает сводку по платформам"""
        platforms = obj.platform_data.all()
        if not platforms:
            return "No platforms"
        
        summary = []
        for platform in platforms:
            icon = self._get_platform_icon(platform.platform)
            platform_name = dict(AppPlatformData.PLATFORM_CHOICES).get(platform.platform, platform.platform)
            reviews_count = platform.reviews.count()
            summary.append(f"{icon} {platform_name} ({reviews_count} reviews)")
        
        return mark_safe("<br>".join(summary))
    get_platforms_summary.short_description = _('Platforms')
    
    def get_total_reviews(self, obj):
        """Показывает общее количество отзывов"""
        total = 0
        for platform_data in obj.platform_data.all():
            total += platform_data.reviews.count()
        
        if total > 0:
            url = reverse('admin:review_review_changelist') + f'?app_platform_data__app__id__exact={obj.id}'
            return format_html('<a href="{}">{} reviews</a>', url, total)
        return f"{total} reviews"
    get_total_reviews.short_description = _('Total Reviews')
    
    def get_avg_rating(self, obj):
        """Показывает средний рейтинг"""
        ratings = []
        for platform_data in obj.platform_data.all():
            if platform_data.rating_average:
                ratings.append(float(platform_data.rating_average))
        
        if ratings:
            avg = sum(ratings) / len(ratings)
            stars = '★' * int(avg) + '☆' * (5 - int(avg))
            return format_html(
                '<span style="font-size: 14px;">{}</span> <span style="font-weight: bold;">({})</span>',
                stars, f"{avg:.2f}"
            )
        return "N/A"
    get_avg_rating.short_description = _('Avg Rating')
    
    def get_primary_platform(self, obj):
        """Показывает основную платформу"""
        primary = obj.primary_platform
        if primary:
            icon = self._get_platform_icon(primary.platform)
            platform_name = dict(AppPlatformData.PLATFORM_CHOICES).get(primary.platform, primary.platform)
            return format_html('{} {}', icon, platform_name)
        return "No primary platform"
    get_primary_platform.short_description = _('Primary Platform')
    
    def competitors_count(self, obj):
        """Показывает количество конкурентов"""
        count = obj.competitors.count()
        if count > 0:
            url = reverse('admin:app_app_changelist') + f'?competitors__id__exact={obj.id}'
            return format_html('<a href="{}">{} competitors</a>', url, count)
        return f"{count} competitors"
    competitors_count.short_description = _('Competitors')
    
    def get_recent_reviews(self, obj):
        """Показывает последние отзывы"""
        from apps.review.models import Review
        recent_reviews = Review.objects.filter(
            app_platform_data__app=obj
        ).order_by('-created_at')[:5]
        
        if not recent_reviews:
            return "No recent reviews"
        
        review_list = []
        for review in recent_reviews:
            platform_icon = self._get_platform_icon(review.app_platform_data.platform)
            stars = '★' * review.rating + '☆' * (5 - review.rating)
            review_list.append(
                f"• {platform_icon} {stars} - {review.author} ({review.created_at.strftime('%Y-%m-%d')})"
            )
        
        return mark_safe("<br>".join(review_list))
    get_recent_reviews.short_description = _('Recent Reviews')
    
    def get_reviews_summary(self, obj):
        """Показывает сводку по отзывам"""
        from apps.review.models import Review
        reviews = Review.objects.filter(app_platform_data__app=obj)
        
        if not reviews:
            return "No reviews"
        
        # Статистика по рейтингам
        rating_stats = {}
        for i in range(1, 6):
            rating_stats[i] = reviews.filter(rating=i).count()
        
        # Статистика по платформам
        platform_stats = {}
        for platform_data in obj.platform_data.all():
            platform_name = dict(AppPlatformData.PLATFORM_CHOICES).get(platform_data.platform, platform_data.platform)
            platform_stats[platform_name] = platform_data.reviews.count()
        
        summary = []
        summary.append("<strong>Rating Distribution:</strong>")
        for rating, count in rating_stats.items():
            stars = '★' * rating + '☆' * (5 - rating)
            summary.append(f"  {stars}: {count} reviews")
        
        summary.append("<br><strong>By Platform:</strong>")
        for platform, count in platform_stats.items():
            summary.append(f"  {platform}: {count} reviews")
        
        return mark_safe("<br>".join(summary))
    get_reviews_summary.short_description = _('Reviews Summary')
    
    def get_competitors_list(self, obj):
        """Показывает список конкурентов"""
        competitors = obj.competitors.all()
        if not competitors:
            return "No competitors"
        
        competitor_list = []
        for competitor in competitors:
            url = reverse('admin:app_app_change', args=[competitor.id])
            competitor_list.append(
                f'<a href="{url}">{competitor.name}</a> (Owner: {competitor.owner.email})'
            )
        
        return mark_safe("<br>".join(competitor_list))
    get_competitors_list.short_description = _('Competitors List')
    
    def _get_platform_icon(self, platform):
        """Возвращает иконку для платформы"""
        platform_icons = {
            'appstore': '🍎',
            'play_market': '🤖',
            'product_hunt': '🔍',
        }
        return platform_icons.get(platform, '📱')
    
    def export_apps(self, request, queryset):
        """Экспорт приложений в CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="apps_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Owner', 'Platforms', 'Total Reviews', 'Avg Rating', 
            'Primary Platform', 'Competitors', 'Created At'
        ])
        
        for app in queryset.prefetch_related('platform_data', 'owner', 'competitors'):
            platforms = ", ".join([p.platform for p in app.platform_data.all()])
            total_reviews = sum(p.reviews.count() for p in app.platform_data.all())
            competitors = ", ".join([c.name for c in app.competitors.all()])
            
            writer.writerow([
                app.name,
                app.owner.email,
                platforms,
                total_reviews,
                app.primary_platform.rating_average if app.primary_platform else "N/A",
                app.primary_platform.platform if app.primary_platform else "N/A",
                competitors,
                app.created_at,
            ])
        
        return response
    export_apps.short_description = 'Export apps to CSV'
    
    def mark_as_featured(self, request, queryset):
        """Отметить приложения как избранные"""
        updated = queryset.update(metadata=F('metadata') + {'featured': True})
        self.message_user(
            request,
            f'Marked as featured: {updated} apps'
        )
    mark_as_featured.short_description = 'Mark as featured'
    
    def update_ratings_summary(self, request, queryset):
        """Обновить сводку рейтингов"""
        updated = 0
        for app in queryset:
            # Здесь можно добавить логику обновления рейтингов
            updated += 1
        
        self.message_user(
            request,
            f'Updated ratings summary for {updated} apps'
        )
    update_ratings_summary.short_description = 'Update ratings summary'
    
    def get_queryset(self, request):
        """Оптимизируем запросы"""
        return super().get_queryset(request).prefetch_related(
            'platform_data__reviews',
            'owner',
            'competitors'
        )
    
    def changelist_view(self, request, extra_context=None):
        """Добавляем статистику в список"""
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            response.context_data['total_apps'] = qs.count()
            
            # Подсчитываем общую статистику
            total_reviews = 0
            total_platforms = 0
            for app in qs:
                for platform_data in app.platform_data.all():
                    total_reviews += platform_data.reviews.count()
                total_platforms += app.platform_data.count()
            
            response.context_data['total_reviews'] = total_reviews
            response.context_data['total_platforms'] = total_platforms
            
        except (AttributeError, KeyError):
            pass
        
        return response


@admin.register(AppPlatformData)
class AppPlatformDataAdmin(admin.ModelAdmin):
    list_display = [
        'app', 'platform', 'name', 'current_version', 'price', 'currency', 
        'get_rating_display', 'is_primary', 'get_reviews_count', 'icon_preview'
    ]
    list_filter = [
        'platform', 'is_primary', 'current_version_release_date', 'currency',
        ('app__owner', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'app__name', 'name', 'platform_app_id', 'bundle_id', 'developer_id'
    ]
    list_editable = ('is_primary',)
    readonly_fields = [
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        (_('Basic Info'), {
            'fields': ('app', 'platform', 'name', 'is_primary')
        }),
        (_('Platform IDs'), {
            'fields': ('platform_app_id', 'bundle_id', 'developer_id')
        }),
        (_('App Details'), {
            'fields': ('current_version', 'current_version_release_date', 'icon_url', 'price', 'currency')
        }),
        (_('Ratings & Reviews'), {
            'fields': ('rating_average', 'rating_count')
        }),
        (_('Extra Data'), {
            'fields': ('extra_metadata',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_rating_display(self, obj):
        """Показывает рейтинг со звездами"""
        if obj.rating_average:
            stars = '★' * int(obj.rating_average) + '☆' * (5 - int(obj.rating_average))
            return format_html(
                '<span style="font-size: 14px;">{}</span> <span style="font-weight: bold;">({})</span>',
                stars, obj.rating_average
            )
        return "N/A"
    get_rating_display.short_description = _('Rating')
    
    def get_reviews_count(self, obj):
        """Показывает количество отзывов с ссылкой"""
        count = obj.reviews.count()
        if count > 0:
            url = reverse('admin:review_review_changelist') + f'?app_platform_data__id__exact={obj.id}'
            return format_html('<a href="{}">{} reviews</a>', url, count)
        return f"{count} reviews"
    get_reviews_count.short_description = _('Reviews')
    
    def icon_preview(self, obj):
        """Показывает иконку приложения"""
        if obj.icon_url:
            return format_html(
                '<img src="{}" style="width: 64px; height: 64px; border-radius: 12px;" />',
                obj.icon_url
            )
        return "No icon"
    icon_preview.short_description = _('Icon')
    
    def get_extra_metadata_summary(self, obj):
        """Показывает краткую сводку extra_metadata"""
        if not obj.extra_metadata:
            return "No extra metadata"
        
        summary = []
        metadata = obj.extra_metadata
        
        if 'description' in metadata:
            desc = metadata['description'][:100] + '...' if len(metadata['description']) > 100 else metadata['description']
            summary.append(f"<strong>Description:</strong> {desc}")
        
        if 'genres' in metadata:
            genres = ", ".join(metadata['genres'][:5])  # Показываем только первые 5
            summary.append(f"<strong>Genres:</strong> {genres}")
        
        if 'languages' in metadata:
            languages = ", ".join(metadata['languages'][:5])
            summary.append(f"<strong>Languages:</strong> {languages}")
        
        if 'devices' in metadata:
            devices = ", ".join(metadata['devices'][:5])
            summary.append(f"<strong>Devices:</strong> {devices}")
        
        return mark_safe("<br>".join(summary))
    get_extra_metadata_summary.short_description = _('Metadata Summary')
    
    def get_queryset(self, request):
        """Оптимизируем запросы"""
        return super().get_queryset(request).select_related('app__owner').prefetch_related('reviews')
