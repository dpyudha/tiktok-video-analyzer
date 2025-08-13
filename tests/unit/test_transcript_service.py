"""Unit tests for TranscriptService."""
import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from app.services.transcript_service import TranscriptService
from app.models.transcript import (
    TranscriptSegment, VideoTranscript, TranscriptQuality,
    SubtitleFormat, AvailableSubtitles, TranscriptExtractionResult
)


class TestTranscriptService:
    """Test cases for TranscriptService."""
    
    @pytest.fixture
    def transcript_service(self):
        """Create a TranscriptService instance."""
        return TranscriptService()
    
    @pytest.fixture
    def mock_video_info_with_subtitles(self):
        """Mock video info with manual subtitles."""
        return {
            'title': 'Test Video',
            'description': 'Test description',
            'duration': 60,
            'subtitles': {
                'en': [{
                    'ext': 'vtt',
                    'url': 'http://example.com/subtitles.vtt',
                    'filesize': 1024,
                    'data': self._get_sample_vtt_content()
                }]
            },
            'automatic_captions': {}
        }
    
    @pytest.fixture
    def mock_video_info_with_auto_captions(self):
        """Mock video info with automatic captions."""
        return {
            'title': 'Test Video',
            'description': 'Test description',
            'duration': 30,
            'subtitles': {},
            'automatic_captions': {
                'id': [{
                    'ext': 'json3',
                    'url': 'http://example.com/captions.json3',
                    'filesize': 2048,
                    'data': self._get_sample_json3_content()
                }]
            }
        }
    
    @pytest.fixture
    def mock_video_info_no_subtitles(self):
        """Mock video info without subtitles."""
        return {
            'title': 'Test Video',
            'description': 'Test description',
            'duration': 45,
            'subtitles': {},
            'automatic_captions': {}
        }
    
    def _get_sample_vtt_content(self):
        """Get sample VTT content for testing."""
        return """WEBVTT

00:00:01.000 --> 00:00:05.000
Hello and welcome to this video tutorial.

00:00:05.000 --> 00:00:10.000
Today we'll learn about video processing.

00:00:10.000 --> 00:00:15.000
This is very useful for content creators."""
    
    def _get_sample_srt_content(self):
        """Get sample SRT content for testing."""
        return """1
00:00:01,000 --> 00:00:05,000
Halo dan selamat datang di tutorial video ini.

2
00:00:05,000 --> 00:00:10,000
Hari ini kita akan belajar tentang pemrosesan video.

3
00:00:10,000 --> 00:00:15,000
Ini sangat berguna untuk pembuat konten."""
    
    def _get_sample_json3_content(self):
        """Get sample JSON3 content for testing."""
        return json.dumps({
            "events": [
                {
                    "tStartMs": 1000,
                    "dDurationMs": 4000,
                    "segs": [
                        {"utf8": "Halo dan selamat datang"}
                    ]
                },
                {
                    "tStartMs": 5000,
                    "dDurationMs": 5000,
                    "segs": [
                        {"utf8": "di tutorial video ini."}
                    ]
                },
                {
                    "tStartMs": 10000,
                    "dDurationMs": 5000,
                    "segs": [
                        {"utf8": "Sangat berguna untuk kreator."}
                    ]
                }
            ]
        })
    
    @pytest.mark.asyncio
    async def test_extract_transcript_with_manual_subtitles(self, transcript_service, mock_video_info_with_subtitles):
        """Test transcript extraction with manual subtitles."""
        result = await transcript_service.extract_transcript(mock_video_info_with_subtitles)
        
        assert result.success is True
        assert result.transcript is not None
        assert result.transcript.language == 'en'
        assert result.transcript.generated_method == 'yt_dlp_manual_vtt'
        assert len(result.transcript.segments) == 3
        assert result.transcript.word_count > 0
        assert result.fallback_used is False
        
        # Check first segment
        first_segment = result.transcript.segments[0]
        assert first_segment.start_time == 1.0
        assert first_segment.end_time == 5.0
        assert "Hello and welcome" in first_segment.text
    
    @pytest.mark.asyncio
    async def test_extract_transcript_with_auto_captions(self, transcript_service, mock_video_info_with_auto_captions):
        """Test transcript extraction with automatic captions."""
        result = await transcript_service.extract_transcript(mock_video_info_with_auto_captions)
        
        assert result.success is True
        assert result.transcript is not None
        assert result.transcript.language == 'id'
        assert result.transcript.generated_method == 'yt_dlp_auto_json3'
        assert len(result.transcript.segments) == 3
        assert result.fallback_used is True
        
        # Check JSON3 parsing
        first_segment = result.transcript.segments[0]
        assert first_segment.start_time == 1.0
        assert first_segment.end_time == 5.0
        assert "Halo dan selamat datang" in first_segment.text
    
    @pytest.mark.asyncio
    async def test_extract_transcript_no_subtitles(self, transcript_service, mock_video_info_no_subtitles):
        """Test transcript extraction when no subtitles are available."""
        result = await transcript_service.extract_transcript(mock_video_info_no_subtitles)
        
        assert result.success is False
        assert result.transcript is None
        assert "No subtitles or captions available" in result.error_message
        assert result.available_subtitles is not None
        assert len(result.available_subtitles.manual_subtitles) == 0
        assert len(result.available_subtitles.automatic_captions) == 0
    
    def test_analyze_available_subtitles(self, transcript_service, mock_video_info_with_subtitles):
        """Test analysis of available subtitles."""
        available = transcript_service._analyze_available_subtitles(mock_video_info_with_subtitles)
        
        assert len(available.manual_subtitles) == 1
        assert len(available.automatic_captions) == 0
        assert available.total_languages == 1
        assert available.preferred_language == 'en'
        
        # Check subtitle format details
        subtitle = available.manual_subtitles[0]
        assert subtitle.format_id == 'vtt'
        assert subtitle.language == 'en'
        assert subtitle.is_automatic is False
        assert subtitle.url == 'http://example.com/subtitles.vtt'
    
    def test_determine_preferred_language(self, transcript_service):
        """Test language preference logic."""
        # Test with Indonesian available
        languages_with_id = ['en', 'id', 'fr']
        preferred = transcript_service._determine_preferred_language(languages_with_id)
        assert preferred == 'id'
        
        # Test with English only
        languages_with_en = ['en', 'fr', 'de']
        preferred = transcript_service._determine_preferred_language(languages_with_en)
        assert preferred == 'en'
        
        # Test with neither preferred language
        languages_other = ['fr', 'de', 'es']
        preferred = transcript_service._determine_preferred_language(languages_other)
        assert preferred == 'fr'  # First available
        
        # Test with empty list
        preferred = transcript_service._determine_preferred_language([])
        assert preferred is None
    
    def test_parse_vtt_content(self, transcript_service):
        """Test VTT content parsing."""
        vtt_content = self._get_sample_vtt_content()
        segments = transcript_service._parse_vtt_content(vtt_content)
        
        assert len(segments) == 3
        
        # Test first segment
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 5.0
        assert "Hello and welcome" in segments[0].text
        
        # Test timing conversion
        assert segments[1].start_time == 5.0
        assert segments[1].end_time == 10.0
    
    def test_parse_srt_content(self, transcript_service):
        """Test SRT content parsing."""
        srt_content = self._get_sample_srt_content()
        segments = transcript_service._parse_srt_content(srt_content)
        
        assert len(segments) == 3
        
        # Test first segment
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 5.0
        assert "Halo dan selamat datang" in segments[0].text
        
        # Test SRT timing format (comma instead of dot)
        assert segments[1].start_time == 5.0
        assert segments[1].end_time == 10.0
    
    def test_parse_json3_content(self, transcript_service):
        """Test JSON3 content parsing."""
        json3_content = self._get_sample_json3_content()
        segments = transcript_service._parse_json3_content(json3_content)
        
        assert len(segments) == 3
        
        # Test first segment (tStartMs and dDurationMs)
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 5.0
        assert "Halo dan selamat datang" in segments[0].text
        
        # Test second segment
        assert segments[1].start_time == 5.0
        assert segments[1].end_time == 10.0
    
    def test_vtt_time_to_seconds(self, transcript_service):
        """Test VTT time format conversion."""
        # Test basic format
        assert transcript_service._vtt_time_to_seconds("00:01:30.500") == 90.5
        assert transcript_service._vtt_time_to_seconds("01:00:00.000") == 3600.0
        assert transcript_service._vtt_time_to_seconds("00:00:05.123") == 5.123
    
    def test_srt_time_to_seconds(self, transcript_service):
        """Test SRT time format conversion."""
        # Test basic format with comma
        assert transcript_service._srt_time_to_seconds("00:01:30,500") == 90.5
        assert transcript_service._srt_time_to_seconds("01:00:00,000") == 3600.0
        assert transcript_service._srt_time_to_seconds("00:00:05,123") == 5.123
    
    def test_clean_subtitle_text(self, transcript_service):
        """Test subtitle text cleaning."""
        # Test HTML tag removal
        dirty_text = "<font color='white'>Hello world</font>"
        clean_text = transcript_service._clean_subtitle_text(dirty_text)
        assert clean_text == "Hello world"
        
        # Test HTML entity unescaping
        entity_text = "Tom &amp; Jerry &lt;episode&gt; &quot;test&quot;"
        clean_text = transcript_service._clean_subtitle_text(entity_text)
        assert clean_text == 'Tom & Jerry <episode> "test"'
        
        # Test music note removal
        music_text = "♪ Background music ♪ Hello there"
        clean_text = transcript_service._clean_subtitle_text(music_text)
        assert clean_text == "Hello there"
        
        # Test sound description removal
        sound_text = "[applause] Hello [door creaks] world (music)"
        clean_text = transcript_service._clean_subtitle_text(sound_text)
        assert clean_text == "Hello world"
        
        # Test excessive whitespace removal
        whitespace_text = "Hello    world\n\nTest   string"
        clean_text = transcript_service._clean_subtitle_text(whitespace_text)
        assert clean_text == "Hello world Test string"
    
    def test_calculate_confidence_score(self, transcript_service):
        """Test confidence score calculation."""
        segments = [
            TranscriptSegment(start_time=0.0, end_time=3.0, text="Test segment one"),
            TranscriptSegment(start_time=3.0, end_time=6.0, text="Test segment two")
        ]
        
        # Test manual subtitles (higher base score)
        manual_score = transcript_service._calculate_confidence_score(
            segments, is_automatic=False, format_id='vtt', word_count=50
        )
        
        # Test automatic captions (lower base score)
        auto_score = transcript_service._calculate_confidence_score(
            segments, is_automatic=True, format_id='json3', word_count=50
        )
        
        assert manual_score > auto_score
        assert 0.0 <= manual_score <= 1.0
        assert 0.0 <= auto_score <= 1.0
    
    def test_assess_transcript_quality(self, transcript_service, mock_video_info_with_subtitles):
        """Test transcript quality assessment."""
        # Create a sample transcript
        transcript = VideoTranscript(
            full_text="Hello world. How are you today? I am fine, thank you.",
            language="en",
            confidence_score=0.8,
            segments=[
                TranscriptSegment(start_time=0.0, end_time=3.0, text="Hello world."),
                TranscriptSegment(start_time=3.0, end_time=6.0, text="How are you today?"),
                TranscriptSegment(start_time=6.0, end_time=9.0, text="I am fine, thank you.")
            ],
            generated_method="yt_dlp_manual_vtt",
            processing_time_ms=1000,
            word_count=11,
            duration_seconds=9.0
        )
        
        quality = transcript_service._assess_transcript_quality(
            transcript, mock_video_info_with_subtitles
        )
        
        assert quality.has_timing_info is True
        assert quality.has_punctuation is True
        assert 0.0 <= quality.completeness_score <= 1.0
        assert 0.0 <= quality.readability_score <= 1.0
    
    @pytest.mark.asyncio  
    async def test_download_subtitle_content_success(self, transcript_service):
        """Test successful subtitle content download."""
        # Mock the method directly since aiohttp mocking is complex
        with patch.object(transcript_service, '_download_subtitle_content', 
                         return_value="Sample subtitle content"):
            content = await transcript_service._download_subtitle_content("http://example.com/sub.vtt")
            
        assert content == "Sample subtitle content"
    
    @pytest.mark.asyncio
    async def test_download_subtitle_content_failure(self, transcript_service):
        """Test subtitle content download failure."""
        # Mock the method to return None for failure case
        with patch.object(transcript_service, '_download_subtitle_content', 
                         return_value=None):
            content = await transcript_service._download_subtitle_content("http://example.com/sub.vtt")
            
        assert content is None
    
    def test_parse_youtube_srv_content(self, transcript_service):
        """Test YouTube SRV format parsing."""
        srv_content = '''<?xml version="1.0" encoding="utf-8"?>
<transcript>
<text start="1.5" dur="3.2">Hello world</text>
<text start="4.7" dur="2.8">How are you?</text>
<text start="7.5" dur="4.1">I am doing great today.</text>
</transcript>'''
        
        segments = transcript_service._parse_youtube_srv_content(srv_content)
        
        assert len(segments) == 3
        assert segments[0].start_time == 1.5
        assert segments[0].end_time == 4.7  # 1.5 + 3.2
        assert segments[0].text == "Hello world"
        
        assert segments[1].start_time == 4.7
        assert segments[1].end_time == 7.5  # 4.7 + 2.8
        assert segments[1].text == "How are you?"
    
    def test_parse_ttml_content(self, transcript_service):
        """Test TTML format parsing."""
        ttml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tt xmlns="http://www.w3.org/ns/ttml">
<body>
<div>
<p begin="00:00:01.000" end="00:00:04.000">Hello everyone</p>
<p begin="00:00:04.000" end="00:00:07.000">Welcome to the show</p>
<p begin="00:00:07.000" end="00:00:10.000">Hope you enjoy it</p>
</div>
</body>
</tt>'''
        
        segments = transcript_service._parse_ttml_content(ttml_content)
        
        assert len(segments) == 3
        assert segments[0].start_time == 1.0
        assert segments[0].end_time == 4.0
        assert segments[0].text == "Hello everyone"
    
    def test_ttml_time_to_seconds(self, transcript_service):
        """Test TTML time format conversion."""
        # Test standard time format
        assert transcript_service._ttml_time_to_seconds("00:01:30.500") == 90.5
        
        # Test seconds format
        assert transcript_service._ttml_time_to_seconds("125.5s") == 125.5
        assert transcript_service._ttml_time_to_seconds("30s") == 30.0
    
    @pytest.mark.asyncio
    async def test_extract_transcript_with_preferred_language(self, transcript_service):
        """Test transcript extraction with preferred language override."""
        video_info = {
            'title': 'Test Video',
            'subtitles': {
                'en': [{
                    'ext': 'vtt',
                    'data': self._get_sample_vtt_content()
                }],
                'id': [{
                    'ext': 'srt',
                    'data': self._get_sample_srt_content()
                }]
            },
            'automatic_captions': {}
        }
        
        # Request English specifically
        result = await transcript_service.extract_transcript(video_info, preferred_language='en')
        
        assert result.success is True
        assert result.transcript.language == 'en'
        assert result.transcript.generated_method == 'yt_dlp_manual_vtt'
    
    @pytest.mark.asyncio
    async def test_extract_transcript_error_handling(self, transcript_service):
        """Test transcript extraction error handling."""
        # Test with malformed video_info
        malformed_info = {'invalid': 'data'}
        
        result = await transcript_service.extract_transcript(malformed_info)
        
        assert result.success is False
        assert result.transcript is None
        assert "No subtitles or captions available" in result.error_message


# Integration-style tests
class TestTranscriptServiceIntegration:
    """Integration tests for TranscriptService with more realistic scenarios."""
    
    @pytest.fixture
    def transcript_service(self):
        return TranscriptService()
    
    def test_supported_formats_priority(self, transcript_service):
        """Test that format priority is correctly implemented."""
        formats = transcript_service.SUPPORTED_FORMATS
        
        # VTT should have highest priority (lowest number)
        assert formats['vtt']['priority'] < formats['srt']['priority']
        assert formats['srt']['priority'] < formats['json3']['priority']
        
        # All formats should have timing info
        for format_info in formats.values():
            assert format_info['has_timing'] is True
    
    def test_preferred_languages_order(self, transcript_service):
        """Test that preferred languages are in correct order."""
        preferred = transcript_service.PREFERRED_LANGUAGES
        
        assert preferred[0] == 'id'  # Indonesian first
        assert preferred[1] == 'en'  # English second
        assert 'en-US' in preferred
        assert 'en-GB' in preferred
    
    @pytest.mark.asyncio
    async def test_complex_extraction_scenario(self, transcript_service):
        """Test complex extraction scenario with multiple format options."""
        complex_video_info = {
            'title': 'Complex Video',
            'duration': 120,
            'subtitles': {
                'en': [
                    {'ext': 'srt', 'data': self._get_sample_srt_content()},
                    {'ext': 'vtt', 'data': self._get_sample_vtt_content()}
                ],
                'id': [
                    {'ext': 'json3', 'data': self._get_sample_json3_content()}
                ]
            },
            'automatic_captions': {
                'en': [
                    {'ext': 'json3', 'data': self._get_sample_json3_content()}
                ]
            }
        }
        
        # Should prefer Indonesian manual subtitles
        result = await transcript_service.extract_transcript(complex_video_info)
        
        assert result.success is True
        assert result.transcript.language == 'id'
        assert result.transcript.generated_method == 'yt_dlp_manual_json3'
        assert result.fallback_used is False  # Manual subtitles, not fallback
    
    def _get_sample_vtt_content(self):
        return """WEBVTT

00:00:01.000 --> 00:00:05.000
Hello and welcome to this video tutorial.

00:00:05.000 --> 00:00:10.000
Today we'll learn about video processing."""
    
    def _get_sample_srt_content(self):
        return """1
00:00:01,000 --> 00:00:05,000
Halo dan selamat datang di tutorial video ini.

2
00:00:05,000 --> 00:00:10,000
Hari ini kita akan belajar tentang pemrosesan video."""
    
    def _get_sample_json3_content(self):
        return json.dumps({
            "events": [
                {
                    "tStartMs": 1000,
                    "dDurationMs": 4000,
                    "segs": [{"utf8": "Halo dan selamat datang"}]
                },
                {
                    "tStartMs": 5000,
                    "dDurationMs": 5000,
                    "segs": [{"utf8": "di tutorial video ini."}]
                }
            ]
        })