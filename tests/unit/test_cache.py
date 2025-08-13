"""Unit tests for cache service."""
import pytest
from unittest.mock import Mock, patch
from app.services.cache_service import InMemoryCacheBackend, CacheService
from app.models.video import VideoMetadata, ThumbnailAnalysis

@pytest.mark.asyncio
class TestInMemoryCacheBackend:
    """Test in-memory cache backend."""
    
    async def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = InMemoryCacheBackend()
        
        test_data = {"key": "value", "number": 42}
        await cache.set("test_key", test_data, 60)
        
        result = await cache.get("test_key")
        assert result == test_data
    
    async def test_cache_miss(self):
        """Test cache miss."""
        cache = InMemoryCacheBackend()
        result = await cache.get("nonexistent_key")
        assert result is None
    
    async def test_cache_expiry(self):
        """Test cache expiry functionality."""
        cache = InMemoryCacheBackend()
        
        # Set with very short TTL (simulate expiry by directly modifying)
        await cache.set("test_key", {"data": "test"}, 1)
        
        # Manually expire by setting past time
        from datetime import datetime, timedelta
        expired_time = (datetime.now() - timedelta(seconds=1)).isoformat()
        cache._cache["test_key"]["expires_at"] = expired_time
        
        result = await cache.get("test_key")
        assert result is None
    
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = InMemoryCacheBackend()
        
        # Initial stats
        stats = await cache.get_stats()
        assert stats["hit_rate"] == 0
        assert stats["total_entries"] == 0
        
        # Add some data
        await cache.set("key1", {"data": "value1"}, 60)
        await cache.set("key2", {"data": "value2"}, 60)
        
        # Test hit
        await cache.get("key1")
        # Test miss
        await cache.get("nonexistent")
        
        stats = await cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["hit_rate"] == 0.5  # 1 hit out of 2 requests

@pytest.mark.asyncio 
class TestCacheService:
    """Test cache service."""
    
    @patch('app.services.cache_service.settings')
    async def test_cache_disabled(self, mock_settings):
        """Test behavior when cache is disabled."""
        mock_settings.cache_enabled = False
        
        cache_service = CacheService()
        
        # Should return None when cache is disabled
        result = await cache_service.get_video_metadata("http://test.com", True)
        assert result is None
    
    @patch('app.services.cache_service.settings')
    async def test_cache_video_metadata(self, mock_settings):
        """Test caching video metadata."""
        mock_settings.cache_enabled = True
        mock_settings.cache_ttl_seconds = 3600
        mock_settings.redis_url = None
        
        cache_service = CacheService()
        
        # Create test metadata
        thumbnail_analysis = ThumbnailAnalysis(
            visual_style="talking_head",
            confidence_score=0.9
        )
        
        metadata = VideoMetadata(
            url="https://www.tiktok.com/@test/video/123",
            platform="tiktok",
            title="Test Video",
            duration=30,
            thumbnail_analysis=thumbnail_analysis
        )
        
        # Cache the metadata
        await cache_service.set_video_metadata(metadata, 3600)
        
        # Retrieve from cache
        cached_result = await cache_service.get_video_metadata(
            "https://www.tiktok.com/@test/video/123", True
        )
        
        assert cached_result is not None
        assert cached_result.url == metadata.url
        assert cached_result.title == metadata.title
        assert cached_result.cache_hit is True
    
    @patch('app.services.cache_service.settings')
    async def test_cache_key_generation(self, mock_settings):
        """Test cache key generation for different parameters."""
        mock_settings.cache_enabled = True
        mock_settings.redis_url = None
        
        cache_service = CacheService()
        
        url = "https://www.tiktok.com/@test/video/123"
        
        key1 = cache_service._generate_cache_key(url, True)
        key2 = cache_service._generate_cache_key(url, False)
        
        # Different analysis options should generate different keys
        assert key1 != key2
        
        # Same parameters should generate same key
        key3 = cache_service._generate_cache_key(url, True)
        assert key1 == key3