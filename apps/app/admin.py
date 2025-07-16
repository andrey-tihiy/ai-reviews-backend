from django.contrib import admin
from .models import App, AppPlatformData


class AppPlatformDataInline(admin.TabularInline):
    model = AppPlatformData
    extra = 0
    fields = ('platform', 'name', 'current_version', 'price', 'currency', 'rating_average', 'is_primary')
    readonly_fields = ('platform_app_id', 'bundle_id')


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'get_primary_platform', 'created_at')
    list_filter = ('created_at', 'owner')
    search_fields = ('name', 'owner__email', 'owner__first_name', 'owner__last_name')
    inlines = [AppPlatformDataInline]
    filter_horizontal = ('competitors',)
    
    def get_primary_platform(self, obj):
        primary = obj.primary_platform
        return f"{primary.platform} - {primary.name}" if primary else "No primary platform"
    get_primary_platform.short_description = 'Primary Platform'


@admin.register(AppPlatformData)
class AppPlatformDataAdmin(admin.ModelAdmin):
    list_display = ('app', 'platform', 'name', 'current_version', 'price', 'currency', 'rating_average', 'is_primary')
    list_filter = ('platform', 'is_primary', 'current_version_release_date')
    search_fields = ('app__name', 'name', 'platform_app_id', 'bundle_id')
    list_editable = ('is_primary',)
    readonly_fields = ('created_at', 'updated_at') if hasattr(AppPlatformData, 'created_at') else ()
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('app', 'platform', 'name', 'is_primary')
        }),
        ('Platform IDs', {
            'fields': ('platform_app_id', 'bundle_id', 'developer_id')
        }),
        ('App Details', {
            'fields': ('current_version', 'current_version_release_date', 'icon_url', 'price', 'currency')
        }),
        ('Ratings', {
            'fields': ('rating_average', 'rating_count')
        }),
        ('Extra Data', {
            'fields': ('extra_metadata',),
            'classes': ('collapse',)
        })
    )
