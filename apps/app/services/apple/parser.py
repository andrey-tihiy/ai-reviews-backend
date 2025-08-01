import logging
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from apps.review.models import Review
from apps.app.services.base import BasePlatformService
from apps.app.models import App, AppPlatformData
from apps.app.services.apple.client import AppleAppStoreClient
from apps.app.services.apple.exceptions import AppleAppStoreError
from django.db import transaction


logger = logging.getLogger('apps.app.services.apple.parser')


class AppleAppStoreService(BasePlatformService):
    """
    Service for processing Apple App Store data
    """
    
    def __init__(self):
        self.client = AppleAppStoreClient()
    
    def get_platform_name(self) -> str:
        """Return platform name."""
        return 'appstore'
    
    def extract_app_id_from_url(self, url: str) -> Optional[str]:
        """Extract app ID from App Store URL."""
        return self.client.extract_app_id_from_url(url)
    
    def fetch_app_info(self, app_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetch app metadata from iTunes API."""
        country = kwargs.get('country', 'us')
        return self.client.fetch_app_info(app_id, country)
    
    def process_app_data(self, app_instance: App, url: str, **kwargs) -> Dict[str, Any]:
        """
        Process app URL and create/update AppPlatformData.
        
        Args:
            app_instance: App model instance
            url: App Store URL
            **kwargs: Additional parameters (country, max_reviews_pages)
        
        Returns:
            Dictionary with processing results
        """
        country = kwargs.get('country', 'us')
        max_reviews_pages = kwargs.get('max_reviews_pages', 5)
        
        try:
            logger.info(f"Processing Apple App Store data for app {app_instance.name} (ID: {app_instance.id})")
            
            # Extract app ID from URL
            app_id = self.extract_app_id_from_url(url)
            if not app_id:
                logger.error(f"Could not extract app ID from URL: {url}")
                raise AppleAppStoreError(f"Could not extract app ID from URL: {url}")
            
            logger.info(f"Extracted app ID {app_id} from URL")
            
            # Fetch app info
            app_info = self.fetch_app_info(app_id, country=country)
            if not app_info:
                logger.error(f"Could not fetch app info for ID: {app_id}")
                raise AppleAppStoreError(f"Could not fetch app info for ID: {app_id}")
            
            # Fetch reviews
            logger.info(f"Fetching reviews for app ID {app_id} (max {max_reviews_pages} pages)")
            reviews = self.client.fetch_reviews(app_id, country, max_reviews_pages)
            
            # Create or update AppPlatformData
            logger.info(f"Creating/updating AppPlatformData for app {app_instance.name}")
            platform_data, created = AppPlatformData.objects.update_or_create(
                app=app_instance,
                platform=self.get_platform_name(),
                defaults=self._map_app_info_to_platform_data(app_info, reviews)
            )

            self.process_app_reviews(platform_data, reviews)
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} AppPlatformData (ID: {platform_data.id}) for app {app_instance.name}")
            
            result = {
                'success': True,
                'platform_data_id': str(platform_data.id),
                'created': created,
                'app_info': app_info,
                'reviews_count': len(reviews),
                'processing_date': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully processed Apple App Store data for app {app_instance.name}")
            return result
            
        except Exception as e:
            logger.exception(f"Error processing Apple App Store data for app {app_instance.name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_date': datetime.now().isoformat()
            }


    def process_app_reviews(
            self,
            app_platform_data: AppPlatformData,
            reviews: list
    ) -> None:
        """ Process and save reviews for the app."""
        objs = []
        for rev in reviews:
            updated_at = rev.get('updated_at', datetime.now().isoformat())
            objs.append(Review(
                app_platform_data=app_platform_data,
                review_id=rev.get('id', ''),
                author=rev.get('author', {}),
                rating=rev.get('rating', 0),
                title=rev.get('title', ''),
                content=rev.get('content', ''),
                version=rev.get('version', ''),
                platform_updated_at=datetime.fromisoformat(updated_at),
                metadata=rev.get('metadata', {})
            ))

            # Create or update Review instance
            with transaction.atomic():
                Review.objects.bulk_create(
                    objs,
                    batch_size=100,
                    ignore_conflicts=True
                )

    def _map_app_info_to_platform_data(self, app_info: Dict, reviews: list) -> Dict[str, Any]:
        """
        Map app info from iTunes API to AppPlatformData fields.
        """
        # Parse dates
        release_date = None
        current_version_release_date = None
        
        if app_info.get('current_version_release_date'):
            try:
                current_version_release_date = datetime.fromisoformat(
                    app_info['current_version_release_date'].replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                current_version_release_date = datetime.now()
        
        # Prepare extra metadata
        extra_metadata = {
            'description': app_info.get('description'),
            'screenshots': app_info.get('screenshots', []),
            'ipad_screenshots': app_info.get('ipad_screenshots', []),
            'languages': app_info.get('languages', []),
            'supported_devices': app_info.get('supported_devices', []),
            'features': app_info.get('features', []),
            'release_notes': app_info.get('release_notes'),
            'seller_name': app_info.get('seller_name'),
            'size_bytes': app_info.get('size_bytes'),
            'minimum_os_version': app_info.get('minimum_os_version'),
            'content_rating': app_info.get('content_rating'),
            'category': app_info.get('category'),
            'category_id': app_info.get('category_id'),
            'genres': app_info.get('genres', []),
            'release_date': app_info.get('release_date'),
            'total_reviews_fetched': len(reviews)
        }
        
        return {
            'platform_app_id': str(app_info.get('id', '')),
            'bundle_id': app_info.get('bundle_id', ''),
            'developer_id': str(app_info.get('developer_id', '')),
            'name': app_info.get('name', ''),
            'current_version': app_info.get('version', ''),
            'current_version_release_date': current_version_release_date or datetime.now(),
            'icon_url': app_info.get('icon_url', ''),
            'price': Decimal(str(app_info.get('price', 0))),
            'currency': app_info.get('currency', 'USD'),
            'rating_average': Decimal(str(app_info.get('rating_average', 0))) if app_info.get('rating_average') else Decimal('0'),
            'rating_count': app_info.get('rating_count', 0) or 0,
            'extra_metadata': extra_metadata
        }

