# Модульный пайплайн анализа отзывов

## Как это работает

Каждый шаг пайплайна теперь полностью независим. Вы можете включать/выключать любые шаги, и анализ будет выполнен только с включенными шагами.

## Конфигурация в Django Admin

### Для анализа только с GPT:

1. Зайдите в **Pipeline Step Configurations**
2. Отключите все шаги кроме:
   - ✅ **GPT Analysis** 
   - ✅ **Persistence** (обязательно для сохранения!)

3. В параметрах GPT Analysis установите:
```json
{
  "model": "gpt-4o-mini",
  "prompt_id": "default_review_analysis",
  "skip_if_simple": false
}
```

### Для полного анализа:

Включите все шаги в порядке:
1. ✅ **Tone Detection** (order: 10)
2. ✅ **Issue Detection** (order: 20)
3. ✅ **Complexity Check** (order: 30)
4. ✅ **GPT Analysis** (order: 40) с `"skip_if_simple": true`
5. ✅ **Persistence** (order: 50)

### Для локального анализа без GPT:

1. ✅ **Tone Detection** (order: 10)
2. ✅ **Issue Detection** (order: 20)
3. ✅ **Complexity Check** (order: 30)
4. ❌ **GPT Analysis** (выключен)
5. ✅ **Persistence** (order: 50)

## Важные моменты

1. **Persistence всегда должен быть включен** - иначе результаты не сохранятся
2. **Persistence должен быть последним** (самый большой order)
3. Параметр `skip_if_simple` в GPT Analysis:
   - `true` - пропускать простые отзывы (если ComplexityCheck пометил их)
   - `false` - анализировать все отзывы через GPT

## Что сохраняется

В `full_payload` каждого анализа сохраняется:
- `executed_steps` - список выполненных шагов
- `processing_timestamp` - время анализа
- `context_keys` - все ключи контекста (для отладки)
- Любые ошибки и предупреждения

## Проверка работы

1. Выберите отзывы в Django Admin
2. Действие "Run analysis on selected reviews"
3. Проверьте результаты в Analysis Results

В колонке "Executed Steps" вы увидите, какие шаги были применены к каждому отзыву.

## Отладка

Если анализ не работает:
1. Проверьте, что Celery worker запущен с очередью 'analysis'
2. Проверьте, что хотя бы один шаг включен
3. Проверьте, что Persistence включен и последний по порядку
4. Смотрите логи Celery для деталей