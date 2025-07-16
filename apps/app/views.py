from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Q

from .models import App
from .serializers import (
    AppListSerializer,
    AppDetailSerializer,
    AppCreateSerializer,
    AppUpdateSerializer,
    AppResponseSerializer,
    AppListResponseSerializer,
)
from apps.service.responses import APIResponse
from apps.user.serializers import ErrorResponseSerializer


class AppPagination(PageNumberPagination):
    """
    Custom pagination for app lists
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AppViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user apps
    """
    pagination_class = AppPagination
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter apps to only show current user's apps
        """
        return App.objects.filter(owner=self.request.user).select_related('owner').prefetch_related('competitors')
    
    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on action
        """
        if self.action == 'list':
            return AppListSerializer
        elif self.action == 'create':
            return AppCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppUpdateSerializer
        else:  # retrieve
            return AppDetailSerializer
    
    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="Apps retrieved successfully",
                response=AppListResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="List user apps",
        description="Retrieve a paginated list of apps owned by the current user.",
        tags=["Apps"]
    )
    def list(self, request):
        """
        List all apps for the current user
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                
                return APIResponse.success(
                    data=paginated_response.data['results'],
                    message="Apps retrieved successfully",
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
                message="Apps retrieved successfully"
            )
            
        except Exception as e:
            return APIResponse.server_error(f"Failed to retrieve apps: {str(e)}")
    
    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="App retrieved successfully",
                response=AppResponseSerializer
            ),
            404: OpenApiResponse(
                description="App not found",
                response=ErrorResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="Get app details",
        description="Retrieve details of a specific app including primary platform data.",
        tags=["Apps"]
    )
    def retrieve(self, request, pk=None):
        """
        Retrieve a specific app with all details
        """
        try:
            app = self.get_object()
            serializer = self.get_serializer(app)
            
            return APIResponse.success(
                data=serializer.data,
                message="App retrieved successfully"
            )
            
        except App.DoesNotExist:
            return APIResponse.not_found_error("App not found")
        except Exception as e:
            return APIResponse.server_error(f"Failed to retrieve app: {str(e)}")
    
    @extend_schema(
        request=AppCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="App created successfully",
                response=AppResponseSerializer
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
        summary="Create new app",
        description="Create a new app for the current user.",
        tags=["Apps"]
    )
    def create(self, request):
        """
        Create a new app
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            app = serializer.save()
            response_serializer = AppDetailSerializer(app)
            
            return APIResponse.success(
                data=response_serializer.data,
                message="App created successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        return APIResponse.validation_error(serializer.errors)
    
    @extend_schema(
        request=AppUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="App updated successfully",
                response=AppResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
            404: OpenApiResponse(
                description="App not found",
                response=ErrorResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="Update app",
        description="Update app information.",
        tags=["Apps"]
    )
    def update(self, request, pk=None):
        """
        Update an app
        """
        try:
            app = self.get_object()
            serializer = self.get_serializer(app, data=request.data)
            
            if serializer.is_valid():
                updated_app = serializer.save()
                response_serializer = AppDetailSerializer(updated_app)
                
                return APIResponse.success(
                    data=response_serializer.data,
                    message="App updated successfully"
                )
            
            return APIResponse.validation_error(serializer.errors)
            
        except App.DoesNotExist:
            return APIResponse.not_found_error("App not found")
        except Exception as e:
            return APIResponse.server_error(f"Failed to update app: {str(e)}")
    
    @extend_schema(
        request=AppUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="App updated successfully",
                response=AppResponseSerializer
            ),
            400: OpenApiResponse(
                description="Validation error",
                response=ErrorResponseSerializer
            ),
            404: OpenApiResponse(
                description="App not found",
                response=ErrorResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="Partially update app",
        description="Partially update app information.",
        tags=["Apps"]
    )
    def partial_update(self, request, pk=None):
        """
        Partially update an app
        """
        try:
            app = self.get_object()
            serializer = self.get_serializer(app, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_app = serializer.save()
                response_serializer = AppDetailSerializer(updated_app)
                
                return APIResponse.success(
                    data=response_serializer.data,
                    message="App updated successfully"
                )
            
            return APIResponse.validation_error(serializer.errors)
            
        except App.DoesNotExist:
            return APIResponse.not_found_error("App not found")
        except Exception as e:
            return APIResponse.server_error(f"Failed to update app: {str(e)}")
    
    @extend_schema(
        responses={
            204: OpenApiResponse(
                description="App deleted successfully"
            ),
            404: OpenApiResponse(
                description="App not found",
                response=ErrorResponseSerializer
            ),
            401: OpenApiResponse(
                description="Authentication required",
                response=ErrorResponseSerializer
            ),
        },
        summary="Delete app",
        description="Delete an app and all its associated data.",
        tags=["Apps"]
    )
    def destroy(self, request, pk=None):
        """
        Delete an app
        """
        try:
            app = self.get_object()
            app_name = app.name
            app.delete()
            
            return APIResponse.success(
                data=None,
                message=f"App '{app_name}' deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
            
        except App.DoesNotExist:
            return APIResponse.not_found_error("App not found")
        except Exception as e:
            return APIResponse.server_error(f"Failed to delete app: {str(e)}")
