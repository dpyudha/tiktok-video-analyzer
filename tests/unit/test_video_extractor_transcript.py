"""Unit tests for VideoExtractor transcript integration."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from app.services.video_extractor import VideoExtractor
from app.models.video import VideoMetadata
from app.models.transcript import TranscriptExtractionResult, VideoTranscript, TranscriptSegment


class TestVideoExtractorTranscript:
    """Test cases for VideoExtractor transcript integration."""
    
    @pytest.fixture
    def video_extractor(self):
        """Create a VideoExtractor instance."""
        return VideoExtractor()
    
    @pytest.fixture
    def mock_video_info_with_subtitles(self):
        """Mock yt-dlp video info with subtitles."""
        return {
            'title': 'Test Video with Subtitles',
            'description': 'A test video description',
            'duration': 60,
            'view_count': 10000,
            'like_count': 500,
            'comment_count': 25,
            'repost_count': 50,
            'upload_date': '20240315',
            'thumbnail': 'https://example.com/thumbnail.jpg',
            'subtitles': {
                'en': [{
                    'ext': 'vtt',
                    'url': 'https://example.com/subtitles.vtt',
                    'data': self._get_sample_vtt_content()
                }]
            },
            'automatic_captions': {}
        }
    
    @pytest.fixture
    def mock_successful_transcript_result(self):
        """Mock successful transcript extraction result."""
        segments = [
            TranscriptSegment(start_time=1.0, end_time=5.0, text="Hello and welcome"),
            TranscriptSegment(start_time=5.0, end_time=10.0, text="to this tutorial")
        ]
        
        transcript = VideoTranscript(
            full_text="Hello and welcome to this tutorial",
            language="en",
            confidence_score=0.85,
            segments=segments,
            generated_method="yt_dlp_manual_vtt",
            processing_time_ms=1500,
            word_count=6,
            duration_seconds=10.0
        )
        
        return TranscriptExtractionResult(
            success=True,
            transcript=transcript,
            fallback_used=False
        )
    
    def _get_sample_vtt_content(self):
        """Sample VTT content for testing."""
        return """WEBVTT

00:00:01.000 --> 00:00:05.000
Hello and welcome

00:00:05.000 --> 00:00:10.000
to this tutorial"""
    
    @pytest.mark.asyncio
    async def test_extract_metadata_without_transcript(self, video_extractor, mock_video_info_with_subtitles):
        """Test metadata extraction without transcript processing."""
        with patch.object(video_extractor, '_extract_direct', return_value=mock_video_info_with_subtitles):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    
                    metadata = await video_extractor.extract_metadata(
                        'https://tiktok.com/test',
                        include_thumbnail_analysis=False,
                        include_transcript=False
                    )
                    
                    assert isinstance(metadata, VideoMetadata)
                    assert metadata.title == 'Test Video with Subtitles'
                    assert metadata.transcript is None
                    assert metadata.has_transcript is None
                    assert metadata.transcript_language is None
                    assert metadata.transcript_confidence is None
                    
                    # Description should be original without transcript
                    assert metadata.description == 'A test video description'
    
    @pytest.mark.asyncio
    async def test_extract_metadata_with_transcript_success(
        self, 
        video_extractor, 
        mock_video_info_with_subtitles,
        mock_successful_transcript_result
    ):
        """Test metadata extraction with successful transcript processing."""
        with patch.object(video_extractor, '_extract_direct', return_value=mock_video_info_with_subtitles):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    with patch('app.services.transcript_service.TranscriptService.extract_transcript', 
                              return_value=mock_successful_transcript_result) as mock_transcript:
                        
                        metadata = await video_extractor.extract_metadata(
                            'https://tiktok.com/test',
                            include_thumbnail_analysis=False,
                            include_transcript=True,
                            request_id='test-123'
                        )
                        
                        # Verify transcript service was called
                        mock_transcript.assert_called_once_with(mock_video_info_with_subtitles, request_id='test-123')
                        
                        # Verify metadata includes transcript data
                        assert isinstance(metadata, VideoMetadata)
                        assert metadata.transcript == mock_successful_transcript_result
                        assert metadata.has_transcript is True
                        assert metadata.transcript_language == 'en'
                        assert metadata.transcript_confidence == 0.85
                        
                        # Description should include transcript
                        assert 'A test video description' in metadata.description
                        assert 'Transcript: Hello and welcome to this tutorial' in metadata.description
    
    @pytest.mark.asyncio
    async def test_extract_metadata_with_transcript_failure(self, video_extractor, mock_video_info_with_subtitles):
        """Test metadata extraction when transcript processing fails."""
        failed_transcript_result = TranscriptExtractionResult(
            success=False,
            transcript=None,
            error_message="No subtitles available",
            fallback_used=False
        )
        
        with patch.object(video_extractor, '_extract_direct', return_value=mock_video_info_with_subtitles):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    with patch('app.services.transcript_service.TranscriptService.extract_transcript', 
                              return_value=failed_transcript_result):
                        
                        metadata = await video_extractor.extract_metadata(
                            'https://tiktok.com/test',
                            include_thumbnail_analysis=False,
                            include_transcript=True
                        )
                        
                        # Verify metadata without transcript data
                        assert isinstance(metadata, VideoMetadata)
                        assert metadata.transcript == failed_transcript_result
                        assert metadata.has_transcript is False
                        assert metadata.transcript_language is None
                        assert metadata.transcript_confidence is None
                        
                        # Description should be original without transcript enhancement
                        assert metadata.description == 'A test video description'
    
    @pytest.mark.asyncio
    async def test_extract_metadata_with_empty_transcript(self, video_extractor, mock_video_info_with_subtitles):
        """Test metadata extraction when transcript is empty."""
        empty_transcript = VideoTranscript(
            full_text="",
            language="en",
            confidence_score=0.1,
            segments=[],
            generated_method="yt_dlp_manual_vtt",
            processing_time_ms=100,
            word_count=0,
            duration_seconds=0.0
        )
        
        empty_transcript_result = TranscriptExtractionResult(
            success=True,
            transcript=empty_transcript,
            fallback_used=False
        )
        
        with patch.object(video_extractor, '_extract_direct', return_value=mock_video_info_with_subtitles):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    with patch('app.services.transcript_service.TranscriptService.extract_transcript', 
                              return_value=empty_transcript_result):
                        
                        metadata = await video_extractor.extract_metadata(
                            'https://tiktok.com/test',
                            include_thumbnail_analysis=False,
                            include_transcript=True
                        )
                        
                        # Verify metadata includes transcript but description isn't enhanced
                        assert metadata.transcript == empty_transcript_result
                        assert metadata.has_transcript is True
                        assert metadata.transcript_language == 'en'
                        assert metadata.transcript_confidence == 0.1
                        
                        # Description should not include empty transcript
                        assert metadata.description == 'A test video description'
    
    @pytest.mark.asyncio
    async def test_create_metadata_logging(self, video_extractor, mock_video_info_with_subtitles):
        """Test that transcript extraction logging works correctly."""
        mock_logger = Mock()
        video_extractor.logger = mock_logger
        
        mock_transcript_result = TranscriptExtractionResult(
            success=True,
            transcript=VideoTranscript(
                full_text="Test transcript",
                language="id",
                confidence_score=0.92,
                segments=[],
                generated_method="yt_dlp_auto_json3",
                processing_time_ms=800,
                word_count=2,
                duration_seconds=5.0
            ),
            fallback_used=True
        )
        
        with patch('app.services.transcript_service.TranscriptService.extract_transcript', 
                  return_value=mock_transcript_result):
            
            metadata = await video_extractor._create_metadata(
                'https://test.com/video',
                'tiktok',
                mock_video_info_with_subtitles,
                processing_time=2000,
                include_thumbnail_analysis=False,
                include_transcript=True
            )
            
            # Verify logging was called for successful transcript
            mock_logger.info.assert_called()
            logged_message = mock_logger.info.call_args[0][0]
            assert 'Transcript extracted: id' in logged_message
            assert 'confidence: 0.92' in logged_message
            assert 'words: 2' in logged_message
    
    @pytest.mark.asyncio
    async def test_create_metadata_with_both_features(
        self, 
        video_extractor, 
        mock_video_info_with_subtitles,
        mock_successful_transcript_result
    ):
        """Test metadata creation with both thumbnail analysis and transcript."""
        from app.models.video import ThumbnailAnalysis
        mock_thumbnail_analysis = ThumbnailAnalysis(
            visual_style="talking_head",
            confidence_score=0.78
        )
        
        with patch('app.services.thumbnail_analyzer.ThumbnailAnalyzer.analyze_thumbnail',
                  return_value=mock_thumbnail_analysis):
            with patch('app.services.transcript_service.TranscriptService.extract_transcript',
                      return_value=mock_successful_transcript_result):
                with patch('app.core.config.settings.enable_thumbnail_analysis', True):
                    
                    metadata = await video_extractor._create_metadata(
                        'https://test.com/video',
                        'tiktok',
                        mock_video_info_with_subtitles,
                        processing_time=3000,
                        include_thumbnail_analysis=True,
                        include_transcript=True
                    )
                    
                    # Verify both features are included
                    assert metadata.thumbnail_analysis == mock_thumbnail_analysis
                    assert metadata.transcript == mock_successful_transcript_result
                    assert metadata.has_transcript is True
                    assert metadata.transcript_language == 'en'
                    assert metadata.transcript_confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self, video_extractor, mock_video_info_with_subtitles):
        """Test that existing API calls without transcript parameter still work."""
        with patch.object(video_extractor, '_extract_direct', return_value=mock_video_info_with_subtitles):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    
                    # Test old-style call without include_transcript parameter
                    metadata = await video_extractor.extract_metadata(
                        'https://tiktok.com/test',
                        include_thumbnail_analysis=False
                        # include_transcript parameter omitted (defaults to False)
                    )
                    
                    assert isinstance(metadata, VideoMetadata)
                    assert metadata.transcript is None
                    assert metadata.has_transcript is None
                    assert metadata.transcript_language is None
                    assert metadata.transcript_confidence is None
    
    @pytest.mark.asyncio
    async def test_transcript_with_correlation_id(self, video_extractor, mock_video_info_with_subtitles):
        """Test that correlation ID is properly passed to transcript service."""
        mock_transcript_service = AsyncMock()
        mock_transcript_service.extract_transcript.return_value = TranscriptExtractionResult(
            success=False,
            transcript=None,
            error_message="Test error"
        )
        
        with patch.object(video_extractor, '_extract_direct', return_value=mock_video_info_with_subtitles):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    with patch('app.services.transcript_service.TranscriptService', return_value=mock_transcript_service):
                        
                        await video_extractor.extract_metadata(
                            'https://tiktok.com/test',
                            include_thumbnail_analysis=False,
                            include_transcript=True,
                            request_id='correlation-abc-123'
                        )
                        
                        # Verify transcript service was called with correlation ID
                        mock_transcript_service.extract_transcript.assert_called_once_with(
                            mock_video_info_with_subtitles, 
                            request_id='correlation-abc-123'
                        )
    
    @pytest.mark.asyncio
    async def test_extract_metadata_exception_handling(self, video_extractor, mock_video_info_with_subtitles):
        """Test that transcript service exceptions don't break metadata extraction."""
        def transcript_exception(*args, **kwargs):
            raise Exception("Transcript service error")
        
        with patch.object(video_extractor, '_extract_direct', return_value=mock_video_info_with_subtitles):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    with patch('app.services.transcript_service.TranscriptService.extract_transcript', 
                              side_effect=transcript_exception):
                        
                        # Should not raise exception, should continue with metadata extraction
                        metadata = await video_extractor.extract_metadata(
                            'https://tiktok.com/test',
                            include_thumbnail_analysis=False,
                            include_transcript=True
                        )
                        
                        # Basic metadata should still be extracted
                        assert isinstance(metadata, VideoMetadata)
                        assert metadata.title == 'Test Video with Subtitles'
                        assert metadata.transcript is None  # Failed transcript extraction
                        assert metadata.has_transcript is False


class TestVideoExtractorTranscriptIntegration:
    """Integration tests for VideoExtractor with transcript functionality."""
    
    @pytest.fixture
    def video_extractor(self):
        return VideoExtractor()
    
    def test_video_metadata_serialization_with_transcript(self):
        """Test that VideoMetadata with transcript can be serialized correctly."""
        segments = [
            TranscriptSegment(start_time=0.0, end_time=3.0, text="Test segment")
        ]
        
        transcript = VideoTranscript(
            full_text="Test segment",
            language="en",
            confidence_score=0.85,
            segments=segments,
            generated_method="yt_dlp_manual_vtt",
            processing_time_ms=1000,
            word_count=2,
            duration_seconds=3.0
        )
        
        transcript_result = TranscriptExtractionResult(
            success=True,
            transcript=transcript,
            fallback_used=False
        )
        
        metadata = VideoMetadata(
            url="https://test.com/video",
            platform="tiktok",
            title="Test Video",
            transcript=transcript_result,
            has_transcript=True,
            transcript_language="en",
            transcript_confidence=0.85
        )
        
        # Test serialization
        serialized = metadata.model_dump()
        
        assert serialized['transcript']['success'] is True
        assert serialized['transcript']['transcript']['language'] == 'en'
        assert serialized['transcript']['transcript']['word_count'] == 2
        assert serialized['has_transcript'] is True
        assert serialized['transcript_language'] == 'en'
        assert serialized['transcript_confidence'] == 0.85
        
        # Test deserialization
        reconstructed = VideoMetadata(**serialized)
        assert reconstructed.has_transcript is True
        assert reconstructed.transcript.transcript.language == 'en'