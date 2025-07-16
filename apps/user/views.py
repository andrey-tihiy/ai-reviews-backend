from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    CreateModelMixin,
)
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.openapi import OpenApiParameter

from .models import User
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    TokenRefreshSerializer,
    PasswordChangeSerializer,
    LoginResponseSerializer,
    TokenRefreshResponseSerializer,
    UserResponseSerializer,
    ErrorResponseSerializer,
)
from apps.service.responses import APIResponse


class UserPagination(PageNumberPagination):
    """
    Custom pagination for user lists
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserViewSet(
    GenericViewSet,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    CreateModelMixin,
):
    """
    A viewset for viewing and editing user instances.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = UserPagination

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ["create", "login"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        """
        if self.action == "create":
            return UserRegistrationSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="User list retrieved successfully",
                response=UserResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="Get user list",
        description="Retrieve a paginated list of users. Requires authentication."
    )
    def list(self, request):
        """
        List all users with pagination
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                
                return APIResponse.success(
                    data=paginated_response.data['results'],
                    message="Users retrieved successfully",
                    pagination={
                        'count': paginated_response.data['count'],
                        'next': paginated_response.data['next'],
                        'previous': paginated_response.data['previous'],
                        'total_pages': paginated_response.data.get('total_pages'),
                    }
                )
            
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success(
                data=serializer.data,
                message="Users retrieved successfully"
            )
            
        except Exception as e:
            return APIResponse.server_error(f"Failed to retrieve users: {str(e)}")

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="User retrieved successfully",
                response=UserResponseSerializer
            ),
            404: OpenApiResponse(
                description="User not found",
                response=ErrorResponseSerializer
            ),
        },
        summary="Get user details",
        description="Retrieve details of a specific user by ID."
    )
    def retrieve(self, request, pk=None):
        """
        Retrieve a specific user
        """
        try:
            user = self.get_object()
            serializer = self.get_serializer(user)
            return APIResponse.success(
                data=serializer.data,
                message="User retrieved successfully"
            )
        except User.DoesNotExist:
            return APIResponse.not_found_error("User not found")
        except Exception as e:
            return APIResponse.server_error(f"Failed to retrieve user: {str(e)}")

    @extend_schema(
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                description="User created successfully",
                response=UserResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
        },
        summary="Create new user",
        description="Register a new user account."
    )
    def create(self, request):
        """
        Create a new user
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserSerializer(user).data
            
            return APIResponse.success(
                data=user_data,
                message="User created successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        return APIResponse.validation_error(serializer.errors)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="User updated successfully",
                response=UserResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
            404: OpenApiResponse(
                description="User not found",
                response=ErrorResponseSerializer
            ),
        },
        summary="Update user",
        description="Update user information."
    )
    def update(self, request, pk=None):
        """
        Update user information
        """
        try:
            user = self.get_object()
            serializer = self.get_serializer(user, data=request.data)
            
            if serializer.is_valid():
                updated_user = serializer.save()
                user_data = UserSerializer(updated_user).data
                
                return APIResponse.success(
                    data=user_data,
                    message="User updated successfully"
                )
            
            return APIResponse.validation_error(serializer.errors)
            
        except User.DoesNotExist:
            return APIResponse.not_found_error("User not found")
        except Exception as e:
            return APIResponse.server_error(f"Failed to update user: {str(e)}")

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="User updated successfully",
                response=UserResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
            404: OpenApiResponse(
                description="User not found",
                response=ErrorResponseSerializer
            ),
        },
        summary="Partially update user",
        description="Partially update user information."
    )
    def partial_update(self, request, pk=None):
        """
        Partially update user information
        """
        try:
            user = self.get_object()
            serializer = self.get_serializer(user, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_user = serializer.save()
                user_data = UserSerializer(updated_user).data
                
                return APIResponse.success(
                    data=user_data,
                    message="User updated successfully"
                )
            
            return APIResponse.validation_error(serializer.errors)
            
        except User.DoesNotExist:
            return APIResponse.not_found_error("User not found")
        except Exception as e:
            return APIResponse.server_error(f"Failed to update user: {str(e)}")

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="Current user information",
                response=UserResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="Get current user",
        description="Get information about the currently authenticated user."
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current user information
        """
        serializer = UserSerializer(request.user)
        return APIResponse.success(
            data=serializer.data,
            message="Current user information retrieved successfully"
        )

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(
                description="Password changed successfully",
                response=UserResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="Change password",
        description="Change the password for the currently authenticated user."
    )
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change user password
        """
        serializer = PasswordChangeSerializer(data=request.data, user=request.user)
        
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserSerializer(user).data
            
            return APIResponse.success(
                data=user_data,
                message="Password changed successfully"
            )
        
        return APIResponse.validation_error(serializer.errors)


class LoginView(APIView):
    """
    User login view
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful",
                response=LoginResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication failed",
                response=ErrorResponseSerializer
            ),
        },
        summary="User login",
        description="Authenticate user with email and password to get JWT tokens."
    )
    def post(self, request):
        """
        Authenticate user and return JWT tokens
        """
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            validated_data = serializer.validated_data
            
            return APIResponse.success(
                data={
                    'user': validated_data['user'],
                    'tokens': validated_data['tokens']
                },
                message="Login successful"
            )
        
        return APIResponse.validation_error(serializer.errors)


class TokenRefreshView(APIView):
    """
    JWT token refresh view
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=TokenRefreshSerializer,
        responses={
            200: OpenApiResponse(
                description="Token refreshed successfully",
                response=TokenRefreshResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
            401: OpenApiResponse(
                description="Invalid or expired token",
                response=ErrorResponseSerializer
            ),
        },
        summary="Refresh JWT token",
        description="Refresh access token using refresh token."
    )
    def post(self, request):
        """
        Refresh JWT access token
        """
        serializer = TokenRefreshSerializer(data=request.data)
        
        if serializer.is_valid():
            validated_data = serializer.validated_data
            
            return APIResponse.success(
                data={
                    'access': validated_data['access'],
                    'user': validated_data['user']
                },
                message="Token refreshed successfully"
            )
        
        return APIResponse.validation_error(serializer.errors)
