"""
Шаг определения тональности отзыва
"""
from typing import Dict, Any
import logging

from apps.review.models import Review
from ..base import BaseAnalysisStep, StepRegistry


logger = logging.getLogger(__name__)

# Опциональные зависимости
try:
    import spacy
    from spacytextblob.spacytextblob import SpacyTextBlob
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy or spacytextblob not installed. Install with: pip install spacy spacytextblob")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logger.warning("vaderSentiment not installed. Install with: pip install vaderSentiment")

# Инициализация моделей NLP
nlp = None
if SPACY_AVAILABLE:
    try:
        nlp = spacy.load('en_core_web_sm')
        nlp.add_pipe('spacytextblob')
    except OSError:
        logger.warning("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")

vader = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None


@StepRegistry.register('tone_detection')
class ToneDetectionStep(BaseAnalysisStep):
    """
    Определение тональности отзыва с использованием VADER и TextBlob
    """
    
    def process(self, review: Review, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует тональность отзыва
        """
        content = review.content
        
        # Используем VADER для более точной полярности
        if vader:
            vader_scores = vader.polarity_scores(content)
            polarity = vader_scores['compound']
        else:
            # Простая эвристика если VADER недоступен
            polarity = self._simple_polarity_analysis(content, review.rating)
            vader_scores = {'compound': polarity, 'pos': 0, 'neu': 0, 'neg': 0}
        
        # TextBlob для субъективности
        subjectivity = 0.5  # Дефолтное значение
        if nlp:
            doc = nlp(content)
            subjectivity = doc._.blob.subjectivity
            # Сохраняем doc для использования в других шагах
            context['nlp_doc'] = doc
        
        # Определяем тональность
        tone = self._get_tone(polarity)
        
        # Обновляем контекст
        context.update({
            'tone': tone,
            'raw_polarity': polarity,
            'raw_subjectivity': subjectivity,
            'vader_scores': vader_scores,
        })
        
        return context
    
    def _get_tone(self, polarity: float) -> str:
        """
        Определяет тональность по полярности
        """
        if polarity < -0.5:
            return "very_negative"
        elif -0.5 <= polarity < -0.1:
            return "negative"
        elif -0.1 <= polarity <= 0.1:
            return "neutral"
        elif 0.1 < polarity <= 0.5:
            return "positive"
        else:
            return "very_positive"
    
    def _simple_polarity_analysis(self, content: str, rating: int) -> float:
        """
        Простой анализ полярности на основе рейтинга и ключевых слов
        """
        # Базовая полярность на основе рейтинга
        base_polarity = (rating - 3) / 2  # Преобразуем 1-5 в -1 to 1
        
        # Простой анализ ключевых слов
        content_lower = content.lower()
        
        positive_words = ['good', 'great', 'excellent', 'love', 'awesome', 'amazing', 'best', 'perfect']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'poor', 'sucks']
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        # Корректируем полярность на основе ключевых слов
        word_polarity = (positive_count - negative_count) * 0.1
        
        # Комбинируем с базовой полярностью
        final_polarity = base_polarity * 0.7 + word_polarity * 0.3
        
        # Ограничиваем диапазон от -1 до 1
        return max(-1.0, min(1.0, final_polarity))