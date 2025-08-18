"""Video service for TikTok scraper."""
from typing import Optional

from app.services.cache_service import CacheService
from app.services.video_extractor import VideoExtractor
from app.models.video import VideoMetadata
from app.utils.validators import URLValidator
from app.core.exceptions import UnsupportedPlatformError


class VideoService:
    """Service for video operations."""
    
    def __init__(self):
        self.cache = CacheService()
        self.extractor = VideoExtractor()
    
    async def get_video_metadata(
        self, 
        url: str, 
        include_thumbnail_analysis: bool = True,
        include_transcript: bool = False,
        request_id: Optional[str] = None
    ) -> VideoMetadata:
        """Get video metadata - check cache first, then extract."""
        
        # Validate URL
        is_valid, platform = URLValidator.validate_and_get_platform(url)
        if not is_valid:
            raise UnsupportedPlatformError(url, platform)
        
        # Check cache first
        cached_data = self.cache.get(url)
        if cached_data:
            # Mark as cache hit
            cached_data.cache_hit = True
            return cached_data
        
        # Extract new data
        video_metadata = await self.extractor.extract_metadata(
            url, include_thumbnail_analysis, include_transcript, request_id
        )
        
        # Cache the result
        self.cache.set(url, video_metadata)
        
        return video_metadata
    
    def is_cached(self, url: str) -> bool:
        """Check if video is cached."""
        return self.cache.exists(url)
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()