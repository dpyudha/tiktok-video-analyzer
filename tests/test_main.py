"""Basic tests for the refactored application."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)

def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Video Scraper Service is running"

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "dependencies" in data
    assert "metrics" in data

def test_supported_platforms_endpoint(client):
    """Test supported platforms endpoint."""
    response = client.get("/supported-platforms")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "platforms" in data["data"]
    assert len(data["data"]["platforms"]) >= 1  # TikTok only

def test_stats_endpoint(client):
    """Test statistics endpoint."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "service_stats" in data["data"]
    assert "cache_stats" in data["data"]

def test_extract_endpoint_without_api_key(client):
    """Test extract endpoint without API key should fail."""
    response = client.post("/extract", json={
        "url": "https://www.tiktok.com/@test/video/123456789"
    })
    assert response.status_code == 403  # Forbidden due to missing API key

def test_extract_endpoint_with_invalid_api_key(client):
    """Test extract endpoint with invalid API key should fail."""
    response = client.post("/extract", json={
        "url": "https://www.tiktok.com/@test/video/123456789"
    }, headers={"x-api-key": "invalid-key"})
    assert response.status_code == 401  # Unauthorized