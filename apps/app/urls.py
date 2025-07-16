from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AppViewSet

router = DefaultRouter()
router.register(r"apps", AppViewSet, basename="app")

urlpatterns = [
    # App management endpoints (handled by ViewSet)
    # GET /api/v1/apps/ - List user apps
    # POST /api/v1/apps/ - Create app
    # GET /api/v1/apps/{id}/ - Get app details
    # PUT /api/v1/apps/{id}/ - Update app
    # PATCH /api/v1/apps/{id}/ - Partially update app
    # DELETE /api/v1/apps/{id}/ - Delete app
] + router.urls 