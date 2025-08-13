"""Custom exceptions for the Video Scraper Service."""
from typing import Optional

class VideoScraperBaseException(Exception):
    """Base exception for video scraper service."""
    
    def __init__(self, message: str, error_code: str, details: Optional[dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(VideoScraperBaseException):
    """Exception raised for input validation errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "VALIDATION_ERROR", details)

class UnsupportedPlatformError(VideoScraperBaseException):
    """Exception raised when platform is not supported."""
    
    def __init__(self, url: str, platform: str):
        message = f"URL is not from a supported platform: {platform}"
        details = {"url": url, "platform": platform}
        super().__init__(message, "UNSUPPORTED_PLATFORM", details)

class VideoUnavailableError(VideoScraperBaseException):
    """Exception raised when video is unavailable."""
    
    def __init__(self, url: str, reason: str = "Video is private, deleted, or restricted"):
        message = f"Video unavailable: {reason}"
        details = {"url": url, "reason": reason}
        super().__init__(message, "VIDEO_UNAVAILABLE", details)

class NotVideoContentError(VideoScraperBaseException):
    """Exception raised when URL doesn't contain video content."""
    
    def __init__(self, url: str, content_type: str = "unknown"):
        message = f"URL contains {content_type}, not a video. Please provide a video URL."
        details = {"url": url, "content_type": content_type}
        super().__init__(message, "NOT_VIDEO_CONTENT", details)

class ExtractionFailedError(VideoScraperBaseException):
    """Exception raised when video extraction fails."""
    
    def __init__(self, url: str, reason: str = "Technical error during extraction"):
        message = f"Failed to extract video: {reason}"
        details = {"url": url, "reason": reason}
        super().__init__(message, "EXTRACTION_FAILED", details)

class ThumbnailAnalysisError(VideoScraperBaseException):
    """Exception raised when thumbnail analysis fails."""
    
    def __init__(self, thumbnail_url: str, reason: str = "OpenAI Vision API error"):
        message = f"Failed to analyze thumbnail: {reason}"
        details = {"thumbnail_url": thumbnail_url, "reason": reason}
        super().__init__(message, "THUMBNAIL_ANALYSIS_FAILED", details)

class RateLimitExceededError(VideoScraperBaseException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: str = "1 minute"):
        message = f"Rate limit exceeded: {limit} requests per {window}"
        details = {"limit": limit, "window": window}
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)

class APIKeyInvalidError(VideoScraperBaseException):
    """Exception raised for invalid API key."""
    
    def __init__(self):
        message = "Invalid or missing API key"
        super().__init__(message, "API_KEY_INVALID")

class ServiceUnavailableError(VideoScraperBaseException):
    """Exception raised when external service is unavailable."""
    
    def __init__(self, service: str, reason: str = "Service temporarily unavailable"):
        message = f"Service unavailable: {service} - {reason}"
        details = {"service": service, "reason": reason}
        super().__init__(message, "SERVICE_UNAVAILABLE", details)

class TimeoutError(VideoScraperBaseException):
    """Exception raised when operation times out."""
    
    def __init__(self, operation: str, timeout_seconds: int):
        message = f"Operation timed out: {operation} (timeout: {timeout_seconds}s)"
        details = {"operation": operation, "timeout_seconds": timeout_seconds}
        super().__init__(message, "TIMEOUT", details)

class CacheError(VideoScraperBaseException):
    """Exception raised for cache-related errors."""
    
    def __init__(self, operation: str, reason: str):
        message = f"Cache error during {operation}: {reason}"
        details = {"operation": operation, "reason": reason}
        super().__init__(message, "CACHE_ERROR", details)

class ConfigurationError(VideoScraperBaseException):
    """Exception raised for configuration errors."""
    
    def __init__(self, setting: str, reason: str):
        message = f"Configuration error for {setting}: {reason}"
        details = {"setting": setting, "reason": reason}
        super().__init__(message, "CONFIGURATION_ERROR", details)