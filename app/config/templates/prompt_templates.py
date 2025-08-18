"""
Prompt Template Engine for dynamic prompt generation.
Handles template loading, rendering, and validation.
"""
import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from dataclasses import dataclass

from app.core.exceptions import ConfigurationError
from app.utils.logging import CorrelatedLogger


@dataclass
class PromptSection:
    """Represents a section of the analysis prompt."""
    title: str
    fields: List[Dict[str, Any]]


@dataclass
class PromptConfig:
    """Configuration for a complete prompt template."""
    system_role: str
    instruction: str
    analysis_sections: Dict[str, PromptSection]
    response_format: Dict[str, str]
    examples: Dict[str, str]


class PromptTemplateEngine:
    """
    Template engine for managing and rendering analysis prompts.
    
    Features:
    - Multi-language prompt support
    - Dynamic template rendering with Jinja2
    - Configuration-based prompt management
    - Validation and fallback handling
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the template engine.
        
        Args:
            config_dir: Path to configuration directory. Defaults to app/config/
        """
        self.logger = CorrelatedLogger(__name__)
        
        # Set up configuration directory
        if config_dir is None:
            config_dir = Path(__file__).parent.parent
        
        self.config_dir = Path(config_dir)
        self.prompts_dir = self.config_dir / "prompts"
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False
        )
        
        # Cache for loaded configurations
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info(f"PromptTemplateEngine initialized with config_dir: {config_dir}")
    
    def load_prompt_config(self, analysis_type: str, language: str = "id") -> PromptConfig:
        """
        Load prompt configuration for specific analysis type and language.
        
        Args:
            analysis_type: Type of analysis (e.g., 'thumbnail_analysis')
            language: Language code (e.g., 'id', 'en')
            
        Returns:
            PromptConfig object with loaded configuration
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        cache_key = f"{analysis_type}_{language}"
        
        if cache_key in self._config_cache:
            return self._build_prompt_config(self._config_cache[cache_key])
        
        config_path = self.prompts_dir / analysis_type / f"{language}.yaml"
        
        if not config_path.exists():
            raise ConfigurationError(
                f"Prompt configuration not found: {config_path}",
                f"Available languages for {analysis_type}: {self._get_available_languages(analysis_type)}"
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Cache the configuration
            self._config_cache[cache_key] = config_data
            
            self.logger.info(f"Loaded prompt configuration: {analysis_type}/{language}")
            return self._build_prompt_config(config_data)
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load prompt configuration: {config_path}", str(e))
    
    def load_schema_config(self, analysis_type: str) -> Dict[str, Any]:
        """
        Load response schema configuration for validation.
        
        Args:
            analysis_type: Type of analysis (e.g., 'thumbnail_analysis')
            
        Returns:
            Schema configuration dictionary
        """
        if analysis_type in self._schema_cache:
            return self._schema_cache[analysis_type]
        
        schema_path = self.prompts_dir / analysis_type / "schema.yaml"
        
        if not schema_path.exists():
            raise ConfigurationError(f"Schema configuration not found: {schema_path}")
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_data = yaml.safe_load(f)
            
            # Cache the schema
            self._schema_cache[analysis_type] = schema_data
            
            self.logger.info(f"Loaded schema configuration: {analysis_type}")
            return schema_data
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load schema configuration: {schema_path}", str(e))
    
    def render_prompt(
        self, 
        analysis_type: str, 
        language: str = "id",
        **template_vars
    ) -> str:
        """
        Render the complete analysis prompt with template variables.
        
        Args:
            analysis_type: Type of analysis (e.g., 'thumbnail_analysis')
            language: Language code (e.g., 'id', 'en')
            **template_vars: Variables to pass to the template
            
        Returns:
            Rendered prompt string
        """
        try:
            config = self.load_prompt_config(analysis_type, language)
            
            # Build the complete prompt
            prompt_parts = [
                config.system_role,
                "",
                config.instruction,
                ""
            ]
            
            # Add analysis sections
            for section_name, section in config.analysis_sections.items():
                prompt_parts.append(f"{section.title}:")
                
                for field_info in section.fields:
                    field_name = field_info['field']
                    description = field_info.get('description', '')
                    
                    if 'options' in field_info:
                        options = ', '.join(field_info['options'])
                        prompt_parts.append(f"{len(prompt_parts)}) {field_name}: {options}")
                    elif field_info.get('type') == 'array':
                        prompt_parts.append(f"{len(prompt_parts)}) {field_name}: {description}")
                    elif field_info.get('type') == 'integer':
                        range_info = field_info.get('range', '')
                        prompt_parts.append(f"{len(prompt_parts)}) {field_name}: {description} {range_info}")
                    elif field_info.get('type') == 'float':
                        range_info = f"({field_info.get('range', ['0.0', '1.0'])[0]}-{field_info.get('range', ['0.0', '1.0'])[1]})"
                        prompt_parts.append(f"{len(prompt_parts)}) {field_name}: {description} {range_info}")
                    else:
                        prompt_parts.append(f"{len(prompt_parts)}) {field_name}: {description}")
                
                prompt_parts.append("")
            
            # Add response format instructions
            prompt_parts.append(config.response_format['instruction'])
            
            # Join all parts and render with template variables
            full_prompt = "\n".join(prompt_parts)
            
            # Use Jinja2 to render template variables if any
            if template_vars:
                template = Template(full_prompt)
                full_prompt = template.render(**template_vars)
            
            self.logger.debug(f"Rendered prompt for {analysis_type}/{language} ({len(full_prompt)} chars)")
            return full_prompt
            
        except Exception as e:
            self.logger.error(f"Failed to render prompt: {analysis_type}/{language} - {str(e)}")
            raise ConfigurationError(f"Prompt rendering failed: {analysis_type}/{language}", str(e))
    
    def get_available_languages(self, analysis_type: str) -> List[str]:
        """Get list of available languages for an analysis type."""
        return self._get_available_languages(analysis_type)
    
    def get_available_analysis_types(self) -> List[str]:
        """Get list of available analysis types."""
        if not self.prompts_dir.exists():
            return []
        
        analysis_types = []
        for item in self.prompts_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                analysis_types.append(item.name)
        
        return sorted(analysis_types)
    
    def validate_configuration(self, analysis_type: str, language: str) -> bool:
        """
        Validate that a configuration is properly formatted.
        
        Args:
            analysis_type: Type of analysis to validate
            language: Language code to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Try to load the configuration
            config = self.load_prompt_config(analysis_type, language)
            
            # Basic validation checks
            if not config.system_role.strip():
                raise ConfigurationError("system_role cannot be empty")
            
            if not config.instruction.strip():
                raise ConfigurationError("instruction cannot be empty")
            
            if not config.analysis_sections:
                raise ConfigurationError("analysis_sections cannot be empty")
            
            # Validate each section has required fields
            for section_name, section in config.analysis_sections.items():
                if not section.fields:
                    raise ConfigurationError(f"Section '{section_name}' has no fields")
                
                for field in section.fields:
                    if 'field' not in field:
                        raise ConfigurationError(f"Field missing 'field' name in section '{section_name}'")
            
            self.logger.info(f"Configuration validation passed: {analysis_type}/{language}")
            return True
            
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {analysis_type}/{language}", str(e))
    
    def _build_prompt_config(self, config_data: Dict[str, Any]) -> PromptConfig:
        """Build PromptConfig object from raw configuration data."""
        main_prompt = config_data.get('main_prompt', {})
        
        # Build analysis sections
        analysis_sections = {}
        sections_data = main_prompt.get('analysis_sections', {})
        
        for section_name, section_data in sections_data.items():
            analysis_sections[section_name] = PromptSection(
                title=section_data.get('title', section_name.upper()),
                fields=section_data.get('fields', [])
            )
        
        return PromptConfig(
            system_role=config_data.get('system_role', ''),
            instruction=main_prompt.get('instruction', ''),
            analysis_sections=analysis_sections,
            response_format=config_data.get('response_format', {}),
            examples=config_data.get('examples', {})
        )
    
    def _get_available_languages(self, analysis_type: str) -> List[str]:
        """Get available language codes for an analysis type."""
        analysis_dir = self.prompts_dir / analysis_type
        
        if not analysis_dir.exists():
            return []
        
        languages = []
        for item in analysis_dir.iterdir():
            if item.is_file() and item.suffix == '.yaml' and item.stem != 'schema':
                languages.append(item.stem)
        
        return sorted(languages)


# Global template engine instance
_template_engine = None

def get_template_engine() -> PromptTemplateEngine:
    """Get global template engine instance (singleton pattern)."""
    global _template_engine
    if _template_engine is None:
        _template_engine = PromptTemplateEngine()
    return _template_engine