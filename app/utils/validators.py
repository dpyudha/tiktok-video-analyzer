"""URL validation utilities."""
import re
from urllib.parse import urlparse
from typing import Tuple
from app.core.config import PlatformConfig
from app.core.exceptions import UnsupportedPlatformError, ValidationError

class URLValidator:
    """URL validation utilities for supported platforms."""
    
    @staticmethod
    def validate_video_url(url: str) -> bool:
        """Validate if URL is from supported platforms (TikTok only)."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            supported_domains = PlatformConfig.get_all_domains()
            return any(domain.endswith(d) for d in supported_domains)
        except Exception:
            return False
    
    @staticmethod
    def get_platform_from_url(url: str) -> str:
        """Extract platform name from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            if 'tiktok.com' in domain:
                return 'tiktok'
            else:
                return 'unknown'
        except Exception:
            return 'unknown'
    
    @staticmethod
    def validate_and_get_platform(url: str) -> Tuple[bool, str]:
        """Validate URL and return validation status with platform."""
        is_valid = URLValidator.validate_video_url(url)
        platform = URLValidator.get_platform_from_url(url)
        return is_valid, platform
    
    @staticmethod
    def extract_video_id_from_url(url: str) -> str:
        """Extract video ID from TikTok URL."""
        patterns = [
            r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w\.-]+/video/(\d+)',
            r'(?:https?://)?(?:vm\.|vt\.)?tiktok\.com/[\w\.-]+/(\d+)',
            r'(?:https?://)?(?:m\.)?tiktok\.com/v/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, try to extract from the URL path
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part.isdigit() and len(part) > 10:  # TikTok video IDs are long numbers
                    return part
        except Exception:
            pass
        
        raise ValidationError(f"Could not extract video ID from URL: {url}")

class ContentValidator:
    """Video content validation utilities."""
    
    @staticmethod
    def is_video_content(video_info: dict) -> bool:
        """Check if the extracted content is actually a video."""
        if not video_info:
            return False
        
        # Check if duration exists and is greater than 0
        duration = video_info.get('duration')
        if not duration or duration <= 0:
            return False
        
        # Check for video-specific fields
        has_video_format = video_info.get('format') or video_info.get('format_id')
        has_video_url = video_info.get('url') and ('video' in str(video_info.get('url', '')).lower() or 'mp4' in str(video_info.get('url', '')).lower())
        
        # Check if it has video codecs or video-related metadata
        vcodec = video_info.get('vcodec', 'none')
        has_video_codec = vcodec and vcodec != 'none'
        
        # For TikTok, check for typical video metadata
        width = video_info.get('width', 0)
        height = video_info.get('height', 0)
        has_video_dimensions = width > 0 and height > 0
        
        # Check if it's explicitly marked as a video
        media_type = video_info.get('_type', '')
        is_video_type = media_type == 'video' or 'video' in media_type.lower()
        
        # Must have duration and at least one video indicator
        return (has_video_format or has_video_url or has_video_codec or has_video_dimensions or is_video_type)
    
    @staticmethod
    def get_content_type(video_info: dict) -> str:
        """Determine the content type from video info."""
        if not video_info:
            return "unknown"
        
        if ContentValidator.is_video_content(video_info):
            return "video"
        
        # Check if it's an image
        width = video_info.get('width', 0)
        height = video_info.get('height', 0)
        if width > 0 and height > 0 and not video_info.get('duration'):
            return "image"
        
        return "unknown content"