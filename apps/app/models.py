from django.db import models
from apps.service.models import UUIDModel
from apps.user.models import User
from django.utils.translation import gettext_lazy as _




class App(UUIDModel):
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=200)
    competitors = models.ManyToManyField('self', blank=True)

    def __str__(self):
        return self.name

    @property
    def primary_platform(self):
        """
        Returns AppPlatformData with is_primary=True (or None).
        """
        return self.platform_data.filter(is_primary=True).first()


class AppPlatformData(models.Model):
    """
    Platform-specific data for App
    """
    PLATFORM_CHOICES = [
        ('appstore', 'App Store'),
        ('play_market', 'Play Market'),
        ('product_hunt', 'Product Hunt'),
    ]

    app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        related_name='platform_data'
    )
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES
    )

    # unique identifiers on platform
    platform_app_id = models.CharField(max_length=50, blank=True, null=True)
    bundle_id = models.CharField(max_length=200, blank=True, null=True)
    developer_id = models.CharField(max_length=50, blank=True, null=True)

    # column fields for quick access
    name = models.CharField(max_length=200)
    current_version = models.CharField(max_length=50)
    current_version_release_date = models.DateTimeField()
    icon_url = models.URLField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2)
    rating_count = models.PositiveIntegerField()
    is_primary = models.BooleanField(default=False)

    # everything else — in JSON
    extra_metadata = models.JSONField(
        blank=True,
        null=True,
        help_text='Description, screenshots, genres, languages, devices, etc.'
    )

    class Meta:
        unique_together = [
            ('app', 'platform'),
            ('platform', 'platform_app_id'),
            ('platform', 'bundle_id'),
        ]
    
    def save(self, *args, **kwargs):
        # If marking this record as primary — reset flag for others
        if self.is_primary:
            self.__class__.objects.filter(
                app=self.app,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)

        # If this is the first record for this App and is_primary is not set, set True
        elif not self.app.platform_data.exclude(pk=self.pk).filter(is_primary=True).exists():
            self.is_primary = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.app.name} [{self.platform}]"
