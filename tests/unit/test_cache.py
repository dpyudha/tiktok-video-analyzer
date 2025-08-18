"""Unit tests for cache service."""
import pytest
from datetime import datetime, timedelta
from app.services.cache_service import CacheService

class TestCacheService:
    """Test simple cache service."""
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = CacheService()
        
        test_url = "https://www.tiktok.com/@test/video/123"
        test_data = {"key": "value", "number": 42}
        
        cache.set(test_url, test_data, 1)  # 1 hour TTL
        
        result = cache.get(test_url)
        assert result == test_data
    
    def test_cache_miss(self):
        """Test cache miss."""
        cache = CacheService()
        result = cache.get("https://nonexistent.com/video/123")
        assert result is None
    
    def test_cache_expiry(self):
        """Test cache expiry functionality."""
        cache = CacheService()
        
        test_url = "https://www.tiktok.com/@test/video/123"
        test_data = {"data": "test"}
        
        # Set with 1 hour TTL
        cache.set(test_url, test_data, 1)
        
        # Manually expire by setting past time
        key = cache._make_key(test_url)
        cache._cache[key]["expires_at"] = datetime.now() - timedelta(hours=1)
        
        result = cache.get(test_url)
        assert result is None
    
    def test_cache_exists(self):
        """Test cache exists functionality."""
        cache = CacheService()
        
        test_url = "https://www.tiktok.com/@test/video/123"
        test_data = {"data": "test"}
        
        # Should not exist initially
        assert not cache.exists(test_url)
        
        # Set data
        cache.set(test_url, test_data, 1)
        
        # Should exist now
        assert cache.exists(test_url)
    
    def test_cache_clear(self):
        """Test cache clear functionality."""
        cache = CacheService()
        
        test_url = "https://www.tiktok.com/@test/video/123"
        test_data = {"data": "test"}
        
        # Set data
        cache.set(test_url, test_data, 1)
        assert cache.get(test_url) is not None
        
        # Clear cache
        cache.clear()
        assert cache.get(test_url) is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = CacheService()
        
        # Initial stats
        stats = cache.get_stats()
        assert stats["total_items"] == 0
        assert "cache_size_mb" in stats
        
        # Add some data
        cache.set("https://test1.com/video/1", {"data": "value1"}, 1)
        cache.set("https://test2.com/video/2", {"data": "value2"}, 1)
        
        stats = cache.get_stats()
        assert stats["total_items"] == 2
    
    def test_cache_key_generation(self):
        """Test cache key generation consistency."""
        cache = CacheService()
        
        url = "https://www.tiktok.com/@test/video/123"
        
        key1 = cache._make_key(url)
        key2 = cache._make_key(url)
        
        # Same URL should generate same key
        assert key1 == key2
        
        # Different URLs should generate different keys
        key3 = cache._make_key("https://www.tiktok.com/@test/video/456")
        assert key1 != key3