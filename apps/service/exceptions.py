from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db import IntegrityError
from rest_framework.exceptions import (
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    MethodNotAllowed,
    Throttled,
    ParseError,
    UnsupportedMediaType,
)
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns unified error responses
    """
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Build unified error response
    error_response = {
        "success": False,
        "message": "An error occurred",
        "data": None,
        "error": {
            "code": None,
            "details": None
        }
    }
    
    # Handle different types of exceptions
    if isinstance(exc, ValidationError):
        error_response["message"] = "Validation failed"
        error_response["error"]["code"] = "VALIDATION_ERROR"
        error_response["error"]["details"] = exc.detail
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
    
    elif isinstance(exc, (NotAuthenticated, AuthenticationFailed, TokenError, InvalidToken)):
        error_response["message"] = "Authentication failed"
        error_response["error"]["code"] = "AUTHENTICATION_ERROR"
        if hasattr(exc, 'detail'):
            error_response["error"]["details"] = exc.detail
        return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
    
    elif isinstance(exc, PermissionDenied):
        error_response["message"] = "Permission denied"
        error_response["error"]["code"] = "PERMISSION_ERROR"
        error_response["error"]["details"] = exc.detail
        return Response(error_response, status=status.HTTP_403_FORBIDDEN)
    
    elif isinstance(exc, (NotFound, Http404)):
        error_response["message"] = "Resource not found"
        error_response["error"]["code"] = "NOT_FOUND_ERROR"
        if hasattr(exc, 'detail'):
            error_response["error"]["details"] = exc.detail
        return Response(error_response, status=status.HTTP_404_NOT_FOUND)
    
    elif isinstance(exc, MethodNotAllowed):
        error_response["message"] = "Method not allowed"
        error_response["error"]["code"] = "METHOD_NOT_ALLOWED"
        error_response["error"]["details"] = exc.detail
        return Response(error_response, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    elif isinstance(exc, Throttled):
        error_response["message"] = "Rate limit exceeded"
        error_response["error"]["code"] = "RATE_LIMIT_ERROR"
        error_response["error"]["details"] = {
            "available_in": f"{exc.wait} seconds" if exc.wait else "unknown"
        }
        return Response(error_response, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    elif isinstance(exc, ParseError):
        error_response["message"] = "Invalid request data"
        error_response["error"]["code"] = "PARSE_ERROR"
        error_response["error"]["details"] = exc.detail
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
    
    elif isinstance(exc, UnsupportedMediaType):
        error_response["message"] = "Unsupported media type"
        error_response["error"]["code"] = "UNSUPPORTED_MEDIA_TYPE"
        error_response["error"]["details"] = exc.detail
        return Response(error_response, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    
    elif isinstance(exc, DjangoValidationError):
        error_response["message"] = "Validation failed"
        error_response["error"]["code"] = "VALIDATION_ERROR"
        if hasattr(exc, 'message_dict'):
            error_response["error"]["details"] = exc.message_dict
        else:
            error_response["error"]["details"] = exc.messages
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
    
    elif isinstance(exc, IntegrityError):
        error_response["message"] = "Database integrity error"
        error_response["error"]["code"] = "INTEGRITY_ERROR"
        error_response["error"]["details"] = str(exc)
        return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
    
    # If we have a response from DRF's default handler, format it
    if response is not None:
        error_response["error"]["details"] = response.data
        return Response(error_response, status=response.status_code)
    
    # For unhandled exceptions, log and return 500
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    error_response["message"] = "Internal server error"
    error_response["error"]["code"] = "SERVER_ERROR"
    error_response["error"]["details"] = str(exc) if hasattr(exc, '__str__') else "Unknown error"
    
    return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APIException(Exception):
    """
    Base exception class for API errors
    """
    def __init__(self, message="An error occurred", error_code=None, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationException(APIException):
    """
    Authentication related exceptions
    """
    def __init__(self, message="Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ValidationException(APIException):
    """
    Validation related exceptions
    """
    def __init__(self, message="Validation failed", errors=None):
        self.errors = errors
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST
        ) 