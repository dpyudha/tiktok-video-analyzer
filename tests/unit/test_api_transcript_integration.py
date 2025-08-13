"""Unit tests for API transcript integration."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.models.requests import ExtractRequest, ExtractBatchRequest
from app.models.video import VideoMetadata
from app.models.transcript import TranscriptExtractionResult, VideoTranscript, TranscriptSegment


class TestAPITranscriptIntegration:
    """Test API integration with transcript functionality."""
    
    @pytest.fixture
    def mock_video_extractor(self):
        """Mock VideoExtractor for API tests."""
        mock_extractor = AsyncMock()
        return mock_extractor
    
    @pytest.fixture
    def mock_cache_service(self):
        """Mock CacheService for API tests."""
        mock_cache = AsyncMock()
        mock_cache.get_video_metadata.return_value = None  # No cache hit by default
        return mock_cache
    
    @pytest.fixture
    def mock_batch_processor(self):
        """Mock BatchProcessor for API tests."""
        mock_processor = AsyncMock()
        return mock_processor
    
    @pytest.fixture
    def sample_metadata_with_transcript(self):
        """Sample VideoMetadata with transcript for testing."""
        segments = [
            TranscriptSegment(start_time=1.0, end_time=5.0, text="Hello world"),
            TranscriptSegment(start_time=5.0, end_time=10.0, text="How are you?")
        ]
        
        transcript = VideoTranscript(
            full_text="Hello world How are you?",
            language="en",
            confidence_score=0.88,
            segments=segments,
            generated_method="yt_dlp_manual_vtt",
            processing_time_ms=1200,
            word_count=5,
            duration_seconds=10.0
        )
        
        transcript_result = TranscriptExtractionResult(
            success=True,
            transcript=transcript,
            fallback_used=False
        )
        
        return VideoMetadata(
            url="https://tiktok.com/test",
            platform="tiktok",
            title="Test Video",
            description="Test description\n\nTranscript: Hello world How are you?",
            duration=60,
            view_count=1000,
            thumbnail_url="https://example.com/thumb.jpg",
            transcript=transcript_result,
            has_transcript=True,
            transcript_language="en",
            transcript_confidence=0.88,
            extracted_at="2024-03-15T10:30:00Z",
            processing_time_ms=3000
        )
    
    def test_extract_request_model_with_transcript(self):
        """Test ExtractRequest model validation with transcript parameter."""
        # Test with transcript enabled
        request_data = {
            "url": "https://tiktok.com/test",
            "include_thumbnail_analysis": True,
            "include_transcript": True,
            "cache_ttl": 3600
        }
        
        request = ExtractRequest(**request_data)
        
        assert str(request.url) == "https://tiktok.com/test"
        assert request.include_thumbnail_analysis is True
        assert request.include_transcript is True
        assert request.cache_ttl == 3600
    
    def test_extract_request_model_default_values(self):
        """Test ExtractRequest model with default values."""
        request_data = {
            "url": "https://tiktok.com/test"
        }
        
        request = ExtractRequest(**request_data)
        
        assert request.include_thumbnail_analysis is True  # Default
        assert request.include_transcript is False  # Default
        assert request.cache_ttl == 3600  # Default
    
    def test_extract_batch_request_model_with_transcript(self):
        """Test ExtractBatchRequest model validation with transcript parameter."""
        request_data = {
            "urls": [
                "https://tiktok.com/test1",
                "https://tiktok.com/test2"
            ],
            "include_thumbnail_analysis": False,
            "include_transcript": True,
            "parallel_processing": False
        }
        
        request = ExtractBatchRequest(**request_data)
        
        assert len(request.urls) == 2
        assert request.include_thumbnail_analysis is False
        assert request.include_transcript is True
        assert request.parallel_processing is False
    
    @pytest.mark.asyncio
    async def test_cache_service_integration_with_transcript(self):
        """Test cache service integration with transcript parameter."""
        from app.services.cache_service import CacheService
        
        cache_service = CacheService()
        
        # Test cache key generation with transcript parameter
        key_without_transcript = cache_service._generate_cache_key(
            "https://test.com", 
            include_thumbnail_analysis=True, 
            include_transcript=False
        )
        
        key_with_transcript = cache_service._generate_cache_key(
            "https://test.com", 
            include_thumbnail_analysis=True, 
            include_transcript=True
        )
        
        # Keys should be different
        assert key_without_transcript != key_with_transcript
        
        # Both should be valid cache keys
        assert key_without_transcript.startswith("video_metadata:")
        assert key_with_transcript.startswith("video_metadata:")
    
    @pytest.mark.asyncio
    async def test_batch_processor_with_transcript(self):
        """Test batch processor with transcript parameter."""
        from app.services.batch_processor import BatchProcessor
        from app.models.requests import ExtractBatchRequest
        
        # Create mock extractor
        mock_extractor = AsyncMock()
        mock_metadata = Mock(spec=VideoMetadata)
        mock_metadata.platform = "tiktok"
        mock_extractor.extract_metadata.return_value = mock_metadata
        
        # Mock the VideoExtractor class to return our mock
        with patch('app.services.batch_processor.VideoExtractor', return_value=mock_extractor):
            processor = BatchProcessor()
            
            request = ExtractBatchRequest(
                urls=["https://tiktok.com/test"],
                include_transcript=True,
                parallel_processing=False
            )
            
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', 
                      return_value=(True, 'tiktok')):
                
                result = await processor.process_batch(request, request_id="test-123")
                
                # Verify extract_metadata was called with transcript parameter
                mock_extractor.extract_metadata.assert_called_once_with(
                    "https://tiktok.com/test",
                    request.include_thumbnail_analysis,
                    request.include_transcript,  # Should pass transcript parameter
                    "test-123"
                )
                
                assert result.summary.total_requested == 1
    
    def test_video_metadata_response_serialization(self, sample_metadata_with_transcript):
        """Test VideoMetadata response serialization with transcript data."""
        # Test model_dump serialization (used in API responses)
        serialized = sample_metadata_with_transcript.model_dump()
        
        # Verify basic metadata fields
        assert serialized['url'] == "https://tiktok.com/test"
        assert serialized['platform'] == "tiktok"
        assert serialized['title'] == "Test Video"
        
        # Verify transcript-specific fields
        assert serialized['has_transcript'] is True
        assert serialized['transcript_language'] == "en"
        assert serialized['transcript_confidence'] == 0.88
        
        # Verify transcript object structure
        assert serialized['transcript']['success'] is True
        assert serialized['transcript']['fallback_used'] is False
        
        transcript_data = serialized['transcript']['transcript']
        assert transcript_data['language'] == "en"
        assert transcript_data['confidence_score'] == 0.88
        assert transcript_data['word_count'] == 5
        assert len(transcript_data['segments']) == 2
        
        # Verify segment structure
        first_segment = transcript_data['segments'][0]
        assert first_segment['start_time'] == 1.0
        assert first_segment['end_time'] == 5.0
        assert first_segment['text'] == "Hello world"
    
    def test_api_response_format_consistency(self, sample_metadata_with_transcript):
        """Test that API response format is consistent with and without transcript."""
        # Simulate API response creation
        from app.utils.response_helpers import ResponseHelper
        
        response = ResponseHelper.create_success_response(
            sample_metadata_with_transcript.model_dump(),
            request_id="test-123",
            processing_time_ms=3000
        )
        
        response_data = response.body
        import json
        parsed_response = json.loads(response_data)
        
        # Verify standard response structure
        assert parsed_response['success'] is True
        assert 'data' in parsed_response
        assert 'metadata' in parsed_response
        
        # Verify data contains transcript information
        data = parsed_response['data']
        assert data['has_transcript'] is True
        assert data['transcript_language'] == "en"
        assert data['transcript']['success'] is True
    
    @pytest.mark.asyncio
    async def test_api_endpoint_parameter_passing(self):
        """Test that API endpoints correctly pass transcript parameters."""
        from app.api.extraction import extract_single_video
        from app.models.requests import ExtractRequest
        
        # Mock dependencies
        mock_extractor = AsyncMock()
        mock_cache = AsyncMock()
        mock_cache.get_video_metadata.return_value = None  # No cache
        
        mock_metadata = Mock(spec=VideoMetadata)
        mock_metadata.platform = "tiktok"
        mock_metadata.model_dump.return_value = {"test": "data"}
        mock_extractor.extract_metadata.return_value = mock_metadata
        
        request = ExtractRequest(
            url="https://tiktok.com/test",
            include_transcript=True
        )
        
        # Call the endpoint function directly
        with patch('app.utils.response_helpers.ResponseHelper.generate_request_id', 
                  return_value="test-req-123"):
            with patch('app.utils.response_helpers.ResponseHelper.create_success_response') as mock_response:
                mock_response.return_value = Mock()
                
                await extract_single_video(
                    request=request,
                    api_key="test-key",
                    extractor=mock_extractor,
                    cache_service=mock_cache
                )
        
        # Verify extract_metadata was called with correct parameters
        mock_extractor.extract_metadata.assert_called_once()
        call_args = mock_extractor.extract_metadata.call_args
        
        assert call_args[0][0] == "https://tiktok.com/test"  # URL
        assert call_args[0][1] is True  # include_thumbnail_analysis (default)
        assert call_args[0][2] is True  # include_transcript
        assert call_args[0][3] == "test-req-123"  # request_id
    
    @pytest.mark.asyncio
    async def test_cache_hit_with_transcript(self, sample_metadata_with_transcript):
        """Test cache hit scenario with transcript data."""
        from app.api.extraction import extract_single_video
        from app.models.requests import ExtractRequest
        
        # Mock cache returning data with transcript
        mock_cache = AsyncMock()
        mock_cache.get_video_metadata.return_value = sample_metadata_with_transcript
        
        mock_extractor = AsyncMock()  # Should not be called
        
        request = ExtractRequest(
            url="https://tiktok.com/test",
            include_transcript=True
        )
        
        with patch('app.utils.response_helpers.ResponseHelper.generate_request_id', 
                  return_value="test-req-123"):
            with patch('app.utils.response_helpers.ResponseHelper.create_success_response') as mock_response:
                mock_response.return_value = Mock()
                
                await extract_single_video(
                    request=request,
                    api_key="test-key",
                    extractor=mock_extractor,
                    cache_service=mock_cache
                )
        
        # Verify cache was checked with correct parameters
        mock_cache.get_video_metadata.assert_called_once_with(
            "https://tiktok.com/test",
            True,  # include_thumbnail_analysis
            True   # include_transcript
        )
        
        # Verify extractor was not called (cache hit)
        mock_extractor.extract_metadata.assert_not_called()
    
    def test_error_response_structure_with_transcript_context(self):
        """Test error response structure when transcript extraction fails."""
        from app.core.exceptions import VideoUnavailableError
        from app.utils.response_helpers import ResponseHelper
        
        # Create an error that might occur during transcript extraction
        error = VideoUnavailableError("https://tiktok.com/test", "Video is private")
        
        response = ResponseHelper.create_error_from_exception(error, "test-req-123")
        
        response_data = response.body
        import json
        parsed_response = json.loads(response_data)
        
        # Verify error response structure
        assert parsed_response['success'] is False
        assert 'error' in parsed_response
        assert parsed_response['error']['code'] == 'VIDEO_UNAVAILABLE'
        assert 'metadata' in parsed_response
        assert parsed_response['metadata']['request_id'] == "test-req-123"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_with_transcript(self):
        """Test concurrent API requests with transcript processing."""
        import asyncio
        from app.services.video_extractor import VideoExtractor
        
        mock_video_info = {
            'title': 'Test Video',
            'description': 'Test',
            'duration': 30,
            'subtitles': {
                'en': [{'ext': 'vtt', 'data': 'WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nTest'}]
            }
        }
        
        extractor = VideoExtractor()
        
        with patch.object(extractor, '_extract_direct', return_value=mock_video_info):
            with patch('app.utils.validators.URLValidator.validate_and_get_platform', return_value=(True, 'tiktok')):
                with patch('app.utils.validators.ContentValidator.is_video_content', return_value=True):
                    
                    # Create multiple concurrent requests
                    tasks = []
                    for i in range(3):
                        task = extractor.extract_metadata(
                            f'https://tiktok.com/test{i}',
                            include_thumbnail_analysis=False,
                            include_transcript=True,
                            request_id=f'req-{i}'
                        )
                        tasks.append(task)
                    
                    # Execute concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # All should succeed
                    assert len(results) == 3
                    for result in results:
                        assert isinstance(result, VideoMetadata)
                        assert result.has_transcript is not None  # Transcript processing attempted
    
    def test_backwards_compatibility_without_transcript(self):
        """Test that existing API usage without transcript parameter still works."""
        # Test request model without transcript parameter
        request_data = {
            "url": "https://tiktok.com/test",
            "include_thumbnail_analysis": True,
            "cache_ttl": 1800
        }
        
        request = ExtractRequest(**request_data)
        
        # Should use default value for transcript
        assert request.include_transcript is False
        
        # Test batch request
        batch_request_data = {
            "urls": ["https://tiktok.com/test1", "https://tiktok.com/test2"],
            "parallel_processing": True
        }
        
        batch_request = ExtractBatchRequest(**batch_request_data)
        
        assert batch_request.include_transcript is False  # Default
        assert batch_request.include_thumbnail_analysis is True  # Default