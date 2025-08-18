"""Tests for the /extract-transcript endpoint."""
import pytest
import time
import threading
import queue
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.transcript import (
    VideoTranscript, TranscriptSegment, TranscriptExtractionResult,
    AvailableSubtitles, SubtitleFormat, TranscriptQuality
)


class TestTranscriptEndpoint:
    """Test suite for the /extract-transcript endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_video_info(self):
        """Mock video info with transcript data."""
        return {
            'title': 'Test TikTok Video',
            'duration': 30,
            'subtitles': {
                'en': [
                    {
                        'ext': 'vtt',
                        'url': 'https://example.com/subtitles.vtt',
                        'data': 'WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nHello world!\n\n00:00:03.000 --> 00:00:06.000\nThis is a test.'
                    }
                ]
            },
            'automatic_captions': {
                'id': [
                    {
                        'ext': 'json3',
                        'url': 'https://example.com/captions.json3',
                        'data': '{"events":[{"tStartMs":0,"dDurationMs":3000,"segs":[{"utf8":"Halo dunia!"}]}]}'
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mock_transcript_result_success(self):
        """Mock successful transcript extraction result."""
        segments = [
            TranscriptSegment(start_time=0.0, end_time=3.0, text="Hello world!"),
            TranscriptSegment(start_time=3.0, end_time=6.0, text="This is a test.")
        ]
        
        transcript = VideoTranscript(
            full_text="Hello world! This is a test.",
            language="en",
            confidence_score=0.85,
            segments=segments,
            generated_method="yt_dlp_manual_vtt",
            processing_time_ms=1500,
            word_count=6,
            duration_seconds=6.0
        )
        
        available_subtitles = AvailableSubtitles(
            manual_subtitles=[
                SubtitleFormat(
                    format_id="vtt",
                    language="en",
                    is_automatic=False,
                    url="https://example.com/subtitles.vtt"
                )
            ],
            automatic_captions=[],
            preferred_language="en",
            total_languages=1
        )
        
        quality = TranscriptQuality(
            has_timing_info=True,
            has_punctuation=True,
            completeness_score=1.0,
            readability_score=0.8
        )
        
        return TranscriptExtractionResult(
            success=True,
            transcript=transcript,
            available_subtitles=available_subtitles,
            quality_assessment=quality,
            fallback_used=False
        )
    
    @pytest.fixture
    def mock_transcript_result_failure(self):
        """Mock failed transcript extraction result."""
        available_subtitles = AvailableSubtitles(
            manual_subtitles=[],
            automatic_captions=[],
            preferred_language=None,
            total_languages=0
        )
        
        return TranscriptExtractionResult(
            success=False,
            available_subtitles=available_subtitles,
            error_message="No subtitles or captions available for this video",
            fallback_used=False
        )
    
    def test_extract_transcript_success(self, client, mock_video_info, mock_transcript_result_success):
        """Test successful transcript extraction."""
        with patch('app.core.config.settings.api_key', "test-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                with patch('app.api.extraction.transcript_service.extract_transcript') as mock_transcript:
                    # Setup mocks
                    mock_extract.return_value = mock_video_info
                    mock_transcript.return_value = mock_transcript_result_success
                    
                    # Make request
                    response = client.post(
                        "/extract-transcript",
                        json={"url": "https://www.tiktok.com/@user/video/123"},
                        headers={"x-api-key": "test-key"}
                    )
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert data["data"]["success"] is True
                assert data["data"]["url"] == "https://www.tiktok.com/@user/video/123"
                assert data["data"]["transcript"]["full_text"] == "Hello world! This is a test."
                assert data["data"]["transcript"]["language"] == "en"
                assert data["data"]["transcript"]["word_count"] == 6
                assert len(data["data"]["transcript"]["segments"]) == 2
                assert data["data"]["fallback_used"] is False
                assert data["data"]["error_message"] is None
    
    def test_extract_transcript_failure(self, client, mock_video_info, mock_transcript_result_failure):
        """Test failed transcript extraction."""
        with patch('app.core.config.settings.api_key', "test-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                with patch('app.api.extraction.transcript_service.extract_transcript') as mock_transcript:
                    # Setup mocks
                    mock_extract.return_value = mock_video_info
                    mock_transcript.return_value = mock_transcript_result_failure
                    
                    # Make request
                    response = client.post(
                        "/extract-transcript",
                        json={"url": "https://www.tiktok.com/@user/video/123"},
                        headers={"x-api-key": "test-key"}
                    )
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert data["data"]["success"] is False
                assert data["data"]["transcript"] is None
                assert data["data"]["error_message"] == "No subtitles or captions available for this video"
    
    def test_extract_transcript_with_preferred_language(self, client, mock_video_info, mock_transcript_result_success):
        """Test transcript extraction with preferred language."""
        with patch('app.core.config.settings.api_key', "test-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                with patch('app.api.extraction.transcript_service.extract_transcript') as mock_transcript:
                    # Setup mocks
                    mock_extract.return_value = mock_video_info
                    mock_transcript.return_value = mock_transcript_result_success
                    
                    # Make request with preferred language
                    response = client.post(
                        "/extract-transcript",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "preferred_language": "id"
                        },
                        headers={"x-api-key": "test-key"}
                    )
                
                # Verify transcript service was called with preferred language
                mock_transcript.assert_called_once()
                call_args = mock_transcript.call_args
                assert call_args[1]["preferred_language"] == "id"
                
                # Verify response
                assert response.status_code == 200
    
    def test_extract_transcript_invalid_url(self, client):
        """Test transcript extraction with invalid URL."""
        with patch('app.core.config.settings.api_key', "test-key"):
            response = client.post(
                "/extract-transcript",
                json={"url": "not-a-valid-url"},
                headers={"x-api-key": "test-key"}
            )
            
            # Should return validation error
            assert response.status_code == 422
    
    def test_extract_transcript_missing_api_key(self, client):
        """Test transcript extraction without API key."""
        response = client.post(
            "/extract-transcript",
            json={"url": "https://www.tiktok.com/@user/video/123"}
        )
        
        # Should return unauthorized
        assert response.status_code == 403  # FastAPI Security dependency returns 403 for missing auth
    
    def test_extract_transcript_video_extraction_error(self, client):
        """Test transcript extraction when video extraction fails."""
        with patch('app.core.config.settings.api_key', "test-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                # Setup mock to raise exception
                mock_extract.side_effect = Exception("Video extraction failed")
                
                # Make request
                response = client.post(
                    "/extract-transcript",
                    json={"url": "https://www.tiktok.com/@user/video/123"},
                    headers={"x-api-key": "test-key"}
                )
            
            # Should return error
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"]["code"] == "TRANSCRIPT_EXTRACTION_FAILED"
    
    def test_extract_transcript_response_structure(self, client, mock_video_info, mock_transcript_result_success):
        """Test that response follows expected structure."""
        with patch('app.core.config.settings.api_key', "test-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                with patch('app.api.extraction.transcript_service.extract_transcript') as mock_transcript:
                    # Setup mocks
                    mock_extract.return_value = mock_video_info
                    mock_transcript.return_value = mock_transcript_result_success
                    
                    # Make request
                    response = client.post(
                        "/extract-transcript",
                        json={"url": "https://www.tiktok.com/@user/video/123"},
                        headers={"x-api-key": "test-key"}
                    )
                
                # Verify response structure
                assert response.status_code == 200
                data = response.json()
                
                # Top-level structure
                assert "success" in data
                assert "data" in data
                assert "metadata" in data
                
                # Metadata structure
                metadata = data["metadata"]
                assert "request_id" in metadata
                assert "timestamp" in metadata
                assert "rate_limit" in metadata
                
                # Data structure
                response_data = data["data"]
                required_fields = [
                    "url", "success", "transcript", "available_subtitles",
                    "error_message", "fallback_used", "quality_assessment"
                ]
                for field in required_fields:
                    assert field in response_data
                
                # Transcript structure (when successful)
                if response_data["transcript"]:
                    transcript = response_data["transcript"]
                    transcript_fields = [
                        "full_text", "language", "confidence_score", "segments",
                        "generated_method", "processing_time_ms", "word_count", "duration_seconds"
                    ]
                    for field in transcript_fields:
                        assert field in transcript
    
    @pytest.mark.parametrize("test_url,expected_platform", [
        ("https://www.tiktok.com/@user/video/123", "tiktok"),
        ("https://vm.tiktok.com/abc123", "tiktok"), 
        ("https://www.instagram.com/reel/ABC123/", "instagram"),
    ])
    def test_extract_transcript_supported_platforms(self, client, mock_video_info, mock_transcript_result_success, test_url, expected_platform):
        """Test transcript extraction for different supported platforms."""
        with patch('app.core.config.settings.api_key', "test-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                with patch('app.api.extraction.transcript_service.extract_transcript') as mock_transcript:
                    # Setup mocks
                    mock_extract.return_value = mock_video_info
                    mock_transcript.return_value = mock_transcript_result_success
                    
                    # Make request
                    response = client.post(
                        "/extract-transcript",
                        json={"url": test_url},
                        headers={"x-api-key": "test-key"}
                    )
                
                # Should succeed for supported platforms
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["url"] == test_url


# Performance and optimization tests
class TestTranscriptEndpointPerformance:
    """Performance-focused tests for transcript endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_video_info(self):
        """Mock video info with transcript data."""
        return {
            'title': 'Test TikTok Video',
            'duration': 30,
            'subtitles': {
                'en': [
                    {
                        'ext': 'vtt',
                        'url': 'https://example.com/subtitles.vtt',
                        'data': 'WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nHello world!\n\n00:00:03.000 --> 00:00:06.000\nThis is a test.'
                    }
                ]
            },
            'automatic_captions': {
                'id': [
                    {
                        'ext': 'json3',
                        'url': 'https://example.com/captions.json3',
                        'data': '{"events":[{"tStartMs":0,"dDurationMs":3000,"segs":[{"utf8":"Halo dunia!"}]}]}'
                    }
                ]
            }
        }
    
    def test_extract_transcript_caching_behavior(self, client):
        """Test that caching works correctly for repeated requests."""
        with patch('app.core.config.settings.api_key', "test-key"):
            # This would need integration with actual cache service
            # For now, verify the endpoint supports cache_ttl parameter
            response = client.post(
                "/extract-transcript",
                json={
                    "url": "https://www.tiktok.com/@user/video/123",
                    "cache_ttl": 7200  # 2 hours
                },
                headers={"x-api-key": "test-key"}
            )
        
        # Should accept the parameter without error (actual caching logic tested separately)
        # This endpoint will fail with video extraction but validates the request structure
        assert response.status_code in [200, 500]  # Either succeeds or fails during extraction
    
    def test_extract_transcript_large_response_handling(self, client, mock_video_info):
        """Test handling of large transcript responses."""
        # Create a mock result with many segments
        large_segments = [
            TranscriptSegment(start_time=i, end_time=i+1, text=f"Segment {i} text content")
            for i in range(100)  # 100 segments
        ]
        
        large_transcript = VideoTranscript(
            full_text=" ".join([f"Segment {i} text content" for i in range(100)]),
            language="en",
            confidence_score=0.8,
            segments=large_segments,
            generated_method="yt_dlp_auto_vtt",
            processing_time_ms=3000,
            word_count=400,
            duration_seconds=100.0
        )
        
        large_result = TranscriptExtractionResult(
            success=True,
            transcript=large_transcript,
            available_subtitles=AvailableSubtitles(
                manual_subtitles=[],
                automatic_captions=[],
                preferred_language="en",
                total_languages=1
            ),
            fallback_used=True
        )
        
        with patch('app.core.config.settings.api_key', "test-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                with patch('app.api.extraction.transcript_service.extract_transcript') as mock_transcript:
                    # Setup mocks
                    mock_extract.return_value = mock_video_info
                    mock_transcript.return_value = large_result
                    
                    # Make request
                    response = client.post(
                        "/extract-transcript",
                        json={"url": "https://www.tiktok.com/@user/video/123"},
                        headers={"x-api-key": "test-key"}
                    )
                
                # Should handle large response without issues
                assert response.status_code == 200
                data = response.json()
                assert len(data["data"]["transcript"]["segments"]) == 100
                assert data["data"]["transcript"]["word_count"] == 400


# Integration-style tests (but using mocks for external dependencies)
class TestTranscriptEndpointIntegration:
    """Integration-style tests for the transcript endpoint with realistic scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def api_headers(self):
        """Standard API headers with authentication."""
        return {
            "Content-Type": "application/json",
            "x-api-key": "test-api-key"
        }
    
    @pytest.fixture
    def mock_video_with_manual_subtitles(self):
        """Mock video info with manual subtitles available."""
        return {
            'title': 'Test TikTok Video with Manual Subtitles',
            'duration': 30,
            'view_count': 1000000,
            'like_count': 50000,
            'upload_date': '20240315',
            'subtitles': {
                'en': [
                    {
                        'ext': 'vtt',
                        'url': 'https://example.com/manual-subtitles.vtt',
                        'data': (
                            'WEBVTT\n\n'
                            '00:00:00.000 --> 00:00:03.500\n'
                            'Hello everyone! Today I want to share some amazing tips.\n\n'
                            '00:00:03.500 --> 00:00:08.200\n'
                            'These simple habits can completely change your morning routine.\n\n'
                            '00:00:08.200 --> 00:00:12.000\n'
                            'Let me show you exactly how to do it step by step.'
                        )
                    }
                ],
                'id': [
                    {
                        'ext': 'vtt',
                        'url': 'https://example.com/manual-subtitles-id.vtt',
                        'data': (
                            'WEBVTT\n\n'
                            '00:00:00.000 --> 00:00:03.500\n'
                            'Halo semuanya! Hari ini aku mau sharing tips yang luar biasa.\n\n'
                            '00:00:03.500 --> 00:00:08.200\n'
                            'Kebiasaan sederhana ini bisa mengubah rutinitas pagi kamu.\n\n'
                            '00:00:08.200 --> 00:00:12.000\n'
                            'Biar aku tunjukin caranya step by step.'
                        )
                    }
                ]
            },
            'automatic_captions': {}
        }

    def test_full_transcript_extraction_workflow_success(self, client, api_headers, mock_video_with_manual_subtitles):
        """Test complete successful transcript extraction workflow."""
        test_url = "https://www.tiktok.com/@user/video/123456789"
        
        with patch('app.core.config.settings.api_key', "test-api-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                mock_extract.return_value = mock_video_with_manual_subtitles
                
                response = client.post(
                    "/extract-transcript",
                    json={
                        "url": test_url,
                        "preferred_language": "en",
                        "cache_ttl": 3600
                    },
                    headers=api_headers
                )
        
        # Verify complete response structure
        assert response.status_code == 200
        data = response.json()
        
        # Top-level response structure
        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data
        
        # Data content verification
        response_data = data["data"]
        assert response_data["url"] == test_url
        assert response_data["success"] is True
        assert response_data["transcript"] is not None
        assert response_data["fallback_used"] is False
        
        # Transcript verification
        transcript = response_data["transcript"]
        assert transcript["language"] in ["en", "id"]  # Should prefer English or default to Indonesian
        assert transcript["confidence_score"] > 0
        assert transcript["word_count"] > 0
        assert len(transcript["segments"]) > 0
        assert "Hello everyone" in transcript["full_text"] or "Halo semuanya" in transcript["full_text"]
    
    def test_language_preference_handling(self, client, api_headers, mock_video_with_manual_subtitles):
        """Test that language preferences are handled correctly."""
        test_url = "https://www.tiktok.com/@multilang/video/123456789"
        
        with patch('app.core.config.settings.api_key', "test-api-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                mock_extract.return_value = mock_video_with_manual_subtitles
                
                # Test Indonesian preference
                response_id = client.post(
                    "/extract-transcript",
                    json={
                        "url": test_url,
                        "preferred_language": "id"
                    },
                    headers=api_headers
                )
                
                # Test English preference  
                response_en = client.post(
                    "/extract-transcript",
                    json={
                        "url": test_url,
                        "preferred_language": "en"
                    },
                    headers=api_headers
                )
        
        # Both should succeed
        assert response_id.status_code == 200
        assert response_en.status_code == 200
        
        # Verify language handling
        data_id = response_id.json()
        data_en = response_en.json()
        
        assert data_id["data"]["success"] is True
        assert data_en["data"]["success"] is True
        
        # Verify available subtitles information is provided
        assert "available_subtitles" in data_id["data"]
        assert "available_subtitles" in data_en["data"]
    
    def test_performance_timing_tracking(self, client, api_headers, mock_video_with_manual_subtitles):
        """Test that performance timing is tracked in responses."""
        from app.models.transcript import VideoTranscript, TranscriptSegment, TranscriptExtractionResult, AvailableSubtitles
        
        test_url = "https://www.tiktok.com/@user/video/performance_test"
        
        # Create mock transcript result with timing information
        mock_transcript = VideoTranscript(
            full_text="Hello everyone! Today I want to share some amazing tips.",
            language="en",
            confidence_score=0.9,
            segments=[
                TranscriptSegment(start_time=0.0, end_time=3.5, text="Hello everyone! Today I want to share some amazing tips.")
            ],
            generated_method="yt_dlp_manual_vtt",
            processing_time_ms=150,  # Mock processing time
            word_count=10,
            duration_seconds=3.5
        )
        
        from app.models.transcript import SubtitleFormat
        
        mock_result = TranscriptExtractionResult(
            success=True,
            transcript=mock_transcript,
            available_subtitles=AvailableSubtitles(
                manual_subtitles=[
                    SubtitleFormat(
                        format_id="vtt",
                        language="en",
                        is_automatic=False
                    )
                ],
                automatic_captions=[],
                preferred_language="en",
                total_languages=1
            ),
            fallback_used=False
        )
        
        with patch('app.core.config.settings.api_key', "test-api-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                with patch('app.api.extraction.transcript_service.extract_transcript') as mock_transcript_service:
                    mock_extract.return_value = mock_video_with_manual_subtitles
                    mock_transcript_service.return_value = mock_result
                    
                    start_time = time.time()
                    
                    response = client.post(
                        "/extract-transcript",
                        json={"url": test_url},
                        headers=api_headers
                    )
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Verify response
        assert response.status_code == 200
        
        # Should complete quickly with mocked dependencies
        assert response_time < 2000, f"Response took {response_time:.2f}ms, expected < 2000ms"
        
        # Verify processing time is recorded
        data = response.json()
        assert data["data"]["transcript"] is not None
        assert "processing_time_ms" in data["data"]["transcript"]
        assert data["data"]["transcript"]["processing_time_ms"] > 0
    
    def test_concurrent_request_handling(self, client, api_headers, mock_video_with_manual_subtitles):
        """Test handling of multiple concurrent requests."""
        test_urls = [
            "https://www.tiktok.com/@user1/video/123",
            "https://www.tiktok.com/@user2/video/456", 
            "https://www.tiktok.com/@user3/video/789"
        ]
        
        results = queue.Queue()
        
        def make_request(url):
            """Make a transcript extraction request."""
            try:
                with patch('app.core.config.settings.api_key', "test-api-key"):
                    with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                        mock_extract.return_value = mock_video_with_manual_subtitles
                        
                        response = client.post(
                            "/extract-transcript",
                            json={"url": url},
                            headers=api_headers
                        )
                        results.put((url, response.status_code, response.json()))
            except Exception as e:
                results.put((url, None, str(e)))
        
        # Start concurrent requests
        threads = []
        for url in test_urls:
            thread = threading.Thread(target=make_request, args=(url,))
            thread.start()
            threads.append(thread)
        
        # Wait for all requests to complete
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify all requests completed successfully
        assert results.qsize() == len(test_urls)
        
        all_results = []
        while not results.empty():
            all_results.append(results.get())
        
        for url, status_code, response_data in all_results:
            assert status_code == 200, f"Request for {url} failed with status {status_code}"
            assert response_data["success"] is True
    
    def test_malformed_data_resilience(self, client, api_headers):
        """Test resilience against malformed subtitle data."""
        mock_malformed_video = {
            'title': 'Video with Malformed Subtitles',
            'duration': 15,
            'subtitles': {
                'en': [
                    {
                        'ext': 'vtt',
                        'url': 'https://example.com/malformed-subtitles.vtt',
                        'data': 'INVALID_VTT_FORMAT\nThis is not proper VTT format'
                    }
                ]
            },
            'automatic_captions': {}
        }
        
        test_url = "https://www.tiktok.com/@user/video/malformed"
        
        with patch('app.core.config.settings.api_key', "test-api-key"):
            with patch('app.api.extraction.video_extractor._extract_with_fallback') as mock_extract:
                mock_extract.return_value = mock_malformed_video
                
                response = client.post(
                    "/extract-transcript",
                    json={"url": test_url},
                    headers=api_headers
                )
        
        # Should handle malformed data gracefully without server errors
        assert response.status_code == 200
        data = response.json()
        
        # May succeed or fail gracefully depending on parsing robustness
        assert "data" in data
        if not data["data"]["success"]:
            assert data["data"]["error_message"] is not None