"""Video extraction service using yt-dlp."""
import asyncio
import requests
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import yt_dlp

from app.core.config import settings, YTDLPConfig
from app.core.exceptions import (
    VideoUnavailableError, ExtractionFailedError, NotVideoContentError,
    ServiceUnavailableError, TimeoutError
)
from app.models.video import VideoMetadata
from app.utils.validators import URLValidator, ContentValidator
from app.utils.logging import CorrelatedLogger

class VideoExtractor:
    """Service for extracting video metadata using yt-dlp."""
    
    def __init__(self):
        self.logger = CorrelatedLogger(__name__)
    
    async def extract_metadata(
        self, 
        url: str, 
        include_thumbnail_analysis: bool = True,
        include_transcript: bool = False,
        request_id: Optional[str] = None
    ) -> VideoMetadata:
        """Extract metadata from a video URL."""
        start_time = datetime.now()
        
        # Set logger correlation ID
        if request_id:
            self.logger.request_id = request_id
        
        try:
            # Validate URL
            is_valid, platform = URLValidator.validate_and_get_platform(url)
            if not is_valid:
                raise VideoUnavailableError(url, f"Unsupported platform: {platform}")
            
            # Extract video info
            video_info = await self._extract_with_fallback(url)
            
            # Validate content type
            if not ContentValidator.is_video_content(video_info):
                content_type = ContentValidator.get_content_type(video_info)
                raise NotVideoContentError(url, content_type)
            
            # Process metadata
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            metadata = await self._create_metadata(
                url, platform, video_info, processing_time, include_thumbnail_analysis, include_transcript
            )
            
            self.logger.info(f"Successfully extracted metadata for: {url}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {url}: {str(e)}")
            if isinstance(e, (VideoUnavailableError, NotVideoContentError, ExtractionFailedError)):
                raise
            raise ExtractionFailedError(url, str(e))
    
    async def _extract_with_fallback(self, url: str) -> dict:
        """Extract video info with ScraperAPI fallback."""
        video_info = None
        
        # Try with ScraperAPI first if configured
        if settings.scraperapi_key:
            try:
                self.logger.info(f"Trying ScraperAPI for: {url}")
                video_info = await self._extract_with_scraperapi(url)
                self.logger.info(f"ScraperAPI extraction successful: {url}")
            except Exception as e:
                self.logger.warning(f"ScraperAPI approach failed for {url}: {str(e)}")
        
        # Fallback to direct yt-dlp
        if video_info is None:
            self.logger.info(f"Trying direct yt-dlp for: {url}")
            video_info = await self._extract_direct(url)
        
        return video_info
    
    async def _extract_with_scraperapi(self, url: str) -> dict:
        """Extract using ScraperAPI for IP rotation."""
        try:
            # Pre-warm URL with ScraperAPI
            scraperapi_url = f"{settings.scraperapi_base_url}?api_key={settings.scraperapi_key}&url={quote(url)}"
            
            response = await asyncio.to_thread(
                requests.get, 
                scraperapi_url, 
                timeout=settings.extraction_timeout
            )
            response.raise_for_status()
            
            # Now use yt-dlp normally
            return await self._extract_direct(url, retries=2)
            
        except requests.RequestException as e:
            raise ServiceUnavailableError("ScraperAPI", str(e))
        except asyncio.TimeoutError:
            raise TimeoutError("ScraperAPI pre-warm", settings.extraction_timeout)
    
    async def _extract_direct(self, url: str, retries: Optional[int] = None) -> dict:
        """Extract using yt-dlp directly."""
        ydl_opts = YTDLPConfig.get_options(
            timeout=settings.extraction_timeout,
            retries=retries or settings.retry_attempts
        )
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = await asyncio.to_thread(
                    ydl.extract_info, 
                    url, 
                    download=False
                )
                return video_info
                
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['private', 'deleted', 'unavailable', 'not found']):
                raise VideoUnavailableError(url, str(e))
            raise ExtractionFailedError(url, str(e))
        except Exception as e:
            raise ExtractionFailedError(url, str(e))
    
    async def _create_metadata(
        self,
        url: str,
        platform: str,
        video_info: dict,
        processing_time: int,
        include_thumbnail_analysis: bool,
        include_transcript: bool
    ) -> VideoMetadata:
        """Create VideoMetadata from extracted info."""
        
        # Get base description (will be enhanced with transcript if needed)
        base_description = video_info.get('description', '')
        
        # Get thumbnail analysis if requested
        thumbnail_analysis = None
        thumbnail_url = video_info.get('thumbnail', '')
        
        if thumbnail_url and include_thumbnail_analysis and settings.enable_thumbnail_analysis:
            # Import here to avoid circular imports
            from .thumbnail_analyzer import ThumbnailAnalyzer
            analyzer = ThumbnailAnalyzer()
            thumbnail_analysis = await analyzer.analyze_thumbnail(thumbnail_url, self.logger.request_id)
        
        # Process transcript if requested
        transcript_result = None
        has_transcript = None
        transcript_language = None
        transcript_confidence = None
        final_description = base_description
        
        if include_transcript:
            try:
                # Import here to avoid circular imports
                from .transcript_service import TranscriptService
                transcript_service = TranscriptService()
                
                # Extract transcript with service correlation ID
                transcript_result = await transcript_service.extract_transcript(
                    video_info, 
                    request_id=self.logger.request_id
                )
                
                if transcript_result.success and transcript_result.transcript:
                    has_transcript = True
                    transcript_language = transcript_result.transcript.language
                    transcript_confidence = transcript_result.transcript.confidence_score
                    
                    # Enhance description with transcript for backward compatibility
                    transcript_text = transcript_result.transcript.full_text
                    if transcript_text and transcript_text.strip():
                        final_description = f"{base_description}\n\nTranscript: {transcript_text}"
                    
                    self.logger.info(
                        f"Transcript extracted: {transcript_language}, "
                        f"confidence: {transcript_confidence:.2f}, "
                        f"words: {transcript_result.transcript.word_count}"
                    )
                else:
                    has_transcript = False
                    self.logger.info(
                        f"Transcript extraction failed: {transcript_result.error_message or 'Unknown error'}"
                    )
            except Exception as e:
                # Don't let transcript errors break metadata extraction
                has_transcript = False
                transcript_result = None
                self.logger.warning(f"Transcript processing failed with exception: {str(e)}")
        
        return VideoMetadata(
            url=url,
            platform=platform,
            title=video_info.get('title', ''),
            description=final_description,
            duration=video_info.get('duration', None),
            view_count=video_info.get('view_count', None),
            like_count=video_info.get('like_count', None),
            comment_count=video_info.get('comment_count', None),
            share_count=video_info.get('repost_count', None),
            upload_date=video_info.get('upload_date', ''),
            thumbnail_url=thumbnail_url,
            thumbnail_analysis=thumbnail_analysis,
            
            # Transcript fields
            transcript=transcript_result,
            has_transcript=has_transcript,
            transcript_language=transcript_language,
            transcript_confidence=transcript_confidence,
            
            extracted_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=processing_time,
            cache_hit=False  # Would be determined by cache layer
        )
