# Логика создания тикетов и флагов

## Когда создаются тикеты

Тикеты создаются автоматически в следующих случаях:

### 1. При обнаружении проблем (auto_ticket_for_problems = true)
- Если в `issues` есть строки с "Problem:"
- Если `ticket_only_for_negative = true`, тикет создается только для негативных отзывов (рейтинг <= 3 или негативная тональность)
- Если `ticket_only_for_negative = false`, тикет создается для всех отзывов с проблемами

### 2. Для сложных отзывов (auto_ticket_for_complex = true)
- Если `complex_review` не пустой
- Например: "Need review: Mixed sentiments"

### 3. При наличии флага поддержки
- Всегда создается тикет если есть `flag_support`

## Фильтрация тикетов

GPT возвращает все проблемы в формате:
- `"Problem: Game resets after each death"`
- `"Problem: Controls not working"`

Настройка `ticket_only_for_negative` контролирует создание тикетов:
- `false` (по умолчанию) - создавать тикеты для **всех** отзывов с проблемами
- `true` - создавать тикеты **только** для негативных отзывов:
  - Рейтинг <= 3 звезд
  - ИЛИ тональность "Negative" / "Very Negative"

## Флаг поддержки (flag_support)

Устанавливается **только** для положительных отзывов (rating >= 4) с проблемами:
- Пример: 5★ отзыв с текстом "Great game but crashes constantly"
- Флаг: "Yes: Hidden issue in positive review"

Для негативных отзывов (rating < 4) флаг НЕ устанавливается.

## Приоритет тикетов

Рассчитывается автоматически на основе:
1. Тональности отзыва (very_negative = +3, negative = +2, и т.д.)
2. Серьезности проблем (critical = +4, high = +3, и т.д.)
3. Наличия флага поддержки (+2)
4. Сложности отзыва (+1)

Максимальный приоритет: 10

## Настройка в Django Admin

В **Pipeline Step Configurations** → **Persistence** → **Parameters**:
```json
{
  "auto_ticket_for_problems": true,
  "auto_ticket_for_complex": true,
  "ticket_only_for_negative": false
}
```

## Проверка работы

1. В **Analysis Results** смотрите колонку "Issues"
2. В **Review Tickets** видны все созданные тикеты
3. В **Debug Information** → **Full payload** можно увидеть все детали анализа