from fastapi import FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import yt_dlp
import logging
import asyncio
from urllib.parse import urlparse, quote
import re
import os
import json
import requests
import ssl
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure SSL to ignore certificate errors globally
ssl._create_default_https_context = ssl._create_unverified_context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
api_key_header = APIKeyHeader(name="x-api-key")
API_KEY = os.getenv("API_KEY", "your-default-api-key-here")
ms_token = os.getenv("MS_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY", "")
SCRAPERAPI_BASE_URL = "http://api.scraperapi.com/"

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI(
    title="Video Scraper Service",
    description="A service for extracting metadata from TikTok and Instagram videos using yt-dlp",
    version="1.0.0",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
    }
)

# Configure OpenAPI security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title="Video Scraper Service",
        version="1.0.0",
        description="A service for extracting metadata from TikTok and Instagram videos using yt-dlp",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key"
        }
    }
    
    # Apply security to all endpoints that need authentication
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method in ["post"] and path in ["/extract", "/extract/batch"]:
                openapi_schema["paths"][path][method]["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ExtractRequest(BaseModel):
    url: HttpUrl
    include_thumbnail_analysis: Optional[bool] = True
    cache_ttl: Optional[int] = 3600

class ExtractBatchRequest(BaseModel):
    urls: List[HttpUrl]
    include_thumbnail_analysis: Optional[bool] = True
    parallel_processing: Optional[bool] = True

# Core data models
class ThumbnailAnalysis(BaseModel):
    # Basic visual elements
    visual_style: Optional[str] = None
    setting: Optional[str] = None
    people_count: Optional[int] = None
    camera_angle: Optional[str] = None
    text_overlay_style: Optional[str] = None
    color_scheme: Optional[str] = None
    hook_elements: Optional[List[str]] = []
    confidence_score: Optional[float] = None
    
    # Enhanced storyboard-specific analysis
    composition_type: Optional[str] = None  # rule_of_thirds, center_focused, diagonal, symmetrical
    focal_point: Optional[str] = None  # what draws the eye first
    lighting_quality: Optional[str] = None  # natural, artificial, dramatic, soft, harsh
    mood_emotion: Optional[str] = None  # excited, calm, urgent, playful, professional
    brand_elements: Optional[List[str]] = []  # logos, products, branding visible
    
    # Content structure indicators
    story_stage: Optional[str] = None  # opening_hook, problem_setup, solution_reveal, result_show
    call_to_action_visible: Optional[bool] = None  # is there visible CTA
    product_prominence: Optional[str] = None  # dominant, subtle, background, none
    
    # Technical production elements
    production_quality: Optional[str] = None  # professional, semi_pro, amateur, phone_quality
    background_complexity: Optional[str] = None  # minimal, moderate, busy, chaotic
    props_objects: Optional[List[str]] = []  # visible props and objects
    
    # Audience engagement indicators
    visual_interest_level: Optional[str] = None  # high, medium, low
    scroll_stopping_power: Optional[str] = None  # strong, moderate, weak
    target_demographic: Optional[str] = None  # remaja, dewasa_muda, keluarga, profesional
    
    # Pattern recognition for storyboard
    content_category: Optional[str] = None  # tutorial, review, demo, lifestyle, entertainment
    pacing_indicator: Optional[str] = None  # fast_paced, moderate, slow_build
    transition_style: Optional[str] = None  # smooth, jump_cut, fade, dynamic

class VideoMetadata(BaseModel):
    url: str
    platform: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    upload_date: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_analysis: Optional[ThumbnailAnalysis] = None
    extracted_at: Optional[str] = None
    processing_time_ms: Optional[int] = None
    cache_hit: Optional[bool] = False

class RateLimit(BaseModel):
    remaining: int
    reset_at: str

class ResponseMetadata(BaseModel):
    request_id: str
    api_version: str = "1.0.0"
    timestamp: Optional[str] = None
    rate_limit: Optional[RateLimit] = None
    processing_time_ms: Optional[int] = None

# Standardized response models
class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    metadata: ResponseMetadata

class ErrorDetails(BaseModel):
    url: Optional[str] = None
    platform: Optional[str] = None
    reason: Optional[str] = None

class ErrorInfo(BaseModel):
    code: str
    message: str
    details: Optional[ErrorDetails] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorInfo
    metadata: ResponseMetadata

# Batch processing models
class ProcessedVideo(BaseModel):
    url: str
    status: str
    data: Optional[VideoMetadata] = None
    error: Optional[ErrorInfo] = None

class BatchSummary(BaseModel):
    total_requested: int
    successful: int
    failed: int
    processing_time_ms: int

class BatchData(BaseModel):
    processed: List[ProcessedVideo]
    failed: List[ProcessedVideo]
    summary: BatchSummary

# Platform support models
class PlatformFeatures(BaseModel):
    name: str
    domain: str
    supported_features: List[str]
    url_patterns: List[str]

class PlatformLimitations(BaseModel):
    max_urls_per_batch: int
    rate_limit_per_minute: int
    max_video_duration: int

class SupportedPlatformsData(BaseModel):
    platforms: List[PlatformFeatures]
    limitations: PlatformLimitations

# Health check models
class DependencyStatus(BaseModel):
    yt_dlp: str
    openai: str
    redis: Optional[str] = "not_configured"

class HealthMetrics(BaseModel):
    uptime_seconds: int
    requests_processed: int
    cache_hit_rate: float

class HealthData(BaseModel):
    status: str
    timestamp: str
    version: str
    dependencies: DependencyStatus
    metrics: HealthMetrics

# Statistics models
class ServiceStats(BaseModel):
    total_extractions: int
    successful_extractions: int
    failed_extractions: int
    success_rate: float
    avg_processing_time_ms: int

class PlatformStats(BaseModel):
    count: int
    success_rate: float

class PlatformBreakdown(BaseModel):
    tiktok: PlatformStats
    instagram: PlatformStats

class CacheStats(BaseModel):
    hit_rate: float
    total_entries: int
    memory_usage_mb: int

class StatsData(BaseModel):
    service_stats: ServiceStats
    platform_breakdown: PlatformBreakdown
    error_breakdown: Dict[str, int]
    cache_stats: CacheStats

# Global variables for statistics
service_start_time = datetime.now()
request_count = 0
successful_requests = 0
failed_requests = 0

# Utility functions
def generate_request_id() -> str:
    """Generate unique request ID"""
    return f"req_{uuid.uuid4().hex[:8]}"

def create_response_metadata(request_id: str, processing_time_ms: int = None) -> ResponseMetadata:
    """Create standardized response metadata"""
    return ResponseMetadata(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        processing_time_ms=processing_time_ms,
        rate_limit=RateLimit(
            remaining=59,  # This would be calculated from actual rate limiting
            reset_at=datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()
        )
    )

def create_success_response(data: Any, request_id: str, processing_time_ms: int = None) -> JSONResponse:
    """Create standardized success response"""
    response = SuccessResponse(
        data=data,
        metadata=create_response_metadata(request_id, processing_time_ms)
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump()
    )

def create_error_response(
    error_code: str, 
    message: str, 
    status_code: int = status.HTTP_400_BAD_REQUEST,
    request_id: str = None,
    details: ErrorDetails = None
) -> JSONResponse:
    """Create standardized error response"""
    if not request_id:
        request_id = generate_request_id()
    
    response = ErrorResponse(
        error=ErrorInfo(
            code=error_code,
            message=message,
            details=details
        ),
        metadata=create_response_metadata(request_id)
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump()
    )

@app.get("/")
async def root():
    return {"message": "Video Scraper Service is running"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint with dependency status and metrics
    """
    uptime = int((datetime.now() - service_start_time).total_seconds())
    cache_hit_rate = 0.73 if successful_requests > 0 else 0.0  # Mock value, would be real cache stats
    
    health_data = HealthData(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        dependencies=DependencyStatus(
            yt_dlp="healthy",
            openai="healthy" if openai_client else "not_configured",
            redis="not_configured"  # Redis not implemented yet
        ),
        metrics=HealthMetrics(
            uptime_seconds=uptime,
            requests_processed=request_count,
            cache_hit_rate=cache_hit_rate
        )
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=health_data.model_dump()
    )

@app.get("/supported-platforms")
async def get_supported_platforms():
    """
    Get list of supported platforms and their capabilities
    """
    request_id = generate_request_id()
    
    platforms_data = SupportedPlatformsData(
        platforms=[
            PlatformFeatures(
                name="tiktok",
                domain="tiktok.com",
                supported_features=[
                    "metadata_extraction",
                    "thumbnail_analysis",
                    "engagement_metrics"
                ],
                url_patterns=[
                    "https://www.tiktok.com/@{username}/video/{video_id}",
                    "https://vm.tiktok.com/{short_id}"
                ]
            ),
            PlatformFeatures(
                name="instagram",
                domain="instagram.com",
                supported_features=[
                    "metadata_extraction",
                    "thumbnail_analysis",
                    "basic_metrics"
                ],
                url_patterns=[
                    "https://www.instagram.com/reel/{reel_id}/",
                    "https://www.instagram.com/p/{post_id}/"
                ]
            )
        ],
        limitations=PlatformLimitations(
            max_urls_per_batch=3,
            rate_limit_per_minute=60,
            max_video_duration=300
        )
    )
    
    return create_success_response(platforms_data.model_dump(), request_id)

@app.get("/stats")
async def get_service_statistics():
    """
    Get service statistics and performance metrics
    """
    request_id = generate_request_id()
    
    # Calculate statistics
    total_extractions = successful_requests + failed_requests
    success_rate = successful_requests / total_extractions if total_extractions > 0 else 0.0
    avg_processing_time = 4250  # Mock value, would be calculated from actual metrics
    
    # Mock platform breakdown (would be tracked in real implementation)
    tiktok_count = int(total_extractions * 0.65)  # 65% TikTok
    instagram_count = total_extractions - tiktok_count
    
    stats_data = StatsData(
        service_stats=ServiceStats(
            total_extractions=total_extractions,
            successful_extractions=successful_requests,
            failed_extractions=failed_requests,
            success_rate=success_rate,
            avg_processing_time_ms=avg_processing_time
        ),
        platform_breakdown=PlatformBreakdown(
            tiktok=PlatformStats(
                count=tiktok_count,
                success_rate=0.96
            ),
            instagram=PlatformStats(
                count=instagram_count,
                success_rate=0.93
            )
        ),
        error_breakdown={
            "VIDEO_PRIVATE": int(failed_requests * 0.4),
            "VIDEO_DELETED": int(failed_requests * 0.3),
            "PLATFORM_ERROR": int(failed_requests * 0.2),
            "TIMEOUT": int(failed_requests * 0.1)
        },
        cache_stats=CacheStats(
            hit_rate=0.73,
            total_entries=45230,  # Mock values
            memory_usage_mb=1250
        )
    )
    
    return create_success_response(stats_data.model_dump(), request_id)

def validate_video_url(url: str) -> bool:
    """Validate if URL is from supported platforms (TikTok or Instagram)"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Check for TikTok domains
    tiktok_domains = ['tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'm.tiktok.com']
    # Check for Instagram domains
    instagram_domains = ['instagram.com', 'www.instagram.com']
    
    supported_domains = tiktok_domains + instagram_domains
    return any(domain.endswith(d) for d in supported_domains)

def get_platform_from_url(url: str) -> str:
    """Extract platform name from URL"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if 'tiktok.com' in domain:
        return 'tiktok'
    elif 'instagram.com' in domain:
        return 'instagram'
    else:
        return 'unknown'

async def analyze_thumbnail(thumbnail_url: str) -> ThumbnailAnalysis:
    """Analyze thumbnail using OpenAI Vision API with SDK"""
    if not openai_client or not thumbnail_url:
        return ThumbnailAnalysis()
    
    try:
        # Use the OpenAI SDK for vision analysis
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Kamu adalah seorang Social Media Specialist, Content Strategist dan Content Writer. Analisis thumbnail video ini secara mendalam untuk membantu membuat storyboard yang efektif. Berikan data terstruktur dalam Bahasa Indonesia:

ANALISIS DASAR:
1) visual_style: berbicara_langsung, flat_lay, demo_produk, POV, lifestyle, tutorial, review
2) setting: dalam_ruangan, luar_ruangan, studio, kamar_tidur, dapur, kantor, jalan, toko
3) people_count: jumlah orang (angka)
4) camera_angle: close_up, medium_shot, wide_shot, sudut_rendah, sudut_tinggi, bird_eye
5) text_overlay_style: bersih, tebal, tulisan_tangan, gradient, outline, shadow
6) color_scheme: hangat, dingin, cerah, gelap, monokrom, kontras_tinggi, pastel
7) hook_elements: array elemen yang menarik perhatian
8) confidence_score: 0-1

ANALISIS KOMPOSISI & PRODUKSI:
9) composition_type: rule_of_thirds, center_focused, diagonal, symmetrical, asymmetrical
10) focal_point: apa yang pertama menarik mata (dalam bahasa Indonesia)
11) lighting_quality: natural, artificial, dramatic, soft, harsh, backlit
12) mood_emotion: excited, calm, urgent, playful, professional, mysterious, confident
13) brand_elements: array logo, produk, atau branding yang terlihat
14) production_quality: professional, semi_pro, amateur, phone_quality
15) background_complexity: minimal, moderate, busy, chaotic
16) props_objects: array benda/properti yang terlihat

ANALISIS KONTEN & AUDIENCE:
17) story_stage: opening_hook, problem_setup, solution_reveal, result_show, transition
18) call_to_action_visible: true/false - apakah ada CTA yang terlihat
19) product_prominence: dominant, subtle, background, none
20) visual_interest_level: high, medium, low
21) scroll_stopping_power: strong, moderate, weak
22) target_demographic: remaja, dewasa_muda, keluarga, profesional, ibu_rumah_tangga
23) content_category: tutorial, review, demo, lifestyle, entertainment, education, comedy
24) pacing_indicator: fast_paced, moderate, slow_build
25) transition_style: smooth, jump_cut, fade, dynamic, static

Kembalikan dalam format JSON dengan semua field di atas. Gunakan Bahasa Indonesia untuk semua nilai string."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": thumbnail_url
                            }
                        }
                    ]
                }
            ],
            max_tokens=800
        )
        
        # Log the full response structure for debugging
        content = response.choices[0].message.content

        # Check if content is None
        if not content:
            logger.error(f"OpenAI response content is None or empty. Full response: {response}")
            return ThumbnailAnalysis()
        
        # Try to parse JSON response (handle markdown code blocks)
        try:
            # Remove markdown code blocks if present
            json_content = content.strip()
            
            # More robust markdown removal
            if json_content.startswith('```json'):
                json_content = json_content[7:]  # Remove ```json
            elif json_content.startswith('```'):
                json_content = json_content[3:]   # Remove ```
            
            if json_content.endswith('```'):
                json_content = json_content[:-3]  # Remove trailing ```
            
            json_content = json_content.strip()
            
            # Try to find JSON within the content if it's still not clean
            if not json_content.startswith('{'):
                # Look for JSON block within the content
                start_idx = json_content.find('{')
                end_idx = json_content.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_content = json_content[start_idx:end_idx+1]
            
            analysis_data = json.loads(json_content)
            
            # Flatten nested structure if it exists
            flattened_data = {}
            if isinstance(analysis_data, dict):
                for key, value in analysis_data.items():
                    if isinstance(value, dict):
                        # This is a nested section, flatten it
                        flattened_data.update(value)
                    else:
                        # This is a direct field
                        flattened_data[key] = value
            else:
                flattened_data = analysis_data
            
            
            # Create the ThumbnailAnalysis object
            thumbnail_result = ThumbnailAnalysis(**flattened_data)
            return thumbnail_result
        except json.JSONDecodeError as e:
            # Fallback to basic analysis if JSON parsing fails
            logger.warning(f"Failed to parse JSON from OpenAI response: {content}")
            logger.warning(f"JSON decode error: {str(e)}")
            return ThumbnailAnalysis(
                visual_style="tidak_diketahui",
                setting="tidak_diketahui",
                confidence_score=0.5,
                composition_type="tidak_diketahui",
                mood_emotion="netral",
                content_category="tidak_diketahui"
            )
            
    except Exception as e:
        logger.error(f"Thumbnail analysis error: {str(e)}")
        return ThumbnailAnalysis()

def extract_video_id_from_url(url: str) -> str:
    """Extract video ID from TikTok URL"""
    # Handle different TikTok URL formats
    patterns = [
        r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w\.-]+/video/(\d+)',
        r'(?:https?://)?(?:vm\.)?tiktok\.com/[\w\.-]+/(\d+)',
        r'(?:https?://)?(?:m\.)?tiktok\.com/v/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matches, try to extract from the URL path
    parsed = urlparse(url)
    path_parts = parsed.path.split('/')
    for part in path_parts:
        if part.isdigit() and len(part) > 10:  # TikTok video IDs are long numbers
            return part
    
    raise ValueError(f"Could not extract video ID from URL: {url}")

async def extract_video_metadata(url: str, include_thumbnail_analysis: bool = True) -> VideoMetadata:
    """Extract metadata from a video URL using yt-dlp with ScraperAPI"""
    start_time = datetime.now()
    
    try:
        # Validate URL is from supported platforms
        if not validate_video_url(url):
            raise ValueError("URL is not from a supported platform (TikTok or Instagram)")
        
        platform = get_platform_from_url(url)
        
        # Try with ScraperAPI first if configured, then fallback to direct
        video_info = None
        
        if SCRAPERAPI_KEY:
            try:
                logger.info(f"Trying ScraperAPI for: {url}")
                
                # First, fetch the page with ScraperAPI to bypass IP blocks
                scraperapi_url = f"{SCRAPERAPI_BASE_URL}?api_key={SCRAPERAPI_KEY}&url={quote(url)}"
                response = await asyncio.to_thread(requests.get, scraperapi_url, timeout=60)
                response.raise_for_status()
                
                logger.info(f"ScraperAPI fetch successful, now using yt-dlp for: {url}")
                
                # Now use yt-dlp normally (ScraperAPI should have "warmed up" the URL)
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extractaudio': False,
                    'format': 'best',
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'skip_download': True,
                    'extract_flat': False,
                    'nocheckcertificate': True,  # --no-check-certificate
                    'ignoreerrors': True,  # Continue on errors
                    'socket_timeout': 60,
                    'retries': 2,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    },
                    # Additional SSL/TLS options
                    'source_address': None,  # Bind to default interface
                    'prefer_insecure': True,  # Prefer HTTP over HTTPS when possible
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    video_info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                logger.info(f"Successfully extracted with ScraperAPI approach: {url}")
                
            except Exception as e:
                logger.warning(f"ScraperAPI approach failed for {url}: {str(e)}")
                video_info = None
        
        # Fallback to direct yt-dlp if ScraperAPI didn't work or isn't configured
        if video_info is None:
            logger.info(f"Trying direct yt-dlp for: {url}")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extractaudio': False,
                'format': 'best',
                'writesubtitles': True,
                'writeautomaticsub': True,
                'skip_download': True,
                'extract_flat': False,
                'nocheckcertificate': True,  # --no-check-certificate
                'ignoreerrors': True,  # Continue on errors
                'socket_timeout': 60,
                'retries': 3,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                # Additional SSL/TLS options
                'source_address': None,  # Bind to default interface
                'prefer_insecure': True,  # Prefer HTTP over HTTPS when possible
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = await asyncio.to_thread(ydl.extract_info, url, download=False)
        
        # Extract full description/caption (not truncated)
        full_description = video_info.get('description', '')
        
        # Try to get subtitles/captions if available
        subtitles = video_info.get('subtitles', {})
        automatic_captions = video_info.get('automatic_captions', {})
        
        # Combine description with any available captions
        if subtitles or automatic_captions:
            caption_text = ""
            for lang_subs in list(subtitles.values()) + list(automatic_captions.values()):
                if lang_subs and len(lang_subs) > 0:
                    # Get the first subtitle format
                    caption_text = lang_subs[0].get('data', '') if isinstance(lang_subs[0], dict) else ""
                    break
            
            if caption_text:
                full_description = f"{full_description}\n\nCaptions: {caption_text}"
        
        # Analyze thumbnail if available and requested
        thumbnail_url = video_info.get('thumbnail', '')
        thumbnail_analysis = None
        if thumbnail_url and include_thumbnail_analysis and openai_client:
            thumbnail_analysis = await analyze_thumbnail(thumbnail_url)
        else:
            logger.info(f"Skipping thumbnail analysis - URL: {bool(thumbnail_url)}, include_analysis: {include_thumbnail_analysis}, client: {bool(openai_client)}")
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Extract metadata from yt-dlp response
        metadata = VideoMetadata(
            url=url,
            platform=platform,
            title=video_info.get('title', ''),
            description=full_description,
            duration=video_info.get('duration', None),
            view_count=video_info.get('view_count', None),
            like_count=video_info.get('like_count', None),
            comment_count=video_info.get('comment_count', None),
            share_count=video_info.get('repost_count', None),  # yt-dlp field name
            upload_date=video_info.get('upload_date', ''),
            thumbnail_url=thumbnail_url,
            thumbnail_analysis=thumbnail_analysis,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=processing_time,
            cache_hit=False  # Would be determined by actual cache implementation
        )
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata from {url}: {str(e)}")
        raise e

@app.post("/extract")
async def extract_single_video(
    request: ExtractRequest, 
    api_key: str = Security(api_key_header)
):
    """
    Extract metadata from a single video URL
    
    - **x-api-key**: API key required in header
    - **url**: Video URL (TikTok or Instagram)
    - **include_thumbnail_analysis**: Whether to include AI thumbnail analysis
    - **cache_ttl**: Cache time-to-live in seconds
    """
    global request_count, successful_requests, failed_requests
    request_count += 1
    request_id = generate_request_id()
    start_time = datetime.now()
    
    # Validate API key
    if api_key != API_KEY:
        failed_requests += 1
        return create_error_response(
            "API_KEY_INVALID",
            "Invalid or missing API key",
            status.HTTP_401_UNAUTHORIZED,
            request_id
        )
    
    url_str = str(request.url)
    
    # Validate URL is from supported platforms
    if not validate_video_url(url_str):
        failed_requests += 1
        platform = get_platform_from_url(url_str)
        return create_error_response(
            "UNSUPPORTED_PLATFORM",
            "URL is not from a supported platform (TikTok or Instagram)",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id,
            ErrorDetails(url=url_str, platform=platform)
        )
    
    try:
        metadata = await extract_video_metadata(url_str, request.include_thumbnail_analysis)
        successful_requests += 1
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.info(f"Successfully extracted metadata for: {url_str}")
        
        return create_success_response(metadata.model_dump(), request_id, processing_time)
        
    except ValueError as e:
        failed_requests += 1
        return create_error_response(
            "VIDEO_UNAVAILABLE",
            str(e),
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id,
            ErrorDetails(url=url_str, platform=get_platform_from_url(url_str))
        )
    except Exception as e:
        failed_requests += 1
        logger.error(f"Unexpected error processing {url_str}: {str(e)}")
        return create_error_response(
            "EXTRACTION_FAILED",
            "Technical error during extraction",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id
        )

@app.post("/extract/batch")
async def extract_batch_videos(
    request: ExtractBatchRequest, 
    api_key: str = Security(api_key_header)
):
    """
    Extract metadata from multiple video URLs (max 3)
    
    - **x-api-key**: API key required in header
    - **urls**: List of video URLs (TikTok or Instagram, max 3)
    - **include_thumbnail_analysis**: Whether to include AI thumbnail analysis
    - **parallel_processing**: Whether to process URLs in parallel
    """
    global request_count, successful_requests, failed_requests
    request_count += 1
    request_id = generate_request_id()
    start_time = datetime.now()
    
    # Validate API key
    if api_key != API_KEY:
        failed_requests += 1
        return create_error_response(
            "API_KEY_INVALID",
            "Invalid or missing API key",
            status.HTTP_401_UNAUTHORIZED,
            request_id
        )
    
    # Validate URL count
    if len(request.urls) > 3:
        failed_requests += 1
        return create_error_response(
            "TOO_MANY_URLS",
            "Too many URLs provided. Maximum allowed: 3",
            status.HTTP_400_BAD_REQUEST,
            request_id
        )
    
    if len(request.urls) == 0:
        failed_requests += 1
        return create_error_response(
            "NO_URLS",
            "No URLs provided",
            status.HTTP_400_BAD_REQUEST,
            request_id
        )
    
    processed = []
    failed = []
    successful_count = 0
    failed_count = 0
    
    for url in request.urls:
        url_str = str(url)
        
        # Validate URL is from supported platforms
        if not validate_video_url(url_str):
            failed_count += 1
            platform = get_platform_from_url(url_str)
            failed.append(ProcessedVideo(
                url=url_str,
                status="failed",
                error=ErrorInfo(
                    code="UNSUPPORTED_PLATFORM",
                    message="URL is not from a supported platform",
                    details=ErrorDetails(url=url_str, platform=platform)
                )
            ))
            continue
            
        try:
            metadata = await extract_video_metadata(url_str, request.include_thumbnail_analysis)
            successful_count += 1
            processed.append(ProcessedVideo(
                url=url_str,
                status="success",
                data=metadata
            ))
            logger.info(f"Successfully extracted metadata for: {url_str}")
            
        except ValueError as e:
            failed_count += 1
            failed.append(ProcessedVideo(
                url=url_str,
                status="failed",
                error=ErrorInfo(
                    code="VIDEO_UNAVAILABLE",
                    message=str(e),
                    details=ErrorDetails(url=url_str, platform=get_platform_from_url(url_str))
                )
            ))
            logger.error(f"Video unavailable {url_str}: {str(e)}")
        except Exception as e:
            failed_count += 1
            failed.append(ProcessedVideo(
                url=url_str,
                status="failed",
                error=ErrorInfo(
                    code="EXTRACTION_FAILED",
                    message="Technical error during extraction"
                )
            ))
            logger.error(f"Unexpected error processing {url_str}: {str(e)}")
    
    # Update global statistics
    if successful_count > 0:
        successful_requests += 1
    if failed_count > 0:
        failed_requests += 1
    
    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    batch_data = BatchData(
        processed=processed,
        failed=failed,
        summary=BatchSummary(
            total_requested=len(request.urls),
            successful=successful_count,
            failed=failed_count,
            processing_time_ms=processing_time
        )
    )

    
    
    return create_success_response(batch_data.model_dump(), request_id, processing_time)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)