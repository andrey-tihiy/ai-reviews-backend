"""
Шаг сохранения результатов анализа
"""
import logging
from typing import Dict, Any
from datetime import datetime

from apps.review.models import Review
from apps.review_analysis.models import AnalysisResult, ReviewTicket
from ..base import BaseAnalysisStep, StepRegistry


logger = logging.getLogger(__name__)


@StepRegistry.register('persistence')
class PersistenceStep(BaseAnalysisStep):
    """
    Сохранение результатов анализа в базу данных
    """
    
    def process(self, review: Review, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сохраняет результаты анализа и создает тикеты при необходимости
        """
        # Добавляем текущий шаг в список выполненных
        executed_steps = context.get('executed_steps', [])
        if 'persistence' not in executed_steps:
            executed_steps.append('persistence')
        context['executed_steps'] = executed_steps
        
        # Подготавливаем данные для сохранения
        analysis_data = {
            'tone': context.get('tone', 'neutral'),
            'raw_polarity': context.get('raw_polarity', 0.0),
            'raw_subjectivity': context.get('raw_subjectivity', 0.5),
            'issues': context.get('issues', []),
            'complex_review': context.get('complex_review'),
            'notes': context.get('notes'),
            'confidence': context.get('confidence', 1.0),
            'analysis_source': context.get('analysis_source', 'local'),
            'full_payload': {
                'vader_scores': context.get('vader_scores', {}),
                'gpt_cost': context.get('gpt_cost'),
                'gpt_error': context.get('gpt_error'),
                'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
                'executed_steps': context.get('executed_steps', []),
                'skip_gpt': context.get('skip_gpt'),
                'context_keys': list(context.keys()),  # Для отладки
            }
        }
        
        # Проверяем флаг поддержки для положительных отзывов с проблемами
        if (review.rating >= 4 and 
            analysis_data['issues'] != ["No specific issue or request detected"] and
            any("Problem:" in issue for issue in analysis_data['issues'])):
            analysis_data['flag_support'] = "Yes: Hidden issue in positive review"
        
        # Создаем или обновляем результат анализа
        analysis_result, created = AnalysisResult.objects.update_or_create(
            review=review,
            defaults=analysis_data
        )
        
        logger.info(f"{'Created' if created else 'Updated'} analysis result for review {review.id}")
        
        # Обновляем контекст
        context['analysis_result_id'] = str(analysis_result.id)
        context['analysis_created'] = created
        
        # Проверяем, нужно ли создать тикет
        if self._should_create_ticket(analysis_result):
            ticket = self._create_or_update_ticket(review, analysis_result)
            context['ticket_id'] = str(ticket.id) if ticket else None
        
        return context
    
    def _should_create_ticket(self, analysis_result: AnalysisResult) -> bool:
        """
        Определяет, нужно ли создать тикет для отзыва
        """
        # Создаем тикет если:
        # 1. Есть проблемы (Problem:)
        # 2. Отзыв помечен как сложный
        # 3. Есть флаг поддержки
        
        has_problems = any("Problem:" in issue for issue in analysis_result.issues)
        is_complex = bool(analysis_result.complex_review)
        has_support_flag = bool(analysis_result.flag_support)
        
        # Проверяем параметры из конфигурации
        auto_ticket_for_problems = self.get_param('auto_ticket_for_problems', True)
        auto_ticket_for_complex = self.get_param('auto_ticket_for_complex', True)
        ticket_only_for_negative = self.get_param('ticket_only_for_negative', False)
        
        # Создаем тикет для проблем
        if has_problems and auto_ticket_for_problems:
            # Если включен флаг ticket_only_for_negative, проверяем тональность
            if ticket_only_for_negative:
                # Создаем тикет только для негативных отзывов (рейтинг <= 3 или негативная тональность)
                if analysis_result.review.rating <= 3 or analysis_result.tone in ['Very Negative', 'Negative']:
                    return True
            else:
                # Создаем тикет для всех отзывов с проблемами
                return True
        
        # Создаем тикет для сложных отзывов
        if is_complex and auto_ticket_for_complex:
            return True
        
        # Всегда создаем тикет если есть флаг поддержки
        if has_support_flag:
            return True
        
        return False
    
    def _create_or_update_ticket(self, review: Review, 
                                 analysis_result: AnalysisResult) -> ReviewTicket:
        """
        Создает или обновляет тикет для отзыва
        """
        try:
            # Проверяем, есть ли уже открытый тикет
            existing_ticket = ReviewTicket.objects.filter(
                review=review,
                status__in=['open', 'in_progress']
            ).first()
            
            if existing_ticket:
                # Обновляем существующий тикет
                existing_ticket.analysis_result = analysis_result
                existing_ticket.save()
                logger.info(f"Updated existing ticket {existing_ticket.id} for review {review.id}")
                return existing_ticket
            
            # Создаем новый тикет
            priority = self._calculate_priority(analysis_result)
            
            ticket = ReviewTicket.objects.create(
                review=review,
                analysis_result=analysis_result,
                priority=priority,
                notes=self._generate_ticket_notes(analysis_result)
            )
            
            logger.info(f"Created new ticket {ticket.id} for review {review.id}")
            return ticket
            
        except Exception as e:
            logger.error(f"Error creating ticket for review {review.id}: {str(e)}")
            return None
    
    def _calculate_priority(self, analysis_result: AnalysisResult) -> int:
        """
        Рассчитывает приоритет тикета
        """
        priority = 0
        
        # Базовый приоритет по тональности
        tone_priorities = {
            'very_negative': 3,
            'negative': 2,
            'neutral': 1,
            'positive': 0,
            'very_positive': 0,
        }
        priority += tone_priorities.get(analysis_result.tone, 1)
        
        # Дополнительный приоритет за серьезность проблем
        for issue in analysis_result.issues:
            if "critical" in issue.lower():
                priority += 4
            elif "high" in issue.lower():
                priority += 3
            elif "medium" in issue.lower():
                priority += 2
            elif "low" in issue.lower():
                priority += 1
        
        # Дополнительный приоритет за флаг поддержки
        if analysis_result.flag_support:
            priority += 2
        
        # Дополнительный приоритет за сложность
        if analysis_result.complex_review:
            priority += 1
        
        return min(priority, 10)  # Максимальный приоритет 10
    
    def _generate_ticket_notes(self, analysis_result: AnalysisResult) -> str:
        """
        Генерирует примечания для тикета
        """
        notes = []
        
        if analysis_result.flag_support:
            notes.append(f"⚠️ {analysis_result.flag_support}")
        
        if analysis_result.complex_review:
            notes.append(f"🔍 {analysis_result.complex_review}")
        
        if analysis_result.issues:
            problems = [i for i in analysis_result.issues if "Problem:" in i]
            requests = [i for i in analysis_result.issues if "Request:" in i]
            
            if problems:
                notes.append(f"🐛 {', '.join(problems)}")
            if requests:
                notes.append(f"💡 {', '.join(requests)}")
        
        return "\n".join(notes)