# Celery Quick Start для Review Analysis

## Запуск Celery Worker

### 1. Основной способ (только очередь analysis):
```bash
cd /Users/tihiy/code/my/aireviews/django_app
source .venv/bin/activate
celery -A django_app worker -Q analysis -l info
```

### 2. Для всех очередей:
```bash
celery -A django_app worker -Q default,analysis -l info --autoreload
```

### 3. Для разработки с автоперезагрузкой:
```bash
celery -A django_app worker -Q analysis -l info --autoreload
```

## Проверка работы

1. В Django Admin выберите один или несколько отзывов
2. Выберите действие "Run analysis on selected reviews" 
3. Нажмите "Go"

В консоли Django вы увидите:
```
INFO Starting analysis for reviews: ['review-id-1', 'review-id-2']
INFO Task submitted with ID: task-id-here
```

В консоли Celery вы увидите:
```
[2024-XX-XX XX:XX:XX,XXX: INFO/MainProcess] Task apps.review_analysis.tasks.reanalyze_reviews[task-id] received
[2024-XX-XX XX:XX:XX,XXX: INFO/ForkPoolWorker-1] Starting reanalysis for 1 reviews: ['review-id']
[2024-XX-XX XX:XX:XX,XXX: INFO/ForkPoolWorker-1] Starting analysis pipeline for review review-id
...
```

## Отладка

### Если задачи не выполняются:

1. Проверьте, что Redis запущен:
```bash
redis-cli ping
# Должен вернуть: PONG
```

2. Проверьте логи Django:
```bash
tail -f logs/django.log
```

3. Запустите тестовую команду:
```bash
python manage.py test_celery
```

### Полезные команды Celery:

```bash
# Посмотреть активные задачи
celery -A django_app inspect active

# Посмотреть зарегистрированные задачи
celery -A django_app inspect registered

# Очистить очередь
celery -A django_app purge -Q analysis
```

## Конфигурация очередей

В проекте настроены две очереди:
- `default` - для общих задач (загрузка отзывов и т.д.)
- `analysis` - для задач анализа отзывов

Задачи автоматически направляются в нужные очереди согласно настройкам в `settings.py`.