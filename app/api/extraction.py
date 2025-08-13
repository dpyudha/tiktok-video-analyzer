"""Video extraction API endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..core.dependencies import verify_api_key, get_video_extractor_dep, get_batch_processor_dep, get_cache_service_dep
from ..core.exceptions import VideoScraperBaseException
from ..models.requests import ExtractRequest, ExtractBatchRequest
from ..services import VideoExtractor, BatchProcessor, CacheService
from ..utils.response_helpers import ResponseHelper
from ..utils.logging import MetricsLogger

router = APIRouter(prefix="/extract", tags=["extraction"])
metrics_logger = MetricsLogger()

@router.post("")
async def extract_single_video(
    request: ExtractRequest,
    api_key: str = Depends(verify_api_key),
    extractor: VideoExtractor = Depends(get_video_extractor_dep),
    cache_service: CacheService = Depends(get_cache_service_dep)
) -> JSONResponse:
    """
    Extract metadata from a single video URL
    
    - **x-api-key**: API key required in header
    - **url**: Video URL (TikTok or Instagram)
    - **include_thumbnail_analysis**: Whether to include AI thumbnail analysis
    - **cache_ttl**: Cache time-to-live in seconds
    """
    request_id = ResponseHelper.generate_request_id()
    start_time = datetime.now()
    
    try:
        url_str = str(request.url)
        
        # Try to get from cache first
        cached_metadata = await cache_service.get_video_metadata(
            url_str, request.include_thumbnail_analysis
        )
        
        if cached_metadata:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Log metrics
            metrics_logger.log_request_metrics(
                request_id, "/extract", "POST", processing_time, 200
            )
            metrics_logger.log_extraction_metrics(
                request_id, url_str, cached_metadata.platform, 
                True, processing_time, cache_hit=True
            )
            
            return ResponseHelper.create_success_response(
                cached_metadata.model_dump(), request_id, processing_time
            )
        
        # Extract from source
        metadata = await extractor.extract_metadata(
            url_str, request.include_thumbnail_analysis, request_id
        )
        
        # Cache the result
        await cache_service.set_video_metadata(metadata, request.cache_ttl)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log metrics
        metrics_logger.log_request_metrics(
            request_id, "/extract", "POST", processing_time, 200
        )
        metrics_logger.log_extraction_metrics(
            request_id, url_str, metadata.platform, 
            True, processing_time, cache_hit=False
        )
        
        return ResponseHelper.create_success_response(
            metadata.model_dump(), request_id, processing_time
        )
        
    except VideoScraperBaseException as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log metrics for failed request
        metrics_logger.log_request_metrics(
            request_id, "/extract", "POST", processing_time, 
            422 if e.error_code in ["VIDEO_UNAVAILABLE", "NOT_VIDEO_CONTENT"] else 500
        )
        
        return ResponseHelper.create_error_from_exception(e, request_id)

@router.post("/batch")
async def extract_batch_videos(
    request: ExtractBatchRequest,
    api_key: str = Depends(verify_api_key),
    processor: BatchProcessor = Depends(get_batch_processor_dep)
) -> JSONResponse:
    """
    Extract metadata from multiple video URLs (max 3)
    
    - **x-api-key**: API key required in header
    - **urls**: List of video URLs (TikTok or Instagram, max 3)
    - **include_thumbnail_analysis**: Whether to include AI thumbnail analysis
    - **parallel_processing**: Whether to process URLs in parallel
    """
    request_id = ResponseHelper.generate_request_id()
    start_time = datetime.now()
    
    try:
        batch_data = await processor.process_batch(request, request_id)
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log metrics
        metrics_logger.log_request_metrics(
            request_id, "/extract/batch", "POST", processing_time, 200, 
            url_count=len(request.urls)
        )
        
        return ResponseHelper.create_success_response(
            batch_data.model_dump(), request_id, processing_time
        )
        
    except VideoScraperBaseException as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log metrics for failed request
        metrics_logger.log_request_metrics(
            request_id, "/extract/batch", "POST", processing_time, 
            400 if e.error_code == "VALIDATION_ERROR" else 500,
            url_count=len(request.urls)
        )
        
        return ResponseHelper.create_error_from_exception(e, request_id)