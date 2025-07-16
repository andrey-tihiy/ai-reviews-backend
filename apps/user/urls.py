from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, LoginView, TokenRefreshView

router = DefaultRouter()
router.register(r"users", UserViewSet)

urlpatterns = [
    # JWT authentication endpoints
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # User management endpoints (handled by ViewSet)
    # GET /api/v1/users/ - List users
    # POST /api/v1/users/register/ - Register user
    # GET /api/v1/users/{id}/ - Get user details
    # PUT /api/v1/users/{id}/ - Update user
    # PATCH /api/v1/users/{id}/ - Partially update user
    # GET /api/v1/users/me/ - Get current user
    # POST /api/v1/users/change_password/ - Change password
] + router.urls
