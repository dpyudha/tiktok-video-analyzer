"""Logging configuration and utilities."""
import logging
import sys
from typing import Optional
from datetime import datetime
from ..core.config import settings

class LoggerSetup:
    """Centralized logging configuration."""
    
    @staticmethod
    def setup_logging(
        level: Optional[str] = None,
        format_string: Optional[str] = None
    ) -> None:
        """Setup application logging."""
        log_level = level or settings.log_level
        log_format = format_string or settings.log_format
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Set specific logger levels
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("fastapi").setLevel(logging.INFO)
        logging.getLogger("yt_dlp").setLevel(logging.WARNING)  # Reduce yt-dlp verbosity
        logging.getLogger("openai").setLevel(logging.WARNING)  # Reduce OpenAI verbosity

class CorrelatedLogger:
    """Logger with correlation ID support for request tracking."""
    
    def __init__(self, name: str, request_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.request_id = request_id
    
    def _format_message(self, message: str) -> str:
        """Format message with request ID if available."""
        if self.request_id:
            return f"[{self.request_id}] {message}"
        return message
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with correlation ID."""
        self.logger.debug(self._format_message(message), **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with correlation ID."""
        self.logger.info(self._format_message(message), **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with correlation ID."""
        self.logger.warning(self._format_message(message), **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with correlation ID."""
        self.logger.error(self._format_message(message), **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception message with correlation ID."""
        self.logger.exception(self._format_message(message), **kwargs)

class MetricsLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self):
        self.logger = logging.getLogger("metrics")
    
    def log_request_metrics(
        self,
        request_id: str,
        endpoint: str,
        method: str,
        processing_time_ms: int,
        status_code: int,
        url_count: int = 1
    ) -> None:
        """Log request processing metrics."""
        self.logger.info(
            f"REQUEST_METRICS request_id={request_id} "
            f"endpoint={endpoint} method={method} "
            f"processing_time_ms={processing_time_ms} "
            f"status_code={status_code} url_count={url_count}"
        )
    
    def log_extraction_metrics(
        self,
        request_id: str,
        url: str,
        platform: str,
        success: bool,
        processing_time_ms: int,
        cache_hit: bool = False,
        error_code: Optional[str] = None
    ) -> None:
        """Log video extraction metrics."""
        status = "success" if success else "failed"
        cache_status = "hit" if cache_hit else "miss"
        
        log_msg = (
            f"EXTRACTION_METRICS request_id={request_id} "
            f"url={url} platform={platform} status={status} "
            f"processing_time_ms={processing_time_ms} cache={cache_status}"
        )
        
        if error_code:
            log_msg += f" error_code={error_code}"
        
        self.logger.info(log_msg)
    
    def log_thumbnail_analysis_metrics(
        self,
        request_id: str,
        thumbnail_url: str,
        success: bool,
        processing_time_ms: int,
        confidence_score: Optional[float] = None,
        error_code: Optional[str] = None
    ) -> None:
        """Log thumbnail analysis metrics."""
        status = "success" if success else "failed"
        
        log_msg = (
            f"THUMBNAIL_ANALYSIS_METRICS request_id={request_id} "
            f"thumbnail_url={thumbnail_url} status={status} "
            f"processing_time_ms={processing_time_ms}"
        )
        
        if confidence_score is not None:
            log_msg += f" confidence_score={confidence_score:.2f}"
        
        if error_code:
            log_msg += f" error_code={error_code}"
        
        self.logger.info(log_msg)