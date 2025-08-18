"""Extraction API endpoints - simple service layer."""
from fastapi import APIRouter, Security
import uuid

from app.models.requests import ExtractRequest, ExtractBatchRequest, ExtractTranscriptRequest
from app.services.video_service import VideoService
from app.services.batch_processor import BatchProcessor
from app.services.transcript_service import TranscriptService
from app.services.video_extractor import VideoExtractor
from app.core.dependencies import verify_api_key
from app.core.exceptions import VideoScraperBaseException
from app.utils.response_helpers import ResponseHelper

# Create router
router = APIRouter()

# Service instances
video_service = VideoService()
batch_processor = BatchProcessor()
transcript_service = TranscriptService()
video_extractor = VideoExtractor()


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


@router.post("/extract-transcript")
async def extract_transcript(
    request: ExtractTranscriptRequest,
    api_key: str = Security(verify_api_key)
):
    """Extract transcript from a TikTok video URL.
    
    This endpoint specifically focuses on extracting transcript/captions from videos.
    It uses yt-dlp to extract available subtitles and captions, with preference for:
    1. Manual subtitles in preferred language
    2. Auto-generated captions in preferred language
    3. Any available subtitles/captions
    
    Returns clean, structured transcript data with timing information when available.
    """
    request_id = str(uuid.uuid4())
    
    try:
        # First, extract basic video info using yt-dlp
        # We need this to get subtitle/caption data
        video_info = await video_extractor._extract_with_fallback(str(request.url))
        
        # Extract transcript using the transcript service
        transcript_result = await transcript_service.extract_transcript(
            video_info=video_info,
            preferred_language=request.preferred_language,
            request_id=request_id
        )
        
        # Create response data structure
        response_data = {
            "url": str(request.url),
            "success": transcript_result.success,
            "transcript": None,
            "available_subtitles": transcript_result.available_subtitles.model_dump() if transcript_result.available_subtitles else None,
            "error_message": transcript_result.error_message,
            "fallback_used": transcript_result.fallback_used,
            "quality_assessment": transcript_result.quality_assessment.model_dump() if transcript_result.quality_assessment else None
        }
        
        # Include transcript data if extraction was successful
        if transcript_result.success and transcript_result.transcript:
            response_data["transcript"] = transcript_result.transcript.model_dump()
        
        return ResponseHelper.create_success_response(
            data=response_data,
            request_id=request_id
        )
        
    except VideoScraperBaseException as e:
        return ResponseHelper.create_error_from_exception(e, request_id)
    except Exception as e:
        return ResponseHelper.create_error_response(
            error_code="TRANSCRIPT_EXTRACTION_FAILED",
            message=f"Failed to extract transcript: {str(e)}",
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


# Direct function access for testing (backwards compatibility)
async def extract_single_video(request=None, api_key=None, extractor=None, cache_service=None, **kwargs):
    """Extract metadata from a single video URL (for testing compatibility)."""
    # Generate request ID (can be mocked in tests)
    from app.utils.response_helpers import ResponseHelper
    request_id = ResponseHelper.generate_request_id()
    
    # Handle both old-style direct parameters and new request-based parameters
    if request:
        url = str(request.url)
        include_thumbnail_analysis = getattr(request, 'include_thumbnail_analysis', True)
        include_transcript = getattr(request, 'include_transcript', False)
    else:
        url = kwargs.get('url')
        include_thumbnail_analysis = kwargs.get('include_thumbnail_analysis', True)
        include_transcript = kwargs.get('include_transcript', False)
    
    try:
        # Check cache first if cache_service provided
        if cache_service:
            cached_metadata = await cache_service.get_video_metadata(
                url,
                include_thumbnail_analysis,
                include_transcript
            )
            if cached_metadata:
                return cached_metadata
        
        # Use the extractor if provided (for testing), otherwise use service
        if extractor:
            video_metadata = await extractor.extract_metadata(
                url,
                include_thumbnail_analysis,
                include_transcript,
                request_id
            )
        else:
            video_metadata = await video_service.get_video_metadata(
                url,
                include_thumbnail_analysis,
                include_transcript,
                request_id
            )
        return video_metadata
    except Exception as e:
        raise e