"""Unit tests for validation utilities."""
import pytest
from app.utils.validators import URLValidator, ContentValidator

class TestURLValidator:
    """Test URL validation utilities."""
    
    def test_validate_tiktok_urls(self):
        """Test TikTok URL validation."""
        valid_urls = [
            "https://www.tiktok.com/@user/video/1234567890",
            "https://tiktok.com/@user/video/1234567890",
            "https://vm.tiktok.com/shortid",
            "https://m.tiktok.com/@user/video/1234567890"
        ]
        
        for url in valid_urls:
            assert URLValidator.validate_video_url(url) is True
            assert URLValidator.get_platform_from_url(url) == "tiktok"
    
    
    def test_reject_unsupported_urls(self):
        """Test rejection of unsupported URLs."""
        invalid_urls = [
            "https://www.youtube.com/watch?v=123",
            "https://www.instagram.com/reel/ABC123/",
            "https://twitter.com/user/status/123",
            "https://facebook.com/video/123",
            "https://example.com/video/123",
            "invalid-url"
        ]
        
        for url in invalid_urls:
            assert URLValidator.validate_video_url(url) is False
            platform = URLValidator.get_platform_from_url(url)
            assert platform == "unknown"

class TestContentValidator:
    """Test content validation utilities."""
    
    def test_valid_video_content(self):
        """Test detection of valid video content."""
        video_info = {
            "duration": 30,
            "width": 1080,
            "height": 1920,
            "vcodec": "h264",
            "_type": "video"
        }
        
        assert ContentValidator.is_video_content(video_info) is True
        assert ContentValidator.get_content_type(video_info) == "video"
    
    def test_invalid_video_content_no_duration(self):
        """Test rejection of content without duration."""
        video_info = {
            "width": 1080,
            "height": 1920
        }
        
        assert ContentValidator.is_video_content(video_info) is False
        assert ContentValidator.get_content_type(video_info) == "image"
    
    def test_invalid_video_content_zero_duration(self):
        """Test rejection of content with zero duration."""
        video_info = {
            "duration": 0,
            "width": 1080,
            "height": 1920
        }
        
        assert ContentValidator.is_video_content(video_info) is False
        assert ContentValidator.get_content_type(video_info) == "image"
    
    def test_empty_video_info(self):
        """Test handling of empty video info."""
        assert ContentValidator.is_video_content(None) is False
        assert ContentValidator.is_video_content({}) is False
        assert ContentValidator.get_content_type({}) == "unknown"