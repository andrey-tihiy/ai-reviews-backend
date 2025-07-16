# Django Auth API Documentation

## Обзор

Этот API предоставляет полнофункциональную систему аутентификации и управления пользователями с JWT токенами. Все ответы API имеют унифицированный формат с правильной обработкой ошибок.

## Унифицированный формат ответов

### Успешный ответ
```json
{
  "success": true,
  "message": "Success message",
  "data": { ... },
  "error": null,
  "pagination": {  // Только для списков
    "count": 100,
    "next": "http://...",
    "previous": null,
    "total_pages": 10
  }
}
```

### Ответ с ошибкой
```json
{
  "success": false,
  "message": "Error message",
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "details": { ... }
  }
}
```

## Аутентификация

### Регистрация пользователя

**POST** `/api/v1/users/register/`

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Ответ (201):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "is_active": true,
    "date_joined": "2023-01-01T00:00:00Z",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  },
  "error": null
}
```

### Вход в систему

**POST** `/api/v1/auth/login/`

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "uuid-string",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "is_active": true,
      "date_joined": "2023-01-01T00:00:00Z",
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
  },
  "error": null
}
```

### Обновление токена

**POST** `/api/v1/auth/refresh/`

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
      "id": "uuid-string",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "is_active": true,
      "date_joined": "2023-01-01T00:00:00Z",
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  },
  "error": null
}
```

## Управление пользователями

### Получение текущего пользователя

**GET** `/api/v1/users/me/`

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Current user information retrieved successfully",
  "data": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "is_active": true,
    "date_joined": "2023-01-01T00:00:00Z",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  },
  "error": null
}
```

### Изменение пароля

**POST** `/api/v1/users/change_password/`

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

```json
{
  "current_password": "CurrentPassword123!",
  "new_password": "NewPassword123!",
  "new_password_confirm": "NewPassword123!"
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Password changed successfully",
  "data": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "is_active": true,
    "date_joined": "2023-01-01T00:00:00Z",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  },
  "error": null
}
```

### Обновление профиля

**PATCH** `/api/v1/users/{user_id}/`

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

```json
{
  "first_name": "Jane",
  "last_name": "Smith"
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "User updated successfully",
  "data": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "full_name": "Jane Smith",
    "is_active": true,
    "date_joined": "2023-01-01T00:00:00Z",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  },
  "error": null
}
```

### Получение списка пользователей

**GET** `/api/v1/users/`

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Query Parameters:**
- `page`: Номер страницы (по умолчанию 1)
- `page_size`: Количество элементов на странице (по умолчанию 20, максимум 100)
- `search`: Поиск по email, имени или фамилии
- `ordering`: Сортировка (например, `created_at`, `-created_at`)

**Ответ (200):**
```json
{
  "success": true,
  "message": "Users retrieved successfully",
  "data": [
    {
      "id": "uuid-string",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "is_active": true,
      "date_joined": "2023-01-01T00:00:00Z",
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ],
  "error": null,
  "pagination": {
    "count": 100,
    "next": "http://localhost:8000/api/v1/users/?page=2",
    "previous": null,
    "total_pages": 5
  }
}
```

## Коды ошибок

### Аутентификация
- `AUTHENTICATION_ERROR`: Неверные учетные данные или отсутствие токена
- `PERMISSION_ERROR`: Недостаточно прав доступа

### Валидация
- `VALIDATION_ERROR`: Ошибки валидации данных
- `PARSE_ERROR`: Неправильный формат данных

### Общие ошибки
- `NOT_FOUND_ERROR`: Ресурс не найден
- `METHOD_NOT_ALLOWED`: Метод не разрешен
- `RATE_LIMIT_ERROR`: Превышен лимит запросов
- `SERVER_ERROR`: Внутренняя ошибка сервера

## Примеры ошибок

### Ошибка валидации

```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "email": ["Enter a valid email address"],
      "password": ["Password must be at least 8 characters long"]
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

### Ошибка не найден

```json
{
  "success": false,
  "message": "Resource not found",
  "data": null,
  "error": {
    "code": "NOT_FOUND_ERROR",
    "details": null
  }
}
```

## Требования к паролю

- Минимум 8 символов
- Должен содержать хотя бы одну заглавную букву
- Должен содержать хотя бы одну строчную букву
- Должен содержать хотя бы одну цифру
- Должен содержать хотя бы один специальный символ (!@#$%^&*(),.?":{}|<>)

## Настройки JWT

- **Access Token**: Действителен 60 минут
- **Refresh Token**: Действителен 7 дней
- **Автоматическое обновление**: Refresh токены обновляются при каждом использовании
- **Blacklist**: Старые токены добавляются в черный список

## Дополнительные возможности

### Swagger UI
Доступен по адресу: `http://localhost:8000/api/docs/`

### Redoc
Доступен по адресу: `http://localhost:8000/api/redoc/`

### Схема OpenAPI
Доступна по адресу: `http://localhost:8000/api/schema/`

## Безопасность

- Все пароли хешируются с использованием Django's PBKDF2
- JWT токены подписываются с помощью HS256
- Включены защиты от XSS, CSRF и других атак
- Настроены ограничения по количеству запросов (throttling)
- Логирование всех ошибок и действий пользователей

## Кеширование

- Используется Redis для кеширования сессий
- Настроено кеширование для улучшения производительности
- Время жизни кеша по умолчанию: 5 минут

## Логирование

- Все запросы и ошибки логируются
- Логи сохраняются в файл `logs/django.log`
- Настроены разные уровни логирования для разных компонентов 