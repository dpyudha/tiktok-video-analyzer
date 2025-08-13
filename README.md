# Video Scraper Service

A high-performance FastAPI service for extracting metadata from TikTok videos using yt-dlp with AI-powered thumbnail analysis.

## Features

- **TikTok Video Extraction**: Extract comprehensive metadata from TikTok URLs
- **AI Thumbnail Analysis**: OpenAI Vision API integration for intelligent thumbnail analysis
- **Batch Processing**: Process multiple URLs simultaneously (max 3 per request)
- **Intelligent Caching**: Multi-backend caching (in-memory by default, Redis optional for production)
- **Rate Limiting**: Built-in protection against abuse
- **RESTful API**: Clean, documented API with proper error handling
- **Health Monitoring**: Comprehensive health checks and service metrics
- **Multilingual Support**: English and Indonesian analysis support

## Quick Start

1. **Clone and Setup**:
```bash
git clone <repository-url>
cd video-scraper-service
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
3. **External APIs** → yt-dlp extraction + OpenAI analysis
4. **Response** → Structured JSON with metadata

## API Endpoints

### Core Extraction Endpoints

#### POST /extract
Extract metadata from a single TikTok video URL with optional AI analysis.

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
  "cache_ttl": 3600
}
```

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
    "extracted_at": "2024-03-15T10:30:00Z",
    "processing_time_ms": 3420,
    "cache_hit": false
  },
  "metadata": {
    "request_id": "req_abc123",
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
  "parallel_processing": true
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "processed": [
      {
        "url": "https://www.tiktok.com/@user1/video/123",
        "status": "success",
        "data": { /* video metadata */ }
      }
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
      "processing_time_ms": 8750
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

- `INVALID_URL`: URL format is invalid or not from TikTok
- `VIDEO_UNAVAILABLE`: Video is private, deleted, or restricted
- `NOT_VIDEO_CONTENT`: URL contains non-video content
- `VIDEO_TOO_LONG`: Video exceeds maximum duration limit
- `EXTRACTION_FAILED`: Technical error during extraction
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `API_KEY_INVALID`: Invalid or missing API key
- `THUMBNAIL_ANALYSIS_FAILED`: OpenAI Vision API error

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

See `.env.example` for complete configuration options with descriptions.

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
docker build -t video-scraper-service .

# Run the container
docker run -p 8000:8000 --env-file .env video-scraper-service
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
