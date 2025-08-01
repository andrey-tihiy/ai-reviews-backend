"""
Test Celery configuration and task submission
"""
from django.core.management.base import BaseCommand
from apps.review_analysis.tasks import reanalyze_reviews, run_review_pipeline
from apps.review.models import Review


class Command(BaseCommand):
    help = 'Test Celery task submission'
    
    def handle(self, *args, **options):
        self.stdout.write("Testing Celery configuration...")
        
        # Проверяем наличие отзывов
        review = Review.objects.first()
        if not review:
            self.stdout.write(self.style.ERROR("No reviews found in database"))
            return
        
        self.stdout.write(f"Found review: {review.id}")
        
        # Тест 1: Прямой вызов задачи
        self.stdout.write("\nTest 1: Direct task call (synchronous)")
        try:
            result = run_review_pipeline(str(review.id))
            self.stdout.write(self.style.SUCCESS(f"Direct call successful: {result}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Direct call failed: {str(e)}"))
        
        # Тест 2: Асинхронный вызов через apply_async
        self.stdout.write("\nTest 2: Async task submission")
        try:
            task_result = run_review_pipeline.apply_async(
                args=[str(review.id)], 
                queue='analysis'
            )
            self.stdout.write(self.style.SUCCESS(f"Task submitted successfully. Task ID: {task_result.id}"))
            self.stdout.write(f"Queue: analysis")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Task submission failed: {str(e)}"))
        
        # Тест 3: Вызов reanalyze_reviews
        self.stdout.write("\nTest 3: Reanalyze reviews task")
        try:
            task_result = reanalyze_reviews.apply_async(
                args=[[str(review.id)]], 
                queue='analysis'
            )
            self.stdout.write(self.style.SUCCESS(f"Reanalyze task submitted. Task ID: {task_result.id}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Reanalyze task failed: {str(e)}"))
        
        # Проверка конфигурации Celery
        self.stdout.write("\nCelery configuration:")
        from django.conf import settings
        self.stdout.write(f"CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
        
        if hasattr(settings, 'CELERY_TASK_ROUTES'):
            self.stdout.write(f"CELERY_TASK_ROUTES: {settings.CELERY_TASK_ROUTES}")
        
        if hasattr(settings, 'CELERY_QUEUES'):
            self.stdout.write(f"CELERY_QUEUES: {settings.CELERY_QUEUES}")