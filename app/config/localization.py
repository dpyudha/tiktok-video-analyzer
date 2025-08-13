"""
Localization support for the thumbnail analysis system.
Handles language detection, fallbacks, and multi-language prompt management.
"""
from typing import Dict, List, Optional, Any
from enum import Enum
import re

from ..utils.logging import CorrelatedLogger


class SupportedLanguage(str, Enum):
    """Supported languages for analysis."""
    INDONESIAN = "id"
    ENGLISH = "en"


class LanguageDetector:
    """
    Automatic language detection based on various inputs.
    
    Can detect language from:
    - Explicit language codes
    - Video metadata (title, description)
    - User preferences
    - Request headers
    """
    
    def __init__(self):
        self.logger = CorrelatedLogger(__name__)
        
        # Language detection patterns
        self.language_patterns = {
            SupportedLanguage.INDONESIAN: [
                # Indonesian specific words/patterns
                r'\b(dan|atau|dengan|untuk|yang|ini|itu|dari|ke|di|pada|dalam)\b',
                r'\b(saya|kamu|kita|mereka|dia|kami)\b',
                r'\b(bagaimana|kenapa|dimana|kapan|apa)\b',
                r'\b(video|konten|tutorial|review|demo)\b',
                # Indonesian social media terms
                r'\b(follower|subscriber|like|share|comment)\b',
                # Indonesian greetings/expressions
                r'\b(hai|halo|selamat|terima kasih|maaf)\b',
            ],
            SupportedLanguage.ENGLISH: [
                # English specific patterns
                r'\b(and|or|with|for|that|this|from|to|at|in|on)\b',
                r'\b(i|you|we|they|he|she|it)\b',
                r'\b(how|why|where|when|what)\b',
                r'\b(video|content|tutorial|review|demo)\b',
                # English social media terms
                r'\b(follow|subscribe|like|share|comment)\b',
                # English greetings/expressions
                r'\b(hi|hello|thanks|thank you|sorry)\b',
            ]
        }
    
    def detect_language(
        self,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        user_preference: Optional[str] = None,
        platform_hint: Optional[str] = None
    ) -> SupportedLanguage:
        """
        Detect the most appropriate language for analysis.
        
        Args:
            video_title: Title of the video being analyzed
            video_description: Description/caption of the video
            user_preference: Explicitly set user language preference
            platform_hint: Platform-specific language hints
            
        Returns:
            Detected language as SupportedLanguage enum
        """
        # Priority 1: Explicit user preference
        if user_preference:
            normalized = user_preference.lower().strip()
            if normalized in ["id", "indonesian", "bahasa", "indonesia"]:
                self.logger.info(f"Using user preference language: Indonesian")
                return SupportedLanguage.INDONESIAN
            elif normalized in ["en", "english"]:
                self.logger.info(f"Using user preference language: English")
                return SupportedLanguage.ENGLISH
        
        # Priority 2: Content-based detection
        text_content = \"\"\n        if video_title:\n            text_content += f\" {video_title}\"\n        if video_description:\n            text_content += f\" {video_description}\"\n        \n        if text_content.strip():\n            detected = self._detect_from_text(text_content)\n            if detected:\n                self.logger.info(f\"Detected language from content: {detected.value}\")\n                return detected\n        \n        # Priority 3: Platform hints\n        if platform_hint:\n            platform_lang = self._detect_from_platform(platform_hint)\n            if platform_lang:\n                self.logger.info(f\"Using platform hint language: {platform_lang.value}\")\n                return platform_lang\n        \n        # Default fallback: Indonesian (primary target market)\n        self.logger.info(\"No language detected, using default: Indonesian\")\n        return SupportedLanguage.INDONESIAN\n    \n    def _detect_from_text(self, text: str) -> Optional[SupportedLanguage]:\n        \"\"\"Detect language from text content using pattern matching.\"\"\"\n        text_lower = text.lower()\n        language_scores = {}\n        \n        for language, patterns in self.language_patterns.items():\n            score = 0\n            for pattern in patterns:\n                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))\n                score += matches\n            language_scores[language] = score\n        \n        # Return language with highest score, if above threshold\n        if language_scores:\n            best_language = max(language_scores, key=language_scores.get)\n            best_score = language_scores[best_language]\n            \n            # Only return detection if score is above threshold\n            if best_score >= 2:  # At least 2 pattern matches\n                return best_language\n        \n        return None\n    \n    def _detect_from_platform(self, platform: str) -> Optional[SupportedLanguage]:\n        \"\"\"Detect language from platform-specific hints.\"\"\"\n        platform_lower = platform.lower()\n        \n        # Platform-specific language hints\n        if \"tiktok\" in platform_lower:\n            # TikTok Indonesia is very popular\n            return SupportedLanguage.INDONESIAN\n        elif \"instagram\" in platform_lower:\n            # Instagram has mixed usage in Indonesia\n            return SupportedLanguage.INDONESIAN\n        \n        return None\n    \n    def get_confidence_score(self, text: str, language: SupportedLanguage) -> float:\n        \"\"\"Get confidence score for language detection.\"\"\"\n        if not text:\n            return 0.0\n        \n        text_lower = text.lower()\n        patterns = self.language_patterns.get(language, [])\n        \n        total_matches = 0\n        for pattern in patterns:\n            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))\n            total_matches += matches\n        \n        # Normalize by text length (rough estimate)\n        words_count = len(text.split())\n        if words_count == 0:\n            return 0.0\n        \n        confidence = min(total_matches / words_count, 1.0)\n        return confidence\n\n\nclass LocalizationManager:\n    \"\"\"\n    Manages localization settings and language-specific configurations.\n    \n    Features:\n    - Language preference management\n    - Fallback language chains\n    - Regional customizations\n    - Culture-specific adjustments\n    \"\"\"\n    \n    def __init__(self):\n        self.logger = CorrelatedLogger(__name__)\n        self.detector = LanguageDetector()\n        \n        # Language fallback chains\n        self.fallback_chains = {\n            SupportedLanguage.INDONESIAN: [SupportedLanguage.INDONESIAN, SupportedLanguage.ENGLISH],\n            SupportedLanguage.ENGLISH: [SupportedLanguage.ENGLISH, SupportedLanguage.INDONESIAN]\n        }\n        \n        # Culture-specific configurations\n        self.culture_configs = {\n            SupportedLanguage.INDONESIAN: {\n                \"target_demographics\": [\"remaja\", \"dewasa_muda\", \"keluarga\", \"profesional\", \"ibu_rumah_tangga\"],\n                \"common_settings\": [\"dalam_ruangan\", \"luar_ruangan\", \"kamar_tidur\", \"dapur\"],\n                \"visual_styles\": [\"berbicara_langsung\", \"lifestyle\", \"tutorial\", \"review\"],\n                \"date_format\": \"%d/%m/%Y\",\n                \"number_format\": \"id_ID\"\n            },\n            SupportedLanguage.ENGLISH: {\n                \"target_demographics\": [\"teens\", \"young_adults\", \"families\", \"professionals\", \"parents\"],\n                \"common_settings\": [\"indoor\", \"outdoor\", \"bedroom\", \"kitchen\"],\n                \"visual_styles\": [\"talking_head\", \"lifestyle\", \"tutorial\", \"review\"],\n                \"date_format\": \"%m/%d/%Y\",\n                \"number_format\": \"en_US\"\n            }\n        }\n    \n    def determine_analysis_language(\n        self,\n        video_metadata: Optional[Dict[str, Any]] = None,\n        user_preference: Optional[str] = None,\n        request_context: Optional[Dict[str, Any]] = None\n    ) -> SupportedLanguage:\n        \"\"\"\n        Determine the best language for thumbnail analysis.\n        \n        Args:\n            video_metadata: Metadata from the video (title, description, etc.)\n            user_preference: User's explicit language preference\n            request_context: Additional context from the request\n            \n        Returns:\n            Selected language for analysis\n        \"\"\"\n        video_title = video_metadata.get(\"title\") if video_metadata else None\n        video_description = video_metadata.get(\"description\") if video_metadata else None\n        platform = video_metadata.get(\"platform\") if video_metadata else None\n        \n        detected_language = self.detector.detect_language(\n            video_title=video_title,\n            video_description=video_description,\n            user_preference=user_preference,\n            platform_hint=platform\n        )\n        \n        self.logger.info(f\"Determined analysis language: {detected_language.value}\")\n        return detected_language\n    \n    def get_fallback_language(self, primary_language: SupportedLanguage) -> SupportedLanguage:\n        \"\"\"Get fallback language if primary analysis fails.\"\"\"\n        fallback_chain = self.fallback_chains.get(primary_language, [])\n        \n        # Return the second language in the chain, or primary if only one\n        if len(fallback_chain) > 1:\n            return fallback_chain[1]\n        else:\n            return primary_language\n    \n    def get_culture_config(self, language: SupportedLanguage) -> Dict[str, Any]:\n        \"\"\"Get culture-specific configuration for a language.\"\"\"\n        return self.culture_configs.get(language, {})\n    \n    def localize_enum_values(self, values: List[str], language: SupportedLanguage) -> List[str]:\n        \"\"\"Localize enum values based on language.\"\"\"\n        # This could be extended with translation mappings\n        # For now, return as-is since our schema already has language-specific enums\n        return values\n    \n    def format_confidence_message(self, confidence: float, language: SupportedLanguage) -> str:\n        \"\"\"Format confidence score message in appropriate language.\"\"\"\n        if language == SupportedLanguage.INDONESIAN:\n            if confidence >= 0.8:\n                return f\"Analisis sangat yakin ({confidence:.1%})\"\n            elif confidence >= 0.6:\n                return f\"Analisis cukup yakin ({confidence:.1%})\"\n            else:\n                return f\"Analisis kurang yakin ({confidence:.1%})\"\n        else:\n            if confidence >= 0.8:\n                return f\"High confidence analysis ({confidence:.1%})\"\n            elif confidence >= 0.6:\n                return f\"Moderate confidence analysis ({confidence:.1%})\"\n            else:\n                return f\"Low confidence analysis ({confidence:.1%})\"\n    \n    def get_supported_languages(self) -> List[str]:\n        \"\"\"Get list of supported language codes.\"\"\"\n        return [lang.value for lang in SupportedLanguage]\n    \n    def validate_language_code(self, language_code: str) -> bool:\n        \"\"\"Validate if a language code is supported.\"\"\"\n        return language_code in self.get_supported_languages()\n\n\n# Global localization manager instance\n_localization_manager = None\n\ndef get_localization_manager() -> LocalizationManager:\n    \"\"\"Get global localization manager instance (singleton pattern).\"\"\"\n    global _localization_manager\n    if _localization_manager is None:\n        _localization_manager = LocalizationManager()\n    return _localization_manager