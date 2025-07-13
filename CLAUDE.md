# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django 5.2.4 REST API application using Django REST Framework. The project follows a standard Django structure with custom user authentication (email-based) and Celery for asynchronous tasks.

## Key Commands

### Development Server
```bash
python manage.py runserver
```

### Database Operations
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### Testing
```bash
python manage.py test
python manage.py test apps.user  # Test specific app
```

### Celery (Background Tasks)
```bash
celery -A django_app worker -l info
celery -A django_app beat -l info  # For scheduled tasks
```

## Architecture Overview

### Application Structure
- **apps/service/**: Base models and utilities (provides UUIDModel abstract base)
- **apps/user/**: Custom user model with email authentication, REST API endpoints
- **django_app/**: Main project configuration (settings, URLs, Celery config)

### Key Design Patterns
1. **UUID Primary Keys**: All models inherit from `UUIDModel` for UUID-based IDs
2. **Email Authentication**: Custom User model uses email instead of username
3. **REST API**: ViewSets and serializers for all API endpoints
4. **Session Authentication**: Default authentication method for API

### API Endpoints
- Admin: `/glory-hole/`
- User API: `/api/users/` (CRUD, login, logout, me)
- API Documentation: `/api/docs/` (Swagger UI)
- API Schema: `/api/schema/`

### Database
- Development: SQLite (db.sqlite3)
- Models use UUID primary keys via `UUIDModel` base class
- All models include `created_at` and `updated_at` timestamps

### Important Notes
1. SECRET_KEY is hardcoded in settings.py - should be moved to environment variables
2. No tests implemented yet - test files exist but are empty
3. CORS is configured for API access
4. Redis is required for Celery broker/backend
5. Frontend application exists separately at `/Users/tihiy/code/my/aireviews/my-app/`