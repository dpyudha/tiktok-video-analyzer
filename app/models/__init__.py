"""Data models for the Video Scraper Service."""
from .requests import ExtractRequest, ExtractBatchRequest
from .video import ThumbnailAnalysis, VideoMetadata
from .responses import (
    RateLimit, ResponseMetadata, ErrorDetails, ErrorInfo,
    SuccessResponse, ErrorResponse, ProcessedVideo, BatchSummary, BatchData,
    PlatformFeatures, PlatformLimitations, SupportedPlatformsData,
    DependencyStatus, HealthMetrics, HealthData,
    ServiceStats, PlatformStats, PlatformBreakdown, CacheStats, StatsData
)

__all__ = [
    "ExtractRequest", "ExtractBatchRequest",
    "ThumbnailAnalysis", "VideoMetadata",
    "RateLimit", "ResponseMetadata", "ErrorDetails", "ErrorInfo",
    "SuccessResponse", "ErrorResponse", "ProcessedVideo", "BatchSummary", "BatchData",
    "PlatformFeatures", "PlatformLimitations", "SupportedPlatformsData",
    "DependencyStatus", "HealthMetrics", "HealthData",
    "ServiceStats", "PlatformStats", "PlatformBreakdown", "CacheStats", "StatsData"
]