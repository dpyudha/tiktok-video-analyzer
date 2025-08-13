"""Response creation utilities."""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import status
from fastapi.responses import JSONResponse

from ..models.responses import (
    SuccessResponse, ErrorResponse, ResponseMetadata, 
    RateLimit, ErrorInfo, ErrorDetails
)
from ..core.exceptions import VideoScraperBaseException

class ResponseHelper:
    """Utilities for creating standardized API responses."""
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate unique request ID."""
        return f"req_{uuid.uuid4().hex[:8]}"
    
    @staticmethod
    def create_response_metadata(request_id: str, processing_time_ms: Optional[int] = None) -> ResponseMetadata:
        """Create standardized response metadata."""
        return ResponseMetadata(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=processing_time_ms,
            rate_limit=RateLimit(
                remaining=59,  # This would be calculated from actual rate limiting
                reset_at=datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()
            )
        )
    
    @staticmethod
    def create_success_response(
        data: Any, 
        request_id: Optional[str] = None, 
        processing_time_ms: Optional[int] = None
    ) -> JSONResponse:
        """Create standardized success response."""
        if not request_id:
            request_id = ResponseHelper.generate_request_id()
            
        response = SuccessResponse(
            data=data,
            metadata=ResponseHelper.create_response_metadata(request_id, processing_time_ms)
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump()
        )
    
    @staticmethod
    def create_error_response(
        error_code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        request_id: Optional[str] = None,
        details: Optional[ErrorDetails] = None
    ) -> JSONResponse:
        """Create standardized error response."""
        if not request_id:
            request_id = ResponseHelper.generate_request_id()
        
        response = ErrorResponse(
            error=ErrorInfo(
                code=error_code,
                message=message,
                details=details
            ),
            metadata=ResponseHelper.create_response_metadata(request_id)
        )
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump()
        )
    
    @staticmethod
    def create_error_from_exception(
        exc: VideoScraperBaseException,
        request_id: Optional[str] = None
    ) -> JSONResponse:
        """Create error response from custom exception."""
        if not request_id:
            request_id = ResponseHelper.generate_request_id()
        
        # Map error codes to HTTP status codes
        status_mapping = {
            "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_PLATFORM": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VIDEO_UNAVAILABLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "NOT_VIDEO_CONTENT": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "EXTRACTION_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "THUMBNAIL_ANALYSIS_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
            "API_KEY_INVALID": status.HTTP_401_UNAUTHORIZED,
            "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
            "TIMEOUT": status.HTTP_408_REQUEST_TIMEOUT,
            "CACHE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "CONFIGURATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        
        http_status = status_mapping.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create error details if exception has details
        error_details = None
        if exc.details:
            error_details = ErrorDetails(**exc.details)
        
        return ResponseHelper.create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=http_status,
            request_id=request_id,
            details=error_details
        )