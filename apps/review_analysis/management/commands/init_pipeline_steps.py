"""
Management command to initialize pipeline step types
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.review_analysis.models import PipelineStepType, PipelineStepConfig


class Command(BaseCommand):
    help = 'Initialize pipeline step types and default configuration'
    
    # Определение предустановленных типов шагов
    PIPELINE_STEP_TYPES = [
        {
            'key': 'tone_detection',
            'label': 'Tone Detection',
            'description': 'Detects the emotional tone of the review using NLP analysis (VADER, TextBlob)'
        },
        {
            'key': 'issue_detection',
            'label': 'Issue Detection',
            'description': 'Identifies problems and feature requests mentioned in the review'
        },
        {
            'key': 'complexity_check',
            'label': 'Complexity Check',
            'description': 'Determines if the review is complex and requires additional analysis'
        },
        {
            'key': 'gpt_analysis',
            'label': 'GPT Analysis',
            'description': 'Advanced analysis using GPT for complex reviews'
        },
        {
            'key': 'persistence',
            'label': 'Persistence',
            'description': 'Saves analysis results and creates tickets if needed'
        },
    ]
    
    # Дефолтная конфигурация пайплайна
    DEFAULT_PIPELINE_CONFIG = [
        {
            'step_key': 'tone_detection',
            'enabled': True,
            'order': 10,
            'params': {}
        },
        {
            'step_key': 'issue_detection',
            'enabled': True,
            'order': 20,
            'params': {}
        },
        {
            'step_key': 'complexity_check',
            'enabled': True,
            'order': 30,
            'params': {}
        },
        {
            'step_key': 'gpt_analysis',
            'enabled': True,
            'order': 40,
            'params': {
                'model': 'gpt-4o-mini',
                'prompt_id': 'default_review_analysis',
                'skip_if_simple': True  # Пропускать простые отзывы если ComplexityCheck включен
            }
        },
        {
            'step_key': 'persistence',
            'enabled': True,
            'order': 50,
            'params': {
                'auto_ticket_for_problems': True,
                'auto_ticket_for_complex': True,
                'ticket_only_for_negative': False  # False = создавать тикеты для всех проблем, True = только для негативных
            }
        },
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--with-config',
            action='store_true',
            help='Also create default pipeline configuration',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing step types and configurations',
        )
    
    def handle(self, *args, **options):
        with_config = options.get('with_config', False)
        reset = options.get('reset', False)
        
        with transaction.atomic():
            # Сброс существующих данных если указан флаг
            if reset:
                self.stdout.write('Resetting existing pipeline steps...')
                PipelineStepConfig.objects.all().delete()
                PipelineStepType.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
            
            # Создание типов шагов
            self.stdout.write('Creating pipeline step types...')
            step_types = {}
            
            for step_data in self.PIPELINE_STEP_TYPES:
                step_type, created = PipelineStepType.objects.update_or_create(
                    key=step_data['key'],
                    defaults={
                        'label': step_data['label'],
                        'description': step_data['description']
                    }
                )
                step_types[step_data['key']] = step_type
                
                if created:
                    self.stdout.write(f"  ✓ Created: {step_data['label']}")
                else:
                    self.stdout.write(f"  ↻ Updated: {step_data['label']}")
            
            # Создание конфигурации если указан флаг
            if with_config:
                self.stdout.write('\nCreating default pipeline configuration...')
                
                for config_data in self.DEFAULT_PIPELINE_CONFIG:
                    step_type = step_types.get(config_data['step_key'])
                    if not step_type:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠ Step type '{config_data['step_key']}' not found, skipping..."
                            )
                        )
                        continue
                    
                    config, created = PipelineStepConfig.objects.update_or_create(
                        step_type=step_type,
                        defaults={
                            'enabled': config_data['enabled'],
                            'order': config_data['order'],
                            'params': config_data['params']
                        }
                    )
                    
                    if created:
                        self.stdout.write(f"  ✓ Created config for: {step_type.label}")
                    else:
                        self.stdout.write(f"  ↻ Updated config for: {step_type.label}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully initialized {len(step_types)} pipeline step types.'
                )
            )
            
            if with_config:
                active_steps = PipelineStepConfig.objects.filter(enabled=True).count()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Pipeline configured with {active_steps} active steps.'
                    )
                )