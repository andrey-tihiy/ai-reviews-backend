"""
Management command to initialize default prompt templates
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.review_analysis.models import PromptTemplate


class Command(BaseCommand):
    help = 'Initialize default prompt templates for GPT analysis'
    
    DEFAULT_PROMPTS = [
        {
            'prompt_id': 'default_review_analysis',
            'version': '1.0',
            'text': """You are a review analyzer for a mobile game app. Analyze user reviews for:
1. Tone: Strictly one of: "Very Negative" (estimated polarity < -0.5), "Negative" (-0.5 to -0.1), "Neutral" (-0.1 to 0.1), "Positive" (0.1 to 0.5), "Very Positive" (>0.5). Base on overall sentiment. When high rating (>=4) and minor/single issue, lean towards Neutral or Positive if overall not strongly negative.
2. Issues/Requests: Array of strings, each as "Problem: [short description]" or "Request: [short description]" (max 50 chars per desc). Detect even in high-rating reviews for support. Empty array if none.
3. Complex review: Null if clear; else string starting with "Need review: [reason]" (e.g., "Need review: Mixed sentiments").
4. Notes: Null or string for extra info not fitting other fields (e.g., "User compared to other games").
5. Confidence: 0-1 score of your certainty.
Output ONLY JSON with EXACTLY these key names in lowercase/snake_case (no variations like capitalization). No additional text, explanations, or formatting outside the JSON object: {"tone": str, "issues": [str], "complex_review": str|null, "raw_polarity": float, "notes": str|null, "confidence": float}""",
            'is_active': True
        }
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing prompt templates',
        )
    
    def handle(self, *args, **options):
        reset = options.get('reset', False)
        
        with transaction.atomic():
            if reset:
                self.stdout.write('Resetting existing prompt templates...')
                PromptTemplate.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('Existing prompts cleared.'))
            
            self.stdout.write('Creating prompt templates...')
            
            for prompt_data in self.DEFAULT_PROMPTS:
                prompt, created = PromptTemplate.objects.update_or_create(
                    prompt_id=prompt_data['prompt_id'],
                    version=prompt_data['version'],
                    defaults={
                        'text': prompt_data['text'],
                        'is_active': prompt_data['is_active']
                    }
                )
                
                if created:
                    self.stdout.write(f"  ✓ Created: {prompt_data['prompt_id']} v{prompt_data['version']}")
                else:
                    self.stdout.write(f"  ↻ Updated: {prompt_data['prompt_id']} v{prompt_data['version']}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully initialized {len(self.DEFAULT_PROMPTS)} prompt templates.'
                )
            )