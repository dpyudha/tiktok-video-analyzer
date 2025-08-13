"""Unit tests for custom exceptions."""
import pytest
from app.core.exceptions import (
    VideoScraperBaseException, ValidationError, UnsupportedPlatformError,
    VideoUnavailableError, NotVideoContentError, APIKeyInvalidError
)

class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_base_exception(self):
        """Test base exception functionality."""
        exc = VideoScraperBaseException(
            "Test message", 
            "TEST_ERROR", 
            {"key": "value"}
        )
        
        assert str(exc) == "Test message"
        assert exc.message == "Test message"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {"key": "value"}
    
    def test_validation_error(self):
        """Test validation error."""
        exc = ValidationError("Invalid input", {"field": "url"})
        
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.message == "Invalid input"
        assert exc.details == {"field": "url"}
    
    def test_unsupported_platform_error(self):
        """Test unsupported platform error."""
        url = "https://youtube.com/watch?v=123"
        exc = UnsupportedPlatformError(url, "youtube")
        
        assert exc.error_code == "UNSUPPORTED_PLATFORM"
        assert "not from a supported platform" in exc.message
        assert exc.details["url"] == url
        assert exc.details["platform"] == "youtube"
    
    def test_video_unavailable_error(self):
        """Test video unavailable error."""
        url = "https://tiktok.com/@user/video/private"
        reason = "Video is private"
        exc = VideoUnavailableError(url, reason)
        
        assert exc.error_code == "VIDEO_UNAVAILABLE"
        assert reason in exc.message
        assert exc.details["url"] == url
        assert exc.details["reason"] == reason
    
    def test_not_video_content_error(self):
        """Test not video content error."""
        url = "https://tiktok.com/@user/image123"
        content_type = "image"
        exc = NotVideoContentError(url, content_type)
        
        assert exc.error_code == "NOT_VIDEO_CONTENT"
        assert "not a video" in exc.message
        assert exc.details["url"] == url
        assert exc.details["content_type"] == content_type
    
    def test_api_key_invalid_error(self):
        """Test API key invalid error."""
        exc = APIKeyInvalidError()
        
        assert exc.error_code == "API_KEY_INVALID"
        assert "Invalid or missing API key" in exc.message