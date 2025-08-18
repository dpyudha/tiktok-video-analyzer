"""Dependency injection setup for FastAPI."""
from functools import lru_cache
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import settings
from .exceptions import APIKeyInvalidError, VideoScraperBaseException
from app.services import VideoExtractor, ThumbnailAnalyzer, BatchProcessor, CacheService
from app.utils.logging import CorrelatedLogger

# Security dependency
api_key_header = APIKeyHeader(name="x-api-key")

# Service instances cache
@lru_cache()
def get_video_extractor() -> VideoExtractor:
    """Get VideoExtractor service instance."""
    return VideoExtractor()

@lru_cache()
def get_thumbnail_analyzer() -> ThumbnailAnalyzer:
    """Get ThumbnailAnalyzer service instance."""
    return ThumbnailAnalyzer()

@lru_cache()
def get_batch_processor() -> BatchProcessor:
    """Get BatchProcessor service instance."""
    return BatchProcessor()

@lru_cache()
def get_cache_service() -> CacheService:
    """Get CacheService instance."""
    return CacheService()

@lru_cache()
def get_logger() -> CorrelatedLogger:
    """Get logger instance."""
    return CorrelatedLogger(__name__)

# Authentication dependency
async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key from request header."""
    if api_key != settings.api_key:
        raise APIKeyInvalidError()
    return api_key

# Service dependencies
def get_video_extractor_dep(
    extractor: VideoExtractor = Depends(get_video_extractor)
) -> VideoExtractor:
    """Dependency for VideoExtractor service."""
    return extractor

def get_batch_processor_dep(
    processor: BatchProcessor = Depends(get_batch_processor)
) -> BatchProcessor:
    """Dependency for BatchProcessor service."""
    return processor

def get_cache_service_dep(
    cache: CacheService = Depends(get_cache_service)
) -> CacheService:
    """Dependency for CacheService."""
    return cache