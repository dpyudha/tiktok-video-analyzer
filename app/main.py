"""Main FastAPI application with modular architecture."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import VideoScraperBaseException
from app.api import extraction_router, health_router
from app.utils.logging import LoggerSetup
from app.utils.response_helpers import ResponseHelper

# Setup logging
LoggerSetup.setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"🚀 {settings.api_title} v{settings.api_version} starting up...")
    yield
    # Shutdown
    print("📪 Application shutting down...")

# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
    }
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure OpenAPI security scheme
def custom_openapi():
    """Custom OpenAPI configuration with security."""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
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
    
    # Apply security to protected endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method in ["post"] and path in ["/extract", "/extract/batch", "/extract-transcript"]:
                openapi_schema["paths"][path][method]["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Global exception handler for custom exceptions
@app.exception_handler(VideoScraperBaseException)
async def video_scraper_exception_handler(request, exc: VideoScraperBaseException):
    """Handle custom video scraper exceptions."""
    return ResponseHelper.create_error_from_exception(exc)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions."""
    return ResponseHelper.create_error_response(
        error_code="HTTP_ERROR",
        message=exc.detail,
        status_code=exc.status_code
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    import traceback
    traceback.print_exc()  # Log full traceback in development
    
    return ResponseHelper.create_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        status_code=500
    )

# Include routers
app.include_router(health_router)
app.include_router(extraction_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug_mode,
        log_level=settings.log_level.lower()
    )