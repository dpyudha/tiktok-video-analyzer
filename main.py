"""Entry point for the refactored FastAPI Video Scraper Service."""

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    from app.core.config import settings
    
    print(f"🚀 Starting {settings.api_title} v{settings.api_version}")
    print(f"📊 Cache enabled: {settings.cache_enabled}")
    print(f"🔧 Max concurrent extractions: {settings.max_concurrent_extractions}")
    print(f"📝 Log level: {settings.log_level}")
    
    uvicorn.run(
        "app.main:app",  # Use string import for hot reload
        host="0.0.0.0",
        port=8000,
        reload=settings.debug_mode,
        log_level=settings.log_level.lower()
    )