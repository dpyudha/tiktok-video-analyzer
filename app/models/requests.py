"""Request models for the Video Scraper Service."""
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class ExtractRequest(BaseModel):
    """Request model for single video extraction."""
    url: HttpUrl
    include_thumbnail_analysis: Optional[bool] = True
    include_transcript: Optional[bool] = False
    cache_ttl: Optional[int] = 3600

class ExtractBatchRequest(BaseModel):
    """Request model for batch video extraction."""
    urls: List[HttpUrl]
    include_thumbnail_analysis: Optional[bool] = True
    include_transcript: Optional[bool] = False
    parallel_processing: Optional[bool] = True