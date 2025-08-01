"""
Шаг проверки сложности отзыва
"""
import logging
from typing import Dict, Any, Optional

from apps.review.models import Review
from ..base import BaseAnalysisStep, StepRegistry


logger = logging.getLogger(__name__)

# Опциональные зависимости
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    vader = None
    VADER_AVAILABLE = False
    logger.warning("vaderSentiment not available for complexity check")


@StepRegistry.register('complexity_check')
class ComplexityCheckStep(BaseAnalysisStep):
    """
    Определение сложных отзывов, требующих дополнительного анализа
    """
    
    def process(self, review: Review, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет, является ли отзыв сложным для анализа
        """
        content = review.content
        rating = review.rating
        polarity = context.get('raw_polarity', 0)
        subjectivity = context.get('raw_subjectivity', 0.5)
        doc = context.get('nlp_doc')
        
        # Проверяем сложность
        complex_reason = self._is_complex(doc, polarity, subjectivity, rating, content)
        
        # Также проверяем, стоит ли пропустить GPT анализ
        should_skip = self._should_skip_gpt(content, rating, polarity, doc)
        
        # Обновляем контекст
        context['complex_review'] = complex_reason
        context['skip_gpt'] = should_skip
        
        return context
    
    def _is_complex(self, doc, polarity: float, subjectivity: float, 
                    rating: int, content: str) -> Optional[str]:
        """
        Улучшенная функция определения сложности с более точными критериями
        """
        # Расширенный диапазон для нейтральной полярности
        if abs(polarity) < 0.3 and subjectivity > 0.4 and doc and len(list(doc.sents)) > 1:
            return "Need review: Mixed or ambiguous sentiment"
        
        # Проверка на сарказм или иронию
        if rating >= 4 and polarity < -0.3:
            return "Need review: High rating but negative sentiment - possible sarcasm"
        
        if rating <= 2 and polarity > 0.3:
            return "Need review: Low rating but positive sentiment"
        
        # Более мягкий порог для несоответствия рейтинга и полярности
        expected_polarity = (rating - 3) / 2  # Преобразуем рейтинг 1-5 в диапазон -1 to 1
        if abs(expected_polarity - polarity) > 0.7:  # Увеличен порог с 0.4
            return "Need review: Significant mismatch between rating and sentiment"
        
        # Проверка на смешанные эмоции
        if doc and vader:
            sentences_sentiments = []
            for sent in doc.sents:
                sent_polarity = vader.polarity_scores(sent.text)['compound']
                sentences_sentiments.append(sent_polarity)
            
            if len(sentences_sentiments) > 1:
                # Проверяем разброс sentiment по предложениям
                min_sent = min(sentences_sentiments)
                max_sent = max(sentences_sentiments)
                if max_sent - min_sent > 1.0:  # Большой разброс
                    return "Need review: Conflicting sentiments across sentences"
        
        # Проверка на короткие отзывы с экстремальными оценками
        word_count = len(content.split())
        if word_count < 5 and rating in [1, 5]:
            # Не отправляем простые положительные отзывы типа "Great game"
            if not (rating == 5 and polarity > 0.3):
                return "Need review: Very short review with extreme rating"
        
        return None
    
    def _should_skip_gpt(self, content: str, rating: int, 
                         polarity: float, doc) -> bool:
        """
        Интеллектуальное определение простых случаев без захардкоженных фраз
        """
        word_count = len(content.split())
        
        # Анализ лексического разнообразия
        if doc:
            unique_words = set([token.lemma_.lower() for token in doc if token.is_alpha and not token.is_stop])
            lexical_diversity = len(unique_words) / max(word_count, 1)
        else:
            lexical_diversity = 0.5  # Дефолтное значение
        
        # Очень короткие отзывы с соответствующей полярностью
        if word_count <= 3:
            # Положительные короткие отзывы
            if rating >= 4 and polarity > 0.3:
                return True
            # Негативные короткие отзывы
            if rating <= 2 and polarity < -0.3:
                return True
        
        # Простые отзывы (4-10 слов) с низким лексическим разнообразием
        if 4 <= word_count <= 10:
            # Проверяем наличие только простых частей речи
            if doc:
                pos_tags = [token.pos_ for token in doc]
                complex_pos = ['VERB', 'NOUN', 'ADJ', 'ADV']
                complex_count = sum(1 for pos in pos_tags if pos in complex_pos)
                
                # Если мало сложных частей речи и соответствие рейтинга/полярности
                if complex_count <= 3 and lexical_diversity < 0.7:
                    if (rating >= 4 and polarity > 0.2) or (rating <= 2 and polarity < -0.2):
                        return True
        
        # Проверка на простые эмоциональные высказывания
        # Используем синтаксический анализ вместо списка фраз
        if doc and len(list(doc.sents)) == 1:  # Одно предложение
            sent = list(doc.sents)[0]
            
            # Паттерн: [Субъект] + [простой глагол] + [объект]
            has_subject = any(token.dep_ in ["nsubj", "nsubjpass"] for token in sent)
            has_simple_verb = any(token.pos_ == "VERB" and token.lemma_ in ['be', 'love', 'hate', 'like', 'dislike'] for token in sent)
            
            if has_subject and has_simple_verb and word_count <= 6:
                # Проверяем соответствие полярности и рейтинга
                polarity_matches = (rating >= 4 and polarity > 0) or (rating <= 2 and polarity < 0)
                if polarity_matches:
                    return True
        
        # Проверка на повторяющиеся слова (как "Hand of the king" в примерах)
        words = content.lower().split()
        if len(words) > 10:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Если одно слово повторяется более 30% раз - это спам или простой отзыв
            max_freq = max(word_freq.values())
            if max_freq / len(words) > 0.3:
                return True
        
        # Проверка на отзывы, состоящие только из восклицаний или эмодзи
        non_alpha_ratio = sum(1 for char in content if not char.isalnum() and not char.isspace()) / max(len(content), 1)
        if non_alpha_ratio > 0.5:  # Более 50% не-буквенных символов
            return True
        
        return False