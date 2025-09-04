# Tiktok Video Analyzer

[![CI](https://github.com/dpyudha/tiktok-video-analyzer/workflows/CI/badge.svg)](https://github.com/dpyudha/tiktok-video-analyzer/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-29%20passing-brightgreen.svg)](#testing)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

A FastAPI service for extracting metadata from TikTok videos with AI thumbnail analysis and transcript generation.

## Features

- **TikTok Video Extraction**: Extract metadata from TikTok URLs
- **AI Thumbnail Analysis**: OpenAI Vision API for thumbnail analysis
- **Transcript Generation**: Extract subtitles with quality assessment
- **Batch Processing**: Process up to 3 URLs simultaneously
- **Anti-Block Protection**: ScraperAPI integration to avoid rate limiting
- **Caching**: In-memory caching (Redis optional for production)
- **Rate Limiting**: Built-in protection against abuse
- **Health Monitoring**: Service health checks and metrics

## Quick Start

1. **Clone and Setup**:
```bash
git clone https://github.com/dpyudha/tiktok-video-analyzer.git
cd tiktok-video-analyzer
pip install -r requirements.txt
```

2. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Run the Service**:
```bash
python main.py
```

The service will be available at `http://localhost:8000`

4. **View API Documentation**:
Visit `http://localhost:8000/docs` for interactive API documentation

5. **Quick Test with Transcript**:
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tiktok.com/@user/video/1234567890",
    "include_transcript": true,
    "include_thumbnail_analysis": true
  }'
```

## Transcript Generation

Extracts subtitles from TikTok videos with timing and quality assessment.

**Features:**
- Language prioritization (Indonesian → English)
- Quality scoring and confidence assessment
- Accurate timing for each segment
- Text cleaning and normalization

**Processing:**
1. Detect available subtitle tracks
2. Select best language and format
3. Parse subtitles with timing
4. Assess quality and generate confidence score
5. Return structured segments with metadata

## Architecture

### 🏗️ Modular Design

The service is built with a clean, modular architecture following FastAPI best practices:

```
app/
├── api/                    # API route handlers
│   ├── extraction.py       # Video extraction endpoints
│   └── health.py          # Health and monitoring endpoints
├── core/                  # Core application components
│   ├── config.py          # Configuration management
│   ├── dependencies.py    # Dependency injection
│   └── exceptions.py      # Custom exception classes
├── models/                # Pydantic data models
│   ├── requests.py        # Request schemas
│   ├── responses.py       # Response schemas
│   └── video.py          # Video-related models
├── services/              # Business logic layer
│   ├── video_extractor.py # Core video extraction
│   ├── thumbnail_analyzer.py # AI thumbnail analysis
│   ├── transcript_service.py # Intelligent transcript extraction
│   ├── batch_processor.py # Concurrent processing
│   └── cache_service.py   # Caching layer
├── config/                # Configuration and templates
│   ├── prompts/           # AI prompt templates
│   │   └── thumbnail_analysis/
│   │       ├── en.yaml    # English prompts
│   │       ├── id.yaml    # Indonesian prompts
│   │       └── schema.yaml # Validation schema
│   └── schemas/           # Validation schemas
└── utils/                 # Utility functions
    ├── validators.py      # Input validation
    ├── response_helpers.py # Response formatting
    └── logging.py         # Logging utilities
```

### ⚡ Key Components

- **API Layer**: Clean route handlers with automatic validation
- **Service Layer**: Business logic with dependency injection
- **Caching Layer**: Multi-backend caching (in-memory by default, Redis optional)
- **Configuration**: Environment-based with YAML templates
- **Validation**: Pydantic V2 with custom validators
- **Error Handling**: Structured exceptions with proper HTTP mapping

### 🔄 Request Flow

1. **API Request** → Route handler validates input
2. **Service Layer** → Checks cache, processes video
3. **External APIs** → yt-dlp extraction + OpenAI analysis + transcript processing
4. **Response** → Structured JSON with metadata, thumbnails, and transcripts

## API Endpoints

### Core Extraction Endpoints

#### POST /extract
Extract metadata from a TikTok video URL with optional AI analysis and transcript generation.

**Headers:**
```
x-api-key: your-api-key-here
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://www.tiktok.com/@user/video/1234567890",
  "include_thumbnail_analysis": true,
  "include_transcript": true,
  "cache_ttl": 3600
}
```

**Parameters:**
- `url` (string, required): TikTok video URL
- `include_thumbnail_analysis` (boolean, optional): Enable AI thumbnail analysis (default: false)
- `include_transcript` (boolean, optional): Enable transcript extraction (default: false)
- `cache_ttl` (integer, optional): Cache time-to-live in seconds (default: 3600)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "url": "https://www.tiktok.com/@user/video/1234567890",
    "platform": "tiktok",
    "title": "5 minute morning routine that changed my life",
    "description": "Start your day right with these simple habits #morningroutine #productivity",
    "duration": 23,
    "view_count": 2500000,
    "like_count": 45000,
    "comment_count": 1200,
    "share_count": 8500,
    "upload_date": "2024-03-10",
    "uploader": "username",
    "thumbnail_url": "https://p16-sign.tiktokcdn.com/...",
    "has_transcript": true,
    "transcript_language": "id",
    "transcript_confidence": 0.92,
    "thumbnail_analysis": {
      "visual_style": "talking_head",
      "setting": "modern_bedroom",
      "people_count": 1,
      "camera_angle": "medium_close_up",
      "text_overlay_style": "clean_white_on_dark",
      "color_scheme": "warm_bright_tones",
      "hook_elements": ["coffee_cup", "surprised_expression"],
      "confidence_score": 0.87
    },
    "transcript": {
      "language": "id",
      "confidence_score": 0.92,
      "total_segments": 8,
      "total_duration": 23.45,
      "segments": [
        {
          "start": 0.0,
          "end": 3.2,
          "text": "Pagi teman-teman! Ini adalah rutinitas 5 menit yang mengubah hidup saya"
        },
        {
          "start": 3.2,
          "end": 7.8,
          "text": "Pertama, saya langsung minum segelas air putih untuk menghidrasi tubuh"
        },
        {
          "start": 7.8,
          "end": 12.5,
          "text": "Kedua, stretching ringan selama 2 menit untuk bangunkan otot-otot"
        },
        {
          "start": 12.5,
          "end": 18.1,
          "text": "Ketiga, menulis 3 hal yang saya syukuri hari ini di jurnal"
        },
        {
          "start": 18.1,
          "end": 23.0,
          "text": "Dan terakhir, setting intention untuk hari ini. Coba deh, pasti berasa bedanya!"
        }
      ],
      "metadata": {
        "format": "vtt",
        "source": "auto-generated",
        "quality": "high"
      }
    },
    "extracted_at": "2024-03-15T10:30:00Z",
    "processing_time_ms": 4850,
    "cache_hit": false
  },
  "metadata": {
    "request_id": "req_abc123",
    "api_version": "1.0.0"
  }
}
```

**Simple Request (Backward Compatible):**
```json
{
  "url": "https://www.tiktok.com/@user/video/1234567890"
}
```

**Simple Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "url": "https://www.tiktok.com/@user/video/1234567890",
    "platform": "tiktok",
    "title": "Amazing video title",
    "description": "Video description here",
    "duration": 15,
    "view_count": 100000,
    "like_count": 5000,
    "uploader": "username",
    "has_transcript": false,
    "transcript_language": null,
    "transcript_confidence": null,
    "extracted_at": "2024-03-15T10:30:00Z",
    "processing_time_ms": 2100,
    "cache_hit": false
  },
  "metadata": {
    "request_id": "req_simple_123",
    "api_version": "1.0.0"
  }
}
```

#### POST /extract/batch
Extract metadata from multiple TikTok video URLs (max 3 per request).

**Request Body:**
```json
{
  "urls": [
    "https://www.tiktok.com/@user1/video/123",
    "https://www.tiktok.com/@user2/video/456",
    "https://www.tiktok.com/@user3/video/789"
  ],
  "include_thumbnail_analysis": true,
  "include_transcript": true,
  "parallel_processing": true
}
```

**Parameters:**
- `urls` (array, required): Array of TikTok video URLs (max 3)
- `include_thumbnail_analysis` (boolean, optional): Enable AI thumbnail analysis (default: false)
- `include_transcript` (boolean, optional): Enable transcript extraction (default: false)
- `parallel_processing` (boolean, optional): Process URLs concurrently (default: true)

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "processed": [
      {
        "url": "https://www.tiktok.com/@user1/video/123",
        "status": "success",
        "data": { 
          /* Complete video metadata with transcript if requested */
          "has_transcript": true,
          "transcript_language": "en",
          "transcript_confidence": 0.89,
          "transcript": { /* TranscriptExtractionResult object */ }
        }
      },
    ],
    "failed": [
      {
        "url": "https://www.tiktok.com/@user2/video/456",
        "status": "failed",
        "error": {
          "code": "VIDEO_PRIVATE",
          "message": "Video is private or deleted"
        }
      }
    ],
    "summary": {
      "total_requested": 3,
      "successful": 2,
      "failed": 1,
      "transcripts_found": 1,
      "processing_time_ms": 12450
    }
  }
}
```

### Monitoring & Information Endpoints

#### GET /
Root endpoint - service status check.

#### GET /health
Comprehensive health check with dependency status and metrics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-15T10:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "yt_dlp": "healthy",
    "openai": "healthy",
    "redis": "healthy"
  },
  "metrics": {
    "uptime_seconds": 86400,
    "requests_processed": 15420,
    "cache_hit_rate": 0.73
  }
}
```

#### GET /supported-platforms
Get information about supported platforms and their capabilities.

#### GET /stats
Detailed service statistics including performance metrics and error breakdown.

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Additional context
    }
  },
  "metadata": {
    "request_id": "req_unique_id",
    "timestamp": "2024-03-15T10:30:00Z"
  }
}
```

### Common Error Codes

- `INVALID_URL`: URL format is invalid or not from supported platforms
- `VIDEO_UNAVAILABLE`: Video is private, deleted, or restricted
- `NOT_VIDEO_CONTENT`: URL contains non-video content
- `VIDEO_TOO_LONG`: Video exceeds maximum duration limit
- `EXTRACTION_FAILED`: Technical error during extraction
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `API_KEY_INVALID`: Invalid or missing API key
- `THUMBNAIL_ANALYSIS_FAILED`: OpenAI Vision API error
- `TRANSCRIPT_EXTRACTION_FAILED`: Error processing video transcripts
- `TRANSCRIPT_UNAVAILABLE`: No subtitles available for transcript extraction

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_cache.py -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=app --cov-report=html
```

### Test Structure
```
tests/
├── unit/                      # Unit tests
│   ├── test_validators.py     # URL validation tests
│   ├── test_cache.py         # Cache system tests
│   └── test_exceptions.py    # Exception handling tests
└── test_main.py              # Application startup tests
```

## Configuration

### Environment Variables

The service uses environment variables for configuration. Copy `.env.example` to `.env` and configure:

**Required Variables:**
- `API_KEY`: API key for authentication 
- `OPENAI_API_KEY`: OpenAI API key for thumbnail analysis

**Optional Variables:**
- `DEBUG_MODE`: Enable debug logging (default: false)
- `MAX_CONCURRENT_EXTRACTIONS`: Max parallel extractions (default: 5)
- `CACHE_ENABLED`: Enable result caching (default: true)
- `REDIS_URL`: Redis URL for distributed caching (optional - falls back to in-memory cache)
- `SCRAPERAPI_KEY`: ScraperAPI key for anti-block protection (highly recommended for production)

**Performance Notes:**
- **Base Extraction**: 3-8 seconds per video without optional features
- **With Thumbnail Analysis**: +2-4 seconds (requires OpenAI API)
- **With Transcript Extraction**: +2-5 seconds (subtitle processing)
- **Combined Features**: 8-15 seconds total processing time
- **Batch Processing**: Concurrent processing reduces total time for multiple URLs

See `.env.example` for complete configuration options with descriptions.

### Anti-Block Protection with ScraperAPI

**Why ScraperAPI?**
TikTok actively blocks automated requests and implements rate limiting. ScraperAPI provides rotating proxies and handles anti-bot measures, significantly improving extraction reliability.

**Setup ScraperAPI:**
1. Sign up at [ScraperAPI.com](https://www.scraperapi.com/)
2. Get your API key from the dashboard
3. Add to your `.env` file:
   ```bash
   SCRAPERAPI_KEY=your-scraperapi-key-here
   ```

**Benefits:**
- ✅ Bypasses TikTok rate limiting and blocks
- ✅ Rotating IP addresses for better success rates
- ✅ Automatic retry logic for failed requests
- ✅ Higher extraction success rate (90%+ vs 60% without)

**Usage:**
When `SCRAPERAPI_KEY` is configured, the service automatically uses ScraperAPI for video extraction. No code changes needed - it's transparent to the API.

### Caching Strategy

The service supports multiple caching backends:

- **In-Memory Cache (Default)**: Works out-of-the-box, no additional setup required
- **Redis Cache (Optional)**: For production deployments with multiple instances

**Cache Behavior:**
- If `REDIS_URL` is not set → Uses in-memory cache
- If `REDIS_URL` is set → Attempts to use Redis, falls back to in-memory on failure
- Cache stores video metadata for 1 hour by default (configurable via `CACHE_TTL_SECONDS`)

**For Production:**
```bash
# Enable Redis caching
REDIS_URL=redis://localhost:6379/0
# or for cloud Redis
REDIS_URL=redis://username:password@redis-host:6379/0
```

## Deployment

### Docker Support

Build and run with Docker:

```bash
# Build the image
docker build -t tiktok-video-analyzer .

# Run the container
docker run -p 8000:8000 --env-file .env tiktok-video-analyzer
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

### Cloud Deployment

This service is optimized for deployment on:
- **Railway**: Zero-config deployment with automatic HTTPS
- **Render**: Easy deployment with built-in monitoring  
- **Heroku**: Classic PaaS deployment
- **VPS/Dedicated Server**: Full control deployment

### Production Considerations

1. **API Keys**: Use secure environment variable management
2. **Rate Limiting**: Configure `MAX_REQUESTS_PER_MINUTE` based on your needs
3. **Caching**: Optionally use Redis for distributed caching in production (in-memory cache works for single instances)
4. **Monitoring**: Enable metrics collection with `ENABLE_METRICS=true`
5. **Logging**: Set appropriate `LOG_LEVEL` for production (INFO or WARNING)
