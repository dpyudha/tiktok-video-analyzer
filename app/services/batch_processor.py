"""Batch processing service for multiple videos."""
import asyncio
from datetime import datetime
from typing import List, Optional

from ..core.config import settings
from ..models.requests import ExtractBatchRequest
from ..models.responses import ProcessedVideo, BatchData, BatchSummary
from ..models.video import VideoMetadata
from ..core.exceptions import VideoScraperBaseException, ValidationError
from ..utils.validators import URLValidator
from ..utils.logging import CorrelatedLogger
from .video_extractor import VideoExtractor

class BatchProcessor:
    """Service for processing multiple videos in batch."""
    
    def __init__(self):
        self.video_extractor = VideoExtractor()
        self.logger = CorrelatedLogger(__name__)
    
    async def process_batch(
        self, 
        request: ExtractBatchRequest, 
        request_id: Optional[str] = None
    ) -> BatchData:
        """Process multiple video URLs in batch."""
        start_time = datetime.now()
        
        # Set logger correlation ID
        if request_id:
            self.logger.request_id = request_id
        
        # Validate request
        self._validate_batch_request(request)
        
        # Process URLs
        if request.parallel_processing:
            results = await self._process_parallel(request, request_id)
        else:
            results = await self._process_sequential(request, request_id)
        
        # Compile results
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return self._compile_batch_results(request.urls, results, processing_time)
    
    def _validate_batch_request(self, request: ExtractBatchRequest) -> None:
        """Validate batch processing request."""
        if len(request.urls) > settings.max_urls_per_batch:
            raise ValidationError(
                f"Too many URLs provided. Maximum allowed: {settings.max_urls_per_batch}",
                {"max_allowed": settings.max_urls_per_batch, "provided": len(request.urls)}
            )
        
        if len(request.urls) == 0:
            raise ValidationError("No URLs provided")
    
    async def _process_parallel(
        self, 
        request: ExtractBatchRequest, 
        request_id: Optional[str]
    ) -> List[tuple]:
        """Process URLs in parallel with concurrency control."""
        semaphore = asyncio.Semaphore(settings.max_concurrent_extractions)
        
        async def process_with_semaphore(url: str) -> tuple:
            async with semaphore:
                return await self._process_single_url(url, request, request_id)
        
        tasks = [process_with_semaphore(str(url)) for url in request.urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_sequential(
        self, 
        request: ExtractBatchRequest, 
        request_id: Optional[str]
    ) -> List[tuple]:
        """Process URLs sequentially."""
        results = []
        for url in request.urls:
            result = await self._process_single_url(str(url), request, request_id)
            results.append(result)
        return results
    
    async def _process_single_url(
        self, 
        url: str, 
        request: ExtractBatchRequest, 
        request_id: Optional[str]
    ) -> tuple:
        """Process a single URL and return result tuple."""
        try:
            # Validate URL first
            is_valid, platform = URLValidator.validate_and_get_platform(url)
            if not is_valid:
                return (url, "failed", None, f"Unsupported platform: {platform}")
            
            # Extract metadata
            metadata = await self.video_extractor.extract_metadata(
                url, 
                request.include_thumbnail_analysis,
                request_id
            )
            
            self.logger.info(f"Successfully processed: {url}")
            return (url, "success", metadata, None)
            
        except VideoScraperBaseException as e:
            self.logger.error(f"Known error processing {url}: {e.message}")
            return (url, "failed", None, e.message)
        except Exception as e:
            self.logger.error(f"Unexpected error processing {url}: {str(e)}")
            return (url, "failed", None, "Technical error during extraction")
    
    def _compile_batch_results(
        self, 
        urls: List[str], 
        results: List[tuple], 
        processing_time: int
    ) -> BatchData:
        """Compile batch processing results."""
        processed = []
        failed = []
        successful_count = 0
        failed_count = 0
        
        for i, result in enumerate(results):
            url = str(urls[i])
            
            # Handle exceptions from parallel processing
            if isinstance(result, Exception):
                failed_count += 1
                failed.append(ProcessedVideo(
                    url=url,
                    status="failed",
                    error=self._create_error_info("EXTRACTION_FAILED", str(result))
                ))
                continue
            
            # Handle normal results
            url, status, metadata, error_message = result
            
            if status == "success":
                successful_count += 1
                processed.append(ProcessedVideo(
                    url=url,
                    status=status,
                    data=metadata
                ))
            else:
                failed_count += 1
                
                # Determine error code from message
                error_code = self._get_error_code_from_message(error_message)
                
                failed.append(ProcessedVideo(
                    url=url,
                    status=status,
                    error=self._create_error_info(error_code, error_message, url)
                ))
        
        return BatchData(
            processed=processed,
            failed=failed,
            summary=BatchSummary(
                total_requested=len(urls),
                successful=successful_count,
                failed=failed_count,
                processing_time_ms=processing_time
            )
        )
    
    def _get_error_code_from_message(self, error_message: str) -> str:
        """Determine error code from error message."""
        if not error_message:
            return "UNKNOWN_ERROR"
        
        message_lower = error_message.lower()
        
        if "unsupported platform" in message_lower:
            return "UNSUPPORTED_PLATFORM"
        elif "not a video" in message_lower:
            return "NOT_VIDEO_CONTENT"
        elif any(keyword in message_lower for keyword in ['private', 'deleted', 'unavailable']):
            return "VIDEO_UNAVAILABLE"
        elif "technical error" in message_lower:
            return "EXTRACTION_FAILED"
        else:
            return "UNKNOWN_ERROR"
    
    def _create_error_info(
        self, 
        code: str, 
        message: str, 
        url: Optional[str] = None
    ) -> dict:
        """Create error info dictionary."""
        error_info = {
            "code": code,
            "message": message
        }
        
        if url:
            platform = URLValidator.get_platform_from_url(url)
            error_info["details"] = {
                "url": url,
                "platform": platform
            }
        
        return error_info