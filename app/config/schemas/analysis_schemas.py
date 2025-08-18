"""
Pydantic schemas for thumbnail analysis response validation.
Provides type-safe validation, serialization, and error handling.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import yaml
from pathlib import Path

from app.utils.logging import CorrelatedLogger


class AnalysisLanguage(str, Enum):
    """Supported analysis languages."""
    INDONESIAN = "id"
    ENGLISH = "en"


class ThumbnailAnalysisResponse(BaseModel):
    """
    Validated response model for thumbnail analysis.
    
    This model ensures type safety and validates all fields according to
    the schema definitions in schema.yaml files.
    """
    
    # Basic Analysis Fields
    visual_style: str = Field(..., description="Main visual style displayed")
    setting: str = Field(..., description="Location or video setting")
    people_count: int = Field(..., ge=0, le=20, description="Number of visible people")
    camera_angle: str = Field(..., description="Camera shooting angle")
    text_overlay_style: Optional[str] = Field(None, description="Text overlay style used")
    color_scheme: str = Field(..., description="Dominant color scheme")
    hook_elements: List[str] = Field(default_factory=list, description="Attention-grabbing elements")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence level")
    
    # Composition & Production Fields
    composition_type: str = Field(..., description="Type of composition used")
    focal_point: str = Field(..., max_length=200, description="What first catches the eye")
    lighting_quality: str = Field(..., description="Lighting quality")
    mood_emotion: str = Field(..., description="Mood or emotion conveyed")
    brand_elements: List[str] = Field(default_factory=list, description="Visible logos, products, or branding")
    production_quality: str = Field(..., description="Video production quality")
    background_complexity: str = Field(..., description="Background complexity level")
    props_objects: List[str] = Field(default_factory=list, description="Visible props and objects")
    
    # Content & Audience Fields
    story_stage: str = Field(..., description="Story stage being displayed")
    call_to_action_visible: bool = Field(..., description="Is there a visible CTA")
    product_prominence: str = Field(..., description="Product visibility level")
    visual_interest_level: str = Field(..., description="Visual appeal level")
    scroll_stopping_power: str = Field(..., description="Scroll-stopping strength")
    target_demographic: str = Field(..., description="Suitable target demographic")
    content_category: str = Field(..., description="Content category")
    pacing_indicator: str = Field(..., description="Pace/speed indicator")
    transition_style: str = Field(..., description="Visible transition style")
    
    model_config = {
        "validate_assignment": True,
        "use_enum_values": True,
        "extra": "forbid"  # Forbid extra fields not defined in schema
    }
    
    @field_validator('hook_elements', 'brand_elements', 'props_objects')
    @classmethod
    def validate_array_lengths(cls, v, info):
        """Validate array field lengths according to schema limits."""
        max_lengths = {
            'hook_elements': 10,
            'brand_elements': 5,
            'props_objects': 15
        }
        
        field_name = info.field_name if info else 'unknown'
        max_len = max_lengths.get(field_name, 10)
        if len(v) > max_len:
            raise ValueError(f"{field_name} cannot have more than {max_len} items")
        
        return v
    
    @field_validator('focal_point')
    @classmethod
    def validate_focal_point_length(cls, v):
        """Validate focal point description length."""
        if len(v.strip()) < 5:
            raise ValueError("focal_point must be at least 5 characters long")
        return v.strip()
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_threshold(cls, v):
        """Validate confidence score meets minimum threshold."""
        if v < 0.3:
            raise ValueError("confidence_score should be at least 0.3 for valid analysis")
        return v
    
    @model_validator(mode='after')
    def validate_people_count_consistency(self):
        """Validate people count consistency with visual style."""
        people_count = self.people_count
        visual_style = self.visual_style.lower() if self.visual_style else ''
        
        # Define styles that typically involve human presence
        human_styles_id = ['berbicara_langsung', 'lifestyle', 'tutorial', 'review']
        human_styles_en = ['talking_head', 'lifestyle', 'tutorial', 'review']
        human_styles = human_styles_id + human_styles_en
        
        if people_count > 0 and visual_style not in human_styles:
            # This is a warning, not an error - log but don't raise
            pass
        
        return self


class AnalysisValidationError(Exception):
    """Exception raised when analysis validation fails."""
    
    def __init__(self, message: str, validation_errors: List[Dict[str, Any]] = None):
        self.message = message
        self.validation_errors = validation_errors or []
        super().__init__(self.message)


class ResponseValidator:
    """
    Validator for thumbnail analysis responses using schema definitions.
    
    Features:
    - Schema-based validation using YAML configurations
    - Multi-language enum validation
    - Custom validation rules
    - Fallback value generation
    - Detailed error reporting
    """
    
    def __init__(self, schema_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the response validator.
        
        Args:
            schema_config: Pre-loaded schema configuration. If None, loads from file.
        """
        self.logger = CorrelatedLogger(__name__)
        self.schema_config = schema_config
        
        if self.schema_config is None:
            self._load_schema_config()
    
    def _load_schema_config(self):
        """Load schema configuration from YAML file."""
        try:
            config_dir = Path(__file__).parent.parent
            schema_path = config_dir / "prompts" / "thumbnail_analysis" / "schema.yaml"
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                self.schema_config = yaml.safe_load(f)
                
            self.logger.info("Loaded schema configuration for response validation")
            
        except Exception as e:
            self.logger.error(f"Failed to load schema configuration: {str(e)}")
            # Use minimal fallback configuration
            self.schema_config = {
                'response_schema': {'required_fields': []},
                'field_definitions': {},
                'fallback_values': {}
            }
    
    def validate_response(
        self, 
        response_data: Dict[str, Any], 
        language: AnalysisLanguage = AnalysisLanguage.INDONESIAN,
        strict: bool = True
    ) -> ThumbnailAnalysisResponse:
        """
        Validate and parse thumbnail analysis response.
        
        Args:
            response_data: Raw response data from AI analysis
            language: Language used for analysis (affects enum validation)
            strict: If True, raises exception on validation errors. If False, uses fallbacks.
            
        Returns:
            Validated ThumbnailAnalysisResponse object
            
        Raises:
            AnalysisValidationError: If validation fails and strict=True
        """
        try:
            # Clean and prepare the response data
            cleaned_data = self._clean_response_data(response_data)
            
            # Validate enum values against schema
            validated_data = self._validate_enum_values(cleaned_data, language)
            
            # Apply custom validation rules
            validated_data = self._apply_custom_validations(validated_data)
            
            # Create the response model (this will trigger Pydantic validation)
            response = ThumbnailAnalysisResponse(**validated_data)
            
            self.logger.info("Response validation successful")
            return response
            
        except Exception as e:
            if strict:
                self.logger.error(f"Response validation failed: {str(e)}")
                raise AnalysisValidationError(f"Validation failed: {str(e)}")
            else:
                self.logger.warning(f"Response validation failed, using fallback: {str(e)}")
                return self._create_fallback_response(language)
    
    def _clean_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize response data."""
        cleaned = {}
        
        for key, value in data.items():
            # Handle different value types
            if isinstance(value, str):
                cleaned[key] = value.strip()
            elif isinstance(value, list):
                # Clean list items
                cleaned[key] = [item.strip() if isinstance(item, str) else item for item in value]
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _validate_enum_values(
        self, 
        data: Dict[str, Any], 
        language: AnalysisLanguage
    ) -> Dict[str, Any]:
        """Validate enum values against schema definitions."""
        if not self.schema_config or 'field_definitions' not in self.schema_config:
            return data
        
        field_definitions = self.schema_config['field_definitions']
        validated = data.copy()
        
        for field_name, field_def in field_definitions.items():
            if field_name not in data:
                continue
            
            value = data[field_name]
            
            # Check for language-specific enums
            enum_key = f"enum_{language.value}" if f"enum_{language.value}" in field_def else "enum"
            
            if enum_key in field_def:
                valid_values = field_def[enum_key]
                if value not in valid_values:
                    # Try to find closest match or use fallback
                    fallback_value = self._find_enum_fallback(value, valid_values, field_name)
                    validated[field_name] = fallback_value
                    self.logger.warning(
                        f"Invalid enum value '{value}' for field '{field_name}', "
                        f"using fallback: '{fallback_value}'"
                    )
        
        return validated
    
    def _find_enum_fallback(self, value: str, valid_values: List[str], field_name: str) -> str:
        """Find the best fallback value for an invalid enum."""
        # Try case-insensitive matching first
        value_lower = value.lower()
        for valid_value in valid_values:
            if valid_value.lower() == value_lower:
                return valid_value
        
        # Try partial matching
        for valid_value in valid_values:
            if value_lower in valid_value.lower() or valid_value.lower() in value_lower:
                return valid_value
        
        # Use schema fallback or first valid value
        fallback_values = self.schema_config.get('fallback_values', {})
        return fallback_values.get(field_name, valid_values[0] if valid_values else "unknown")
    
    def _apply_custom_validations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom validation rules defined in schema."""
        if not self.schema_config or 'validation_rules' not in self.schema_config:
            return data
        
        validation_rules = self.schema_config['validation_rules']
        validated = data.copy()
        
        # Apply cross-field validations
        cross_field_rules = validation_rules.get('cross_field_validations', [])
        for rule in cross_field_rules:
            validated = self._apply_cross_field_rule(validated, rule)
        
        # Apply data quality checks
        quality_checks = validation_rules.get('data_quality_checks', [])
        for check in quality_checks:
            validated = self._apply_quality_check(validated, check)
        
        return validated
    
    def _apply_cross_field_rule(self, data: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a cross-field validation rule."""
        rule_name = rule.get('name', '')
        
        if rule_name == 'people_count_consistency':
            # This is handled in the Pydantic validator
            pass
        elif rule_name == 'confidence_threshold':
            min_confidence = rule.get('minimum_confidence', 0.3)
            if data.get('confidence_score', 0) < min_confidence:
                data['confidence_score'] = min_confidence
                self.logger.warning(f"Adjusted confidence_score to minimum threshold: {min_confidence}")
        
        return data
    
    def _apply_quality_check(self, data: Dict[str, Any], check: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a data quality check."""
        check_name = check.get('name', '')
        
        if check_name == 'array_length_limits':
            # Trim arrays that are too long
            max_lengths = {
                'hook_elements': check.get('hook_elements_max', 10),
                'brand_elements': check.get('brand_elements_max', 5),
                'props_objects': check.get('props_objects_max', 15)
            }
            
            for field, max_len in max_lengths.items():
                if field in data and isinstance(data[field], list):
                    if len(data[field]) > max_len:
                        data[field] = data[field][:max_len]
                        self.logger.warning(f"Trimmed {field} to {max_len} items")
        
        elif check_name == 'string_length_limits':
            focal_point_min = check.get('focal_point_min', 5)
            focal_point_max = check.get('focal_point_max', 200)
            
            if 'focal_point' in data:
                fp = data['focal_point']
                if len(fp) < focal_point_min:
                    data['focal_point'] = fp + " (detail tidak mencukupi)"
                elif len(fp) > focal_point_max:
                    data['focal_point'] = fp[:focal_point_max-3] + "..."
        
        return data
    
    def _create_fallback_response(self, language: AnalysisLanguage) -> ThumbnailAnalysisResponse:
        """Create a fallback response when validation completely fails."""
        fallback_values = self.schema_config.get('fallback_values', {})
        
        # Get language-specific fallback values
        lang_suffix = f"_{language.value}"
        
        fallback_data = {
            'visual_style': fallback_values.get(f'visual_style{lang_suffix}', 'unknown'),
            'setting': fallback_values.get(f'setting{lang_suffix}', 'unknown'),
            'people_count': fallback_values.get('people_count', 0),
            'camera_angle': 'medium_shot',
            'text_overlay_style': None,
            'color_scheme': 'neutral',
            'hook_elements': [],
            'confidence_score': fallback_values.get('confidence_score', 0.5),
            'composition_type': 'center_focused',
            'focal_point': 'Analisis tidak dapat dilakukan dengan baik',
            'lighting_quality': 'natural',
            'mood_emotion': fallback_values.get('mood_emotion', 'neutral'),
            'brand_elements': [],
            'production_quality': 'amateur',
            'background_complexity': 'moderate',
            'props_objects': [],
            'story_stage': 'opening_hook',
            'call_to_action_visible': False,
            'product_prominence': 'none',
            'visual_interest_level': 'medium',
            'scroll_stopping_power': 'moderate',
            'target_demographic': fallback_values.get(f'target_demographic{lang_suffix}', 'unknown'),
            'content_category': fallback_values.get('content_category', 'unknown'),
            'pacing_indicator': 'moderate',
            'transition_style': 'static'
        }
        
        return ThumbnailAnalysisResponse(**fallback_data)


# Global validator instance
_response_validator = None

def get_response_validator() -> ResponseValidator:
    """Get global response validator instance (singleton pattern)."""
    global _response_validator
    if _response_validator is None:
        _response_validator = ResponseValidator()
    return _response_validator