from rest_framework import serializers
from .models import App, AppPlatformData
from apps.user.serializers import UserSerializer


class AppPlatformDataSerializer(serializers.ModelSerializer):
    """
    Serializer for AppPlatformData model
    """
    class Meta:
        model = AppPlatformData
        fields = [
            'id', 'platform', 'platform_app_id', 'bundle_id', 'developer_id',
            'name', 'current_version', 'current_version_release_date',
            'icon_url', 'price', 'currency', 'rating_average', 'rating_count',
            'is_primary', 'extra_metadata'
        ]
        read_only_fields = ['id']


class AppListSerializer(serializers.ModelSerializer):
    """
    Serializer for App list view (without platform data for performance)
    """
    owner = UserSerializer(read_only=True)
    competitors_count = serializers.SerializerMethodField()
    
    class Meta:
        model = App
        fields = [
            'id', 'name', 'owner', 'competitors_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def get_competitors_count(self, obj):
        return obj.competitors.count()


class AppDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for App detail view (with primary platform data)
    """
    owner = UserSerializer(read_only=True)
    primary_platform_data = serializers.SerializerMethodField()
    competitors_count = serializers.SerializerMethodField()
    
    class Meta:
        model = App
        fields = [
            'id', 'name', 'owner', 'primary_platform_data',
            'competitors_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def get_primary_platform_data(self, obj):
        primary_platform = obj.primary_platform
        if primary_platform:
            return AppPlatformDataSerializer(primary_platform).data
        return None
    
    def get_competitors_count(self, obj):
        return obj.competitors.count()


class AppCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for App creation
    """
    url = serializers.URLField()
    
    class Meta:
        model = App
        fields = ['name', 'url']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit competitors queryset to current user's apps

    
    def validate_name(self, value):
        """
        Validate that app name is unique for this user
        """
        user = self.context['request'].user
        if App.objects.filter(owner=user, name=value).exists():
            raise serializers.ValidationError("You already have an app with this name")
        return value
    
    def create(self, validated_data):
        """
        Create app with current user as owner
        """
        from .tasks import process_new_app
        
        user = self.context['request'].user
        url = validated_data.pop('url', None)
        app = App.objects.create(owner=user, **validated_data)
        
        # Start async processing of the new app
        process_new_app.delay(
            app_id=str(app.id),
            url=url
        )
        
        return app


class AppUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for App updates
    """
    competitors = serializers.PrimaryKeyRelatedField(
        queryset=App.objects.none(),
        many=True,
        required=False,
        help_text="List of competitor app IDs"
    )
    
    class Meta:
        model = App
        fields = ['name', 'competitors']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit competitors queryset to current user's apps
        if self.context.get('request'):
            user = self.context['request'].user
            self.fields['competitors'].queryset = App.objects.filter(owner=user)
    
    def validate_name(self, value):
        """
        Validate that app name is unique for this user (excluding current app)
        """
        user = self.context['request'].user
        existing_apps = App.objects.filter(owner=user, name=value)
        
        if self.instance:
            existing_apps = existing_apps.exclude(pk=self.instance.pk)
        
        if existing_apps.exists():
            raise serializers.ValidationError("You already have an app with this name")
        
        return value
    
    def update(self, instance, validated_data):
        """
        Update app
        """
        competitors = validated_data.pop('competitors', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Update competitors if provided
        if competitors is not None:
            instance.competitors.set(competitors)
        
        return instance


# Response serializers for API documentation
class AppResponseSerializer(serializers.Serializer):
    """
    Serializer for app response documentation
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AppDetailSerializer()
    error = serializers.CharField(allow_null=True)


class AppListResponseSerializer(serializers.Serializer):
    """
    Serializer for app list response documentation
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AppListSerializer(many=True)
    error = serializers.CharField(allow_null=True)
    pagination = serializers.DictField(allow_null=True) 