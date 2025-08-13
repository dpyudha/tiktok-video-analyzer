"""Transcript-related data models."""
from typing import Optional, List
from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """Individual transcript segment with timing information."""
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Segment text content")
    confidence: Optional[float] = Field(None, description="Confidence score for this segment (0.0-1.0)")


class VideoTranscript(BaseModel):
    """Complete video transcript with timing and metadata."""
    full_text: str = Field(..., description="Complete transcript text")
    language: str = Field(..., description="Detected or specified language code (e.g., 'en', 'id')")
    confidence_score: float = Field(..., description="Overall confidence score (0.0-1.0)")
    segments: List[TranscriptSegment] = Field(default=[], description="Individual transcript segments with timing")
    generated_method: str = Field(..., description="Method used: 'yt_dlp_manual', 'yt_dlp_auto', 'whisper_api', 'whisper_local'")
    processing_time_ms: int = Field(..., description="Time taken to process transcript in milliseconds")
    word_count: int = Field(..., description="Total word count in transcript")
    duration_seconds: Optional[float] = Field(None, description="Total duration covered by transcript")


class TranscriptQuality(BaseModel):
    """Transcript quality assessment."""
    has_timing_info: bool = Field(..., description="Whether segments have accurate timing")
    has_punctuation: bool = Field(..., description="Whether text includes proper punctuation")
    completeness_score: float = Field(..., description="Estimated completeness (0.0-1.0)")
    readability_score: float = Field(..., description="Text readability assessment (0.0-1.0)")


class SubtitleFormat(BaseModel):
    """Individual subtitle format information."""
    format_id: str = Field(..., description="Format identifier (e.g., 'vtt', 'srt', 'json3')")
    language: str = Field(..., description="Language code")
    is_automatic: bool = Field(..., description="Whether subtitles are auto-generated")
    url: Optional[str] = Field(None, description="Download URL for subtitle file")
    file_size: Optional[int] = Field(None, description="File size in bytes")


class AvailableSubtitles(BaseModel):
    """Available subtitle information for a video."""
    manual_subtitles: List[SubtitleFormat] = Field(default=[], description="Human-created subtitles")
    automatic_captions: List[SubtitleFormat] = Field(default=[], description="Auto-generated captions")
    preferred_language: Optional[str] = Field(None, description="Detected preferred language")
    total_languages: int = Field(0, description="Total number of available languages")


class TranscriptExtractionResult(BaseModel):
    """Result of transcript extraction attempt."""
    success: bool = Field(..., description="Whether extraction was successful")
    transcript: Optional[VideoTranscript] = Field(None, description="Extracted transcript if successful")
    available_subtitles: Optional[AvailableSubtitles] = Field(None, description="Available subtitle information")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")
    fallback_used: bool = Field(False, description="Whether fallback method was used")
    quality_assessment: Optional[TranscriptQuality] = Field(None, description="Quality assessment of transcript")