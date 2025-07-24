# Video Scraper Service

A FastAPI service for extracting metadata from TikTok and Instagram videos using yt-dlp.

## Features

- Extract video metadata from TikTok and Instagram URLs
- Validate URLs to ensure they're from supported platforms
- Batch processing of multiple URLs (max 3)
- RESTful API with proper error handling
- Structured response format with metadata

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export API_KEY="your-secret-api-key-here"
export INSTAGRAM_USERNAME="your-instagram-username"
export INSTAGRAM_PASSWORD="your-instagram-password"
```

3. Run the service:
```bash
python main.py
```

The service will be available at `http://localhost:8000`

## API Endpoints

### GET /
Health check endpoint

### GET /health
Service health status

### POST /scrape
Scrape metadata from multiple video URLs

**Headers:**
```
x-api-key: your-api-key-here
```

**Request Body:**
```json
{
  "urls": [
    "https://www.tiktok.com/@user/video/123",
    "https://www.instagram.com/reel/abc123"
  ],
  "max_urls": 3
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "url": "https://www.tiktok.com/@user/video/123",
      "title": "Video Title",
      "description": "Video description",
      "duration": 30,
      "view_count": 1000,
      "like_count": 50,
      "comment_count": 10,
      "upload_date": "20231201",
      "uploader": "username",
      "thumbnail": "https://...",
      "platform": "tiktok",
      "width": 1080,
      "height": 1920,
      "fps": 30.0
    }
  ],
  "errors": []
}
```

### POST /scrape-single
Scrape metadata from a single video URL

**Headers:**
```
x-api-key: your-api-key-here
```

**Request Body:**
```json
{
  "url": "https://www.tiktok.com/@user/video/123"
}
```

## Deployment

This service is designed to be deployed on Railway, Render, or a dedicated VPS.

### Environment Variables

- `API_KEY`: API key for authentication (required)
- `INSTAGRAM_USERNAME`: Instagram username for authentication (optional, helps with rate limiting)
- `INSTAGRAM_PASSWORD`: Instagram password for authentication (optional, helps with rate limiting)
- `PORT`: Port to run the service on (default: 8000)
- `HOST`: Host to bind to (default: 0.0.0.0)

### Docker Support

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```