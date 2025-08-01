"""
Celery задачи для анализа отзывов
"""
import logging
from typing import Dict, Any
from datetime import datetime
from celery import shared_task
from django.db import transaction

from apps.review.models import Review
from apps.review_analysis.models import PipelineStepConfig, PipelineStepType
from apps.review_analysis.services.base import StepRegistry


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_review_pipeline(self, review_id: str) -> Dict[str, Any]:
    """
    Запускает пайплайн анализа для отзыва
    
    Args:
        review_id: UUID отзыва для анализа
        
    Returns:
        Результат выполнения пайплайна
    """
    try:
        # Получаем отзыв
        review = Review.objects.select_related(
            'app_platform_data__app'
        ).get(id=review_id)
        
        logger.info(f"Starting analysis pipeline for review {review_id}")
        
        # Инициализируем контекст
        context = {
            'review_id': str(review_id),
            'app_name': review.app_platform_data.app.name,
            'platform': review.app_platform_data.platform,
            'rating': review.rating,
        }
        
        # Получаем активные шаги пайплайна
        pipeline_steps = PipelineStepConfig.objects.filter(
            enabled=True
        ).select_related('step_type').order_by('order')
        
        if not pipeline_steps:
            logger.warning(f"No enabled pipeline steps configured for review {review_id}")
            # Даже если нет шагов, создаем минимальный результат
            from apps.review_analysis.models import AnalysisResult
            analysis_result, created = AnalysisResult.objects.update_or_create(
                review=review,
                defaults={
                    'tone': 'neutral',
                    'raw_polarity': 0.0,
                    'raw_subjectivity': 0.5,
                    'issues': ["No analysis performed - all steps disabled"],
                    'analysis_source': 'none',
                    'confidence': 0.0,
                    'full_payload': {
                        'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
                        'executed_steps': [],
                        'warning': 'No pipeline steps were enabled'
                    }
                }
            )
            return {
                'success': True,
                'review_id': str(review_id),
                'analysis_result_id': str(analysis_result.id),
                'warning': 'No enabled pipeline steps configured',
                'analysis_source': 'none'
            }
        
        # Отслеживаем выполненные шаги
        executed_steps = []
        
        # Выполняем каждый шаг
        for step_config in pipeline_steps:
            try:
                step_key = step_config.step_type.key
                logger.info(f"Executing step: {step_key}")
                
                # Получаем класс шага из реестра
                step_class = StepRegistry.get_step_class(step_key)
                if not step_class:
                    logger.error(f"Step class not found for key: {step_key}")
                    continue
                
                # Создаем экземпляр шага с параметрами
                step_instance = step_class(**step_config.params)
                
                # Выполняем шаг
                context = step_instance.process(review, context)
                
                logger.info(f"Step {step_key} completed successfully")
                executed_steps.append(step_key)
                
            except Exception as e:
                logger.error(f"Error in step {step_key}: {str(e)}", exc_info=True)
                # Продолжаем выполнение остальных шагов
                context[f'{step_key}_error'] = str(e)
                executed_steps.append(f"{step_key} (error)")
        
        # Сохраняем информацию о выполненных шагах
        context['executed_steps'] = executed_steps
        
        # Если включен только один шаг и это не persistence, нужно все равно сохранить результаты
        if executed_steps and 'persistence' not in executed_steps:
            persistence_config = PipelineStepConfig.objects.filter(
                step_type__key='persistence', 
                enabled=True
            ).first()
            
            if not persistence_config:
                logger.warning("Persistence step not configured or disabled - results won't be saved!")
        
        # Результат выполнения
        result = {
            'success': True,
            'review_id': str(review_id),
            'analysis_result_id': context.get('analysis_result_id'),
            'ticket_id': context.get('ticket_id'),
            'analysis_source': context.get('analysis_source', 'local'),
            'tone': context.get('tone'),
            'issues_count': len(context.get('issues', [])),
            'gpt_cost': context.get('gpt_cost'),
        }
        
        logger.info(f"Analysis pipeline completed for review {review_id}")
        return result
        
    except Review.DoesNotExist:
        logger.error(f"Review {review_id} not found")
        return {
            'success': False,
            'error': f'Review {review_id} not found'
        }
    except Exception as e:
        logger.error(f"Pipeline error for review {review_id}: {str(e)}", exc_info=True)
        
        # Повторяем задачу при ошибке
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def reanalyze_reviews(review_ids: list) -> Dict[str, Any]:
    """
    Переанализирует список отзывов
    
    Args:
        review_ids: Список UUID отзывов для переанализа
        
    Returns:
        Статистика выполнения
    """
    logger.info(f"Starting reanalysis for {len(review_ids)} reviews: {review_ids}")
    
    results = {
        'total': len(review_ids),
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for review_id in review_ids:
        try:
            task = run_review_pipeline.apply_async(
                args=[review_id],
                queue='analysis'
            )
            logger.info(f"Submitted analysis task for review {review_id}, task ID: {task.id}")
            results['successful'] += 1
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'review_id': review_id,
                'error': str(e)
            })
    
    return results


@shared_task
def analyze_app_reviews(app_id: str, limit: int = None) -> Dict[str, Any]:
    """
    Анализирует все отзывы приложения
    
    Args:
        app_id: UUID приложения
        limit: Ограничение количества отзывов для анализа
        
    Returns:
        Статистика выполнения
    """
    from apps.app.models import App
    
    try:
        app = App.objects.get(id=app_id)
        
        # Получаем отзывы без результатов анализа
        reviews = Review.objects.filter(
            app_platform_data__app=app
        ).exclude(
            analysis_result__isnull=False
        )
        
        if limit:
            reviews = reviews[:limit]
        
        review_ids = list(reviews.values_list('id', flat=True))
        
        logger.info(f"Starting analysis for {len(review_ids)} reviews of app {app.name}")
        
        return reanalyze_reviews(review_ids)
        
    except App.DoesNotExist:
        return {
            'success': False,
            'error': f'App {app_id} not found'
        }


@shared_task
def cleanup_old_tickets(days: int = 30) -> Dict[str, Any]:
    """
    Очистка старых закрытых тикетов
    
    Args:
        days: Количество дней для хранения закрытых тикетов
        
    Returns:
        Количество удаленных тикетов
    """
    from datetime import datetime, timedelta
    from apps.review_analysis.models import ReviewTicket
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    old_tickets = ReviewTicket.objects.filter(
        status='closed',
        updated_at__lt=cutoff_date
    )
    
    count = old_tickets.count()
    old_tickets.delete()
    
    logger.info(f"Deleted {count} old closed tickets")
    
    return {
        'deleted': count,
        'cutoff_date': cutoff_date.isoformat()
    }