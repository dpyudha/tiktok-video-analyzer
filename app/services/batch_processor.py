"""Simple batch service for TikTok scraper."""
import asyncio
from typing import List, Optional
from datetime import datetime

from app.services.video_service import VideoService
from app.models.requests import ExtractBatchRequest
from app.models.responses import BatchData, BatchSummary, ProcessedVideo
from app.core.exceptions import ValidationError, VideoScraperBaseException
from app.core.config import settings


class BatchProcessor:
    """Simple service for batch video processing."""
    
    def __init__(self):
        self.video_service = VideoService()
    
    async def process_batch(
        self, 
        request: ExtractBatchRequest, 
        request_id: Optional[str] = None
    ) -> BatchData:
        """Process multiple videos."""
        start_time = datetime.now()
        
        # Validate request
        self._validate_request(request)
        
        # Process URLs
        if request.parallel_processing:
            results = await self._process_parallel(request, request_id)
        else:
            results = await self._process_sequential(request, request_id)
        
        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return self._create_response(request.urls, results, processing_time)
    
    def _validate_request(self, request: ExtractBatchRequest) -> None:
        """Validate batch request."""
        if len(request.urls) > settings.max_urls_per_batch:
            raise ValidationError(f"Too many URLs. Max: {settings.max_urls_per_batch}")
        
        if len(request.urls) == 0:
            raise ValidationError("No URLs provided")
    
    async def _process_parallel(
        self, 
        request: ExtractBatchRequest, 
        request_id: Optional[str]
    ) -> List[tuple]:
        """Process URLs in parallel."""
        semaphore = asyncio.Semaphore(settings.max_concurrent_extractions)
        
        async def process_one(url: str) -> tuple:
            async with semaphore:
                return await self._process_single_url(url, request, request_id)
        
        tasks = [process_one(str(url)) for url in request.urls]
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
        """Process single URL."""
        try:
            # Use video service to extract metadata
            metadata = await self.video_service.get_video_metadata(
                url, 
                request.include_thumbnail_analysis,
                request.include_transcript,
                request_id
            )
            return (url, "success", metadata, None)
            
        except VideoScraperBaseException as e:
            return (url, "failed", None, e.message)
        except Exception as e:
            return (url, "failed", None, str(e))
    
    def _create_response(
        self, 
        urls: List[str], 
        results: List[tuple], 
        processing_time: int
    ) -> BatchData:
        """Create batch response."""
        processed = []
        failed = []
        
        for i, result in enumerate(results):
            url = str(urls[i])
            
            # Handle exceptions
            if isinstance(result, Exception):
                failed.append(ProcessedVideo(
                    url=url,
                    status="failed",
                    error={"code": "EXTRACTION_FAILED", "message": str(result)}
                ))
                continue
            
            # Handle normal results
            url, status, metadata, error_message = result
            
            if status == "success":
                processed.append(ProcessedVideo(
                    url=url,
                    status=status,
                    data=metadata
                ))
            else:
                failed.append(ProcessedVideo(
                    url=url,
                    status=status,
                    error={"code": "EXTRACTION_FAILED", "message": error_message}
                ))
        
        return BatchData(
            processed=processed,
            failed=failed,
            summary=BatchSummary(
                total_requested=len(urls),
                successful=len(processed),
                failed=len(failed),
                processing_time_ms=processing_time
            )
        )