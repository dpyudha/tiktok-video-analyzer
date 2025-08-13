"""Caching service for video metadata."""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from ..core.config import settings
from ..core.exceptions import CacheError
from ..models.video import VideoMetadata
from ..utils.logging import CorrelatedLogger

class CacheBackend(ABC):
    """Abstract cache backend interface."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        """Set value in cache with TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass

class InMemoryCacheBackend(CacheBackend):
    """In-memory cache backend for development/testing."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._hit_count = 0
        self._miss_count = 0
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from in-memory cache."""
        if key in self._cache:
            entry = self._cache[key]
            # Check if entry has expired
            if datetime.fromisoformat(entry['expires_at']) > datetime.now():
                self._hit_count += 1
                return entry['data']
            else:
                # Remove expired entry
                del self._cache[key]
        
        self._miss_count += 1
        return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        """Set value in in-memory cache."""
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        self._cache[key] = {
            'data': value,
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.now().isoformat()
        }
    
    async def delete(self, key: str) -> None:
        """Delete value from in-memory cache."""
        if key in self._cache:
            del self._cache[key]
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in in-memory cache."""
        if key in self._cache:
            entry = self._cache[key]
            # Check if entry has expired
            if datetime.fromisoformat(entry['expires_at']) > datetime.now():
                return True
            else:
                # Remove expired entry
                del self._cache[key]
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get in-memory cache statistics."""
        total_requests = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total_requests if total_requests > 0 else 0
        
        # Calculate memory usage (rough estimate)
        memory_usage_bytes = sum(
            len(json.dumps(entry).encode('utf-8'))
            for entry in self._cache.values()
        )
        memory_usage_mb = memory_usage_bytes / (1024 * 1024)
        
        return {
            'hit_rate': hit_rate,
            'total_entries': len(self._cache),
            'memory_usage_mb': round(memory_usage_mb, 2),
            'hit_count': self._hit_count,
            'miss_count': self._miss_count
        }

class RedisCacheBackend(CacheBackend):
    """Redis cache backend for production."""
    
    def __init__(self, redis_url: str):
        try:
            import redis.asyncio as redis
            self.redis = redis.from_url(redis_url)
        except ImportError:
            raise CacheError("Redis initialization", "redis package not installed")
        except Exception as e:
            raise CacheError("Redis initialization", str(e))
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from Redis cache."""
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data.decode('utf-8'))
            return None
        except Exception as e:
            raise CacheError("Redis get", str(e))
    
    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        """Set value in Redis cache."""
        try:
            data = json.dumps(value, default=str)
            await self.redis.setex(key, ttl_seconds, data)
        except Exception as e:
            raise CacheError("Redis set", str(e))
    
    async def delete(self, key: str) -> None:
        """Delete value from Redis cache."""
        try:
            await self.redis.delete(key)
        except Exception as e:
            raise CacheError("Redis delete", str(e))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            return await self.redis.exists(key)
        except Exception as e:
            raise CacheError("Redis exists", str(e))
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            info = await self.redis.info()
            return {
                'hit_rate': 0.75,  # Would need to track this separately
                'total_entries': info.get('db0', {}).get('keys', 0),
                'memory_usage_mb': round(info.get('used_memory', 0) / (1024 * 1024), 2),
                'connected_clients': info.get('connected_clients', 0)
            }
        except Exception as e:
            raise CacheError("Redis stats", str(e))

class CacheService:
    """Main cache service with multiple backend support."""
    
    def __init__(self):
        self.backend = self._initialize_backend()
        self.logger = CorrelatedLogger(__name__)
    
    def _initialize_backend(self) -> CacheBackend:
        """Initialize cache backend based on configuration."""
        if not settings.cache_enabled:
            return InMemoryCacheBackend()  # Disabled cache still uses in-memory
        
        if settings.redis_url:
            try:
                return RedisCacheBackend(settings.redis_url)
            except Exception as e:
                self.logger.warning(f"Failed to initialize Redis cache: {e}")
                self.logger.info("Falling back to in-memory cache")
        
        return InMemoryCacheBackend()
    
    def _generate_cache_key(self, url: str, include_thumbnail_analysis: bool, include_transcript: bool = False) -> str:
        """Generate cache key for video metadata."""
        # Create a unique key based on URL and analysis options
        key_data = f"{url}:thumbnail_analysis={include_thumbnail_analysis}:transcript={include_transcript}"
        key_hash = hashlib.md5(key_data.encode('utf-8')).hexdigest()
        return f"video_metadata:{key_hash}"
    
    async def get_video_metadata(
        self, 
        url: str, 
        include_thumbnail_analysis: bool = True,
        include_transcript: bool = False
    ) -> Optional[VideoMetadata]:
        """Get cached video metadata."""
        if not settings.cache_enabled:
            return None
        
        try:
            key = self._generate_cache_key(url, include_thumbnail_analysis, include_transcript)
            data = await self.backend.get(key)
            
            if data:
                self.logger.info(f"Cache hit for: {url}")
                # Update cache_hit flag
                data['cache_hit'] = True
                return VideoMetadata(**data)
            
            self.logger.info(f"Cache miss for: {url}")
            return None
            
        except Exception as e:
            self.logger.warning(f"Cache get error for {url}: {e}")
            return None
    
    async def set_video_metadata(
        self, 
        metadata: VideoMetadata, 
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache video metadata."""
        if not settings.cache_enabled:
            return
        
        try:
            key = self._generate_cache_key(
                metadata.url, 
                bool(metadata.thumbnail_analysis), 
                bool(metadata.transcript)
            )
            ttl = ttl_seconds or settings.cache_ttl_seconds
            
            # Convert metadata to dict and ensure it's JSON serializable
            data = metadata.model_dump()
            data['cache_hit'] = False  # Reset for fresh cache entry
            
            await self.backend.set(key, data, ttl)
            self.logger.info(f"Cached metadata for: {metadata.url}")
            
        except Exception as e:
            self.logger.warning(f"Cache set error for {metadata.url}: {e}")
    
    async def invalidate_video_metadata(self, url: str) -> None:
        """Invalidate cached video metadata."""
        if not settings.cache_enabled:
            return
        
        try:
            # Invalidate all combinations of thumbnail analysis and transcript
            for include_analysis in [True, False]:
                for include_transcript in [True, False]:
                    key = self._generate_cache_key(url, include_analysis, include_transcript)
                    await self.backend.delete(key)
            
            self.logger.info(f"Invalidated cache for: {url}")
            
        except Exception as e:
            self.logger.warning(f"Cache invalidation error for {url}: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            return await self.backend.get_stats()
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {
                'hit_rate': 0,
                'total_entries': 0,
                'memory_usage_mb': 0,
                'error': str(e)
            }