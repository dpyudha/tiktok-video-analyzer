"""
Configuration management for the Video Scraper Service.
Centralizes environment variable handling and application settings.
"""
import os
import ssl
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # API Configuration
        self.api_title = "Video Scraper Service"
        self.api_description = "A service for extracting metadata from TikTok and Instagram videos using yt-dlp"
        self.api_version = "1.0.0"
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        # Security
        self.api_key = os.getenv("API_KEY", "your-default-api-key-here")
        self.allowed_origins = ["*"]  # Would be configurable in production
        
        # External API Keys
        self.ms_token = os.getenv("MS_TOKEN", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.scraperapi_key = os.getenv("SCRAPERAPI_KEY", "")
        self.scraperapi_base_url = os.getenv("SCRAPERAPI_BASE_URL", "http://api.scraperapi.com/")
        
        # Rate Limiting
        self.max_requests_per_minute = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
        self.max_concurrent_extractions = int(os.getenv("MAX_CONCURRENT_EXTRACTIONS", "5"))
        self.max_urls_per_batch = int(os.getenv("MAX_URLS_PER_BATCH", "3"))
        
        # Video Processing
        self.max_video_duration = int(os.getenv("MAX_VIDEO_DURATION", "300"))  # 5 minutes
        self.extraction_timeout = int(os.getenv("EXTRACTION_TIMEOUT", "60"))  # seconds
        self.retry_attempts = int(os.getenv("RETRY_ATTEMPTS", "3"))
        
        # Cache Configuration
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour
        self.redis_url = os.getenv("REDIS_URL")
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Performance
        self.connection_pool_size = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
        self.connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", "30"))
        
        # Feature Flags
        self.enable_thumbnail_analysis = os.getenv("ENABLE_THUMBNAIL_ANALYSIS", "true").lower() == "true"
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.enable_health_checks = os.getenv("ENABLE_HEALTH_CHECKS", "true").lower() == "true"
        
        # Prompt Management System
        self.prompt_system_debug = os.getenv("PROMPT_SYSTEM_DEBUG", "false").lower() == "true"
        self.prompt_cache_enabled = os.getenv("PROMPT_CACHE_ENABLED", "true").lower() == "true"
        self.prompt_validation_strict = os.getenv("PROMPT_VALIDATION_STRICT", "false").lower() == "true"
        self.default_analysis_language = os.getenv("DEFAULT_ANALYSIS_LANGUAGE", "id")
        self.enable_language_detection = os.getenv("ENABLE_LANGUAGE_DETECTION", "true").lower() == "true"

class PlatformConfig:
    """Platform-specific configurations."""
    
    SUPPORTED_PLATFORMS = {
        "tiktok": {
            "domains": ["tiktok.com", "www.tiktok.com", "vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com"],
            "features": ["metadata_extraction", "thumbnail_analysis", "engagement_metrics"],
            "url_patterns": [
                "https://www.tiktok.com/@{username}/video/{video_id}",
                "https://vm.tiktok.com/{short_id}",
                "https://vt.tiktok.com/{short_id}"
            ]
        }
    }
    
    @classmethod
    def get_platform_domains(cls, platform: str) -> List[str]:
        """Get supported domains for a platform."""
        return cls.SUPPORTED_PLATFORMS.get(platform, {}).get("domains", [])
    
    @classmethod
    def get_all_domains(cls) -> List[str]:
        """Get all supported domains."""
        domains = []
        for platform_config in cls.SUPPORTED_PLATFORMS.values():
            domains.extend(platform_config.get("domains", []))
        return domains
    
    @classmethod
    def get_platform_features(cls, platform: str) -> List[str]:
        """Get supported features for a platform."""
        return cls.SUPPORTED_PLATFORMS.get(platform, {}).get("features", [])

class YTDLPConfig:
    """Configuration for yt-dlp extraction."""
    
    BASE_OPTIONS = {
        'quiet': True,
        'no_warnings': True,
        'extractaudio': False,
        'format': 'best',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'skip_download': True,
        'extract_flat': False,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'socket_timeout': 60,
        'retries': 3,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'source_address': None,
        'prefer_insecure': True,
    }
    
    @classmethod
    def get_options(cls, timeout: int = 60, retries: int = 3) -> dict:
        """Get yt-dlp options with custom timeout and retries."""
        options = cls.BASE_OPTIONS.copy()
        options.update({
            'socket_timeout': timeout,
            'retries': retries
        })
        return options

class SecurityConfig:
    """Security-related configuration."""
    
    @staticmethod
    def configure_ssl():
        """Configure SSL settings globally."""
        ssl._create_default_https_context = ssl._create_unverified_context

# Create global settings instance
settings = Settings()

# Configure SSL on module import
SecurityConfig.configure_ssl()