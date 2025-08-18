"""Extraction API endpoints - simple service layer."""
from fastapi import APIRouter, Security
import uuid

from app.models.requests import ExtractRequest, ExtractBatchRequest
from app.services.video_service import VideoService
from app.services.batch_processor import BatchProcessor
from app.core.dependencies import verify_api_key
from app.core.exceptions import VideoScraperBaseException
from app.utils.response_helpers import ResponseHelper

# Create router
router = APIRouter()

# Service instances
video_service = VideoService()
batch_processor = BatchProcessor()


@router.post("/extract")
async def extract_video_metadata(
    request: ExtractRequest,
    api_key: str = Security(verify_api_key)
):
    """Extract metadata from a single video URL."""
    request_id = str(uuid.uuid4())
    
    try:
        # Use service to get video metadata
        video_metadata = await video_service.get_video_metadata(
            str(request.url),
            request.include_thumbnail_analysis,
            request.include_transcript,
            request_id
        )
        
        return ResponseHelper.create_success_response(
            data=video_metadata.model_dump() if hasattr(video_metadata, 'model_dump') else video_metadata.__dict__,
            request_id=request_id
        )
        
    except VideoScraperBaseException as e:
        return ResponseHelper.create_error_from_exception(e, request_id)
    except Exception as e:
        return ResponseHelper.create_error_response(
            error_code="EXTRACTION_FAILED",
            message=str(e),
            status_code=500,
            request_id=request_id
        )


@router.post("/extract/batch")
async def extract_batch_video_metadata(
    request: ExtractBatchRequest,
    api_key: str = Security(verify_api_key)
):
    """Extract metadata from multiple video URLs."""
    request_id = str(uuid.uuid4())
    
    try:
        # Use service to process batch
        batch_result = await batch_processor.process_batch(request, request_id)
        
        return ResponseHelper.create_success_response(
            data=batch_result.model_dump() if hasattr(batch_result, 'model_dump') else batch_result.__dict__,
            request_id=request_id
        )
        
    except VideoScraperBaseException as e:
        return ResponseHelper.create_error_from_exception(e, request_id)
    except Exception as e:
        return ResponseHelper.create_error_response(
            error_code="BATCH_PROCESSING_FAILED",
            message=str(e),
            status_code=500,
            request_id=request_id
        )


@router.get("/cache/stats")
async def get_cache_stats(
    api_key: str = Security(verify_api_key)
):
    """Get cache statistics."""
    try:
        stats = video_service.get_cache_stats()
        return ResponseHelper.create_success_response(
            data=stats,
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        return ResponseHelper.create_error_response(
            error_code="STATS_ERROR",
            message=str(e),
            status_code=500,
            request_id=str(uuid.uuid4())
        )