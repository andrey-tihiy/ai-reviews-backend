from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from .utils import (
    authenticate_user,
    generate_user_tokens,
    validate_user_data,
    format_user_data,
    check_email_availability,
    validate_email_format
)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data output
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_active",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "date_joined", "created_at", "updated_at"]
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name"]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        """
        Validate registration data
        """
        # Check password confirmation
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                "password_confirm": ["Passwords do not match"]
            })
        
        # Remove password_confirm from validated data
        attrs.pop('password_confirm', None)
        
        # Validate user data using utility function
        validated_data = validate_user_data(attrs)
        
        return validated_data
    
    def create(self, validated_data):
        """
        Create user with validated data
        """
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile updates
    """
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    password_confirm = serializers.CharField(write_only=True, min_length=8, required=False)
    
    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name"]
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate(self, attrs):
        """
        Validate update data
        """
        # Check password confirmation if password is provided
        if attrs.get('password') and attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                "password_confirm": ["Passwords do not match"]
            })
        
        # Remove password_confirm from validated data
        attrs.pop('password_confirm', None)
        
        # Validate user data using utility function
        validated_data = validate_user_data(attrs, user_instance=self.instance)
        
        return validated_data
    
    def update(self, instance, validated_data):
        """
        Update user with validated data
        """
        password = validated_data.pop('password', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update password if provided
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """
        Authenticate user and return tokens
        """
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password', '')
        
        # Authenticate user using utility function
        user = authenticate_user(email, password)
        
        # Generate tokens
        tokens = generate_user_tokens(user)
        
        return {
            'user': format_user_data(user),
            'tokens': tokens
        }


class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for token refresh
    """
    refresh = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """
        Refresh access token
        """
        refresh_token = attrs.get('refresh')
        
        try:
            refresh = RefreshToken(refresh_token)
            
            # Get user from token
            user_id = refresh.payload.get('user_id')
            user = User.objects.get(id=user_id)
            
            # Check if user is still active
            if not user.is_active:
                raise serializers.ValidationError({
                    "non_field_errors": ["Account is disabled"]
                })
            
            # Generate new access token
            access_token = str(refresh.access_token)
            
            return {
                'access': access_token,
                'user': format_user_data(user)
            }
            
        except Exception as e:
            raise serializers.ValidationError({
                "refresh": ["Invalid or expired refresh token"]
            })


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def validate(self, attrs):
        """
        Validate password change data
        """
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        
        # Check current password
        if not self.user.check_password(current_password):
            raise serializers.ValidationError({
                "current_password": ["Current password is incorrect"]
            })
        
        # Check new password confirmation
        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                "new_password_confirm": ["New passwords do not match"]
            })
        
        # Validate new password using utility function
        validate_user_data({'password': new_password})
        
        return attrs
    
    def save(self):
        """
        Save new password
        """
        new_password = self.validated_data['new_password']
        self.user.set_password(new_password)
        self.user.save()
        return self.user


# Response serializers for API documentation
class LoginResponseSerializer(serializers.Serializer):
    """
    Serializer for login response documentation
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField()
    error = serializers.CharField(allow_null=True)


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Serializer for token refresh response documentation
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField()
    error = serializers.CharField(allow_null=True)


class UserResponseSerializer(serializers.Serializer):
    """
    Serializer for user response documentation
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = UserSerializer()
    error = serializers.CharField(allow_null=True)


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer for error response documentation
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.CharField(allow_null=True)
    error = serializers.DictField()
