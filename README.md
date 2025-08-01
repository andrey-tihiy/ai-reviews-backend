# AI Reviews - Django Application Management System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-5.2.4-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15.2-red.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive application and review management system with multi-platform support (App Store, Play Market, Product Hunt). Allows tracking ratings, reviews, and analytics for applications in a unified interface.

## 🚀 Key Features

- **Multi-platform Support**: App Store, Google Play Market, Product Hunt
- **Application Management**: Add, edit, delete applications
- **Review Analysis**: Collect and analyze reviews from various platforms
- **User System**: Registration, authentication, profile management
- **REST API**: Full-featured API with Swagger documentation
- **Admin Panel**: Advanced admin panel with analytics
- **Asynchronous Tasks**: Celery for background operations
- **Caching**: Redis for performance improvement

## 🏗️ Project Architecture

```
django_app/
├── apps/
│   ├── app/           # Application management
│   ├── review/        # Review system
│   ├── user/          # Users and authentication
│   └── service/       # Common services and utilities
├── django_app/        # Main Django settings
├── logs/              # Application logs
└── requirements.txt   # Python dependencies
```

## 📋 Requirements

- Python 3.8+
- Django 5.2.4
- PostgreSQL (recommended) or SQLite
- Redis (for Celery and caching)
- Node.js (for frontend build, if planned)

## 🛠️ Installation and Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd django_app
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Variables Setup

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Start Development Server

```bash
python manage.py runserver
```

## 🚀 Production Deployment

### 1. Database Setup

```bash
# For PostgreSQL
pip install psycopg2-binary

# Update DATABASES in settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 2. Redis Setup

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis
brew services start redis

# Windows
# Download Redis for Windows
```

### 3. Celery Setup

```bash
# Start Celery worker
celery -A django_app worker -l info

# Start Celery beat (for periodic tasks)
celery -A django_app beat -l info
```

### 4. Collect Static Files

```bash
python manage.py collectstatic
```

## 📚 API Documentation

### Swagger UI
Available at: `http://localhost:8000/api/docs/`

### ReDoc
Available at: `http://localhost:8000/api/redoc/`

### Main Endpoints

#### Authentication
- `POST /api/v1/users/register/` - User registration
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/refresh/` - Token refresh

#### Users
- `GET /api/v1/users/me/` - Current user information
- `PATCH /api/v1/users/{id}/` - Profile update
- `POST /api/v1/users/change_password/` - Password change

#### Applications
- `GET /api/v1/apps/` - User's applications list
- `POST /api/v1/apps/` - Create new application
- `GET /api/v1/apps/{id}/` - Application details
- `PUT /api/v1/apps/{id}/` - Update application
- `DELETE /api/v1/apps/{id}/` - Delete application

## 🔧 Admin Panel

Admin panel is available at: `http://localhost:8000/glory-hole/`

### Admin Panel Features:

- **Application Management**: View, edit, delete applications
- **Review Analysis**: Statistics by ratings and platforms
- **User Management**: Create, edit users
- **Data Export**: Export applications to CSV
- **Bulk Operations**: Mark applications as featured

## 🧪 Testing

### Quick API Testing

```bash
# User registration
curl -X POST http://localhost:8000/api/v1/users/register/ \
-H "Content-Type: application/json" \
-d '{
  "email": "test@example.com",
  "password": "TestPassword123!",
  "password_confirm": "TestPassword123!",
  "first_name": "Test",
  "last_name": "User"
}'

# User login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
-H "Content-Type: application/json" \
-d '{
  "email": "test@example.com",
  "password": "TestPassword123!"
}'
```

### Run Tests

```bash
python manage.py test
```

## 📊 Data Models

### App (Application)
- Main application model
- User relationship (owner)
- Competitor support
- Metadata in JSON format

### AppPlatformData (Platform Data)
- Platform-specific data
- Ratings, prices, versions
- Unique platform identifiers
- Additional metadata

### Review
- User reviews
- Ratings and comments
- Application platform relationship
- Review metadata

### User
- Custom user model
- Email-based authentication
- JWT tokens for API

## 🔌 Integrations

### Apple App Store
- Data extraction via iTunes API
- Review collection via RSS feed
- Multi-country support

### Google Play Market
- Integration planned
- Data collection via Google Play API

### Product Hunt
- Integration planned
- Data collection via Product Hunt API

## 🚀 Deployment

### Docker (recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "django_app.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/dbname
      - REDIS_URL=redis://redis:6379/0

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=dbname
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password

  redis:
    image: redis:6-alpine

  celery:
    build: .
    command: celery -A django_app worker -l info
    depends_on:
      - db
      - redis
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you have questions or suggestions:

- Create an Issue on GitHub
- Email us: support@example.com
- Join our Discord server

## 🔄 Updates

### v1.0.0 (Current Version)
- ✅ Basic application management functionality
- ✅ Apple App Store integration
- ✅ User system and authentication
- ✅ REST API with documentation
- ✅ Admin panel with analytics

### Planned Updates
- 🔄 Google Play Market integration
- 🔄 Product Hunt integration
- 🔄 Dashboard with charts and analytics
- 🔄 Rating change notifications
- 🔄 Report export in various formats

---

**AI Reviews** - Smart application and review management system 🚀 