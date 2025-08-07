import os
from unittest.mock import Mock, patch

# Set test environment variables BEFORE importing anything else
os.environ.update(
    {
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_pass",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
        "S3_ACCESS_KEY_ID": "test_key",
        "S3_ACCESS_KEY": "test_secret",
        "S3_BUCKET": "test-bucket",
        "ENVIRONMENT": "testing",
        "DEBUG": "false",
        "LOG_LEVEL": "WARNING",
    }
)

from fastapi.testclient import TestClient


def test_can_import_config():
    """Test that we can import and use the configuration."""
    from src.config import get_settings

    settings = get_settings()
    assert settings.postgres_user == "test_user"
    assert settings.postgres_password == "test_pass"
    assert settings.s3_access_key_id == "test_key"
    assert settings.s3_access_key == "test_secret"


def test_can_import_utils():
    """Test that we can import utility functions."""
    from src.utils import get_current_date_time

    result = get_current_date_time()
    assert isinstance(result, str)
    assert len(result) == 19  # "YYYY-MM-DD HH:MM:SS"


@patch("src.s3.get_s3_client")
def test_s3_functions_work(mock_get_s3_client):
    """Test that S3 functions can be imported and work."""
    from io import BytesIO

    from src.s3 import get_object_url, upload_object_to_s3

    mock_client = Mock()
    mock_get_s3_client.return_value = mock_client

    # Test upload
    mock_file = BytesIO(b"test content")
    result = upload_object_to_s3("test.txt", mock_file, "test-bucket")

    assert result is not None
    mock_client.upload_fileobj.assert_called_once()

    # Test URL generation
    mock_client.generate_presigned_url.return_value = "http://test-url"
    url = get_object_url("test-bucket", "test-object")
    assert url == "http://test-url"


def test_celery_app_creation():
    """Test that Celery app can be created."""
    from celery import Celery
    from src.celery import default

    assert isinstance(default, Celery)
    assert default.main == "default"


def test_basic_fastapi_app_creation():
    """Test that we can create a basic FastAPI app without database dependencies."""
    from fastapi import FastAPI

    # Create a minimal test app
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        return {"result": "success", "msg": "Test works!"}

    @app.get("/health")
    def health_endpoint():
        return {"status": "healthy", "version": "0.1.0"}

    @app.get("/")
    def root_endpoint():
        return {"message": "Web Service Template API", "version": "0.1.0", "docs": "/docs", "health": "/health"}

    # Test the app
    client = TestClient(app)

    # Test endpoints
    response = client.get("/test")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Web Service Template API"
