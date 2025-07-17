from django.db import models
from apps.service.models import UUIDModel
from apps.app.models import AppPlatformData


class Review(UUIDModel):
    app_platform_data = models.ForeignKey(
        AppPlatformData,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    review_id = models.CharField(
        max_length=100,
        help_text='ID review on platform',
        db_index=True
    )
    author = models.CharField(max_length=255, blank=True)
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=500, blank=True)
    content = models.TextField()
    version = models.CharField(max_length=50, blank=True)
    platform_updated_at = models.DateTimeField(help_text='Date and time of the last update')

    metadata = models.JSONField(
        blank=True,
        default=dict,
        help_text='Metadata'
    )

    class Meta:
        unique_together = [('app_platform_data', 'review_id')]
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['app_platform_data', 'updated_at']),
            models.Index(fields=['review_id']),
        ]

    def __str__(self):
        return f"{self.app_platform_data.app.name} | {self.rating}★ | {self.author[:20]}"
