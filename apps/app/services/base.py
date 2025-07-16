from abc import ABC, abstractmethod
from typing import Dict, Optional, Any


class BasePlatformService(ABC):
    """
    Base class for all platform services (Apple App Store, Google Play, etc.)
    """
    
    @abstractmethod
    def extract_app_id_from_url(self, url: str) -> Optional[str]:
        """Extract app ID from platform URL."""
        pass
    
    @abstractmethod
    def fetch_app_info(self, app_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetch app metadata from platform API."""
        pass
    
    @abstractmethod
    def process_app_data(self, app_instance, url: str, **kwargs) -> Dict[str, Any]:
        """Process app URL and create/update AppPlatformData."""
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return platform name (appstore, play_market, etc.)."""
        pass