from rest_framework.response import Response
from rest_framework import status
from typing import Any, Dict, Optional


class APIResponse:
    """
    Unified API response format for all endpoints
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK,
        pagination: Optional[Dict] = None
    ) -> Response:
        """
        Success response format
        """
        response_data = {
            "success": True,
            "message": message,
            "data": data,
            "error": None
        }
        
        if pagination:
            response_data["pagination"] = pagination
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        message: str = "An error occurred",
        errors: Optional[Dict] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None
    ) -> Response:
        """
        Error response format
        """
        response_data = {
            "success": False,
            "message": message,
            "data": None,
            "error": {
                "code": error_code,
                "details": errors
            }
        }
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def validation_error(errors: Dict, message: str = "Validation failed") -> Response:
        """
        Validation error response format
        """
        return APIResponse.error(
            message=message,
            errors=errors,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR"
        )
    
    @staticmethod
    def authentication_error(message: str = "Authentication failed") -> Response:
        """
        Authentication error response format
        """
        return APIResponse.error(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR"
        )
    
    @staticmethod
    def permission_error(message: str = "Permission denied") -> Response:
        """
        Permission error response format
        """
        return APIResponse.error(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_ERROR"
        )
    
    @staticmethod
    def not_found_error(message: str = "Resource not found") -> Response:
        """
        Not found error response format
        """
        return APIResponse.error(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND_ERROR"
        )
    
    @staticmethod
    def server_error(message: str = "Internal server error") -> Response:
        """
        Server error response format
        """
        return APIResponse.error(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="SERVER_ERROR"
        ) 