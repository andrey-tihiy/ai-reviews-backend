import logging
from celery import shared_task
from .models import App
from .services.apple.parser import AppleAppStoreService
import requests

logger = logging.getLogger('apps.app.tasks')


@shared_task
def process_new_app(app_id: str, url: str):
    """
    Process newly created app - analyze URL and collect platform data
    
    Args:
        app_id (str): UUID of the created app
        url (str): App store URL for processing
    """
    try:
        app = App.objects.get(id=app_id)
        logger.info(f"Processing app: {app.name} (ID: {app.id})")
        logger.info(f"App URL for processing: {url}")
        
        # Determine platform and process accordingly
        if 'apps.apple.com' in url:
            apple_service = AppleAppStoreService()
            result = apple_service.process_app_data(app, url)
            
            if result.get('success'):
                logger.info(f"Successfully processed Apple App Store data:")
                logger.info(f"- Platform data ID: {result.get('platform_data_id')}")
                logger.info(f"- Created new record: {result.get('created')}")
                logger.info(f"- Reviews fetched: {result.get('reviews_count')}")
            else:
                logger.error(f"Failed to process Apple App Store data: {result.get('error')}")
            
            return result
        else:
            logger.warning(f"Unsupported platform URL: {url}")
            return {'success': False, 'error': f'Unsupported platform URL: {url}'}
        
        # Future: Add support for Google Play, Product Hunt, etc.
        
    except App.DoesNotExist:
        error_msg = f"App with ID {app_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Error processing app: {str(e)}"
        logger.exception(error_msg)  # .exception() automatically includes stack trace
        return {'success': False, 'error': error_msg}