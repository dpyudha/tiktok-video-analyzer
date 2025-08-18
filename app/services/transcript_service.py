"""Enhanced transcript extraction service using yt-dlp subtitle data."""
import re
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from app.core.config import settings
from app.core.exceptions import ExtractionFailedError, ServiceUnavailableError
from app.models.transcript import (
    TranscriptSegment, VideoTranscript, TranscriptQuality,
    SubtitleFormat, AvailableSubtitles, TranscriptExtractionResult
)
from app.utils.logging import CorrelatedLogger


class TranscriptService:
    """Service for extracting and processing video transcripts from yt-dlp subtitle data."""
    
    # Language preference order (Indonesian, English, then others)
    PREFERRED_LANGUAGES = ['id', 'en', 'en-US', 'en-GB']
    
    # Supported subtitle formats with processing capabilities
    SUPPORTED_FORMATS = {
        'vtt': {'priority': 1, 'has_timing': True},
        'srt': {'priority': 2, 'has_timing': True}, 
        'json3': {'priority': 3, 'has_timing': True},
        'srv1': {'priority': 4, 'has_timing': True},
        'srv2': {'priority': 5, 'has_timing': True},
        'srv3': {'priority': 6, 'has_timing': True},
        'ttml': {'priority': 7, 'has_timing': True},
    }
    
    def __init__(self):
        self.logger = CorrelatedLogger(__name__)
    
    async def extract_transcript(
        self,
        video_info: dict,
        preferred_language: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> TranscriptExtractionResult:
        """
        Extract transcript from yt-dlp video information.
        
        Args:
            video_info: Complete yt-dlp extraction result
            preferred_language: Preferred language code (defaults to 'id')
            request_id: Request correlation ID for logging
            
        Returns:
            TranscriptExtractionResult containing extracted transcript or error information
        """
        start_time = datetime.now()
        
        # Set logger correlation ID
        if request_id:
            self.logger.request_id = request_id
        
        try:
            # Analyze available subtitles
            available_subtitles = self._analyze_available_subtitles(video_info)
            
            if not available_subtitles.manual_subtitles and not available_subtitles.automatic_captions:
                return TranscriptExtractionResult(
                    success=False,
                    available_subtitles=available_subtitles,
                    error_message="No subtitles or captions available for this video",
                    fallback_used=False
                )
            
            # Determine target language
            target_language = preferred_language or settings.default_analysis_language or 'id'
            
            # Try to extract transcript with preference order
            transcript = await self._extract_best_transcript(
                video_info, available_subtitles, target_language
            )
            
            if not transcript:
                return TranscriptExtractionResult(
                    success=False,
                    available_subtitles=available_subtitles,
                    error_message="Failed to extract readable transcript from available subtitles",
                    fallback_used=True
                )
            
            # Assess transcript quality
            quality = self._assess_transcript_quality(transcript, video_info)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            transcript.processing_time_ms = processing_time
            
            self.logger.info(
                f"Successfully extracted transcript in {transcript.language} "
                f"({len(transcript.segments)} segments, {transcript.word_count} words)"
            )
            
            return TranscriptExtractionResult(
                success=True,
                transcript=transcript,
                available_subtitles=available_subtitles,
                quality_assessment=quality,
                fallback_used=transcript.generated_method.startswith('yt_dlp_auto')
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"Error extracting transcript: {str(e)}")
            
            return TranscriptExtractionResult(
                success=False,
                error_message=f"Transcript extraction failed: {str(e)}",
                fallback_used=False
            )
    
    def _analyze_available_subtitles(self, video_info: dict) -> AvailableSubtitles:
        """Analyze available subtitle formats and languages."""
        manual_subtitles = []
        automatic_captions = []
        
        # Process manual subtitles
        subtitles = video_info.get('subtitles', {})
        for lang_code, formats in subtitles.items():
            if isinstance(formats, list):
                for fmt in formats:
                    if isinstance(fmt, dict):
                        manual_subtitles.append(SubtitleFormat(
                            format_id=fmt.get('ext', 'unknown'),
                            language=lang_code,
                            is_automatic=False,
                            url=fmt.get('url'),
                            file_size=fmt.get('filesize')
                        ))
        
        # Process automatic captions
        auto_captions = video_info.get('automatic_captions', {})
        for lang_code, formats in auto_captions.items():
            if isinstance(formats, list):
                for fmt in formats:
                    if isinstance(fmt, dict):
                        automatic_captions.append(SubtitleFormat(
                            format_id=fmt.get('ext', 'unknown'),
                            language=lang_code,
                            is_automatic=True,
                            url=fmt.get('url'),
                            file_size=fmt.get('filesize')
                        ))
        
        # Determine preferred language based on availability
        all_languages = list(set([s.language for s in manual_subtitles + automatic_captions]))
        preferred_language = self._determine_preferred_language(all_languages)
        
        return AvailableSubtitles(
            manual_subtitles=manual_subtitles,
            automatic_captions=automatic_captions,
            preferred_language=preferred_language,
            total_languages=len(all_languages)
        )
    
    def _determine_preferred_language(self, available_languages: List[str]) -> Optional[str]:
        """Determine the best available language based on preferences."""
        for preferred in self.PREFERRED_LANGUAGES:
            if preferred in available_languages:
                return preferred
        
        # Return first available language if no preferred match
        return available_languages[0] if available_languages else None
    
    async def _extract_best_transcript(
        self,
        video_info: dict,
        available_subtitles: AvailableSubtitles,
        target_language: str
    ) -> Optional[VideoTranscript]:
        """Extract the best available transcript with language and format preferences."""
        
        # Priority 1: Manual subtitles in target language
        for subtitle in available_subtitles.manual_subtitles:
            if subtitle.language == target_language and subtitle.format_id in self.SUPPORTED_FORMATS:
                transcript = await self._extract_from_subtitle_format(
                    video_info, subtitle.language, subtitle.format_id, is_automatic=False
                )
                if transcript:
                    return transcript
        
        # Priority 2: Manual subtitles in preferred languages
        for lang in self.PREFERRED_LANGUAGES:
            for subtitle in available_subtitles.manual_subtitles:
                if subtitle.language == lang and subtitle.format_id in self.SUPPORTED_FORMATS:
                    transcript = await self._extract_from_subtitle_format(
                        video_info, subtitle.language, subtitle.format_id, is_automatic=False
                    )
                    if transcript:
                        return transcript
        
        # Priority 3: Auto captions in target language
        for subtitle in available_subtitles.automatic_captions:
            if subtitle.language == target_language and subtitle.format_id in self.SUPPORTED_FORMATS:
                transcript = await self._extract_from_subtitle_format(
                    video_info, subtitle.language, subtitle.format_id, is_automatic=True
                )
                if transcript:
                    return transcript
        
        # Priority 4: Auto captions in preferred languages
        for lang in self.PREFERRED_LANGUAGES:
            for subtitle in available_subtitles.automatic_captions:
                if subtitle.language == lang and subtitle.format_id in self.SUPPORTED_FORMATS:
                    transcript = await self._extract_from_subtitle_format(
                        video_info, subtitle.language, subtitle.format_id, is_automatic=True
                    )
                    if transcript:
                        return transcript
        
        # Priority 5: Any available manual subtitles
        sorted_manual = sorted(
            available_subtitles.manual_subtitles,
            key=lambda x: self.SUPPORTED_FORMATS.get(x.format_id, {}).get('priority', 999)
        )
        for subtitle in sorted_manual:
            transcript = await self._extract_from_subtitle_format(
                video_info, subtitle.language, subtitle.format_id, is_automatic=False
            )
            if transcript:
                return transcript
        
        # Priority 6: Any available auto captions
        sorted_auto = sorted(
            available_subtitles.automatic_captions,
            key=lambda x: self.SUPPORTED_FORMATS.get(x.format_id, {}).get('priority', 999)
        )
        for subtitle in sorted_auto:
            transcript = await self._extract_from_subtitle_format(
                video_info, subtitle.language, subtitle.format_id, is_automatic=True
            )
            if transcript:
                return transcript
        
        return None
    
    async def _extract_from_subtitle_format(
        self,
        video_info: dict,
        language: str,
        format_id: str,
        is_automatic: bool
    ) -> Optional[VideoTranscript]:
        """Extract transcript from specific subtitle format."""
        try:
            # Get subtitle data from video_info
            subtitle_source = video_info.get('automatic_captions' if is_automatic else 'subtitles', {})
            lang_subtitles = subtitle_source.get(language, [])
            
            if not lang_subtitles:
                return None
            
            # Find matching format
            subtitle_data = None
            for sub_format in lang_subtitles:
                if isinstance(sub_format, dict) and sub_format.get('ext') == format_id:
                    subtitle_data = sub_format
                    break
            
            if not subtitle_data:
                return None
            
            # Extract subtitle content
            content = None
            if 'data' in subtitle_data and subtitle_data['data']:
                # Direct data available
                content = subtitle_data['data']
            elif 'url' in subtitle_data and subtitle_data['url']:
                # Download from URL
                content = await self._download_subtitle_content(subtitle_data['url'])
            
            if not content:
                return None
            
            # Parse content based on format
            segments = self._parse_subtitle_content(content, format_id)
            if not segments:
                return None
            
            # Create full text
            full_text = ' '.join([seg.text for seg in segments])
            word_count = len(full_text.split())
            
            # Calculate duration
            duration_seconds = None
            if segments:
                duration_seconds = max(seg.end_time for seg in segments)
            
            # Determine generation method
            method_prefix = 'yt_dlp_auto' if is_automatic else 'yt_dlp_manual'
            generated_method = f"{method_prefix}_{format_id}"
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                segments, is_automatic, format_id, word_count
            )
            
            return VideoTranscript(
                full_text=full_text,
                language=language,
                confidence_score=confidence_score,
                segments=segments,
                generated_method=generated_method,
                processing_time_ms=0,  # Will be set by caller
                word_count=word_count,
                duration_seconds=duration_seconds
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to extract from {format_id} format in {language}: {str(e)}")
            return None
    
    async def _download_subtitle_content(self, url: str) -> Optional[str]:
        """Download subtitle content from URL."""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content
                    else:
                        self.logger.warning(f"Failed to download subtitle: HTTP {response.status}")
                        return None
        except Exception as e:
            self.logger.warning(f"Error downloading subtitle from {url}: {str(e)}")
            return None
    
    def _parse_subtitle_content(self, content: str, format_id: str) -> List[TranscriptSegment]:
        """Parse subtitle content based on format."""
        try:
            if format_id == 'vtt':
                return self._parse_vtt_content(content)
            elif format_id == 'srt':
                return self._parse_srt_content(content)
            elif format_id == 'json3':
                return self._parse_json3_content(content)
            elif format_id.startswith('srv'):
                return self._parse_youtube_srv_content(content)
            elif format_id == 'ttml':
                return self._parse_ttml_content(content)
            else:
                self.logger.warning(f"Unsupported subtitle format: {format_id}")
                return []
        except Exception as e:
            self.logger.error(f"Error parsing {format_id} content: {str(e)}")
            return []
    
    def _parse_vtt_content(self, content: str) -> List[TranscriptSegment]:
        """Parse WebVTT subtitle content."""
        segments = []
        
        # Split into blocks
        blocks = re.split(r'\n\n+', content)
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 2:
                continue
            
            # Look for time pattern
            time_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})'
            time_match = None
            text_start_idx = 0
            
            for i, line in enumerate(lines):
                match = re.search(time_pattern, line)
                if match:
                    time_match = match
                    text_start_idx = i + 1
                    break
            
            if time_match and text_start_idx < len(lines):
                start_time = self._vtt_time_to_seconds(time_match.group(1))
                end_time = self._vtt_time_to_seconds(time_match.group(2))
                
                # Combine remaining lines as text
                text = ' '.join(lines[text_start_idx:])
                text = self._clean_subtitle_text(text)
                
                if text.strip():
                    segments.append(TranscriptSegment(
                        start_time=start_time,
                        end_time=end_time,
                        text=text.strip()
                    ))
        
        return segments
    
    def _parse_srt_content(self, content: str) -> List[TranscriptSegment]:
        """Parse SRT subtitle content."""
        segments = []
        
        # Split into blocks
        blocks = re.split(r'\n\n+', content)
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            # SRT format: index, time, text...
            time_pattern = r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})'
            time_match = re.search(time_pattern, lines[1])
            
            if time_match:
                start_time = self._srt_time_to_seconds(time_match.group(1))
                end_time = self._srt_time_to_seconds(time_match.group(2))
                
                # Combine text lines
                text = ' '.join(lines[2:])
                text = self._clean_subtitle_text(text)
                
                if text.strip():
                    segments.append(TranscriptSegment(
                        start_time=start_time,
                        end_time=end_time,
                        text=text.strip()
                    ))
        
        return segments
    
    def _parse_json3_content(self, content: str) -> List[TranscriptSegment]:
        """Parse JSON3 subtitle content (YouTube specific)."""
        try:
            data = json.loads(content)
            segments = []
            
            events = data.get('events', [])
            for event in events:
                if 'tStartMs' in event and 'dDurationMs' in event:
                    start_time = event['tStartMs'] / 1000.0
                    duration = event['dDurationMs'] / 1000.0
                    end_time = start_time + duration
                    
                    # Extract text from segs
                    text_parts = []
                    for seg in event.get('segs', []):
                        if 'utf8' in seg:
                            text_parts.append(seg['utf8'])
                    
                    text = ''.join(text_parts)
                    text = self._clean_subtitle_text(text)
                    
                    if text.strip():
                        segments.append(TranscriptSegment(
                            start_time=start_time,
                            end_time=end_time,
                            text=text.strip()
                        ))
            
            return segments
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Error parsing JSON3 content: {str(e)}")
            return []
    
    def _parse_youtube_srv_content(self, content: str) -> List[TranscriptSegment]:
        """Parse YouTube SRV subtitle content."""
        try:
            # SRV formats are XML-based
            segments = []
            
            # Extract text elements with timing
            text_pattern = r'<text start="([^"]*)"(?:\s+dur="([^"]*)")?[^>]*>([^<]*)</text>'
            matches = re.findall(text_pattern, content)
            
            for match in matches:
                try:
                    start_time = float(match[0])
                    duration = float(match[1]) if match[1] else 3.0  # Default duration
                    end_time = start_time + duration
                    text = match[2]
                    
                    text = self._clean_subtitle_text(text)
                    
                    if text.strip():
                        segments.append(TranscriptSegment(
                            start_time=start_time,
                            end_time=end_time,
                            text=text.strip()
                        ))
                except (ValueError, IndexError):
                    continue
            
            return segments
        except Exception as e:
            self.logger.warning(f"Error parsing SRV content: {str(e)}")
            return []
    
    def _parse_ttml_content(self, content: str) -> List[TranscriptSegment]:
        """Parse TTML subtitle content."""
        try:
            segments = []
            
            # Extract p elements with timing
            p_pattern = r'<p[^>]*begin="([^"]*)"[^>]*end="([^"]*)"[^>]*>([^<]*)</p>'
            matches = re.findall(p_pattern, content)
            
            for match in matches:
                try:
                    start_time = self._ttml_time_to_seconds(match[0])
                    end_time = self._ttml_time_to_seconds(match[1])
                    text = match[2]
                    
                    text = self._clean_subtitle_text(text)
                    
                    if text.strip():
                        segments.append(TranscriptSegment(
                            start_time=start_time,
                            end_time=end_time,
                            text=text.strip()
                        ))
                except ValueError:
                    continue
            
            return segments
        except Exception as e:
            self.logger.warning(f"Error parsing TTML content: {str(e)}")
            return []
    
    def _vtt_time_to_seconds(self, time_str: str) -> float:
        """Convert VTT time format to seconds."""
        # Format: HH:MM:SS.mmm
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    
    def _srt_time_to_seconds(self, time_str: str) -> float:
        """Convert SRT time format to seconds."""
        # Format: HH:MM:SS,mmm
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split(',')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    
    def _ttml_time_to_seconds(self, time_str: str) -> float:
        """Convert TTML time format to seconds."""
        # Format can be: HH:MM:SS.mmm or just seconds
        if ':' in time_str:
            return self._vtt_time_to_seconds(time_str)
        else:
            # Direct seconds format
            return float(time_str.rstrip('s'))
    
    def _clean_subtitle_text(self, text: str) -> str:
        """Clean and normalize subtitle text."""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Unescape HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # Remove subtitle formatting artifacts
        text = re.sub(r'^\d+\s*', '', text)  # Remove leading numbers
        text = re.sub(r'♪.*?♪', '', text)    # Remove music notes
        text = re.sub(r'\[.*?\]', '', text)  # Remove sound descriptions
        text = re.sub(r'\(.*?\)', '', text)  # Remove parenthetical sounds
        
        # Remove excessive whitespace (after removing artifacts)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _calculate_confidence_score(
        self,
        segments: List[TranscriptSegment],
        is_automatic: bool,
        format_id: str,
        word_count: int
    ) -> float:
        """Calculate confidence score for transcript quality."""
        base_score = 0.6 if is_automatic else 0.8
        
        # Format quality bonus
        format_bonus = self.SUPPORTED_FORMATS.get(format_id, {}).get('priority', 999)
        format_score = max(0, (10 - format_bonus) / 10 * 0.1)
        
        # Length quality (longer transcripts generally better)
        length_score = min(word_count / 100, 1.0) * 0.1
        
        # Segment quality (good timing distribution)
        segment_score = 0
        if segments:
            avg_duration = sum(s.end_time - s.start_time for s in segments) / len(segments)
            if 1.0 <= avg_duration <= 5.0:  # Reasonable segment length
                segment_score = 0.1
        
        final_score = base_score + format_score + length_score + segment_score
        return min(final_score, 1.0)
    
    def _assess_transcript_quality(
        self,
        transcript: VideoTranscript,
        video_info: dict
    ) -> TranscriptQuality:
        """Assess the quality of extracted transcript."""
        
        # Check timing information
        has_timing_info = len(transcript.segments) > 0 and all(
            seg.start_time is not None and seg.end_time is not None 
            for seg in transcript.segments
        )
        
        # Check punctuation
        punctuation_chars = set('.,!?;:')
        has_punctuation = any(char in transcript.full_text for char in punctuation_chars)
        
        # Estimate completeness based on video duration
        completeness_score = 1.0
        video_duration = video_info.get('duration')
        if video_duration and transcript.duration_seconds:
            coverage_ratio = transcript.duration_seconds / video_duration
            completeness_score = min(coverage_ratio, 1.0)
        
        # Readability based on word count and sentence structure
        readability_score = 0.5
        if transcript.word_count > 10:
            sentences = len(re.split(r'[.!?]+', transcript.full_text))
            if sentences > 0:
                avg_words_per_sentence = transcript.word_count / sentences
                if 5 <= avg_words_per_sentence <= 20:
                    readability_score = 0.8
                elif avg_words_per_sentence <= 30:
                    readability_score = 0.6
        
        return TranscriptQuality(
            has_timing_info=has_timing_info,
            has_punctuation=has_punctuation,
            completeness_score=completeness_score,
            readability_score=readability_score
        )