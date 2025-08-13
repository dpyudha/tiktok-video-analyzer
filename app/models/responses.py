"""Response models for the Video Scraper Service."""
from typing import Any, Optional, List, Dict
from pydantic import BaseModel
from .video import VideoMetadata

class RateLimit(BaseModel):
    """Rate limit information."""
    remaining: int
    reset_at: str

class ResponseMetadata(BaseModel):
    """Standard response metadata."""
    request_id: str
    api_version: str = "1.0.0"
    timestamp: Optional[str] = None
    rate_limit: Optional[RateLimit] = None
    processing_time_ms: Optional[int] = None

class ErrorDetails(BaseModel):
    """Detailed error information."""
    url: Optional[str] = None
    platform: Optional[str] = None
    reason: Optional[str] = None

class ErrorInfo(BaseModel):
    """Error information structure."""
    code: str
    message: str
    details: Optional[ErrorDetails] = None

class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    data: Any
    metadata: ResponseMetadata

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: ErrorInfo
    metadata: ResponseMetadata

class ProcessedVideo(BaseModel):
    """Single video processing result."""
    url: str
    status: str
    data: Optional[VideoMetadata] = None
    error: Optional[ErrorInfo] = None

class BatchSummary(BaseModel):
    """Summary of batch processing results."""
    total_requested: int
    successful: int
    failed: int
    processing_time_ms: int

class BatchData(BaseModel):
    """Batch processing response data."""
    processed: List[ProcessedVideo]
    failed: List[ProcessedVideo]
    summary: BatchSummary

class PlatformFeatures(BaseModel):
    """Platform feature description."""
    name: str
    domain: str
    supported_features: List[str]
    url_patterns: List[str]

class PlatformLimitations(BaseModel):
    """Platform usage limitations."""
    max_urls_per_batch: int
    rate_limit_per_minute: int
    max_video_duration: int

class SupportedPlatformsData(BaseModel):
    """Supported platforms information."""
    platforms: List[PlatformFeatures]
    limitations: PlatformLimitations

class DependencyStatus(BaseModel):
    """Service dependency status."""
    yt_dlp: str
    openai: str
    redis: Optional[str] = "not_configured"

class HealthMetrics(BaseModel):
    """Service health metrics."""
    uptime_seconds: int
    requests_processed: int
    cache_hit_rate: float

class HealthData(BaseModel):
    """Complete health check response."""
    status: str
    timestamp: str
    version: str
    dependencies: DependencyStatus
    metrics: HealthMetrics

class ServiceStats(BaseModel):
    """Service usage statistics."""
    total_extractions: int
    successful_extractions: int
    failed_extractions: int
    success_rate: float
    avg_processing_time_ms: int

class PlatformStats(BaseModel):
    """Platform-specific statistics."""
    count: int
    success_rate: float

class PlatformBreakdown(BaseModel):
    """Breakdown by platform."""
    tiktok: PlatformStats
    instagram: PlatformStats

class CacheStats(BaseModel):
    """Cache performance statistics."""
    hit_rate: float
    total_entries: int
    memory_usage_mb: int

class StatsData(BaseModel):
    """Complete statistics response."""
    service_stats: ServiceStats
    platform_breakdown: PlatformBreakdown
    error_breakdown: Dict[str, int]
    cache_stats: CacheStats