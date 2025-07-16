import logging
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse

from .exceptions import AppNotFoundError, InvalidAppUrlError, APIRequestError, DataParsingError

logger = logging.getLogger('apps.app.services.apple.client')


class AppleAppStoreClient:
    """
    Client for interacting with Apple App Store APIs
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def extract_app_id_from_url(self, url: str) -> Optional[str]:
        """Extract app ID from App Store URL."""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            
            for part in path_parts:
                if part.startswith('id'):
                    return part[2:]  # Remove 'id' prefix
            
            return None
        except Exception:
            raise InvalidAppUrlError(f"Invalid App Store URL: {url}")
    
    def fetch_app_info(self, app_id: str, country: str = 'us') -> Optional[Dict]:
        """
        Fetch app metadata from iTunes API.
        
        Args:
            app_id: The App Store app ID (numeric)
            country: Country code (default: 'us')
        
        Returns:
            Dictionary with app information
        """
        url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
        logger.info(f"Fetching app info for ID {app_id} from country {country}")
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('resultCount', 0) > 0:
                app_data = data['results'][0]
                logger.info(f"Successfully fetched app info for {app_data.get('trackName', 'Unknown')}")
                
                # Extract relevant fields
                app_info = {
                    'id': app_data.get('trackId'),
                    'name': app_data.get('trackName'),
                    'bundle_id': app_data.get('bundleId'),
                    'version': app_data.get('version'),
                    'description': app_data.get('description'),
                    'developer_name': app_data.get('artistName'),
                    'developer_id': app_data.get('artistId'),
                    'category': app_data.get('primaryGenreName'),
                    'category_id': app_data.get('primaryGenreId'),
                    'genres': app_data.get('genres', []),
                    'price': app_data.get('price', 0),
                    'currency': app_data.get('currency'),
                    'rating_average': app_data.get('averageUserRating'),
                    'rating_count': app_data.get('userRatingCount'),
                    'rating_count_current_version': app_data.get('userRatingCountForCurrentVersion'),
                    'release_date': app_data.get('releaseDate'),
                    'current_version_release_date': app_data.get('currentVersionReleaseDate'),
                    'size_bytes': app_data.get('fileSizeBytes'),
                    'minimum_os_version': app_data.get('minimumOsVersion'),
                    'content_rating': app_data.get('contentAdvisoryRating'),
                    'app_store_url': app_data.get('trackViewUrl'),
                    'icon_url': app_data.get('artworkUrl512') or app_data.get('artworkUrl100'),
                    'screenshots': app_data.get('screenshotUrls', []),
                    'ipad_screenshots': app_data.get('ipadScreenshotUrls', []),
                    'languages': app_data.get('languageCodesISO2A', []),
                    'supported_devices': app_data.get('supportedDevices', []),
                    'features': app_data.get('features', []),
                    'release_notes': app_data.get('releaseNotes'),
                    'seller_name': app_data.get('sellerName')
                }
                
                return app_info
            else:
                logger.warning(f"App with ID {app_id} not found in iTunes API")
                raise AppNotFoundError(f"App with ID {app_id} not found")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching app info for ID {app_id}: {e}")
            raise APIRequestError(f"Error fetching app info: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for app info ID {app_id}: {e}")
            raise DataParsingError(f"Error parsing app info JSON: {e}")
    
    def fetch_reviews(self, app_id: str, country: str = 'us', max_pages: int = 10) -> List[Dict]:
        """
        Fetch reviews from Apple App Store RSS feed.
        
        Args:
            app_id: The App Store app ID (numeric)
            country: Country code (default: 'us')
            max_pages: Maximum pages to fetch (max 50, each page has 50 reviews)
        
        Returns:
            List of review dictionaries
        """
        logger.info(f"Fetching reviews for app ID {app_id}, max pages: {max_pages}")
        all_reviews = []
        
        for page in range(1, min(max_pages + 1, 51)):  # RSS feed supports up to 50 pages
            url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/json"
            logger.debug(f"Fetching reviews page {page} for app ID {app_id}")
            
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                # Check if we have entries
                if 'feed' in data and 'entry' in data['feed']:
                    entries = data['feed']['entry']
                    
                    # Skip first entry on page 1 (it's app info, not a review)
                    if page == 1 and len(entries) > 0:
                        entries = entries[1:]
                    
                    for entry in entries:
                        review = {
                            'author': entry.get('author', {}).get('name', {}).get('label', 'Unknown'),
                            'rating': entry.get('im:rating', {}).get('label', 'N/A'),
                            'title': entry.get('title', {}).get('label', ''),
                            'content': entry.get('content', {}).get('label', ''),
                            'version': entry.get('im:version', {}).get('label', 'Unknown'),
                            'id': entry.get('id', {}).get('label', ''),
                            'updated': entry.get('updated', {}).get('label', '')
                        }
                        all_reviews.append(review)
                    
                    logger.debug(f"Fetched {len(entries)} reviews from page {page}")
                else:
                    # No more reviews
                    logger.info(f"No more reviews found at page {page}, stopping")
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error fetching reviews page {page} for app ID {app_id}: {e}")
                raise APIRequestError(f"Error fetching reviews page {page}: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error for reviews page {page} for app ID {app_id}: {e}")
                raise DataParsingError(f"Error parsing reviews JSON for page {page}: {e}")
        
        logger.info(f"Successfully fetched {len(all_reviews)} total reviews for app ID {app_id}")
        return all_reviews