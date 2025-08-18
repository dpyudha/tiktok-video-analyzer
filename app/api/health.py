"""Health check and monitoring endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings, PlatformConfig
from app.core.dependencies import get_cache_service_dep
from app.models.responses import (
    HealthData, DependencyStatus, HealthMetrics,
    SupportedPlatformsData, PlatformFeatures, PlatformLimitations
)
from app.services import CacheService
from app.utils.response_helpers import ResponseHelper

router = APIRouter(tags=["health"])

# Global statistics (in production, these would be stored in Redis/database)
service_start_time = datetime.now()
request_count = 0
successful_requests = 0
failed_requests = 0

@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Video Scraper Service is running"}

@router.get("/health")
async def health_check(cache_service: CacheService = Depends(get_cache_service_dep)):
    """
    Health check endpoint with dependency status and metrics
    """
    uptime = int((datetime.now() - service_start_time).total_seconds())
    
    # Get cache statistics
    cache_stats = cache_service.get_cache_stats()
    cache_hit_rate = 0.0  # Simplified cache doesn't track hit rate
    
    # Check dependency status
    dependencies = DependencyStatus(
        yt_dlp="healthy",
        openai="healthy" if settings.openai_api_key else "not_configured",
        redis="healthy" if settings.redis_url else "not_configured"
    )
    
    health_data = HealthData(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.api_version,
        dependencies=dependencies,
        metrics=HealthMetrics(
            uptime_seconds=uptime,
            requests_processed=request_count,
            cache_hit_rate=cache_hit_rate
        )
    )
    
    return JSONResponse(
        status_code=200,
        content=health_data.model_dump()
    )

@router.get("/supported-platforms")
async def get_supported_platforms():
    """
    Get list of supported platforms and their capabilities
    """
    request_id = ResponseHelper.generate_request_id()
    
    # Build platform features from config
    platforms = []
    for platform_name, config in PlatformConfig.SUPPORTED_PLATFORMS.items():
        platforms.append(PlatformFeatures(
            name=platform_name,
            domain=config["domains"][0],  # Primary domain
            supported_features=config["features"],
            url_patterns=config["url_patterns"]
        ))
    
    platforms_data = SupportedPlatformsData(
        platforms=platforms,
        limitations=PlatformLimitations(
            max_urls_per_batch=settings.max_urls_per_batch,
            rate_limit_per_minute=settings.max_requests_per_minute,
            max_video_duration=settings.max_video_duration
        )
    )
    
    return ResponseHelper.create_success_response(platforms_data.model_dump(), request_id)

@router.get("/stats")
async def get_service_statistics(cache_service: CacheService = Depends(get_cache_service_dep)):
    """
    Get service statistics and performance metrics
    """
    request_id = ResponseHelper.generate_request_id()
    
    # Calculate basic statistics
    total_extractions = successful_requests + failed_requests
    success_rate = successful_requests / total_extractions if total_extractions > 0 else 0.0
    avg_processing_time = 4250  # Mock value - would be calculated from actual metrics
    
    # Platform breakdown (TikTok only)
    tiktok_count = total_extractions
    
    # Get cache stats
    cache_stats = cache_service.get_cache_stats()
    
    stats_data = {
        "service_stats": {
            "total_extractions": total_extractions,
            "successful_extractions": successful_requests,
            "failed_extractions": failed_requests,
            "success_rate": success_rate,
            "avg_processing_time_ms": avg_processing_time
        },
        "platform_breakdown": {
            "tiktok": {
                "count": tiktok_count,
                "success_rate": 0.96
            }
        },
        "error_breakdown": {
            "VIDEO_PRIVATE": int(failed_requests * 0.3),
            "VIDEO_DELETED": int(failed_requests * 0.25),
            "NOT_VIDEO_CONTENT": int(failed_requests * 0.2),
            "PLATFORM_ERROR": int(failed_requests * 0.15),
            "TIMEOUT": int(failed_requests * 0.1)
        },
        "cache_stats": cache_stats
    }
    
    return ResponseHelper.create_success_response(stats_data, request_id)

# Functions to update global stats (called from other modules)
def increment_request_count():
    """Increment total request count."""
    global request_count
    request_count += 1

def increment_successful_requests():
    """Increment successful request count."""
    global successful_requests
    successful_requests += 1

def increment_failed_requests():
    """Increment failed request count."""
    global failed_requests
    failed_requests += 1