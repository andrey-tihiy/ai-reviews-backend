# Быстрое тестирование API

## 1. Запуск сервера

```bash
python manage.py runserver
```

Сервер будет доступен на `http://localhost:8000`

## 2. Swagger UI

Откройте в браузере: `http://localhost:8000/api/docs/`

## 3. Тестирование через curl

### Регистрация пользователя

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
-H "Content-Type: application/json" \
-d '{
  "email": "test@example.com",
  "password": "TestPassword123!",
  "password_confirm": "TestPassword123!",
  "first_name": "Test",
  "last_name": "User"
}'
```

### Логин

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
-H "Content-Type: application/json" \
-d '{
  "email": "test@example.com",
  "password": "TestPassword123!"
}'
```

Сохраните access token из ответа для дальнейших запросов.

### Получение информации о текущем пользователе

```bash
curl -X GET http://localhost:8000/api/v1/users/me/ \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Обновление токена

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
-H "Content-Type: application/json" \
-d '{
  "refresh": "YOUR_REFRESH_TOKEN"
}'
```

### Смена пароля

```bash
curl -X POST http://localhost:8000/api/v1/users/change_password/ \
-H "Content-Type: application/json" \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-d '{
  "current_password": "TestPassword123!",
  "new_password": "NewPassword123!",
  "new_password_confirm": "NewPassword123!"
}'
```

## 4. Тестирование ошибок

### Неверный пароль

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
-H "Content-Type: application/json" \
-d '{
  "email": "test@example.com",
  "password": "wrong_password"
}'
```

### Слабый пароль при регистрации

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
-H "Content-Type: application/json" \
-d '{
  "email": "test2@example.com",
  "password": "weak",
  "password_confirm": "weak",
  "first_name": "Test",
  "last_name": "User"
}'
```

### Запрос без авторизации

```bash
curl -X GET http://localhost:8000/api/v1/users/me/
```

## 5. Примеры ответов

### Успешная регистрация

```json
{
  "success": true,
  "message": "User created successfully",
  "data": {
    "id": "uuid-here",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "full_name": "Test User",
    "is_active": true,
    "date_joined": "2024-01-01T00:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "error": null
}
```

### Ошибка валидации

```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "password": [
        "Password must be at least 8 characters long",
        "Password must contain at least one uppercase letter",
        "Password must contain at least one digit",
        "Password must contain at least one special character"
      ]
    }
  }
}
```

### Ошибка аутентификации

```json
{
  "success": false,
  "message": "Authentication failed",
  "data": null,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "details": {
      "non_field_errors": ["Invalid email or password"]
    }
  }
}
```

## 6. Полезные команды

### Создание суперпользователя

```bash
python manage.py createsuperuser
```

### Просмотр логов

```bash
tail -f logs/django.log
```

### Миграции

```bash
python manage.py makemigrations
python manage.py migrate
```

## 7. Использование Redis (опционально)

Если хотите использовать Redis для кеширования:

1. Установите и запустите Redis:
```bash
brew install redis
brew services start redis
```

2. Раскомментируйте Redis конфигурацию в `django_app/settings.py`:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "auth_app",
        "TIMEOUT": 300,
    }
}
```

3. Перезапустите сервер 