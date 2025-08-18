"""Simple cache service for TikTok scraper."""
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class CacheService:
    """Simple in-memory cache for video metadata."""
    
    def __init__(self, default_ttl_hours: int = 24):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl_hours = default_ttl_hours
    
    def _make_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return f"video:{hashlib.md5(url.encode()).hexdigest()}"
    
    def get(self, url: str) -> Optional[Any]:
        """Get cached video data."""
        key = self._make_key(url)
        
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        
        # Check if expired
        if datetime.now() > item['expires_at']:
            del self._cache[key]
            return None
        
        return item['data']
    
    def set(self, url: str, data: Any, ttl_hours: Optional[int] = None) -> None:
        """Cache video data."""
        key = self._make_key(url)
        ttl = ttl_hours or self.default_ttl_hours
        
        self._cache[key] = {
            'data': data,
            'expires_at': datetime.now() + timedelta(hours=ttl),
            'created_at': datetime.now()
        }
    
    def exists(self, url: str) -> bool:
        """Check if URL is cached."""
        key = self._make_key(url)
        
        if key not in self._cache:
            return False
        
        item = self._cache[key]
        
        # Check if expired
        if datetime.now() > item['expires_at']:
            del self._cache[key]
            return False
        
        return True
    
    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache stats."""
        return {
            "total_items": len(self._cache),
            "cache_size_mb": len(str(self._cache)) / (1024 * 1024)
        }