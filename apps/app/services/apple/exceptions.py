class AppleAppStoreError(Exception):
    """Base exception for Apple App Store related errors."""
    pass


class AppNotFoundError(AppleAppStoreError):
    """Raised when app is not found in App Store."""
    pass


class InvalidAppUrlError(AppleAppStoreError):
    """Raised when App Store URL is invalid."""
    pass


class APIRequestError(AppleAppStoreError):
    """Raised when API request fails."""
    pass


class DataParsingError(AppleAppStoreError):
    """Raised when data parsing fails."""
    pass