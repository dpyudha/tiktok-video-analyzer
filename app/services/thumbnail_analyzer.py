"""Thumbnail analysis service using OpenAI Vision API."""
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from openai import OpenAI

from ..core.config import settings
from ..core.exceptions import ThumbnailAnalysisError, ConfigurationError
from ..models.video import ThumbnailAnalysis
from ..utils.logging import CorrelatedLogger
from ..config.templates import get_template_engine
from ..config.schemas import (
    get_response_validator, 
    AnalysisLanguage, 
    AnalysisValidationError,
    ThumbnailAnalysisResponse
)

class ThumbnailAnalyzer:
    """Service for analyzing video thumbnails using OpenAI Vision API."""
    
    def __init__(self, language: str = "id"):
        self.client = self._initialize_client()
        self.logger = CorrelatedLogger(__name__)
        self.language = AnalysisLanguage(language) if language in ["id", "en"] else AnalysisLanguage.INDONESIAN
        self.template_engine = get_template_engine()
        self.validator = get_response_validator()
        
        self.logger.info(f"ThumbnailAnalyzer initialized with language: {self.language.value}")
    
    def _initialize_client(self) -> Optional[OpenAI]:
        """Initialize OpenAI client if API key is configured."""
        if not settings.openai_api_key:
            return None
        
        try:
            return OpenAI(api_key=settings.openai_api_key)
        except Exception as e:
            raise ConfigurationError("OpenAI client", str(e))
    
    async def analyze_thumbnail(
        self, 
        thumbnail_url: str, 
        request_id: Optional[str] = None,
        language: Optional[str] = None
    ) -> Optional[ThumbnailAnalysis]:
        """Analyze thumbnail using OpenAI Vision API with configurable prompts."""
        if not self.client or not thumbnail_url:
            return None
        
        # Set logger correlation ID
        if request_id:
            self.logger.request_id = request_id
        
        # Use specified language or instance default
        analysis_language = AnalysisLanguage(language) if language in ["id", "en"] else self.language
        
        start_time = datetime.now()
        
        try:
            self.logger.info(
                f"Starting thumbnail analysis for: {thumbnail_url} "
                f"(language: {analysis_language.value})"
            )
            
            # Generate prompt using template engine
            prompt_text = self.template_engine.render_prompt(
                analysis_type="thumbnail_analysis",
                language=analysis_language.value
            )
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o",
                messages=self._create_analysis_prompt(thumbnail_url, prompt_text),
                max_tokens=1200,  # Increased for more detailed analysis
                temperature=0.1   # Lower temperature for more consistent results
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            content = response.choices[0].message.content
            if not content:
                self.logger.warning(f"OpenAI response content is None for: {thumbnail_url}")
                return self._create_legacy_fallback()
            
            # Parse and validate response using new validation system
            validated_response = self._parse_and_validate_response(
                content, analysis_language, thumbnail_url
            )
            
            # Convert to legacy ThumbnailAnalysis for backward compatibility
            legacy_result = self._convert_to_legacy_format(validated_response)
            
            self.logger.info(
                f"Thumbnail analysis completed in {processing_time}ms with "
                f"confidence {legacy_result.confidence_score or 0:.2f}"
            )
            
            return legacy_result
            
        except AnalysisValidationError as e:
            self.logger.warning(
                f"Analysis validation failed for {thumbnail_url}: {str(e)}, using fallback"
            )
            return self._create_legacy_fallback()
        except Exception as e:
            self.logger.error(f"Thumbnail analysis error: {str(e)}")
            raise ThumbnailAnalysisError(thumbnail_url, str(e))
    
    def _create_analysis_prompt(self, thumbnail_url: str, prompt_text: str) -> list:
        """Create the analysis prompt for OpenAI Vision API using template system."""
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": thumbnail_url,
                            "detail": "high"  # Request high-detail analysis
                        }
                    }
                ]
            }
        ]
    
    def _parse_and_validate_response(
        self, 
        content: str, 
        language: AnalysisLanguage,
        thumbnail_url: str
    ) -> ThumbnailAnalysisResponse:
        """Parse and validate OpenAI response using new validation system."""
        try:
            # Parse raw JSON response
            raw_data = self._extract_json_from_content(content)
            
            # Validate using schema-based validator
            validated_response = self.validator.validate_response(
                raw_data, 
                language=language,
                strict=False  # Use fallbacks instead of raising exceptions
            )
            
            self.logger.debug(
                f"Response validation successful for {thumbnail_url} "
                f"(language: {language.value})"
            )
            
            return validated_response
            
        except Exception as e:
            self.logger.error(
                f"Failed to parse/validate response for {thumbnail_url}: {str(e)}"
            )
            # Return fallback response
            return self.validator._create_fallback_response(language)
    
    def _extract_json_from_content(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON from OpenAI response content."""
        # Clean up the response content
        json_content = content.strip()
        
        # Remove markdown code blocks if present
        if json_content.startswith('```json'):
            json_content = json_content[7:]
        elif json_content.startswith('```'):
            json_content = json_content[3:]
        
        if json_content.endswith('```'):
            json_content = json_content[:-3]
        
        json_content = json_content.strip()
        
        # Try to find JSON within the content if it's still not clean
        if not json_content.startswith('{'):
            start_idx = json_content.find('{')
            end_idx = json_content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = json_content[start_idx:end_idx+1]
        
        try:
            analysis_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON decode error: {str(e)}, content: {json_content[:200]}...")
            raise
        
        # Flatten nested structure if it exists (for backward compatibility)
        if isinstance(analysis_data, dict):
            flattened_data = {}
            for key, value in analysis_data.items():
                if isinstance(value, dict):
                    # This is a nested section, flatten it
                    flattened_data.update(value)
                else:
                    # This is a direct field
                    flattened_data[key] = value
            return flattened_data
        
        return analysis_data
    
    def _convert_to_legacy_format(self, validated_response: ThumbnailAnalysisResponse) -> ThumbnailAnalysis:
        """Convert new validated response to legacy ThumbnailAnalysis format."""
        return ThumbnailAnalysis(
            # Basic visual elements
            visual_style=validated_response.visual_style,
            setting=validated_response.setting,
            people_count=validated_response.people_count,
            camera_angle=validated_response.camera_angle,
            text_overlay_style=validated_response.text_overlay_style,
            color_scheme=validated_response.color_scheme,
            hook_elements=validated_response.hook_elements,
            confidence_score=validated_response.confidence_score,
            
            # Enhanced storyboard-specific analysis
            composition_type=validated_response.composition_type,
            focal_point=validated_response.focal_point,
            lighting_quality=validated_response.lighting_quality,
            mood_emotion=validated_response.mood_emotion,
            brand_elements=validated_response.brand_elements,
            
            # Content structure indicators
            story_stage=validated_response.story_stage,
            call_to_action_visible=validated_response.call_to_action_visible,
            product_prominence=validated_response.product_prominence,
            
            # Technical production elements
            production_quality=validated_response.production_quality,
            background_complexity=validated_response.background_complexity,
            props_objects=validated_response.props_objects,
            
            # Audience engagement indicators
            visual_interest_level=validated_response.visual_interest_level,
            scroll_stopping_power=validated_response.scroll_stopping_power,
            target_demographic=validated_response.target_demographic,
            
            # Pattern recognition for storyboard
            content_category=validated_response.content_category,
            pacing_indicator=validated_response.pacing_indicator,
            transition_style=validated_response.transition_style
        )
    
    def _create_legacy_fallback(self) -> ThumbnailAnalysis:
        """Create legacy fallback analysis when all parsing fails."""
        language_suffix = "_id" if self.language == AnalysisLanguage.INDONESIAN else "_en"
        
        return ThumbnailAnalysis(
            visual_style="tidak_diketahui" if self.language == AnalysisLanguage.INDONESIAN else "unknown",
            setting="tidak_diketahui" if self.language == AnalysisLanguage.INDONESIAN else "unknown",
            confidence_score=0.5,
            composition_type="center_focused",
            mood_emotion="neutral",
            content_category="tidak_diketahui" if self.language == AnalysisLanguage.INDONESIAN else "unknown",
            people_count=0,
            camera_angle="medium_shot",
            color_scheme="neutral",
            lighting_quality="natural",
            production_quality="amateur",
            background_complexity="moderate",
            story_stage="opening_hook",
            call_to_action_visible=False,
            product_prominence="none",
            visual_interest_level="medium",
            scroll_stopping_power="moderate",
            target_demographic="dewasa_muda" if self.language == AnalysisLanguage.INDONESIAN else "young_adults",
            pacing_indicator="moderate",
            transition_style="static"
        )
    
    def set_language(self, language: str) -> None:
        """Set analysis language for this instance."""
        if language in ["id", "en"]:
            self.language = AnalysisLanguage(language)
            self.logger.info(f"Analysis language changed to: {self.language.value}")
        else:
            self.logger.warning(f"Invalid language '{language}', keeping current: {self.language.value}")
    
    def get_available_languages(self) -> list[str]:
        """Get list of available analysis languages."""
        return self.template_engine.get_available_languages("thumbnail_analysis")