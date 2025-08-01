"""
Шаг анализа с использованием GPT
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime
from openai import OpenAI
from django.conf import settings

from apps.review.models import Review
from ..base import BaseAnalysisStep, StepRegistry


logger = logging.getLogger(__name__)


@StepRegistry.register('gpt_analysis')
class GPTAnalysisStep(BaseAnalysisStep):
    """
    Анализ отзывов с использованием GPT для сложных случаев
    """
    
    # Средние значения для подсчета стоимости
    AVG_INPUT_TOKENS = 200
    AVG_OUTPUT_TOKENS = 100
    INPUT_PRICE_PER_TOKEN = 0.0000001
    OUTPUT_PRICE_PER_TOKEN = 0.0000004
    
    def __init__(self, **params):
        super().__init__(**params)
        
        # Получаем API ключ из настроек или параметров
        api_key = settings.OPENAI_API_KEY
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            logger.warning("OpenAI API key not configured")
        
        # Получаем модель из параметров
        self.model = self.get_param('model', 'gpt-4o-mini')
        
        # Получаем prompt_id из параметров
        self.prompt_id = self.get_param('prompt_id')
    
    def process(self, review: Review, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует отзыв с помощью GPT
        """
        # Проверяем доступность клиента
        if not self.client:
            logger.warning("GPT analysis skipped - OpenAI client not configured")
            return context
        
        # Проверяем параметр skip_if_simple
        skip_if_simple = self.get_param('skip_if_simple', True)
        
        # Если включен параметр skip_if_simple, проверяем условия пропуска
        if skip_if_simple:
            # Проверяем флаг skip_gpt от ComplexityCheck
            if context.get('skip_gpt', False):
                logger.info(f"Skipping GPT analysis for review {review.id} - marked as simple")
                return context
            
            # Проверяем наличие complex_review
            if 'complex_review' in context and not context.get('complex_review'):
                logger.info(f"Skipping GPT analysis for review {review.id} - not complex")
                return context
        
        # Если ComplexityCheck не запущен или skip_if_simple=False, анализируем всегда
        logger.info(f"Running GPT analysis for review {review.id}")
        
        try:
            # Получаем системный промпт
            system_prompt = self._get_system_prompt()
            
            # Формируем пользовательский ввод
            user_input = f"Review rating: {review.rating}\nTitle: {review.title}\nContent: {review.content}"
            
            # Вызываем GPT
            response = self._call_gpt(system_prompt, user_input)
            
            # Парсим результат
            gpt_result = json.loads(response)
            
            # Обновляем контекст с результатами GPT
            context.update({
                'tone': self._map_tone(gpt_result.get('tone', context.get('tone', 'neutral'))),
                'issues': gpt_result.get('issues', context.get('issues', [])),
                'complex_review': gpt_result.get('complex_review'),
                'raw_polarity': gpt_result.get('raw_polarity', context.get('raw_polarity', 0)),
                'notes': gpt_result.get('notes'),
                'confidence': gpt_result.get('confidence', 0.8),
                'analysis_source': 'gpt',
            })
            
            # Подсчитываем примерную стоимость
            cost = (self.AVG_INPUT_TOKENS * self.INPUT_PRICE_PER_TOKEN) + \
                   (self.AVG_OUTPUT_TOKENS * self.OUTPUT_PRICE_PER_TOKEN)
            context['gpt_cost'] = cost
            
        except Exception as e:
            logger.error(f"GPT analysis error for review {review.id}: {str(e)}")
            context['gpt_error'] = str(e)
            # При ошибке оставляем локальный анализ
            context['analysis_source'] = 'local'
        
        return context
    
    def _get_system_prompt(self) -> str:
        """
        Получает системный промпт из базы данных или использует дефолтный
        """
        if self.prompt_id:
            # Попытка получить промпт из базы
            from apps.review_analysis.models import PromptTemplate
            try:
                prompt = PromptTemplate.objects.get(
                    prompt_id=self.prompt_id,
                    is_active=True
                )
                return prompt.text
            except PromptTemplate.DoesNotExist:
                logger.warning(f"Prompt template {self.prompt_id} not found, using default")
        
        # Дефолтный промпт
        return """You are a review analyzer for a mobile game app. Analyze user reviews for:
1. Tone: Strictly one of: "Very Negative" (estimated polarity < -0.5), "Negative" (-0.5 to -0.1), "Neutral" (-0.1 to 0.1), "Positive" (0.1 to 0.5), "Very Positive" (>0.5). Base on overall sentiment. When high rating (>=4) and minor/single issue, lean towards Neutral or Positive if overall not strongly negative.
2. Issues/Requests: Array of strings, each as "Problem: [short description]" or "Request: [short description]" (max 50 chars per desc). Detect even in high-rating reviews for support. Empty array if none.
3. Complex review: Null if clear; else string starting with "Need review: [reason]" (e.g., "Need review: Mixed sentiments").
4. Notes: Null or string for extra info not fitting other fields (e.g., "User compared to other games").
5. Confidence: 0-1 score of your certainty.
Output ONLY JSON with EXACTLY these key names in lowercase/snake_case (no variations like capitalization). No additional text, explanations, or formatting outside the JSON object: {"tone": str, "issues": [str], "complex_review": str|null, "raw_polarity": float, "notes": str|null, "confidence": float}"""
    
    def _call_gpt(self, system_prompt: str, user_input: str) -> str:
        """
        Вызывает GPT API
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content
    
    def _map_tone(self, gpt_tone: str) -> str:
        """
        Мапит тональность из GPT в наш формат
        """
        tone_mapping = {
            'Very Negative': 'very_negative',
            'Negative': 'negative',
            'Neutral': 'neutral',
            'Positive': 'positive',
            'Very Positive': 'very_positive',
            # На случай если GPT вернет в другом формате
            'very negative': 'very_negative',
            'very positive': 'very_positive',
        }
        return tone_mapping.get(gpt_tone, 'neutral')