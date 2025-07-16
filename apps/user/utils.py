from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from .models import User
import re


def validate_password_strength(password):
    """
    Validate password strength
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return errors


def validate_email_format(email):
    """
    Validate email format
    """
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def check_email_availability(email, exclude_user_id=None):
    """
    Check if email is available for registration
    """
    queryset = User.objects.filter(email__iexact=email)
    
    if exclude_user_id:
        queryset = queryset.exclude(id=exclude_user_id)
    
    return not queryset.exists()


def authenticate_user(email, password):
    """
    Authenticate user with email and password
    """
    if not email or not password:
        raise serializers.ValidationError({
            "non_field_errors": ["Email and password are required"]
        })
    
    if not validate_email_format(email):
        raise serializers.ValidationError({
            "email": ["Enter a valid email address"]
        })
    
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        raise serializers.ValidationError({
            "non_field_errors": ["Invalid email or password"]
        })
    
    if not user.check_password(password):
        raise serializers.ValidationError({
            "non_field_errors": ["Invalid email or password"]
        })
    
    if not user.is_active:
        raise serializers.ValidationError({
            "non_field_errors": ["Account is disabled"]
        })
    
    return user


def generate_user_tokens(user):
    """
    Generate JWT tokens for user
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def validate_user_data(data, user_instance=None):
    """
    Validate user registration/update data
    """
    errors = {}
    
    # Validate email
    email = data.get('email', '').strip().lower()
    if email:
        if not validate_email_format(email):
            errors['email'] = ["Enter a valid email address"]
        elif not check_email_availability(email, exclude_user_id=user_instance.id if user_instance else None):
            errors['email'] = ["User with this email already exists"]
    elif not user_instance:  # Required for registration
        errors['email'] = ["Email is required"]
    
    # Validate password (only for registration or when provided)
    password = data.get('password', '')
    if password:
        password_errors = validate_password_strength(password)
        if password_errors:
            errors['password'] = password_errors
    elif not user_instance:  # Required for registration
        errors['password'] = ["Password is required"]
    
    # Validate names
    first_name = data.get('first_name', '').strip()
    if first_name:
        if len(first_name) < 2:
            errors['first_name'] = ["First name must be at least 2 characters long"]
        elif len(first_name) > 50:
            errors['first_name'] = ["First name cannot exceed 50 characters"]
    elif not user_instance:  # Required for registration
        errors['first_name'] = ["First name is required"]
    
    last_name = data.get('last_name', '').strip()
    if last_name:
        if len(last_name) < 2:
            errors['last_name'] = ["Last name must be at least 2 characters long"]
        elif len(last_name) > 50:
            errors['last_name'] = ["Last name cannot exceed 50 characters"]
    elif not user_instance:  # Required for registration
        errors['last_name'] = ["Last name is required"]
    
    if errors:
        raise serializers.ValidationError(errors)
    
    return {
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        **({"password": password} if password else {})
    }


def format_user_data(user):
    """
    Format user data for API response
    """
    return {
        'id': str(user.id),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': f"{user.first_name} {user.last_name}".strip(),
        'is_active': user.is_active,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
    } 