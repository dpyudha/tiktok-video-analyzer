"""
Simple tests for the ThumbnailAnalyzer service.
Basic functionality tests to ensure the service works correctly.
"""
import pytest
from unittest.mock import Mock, patch

from app.services.thumbnail_analyzer import ThumbnailAnalyzer
from app.config.schemas import AnalysisLanguage


class TestThumbnailAnalyzer:
    """Basic test cases for ThumbnailAnalyzer."""
    
    def test_analyzer_initialization_default(self):
        """Test analyzer initialization with default settings."""
        with patch('app.services.thumbnail_analyzer.get_template_engine'), \
             patch('app.services.thumbnail_analyzer.get_response_validator'):
            
            analyzer = ThumbnailAnalyzer()
            
            assert analyzer.language == AnalysisLanguage.INDONESIAN
    
    def test_analyzer_initialization_custom_language(self):
        """Test analyzer initialization with custom language."""
        with patch('app.services.thumbnail_analyzer.get_template_engine'), \
             patch('app.services.thumbnail_analyzer.get_response_validator'):
            
            analyzer = ThumbnailAnalyzer(language="en")
            
            assert analyzer.language == AnalysisLanguage.ENGLISH
    
    def test_analyzer_invalid_language_fallback(self):
        """Test analyzer falls back to default for invalid language."""
        with patch('app.services.thumbnail_analyzer.get_template_engine'), \
             patch('app.services.thumbnail_analyzer.get_response_validator'):
            
            analyzer = ThumbnailAnalyzer(language="invalid")
            
            assert analyzer.language == AnalysisLanguage.INDONESIAN
    
    @patch('app.services.thumbnail_analyzer.settings')
    def test_no_openai_key_returns_none(self, mock_settings):
        """Test that missing OpenAI key returns None."""
        mock_settings.openai_api_key = None
        
        with patch('app.services.thumbnail_analyzer.get_template_engine'), \
             patch('app.services.thumbnail_analyzer.get_response_validator'):
            
            analyzer = ThumbnailAnalyzer()
            
            # Since analyze_thumbnail is async, we test the client initialization
            assert analyzer.client is None