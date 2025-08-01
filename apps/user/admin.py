from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg, Q
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render

from .models import User


# Inline classes removed to avoid circular imports
# The UserAdmin will show apps through the apps_count method with a link to filtered view


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'full_name', 'apps_count', 'total_reviews', 
        'avg_rating', 'is_active', 'date_joined', 'last_login'
    ]
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 
        'date_joined', 'last_login'
    ]
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = [
        'date_joined', 'last_login', 'apps_count', 'total_reviews', 
        'avg_rating', 'platforms_summary', 'recent_activity', 'password_link'
    ]
    ordering = ['-date_joined']
    
    fieldsets = (
        (_('Personal Information'), {
            'fields': ('email', 'first_name', 'last_name', 'password_link')
        }),
        (_('Statistics'), {
            'fields': ('apps_count', 'total_reviews', 'avg_rating', 'platforms_summary'),
        }),
        (_('Recent Activity'), {
            'fields': ('recent_activity',),
        }),
        (_('Important Dates'), {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
    )
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = _('Full Name')
    full_name.admin_order_field = 'first_name'
    
    def apps_count(self, obj):
        count = obj.app_set.count()
        if count > 0:
            url = reverse('admin:app_app_changelist') + f'?owner__id__exact={obj.id}'
            return format_html('<a href="{}">{} apps</a>', url, count)
        return f"{count} apps"
    apps_count.short_description = _('Apps')
    
    def total_reviews(self, obj):
        total = 0
        for app in obj.app_set.all():
            for platform_data in app.platform_data.all():
                total += platform_data.reviews.count()
        return total
    total_reviews.short_description = _('Total Reviews')
    
    def avg_rating(self, obj):
        ratings = []
        for app in obj.app_set.all():
            for platform_data in app.platform_data.all():
                if platform_data.rating_average:
                    ratings.append(float(platform_data.rating_average))
        
        if ratings:
            avg = sum(ratings) / len(ratings)
            return f"{avg:.2f}★"
        return "N/A"
    avg_rating.short_description = _('Avg Rating')
    
    def platforms_summary(self, obj):
        platforms = {}
        for app in obj.app_set.all():
            for platform_data in app.platform_data.all():
                platform = platform_data.platform
                if platform not in platforms:
                    platforms[platform] = 0
                platforms[platform] += 1
        
        if platforms:
            summary = []
            for platform, count in platforms.items():
                summary.append(f"{platform}: {count}")
            return ", ".join(summary)
        return "No platforms"
    platforms_summary.short_description = _('Platforms Summary')
    
    def recent_activity(self, obj):
        # Get recent reviews for user's apps
        from apps.review.models import Review
        recent_reviews = Review.objects.filter(
            app_platform_data__app__owner=obj
        ).order_by('-created_at')[:5]
        
        if not recent_reviews:
            return "No recent activity"
        
        activity_list = []
        for review in recent_reviews:
            app_name = review.app_platform_data.app.name
            platform = review.app_platform_data.platform
            activity_list.append(
                f"• {review.rating}★ review for {app_name} ({platform}) - {review.created_at.strftime('%Y-%m-%d')}"
            )
        
        return mark_safe("<br>".join(activity_list))
    recent_activity.short_description = _('Recent Activity')
    
    def password_link(self, obj):
        """Display password change link"""
        if obj.pk:
            # Use the correct URL pattern for password change
            url = reverse('admin:user_user_change', args=[obj.pk]) + 'password/'
            return format_html('<a href="{}" class="button">Change Password</a>', url)
        return "Save user first to change password"
    password_link.short_description = _('Password')
    
    def get_urls(self):
        """Add custom URL for password change"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/password/',
                self.admin_site.admin_view(self.password_change_view),
                name='user_user_password_change',
            ),
        ]
        return custom_urls + urls
    
    def password_change_view(self, request, object_id):
        """Custom password change view"""
        from django.contrib.auth.forms import AdminPasswordChangeForm
        from django.contrib import messages
        from django.shortcuts import redirect
        
        try:
            user = self.get_object(request, object_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('admin:user_user_changelist')
        
        if request.method == 'POST':
            form = AdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Password changed successfully.')
                return redirect('admin:user_user_change', object_id)
        else:
            form = AdminPasswordChangeForm(user)
        
        context = {
            'title': f'Change password for {user}',
            'form': form,
            'user': user,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request, user),
        }
        return render(request, 'admin/auth/user/change_password.html', context)
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'app_set__platform_data__reviews'
        )
    
    def changelist_view(self, request, extra_context=None):
        """Add statistics to the changelist view"""
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            response.context_data['total_users'] = qs.count()
            response.context_data['active_users'] = qs.filter(is_active=True).count()
            
            # Calculate total apps and reviews
            total_apps = 0
            total_reviews = 0
            for user in qs:
                total_apps += user.app_set.count()
                for app in user.app_set.all():
                    for platform_data in app.platform_data.all():
                        total_reviews += platform_data.reviews.count()
            
            response.context_data['total_apps'] = total_apps
            response.context_data['total_reviews'] = total_reviews
            
        except (AttributeError, KeyError):
            pass
        
        return response
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Add user statistics to the change form view"""
        response = super().changeform_view(request, object_id, form_url, extra_context)
        
        if object_id and hasattr(response, 'context_data'):
            try:
                user = User.objects.get(pk=object_id)
                
                # Calculate user statistics
                apps_count = user.app_set.count()
                
                total_reviews = 0
                avg_rating = 0
                rating_count = 0
                
                for app in user.app_set.all():
                    for platform_data in app.platform_data.all():
                        reviews_count = platform_data.reviews.count()
                        total_reviews += reviews_count
                        
                        if platform_data.rating_average:
                            avg_rating += float(platform_data.rating_average)
                            rating_count += 1
                
                if rating_count > 0:
                    avg_rating = avg_rating / rating_count
                
                # Get recent activity
                from apps.review.models import Review
                recent_reviews = Review.objects.filter(
                    app_platform_data__app__owner=user
                ).order_by('-created_at')[:5]
                
                response.context_data.update({
                    'user_apps_count': apps_count,
                    'user_total_reviews': total_reviews,
                    'user_avg_rating': avg_rating,
                    'user_recent_reviews': recent_reviews,
                })
                
            except User.DoesNotExist:
                pass
        
        return response


# Note: App, AppPlatformData, and Review models are registered in their respective admin.py files
