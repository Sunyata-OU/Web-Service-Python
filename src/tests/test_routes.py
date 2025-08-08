import os
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from src.tests.utils import client

# Skip S3 integration tests if S3 service is not available
skip_s3_integration = pytest.mark.skipif(
    os.environ.get("ENVIRONMENT") == "testing", reason="S3 integration tests require MinIO service"
)


class TestIndexRoute:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Web Service Template API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestS3Routes:
    @skip_s3_integration
    def test_s3_upload_success(self):
        """Test S3 upload success - requires S3 service."""
        file_content = b"test file content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        response = client.post("/s3/s3-upload", files=files)
        assert response.status_code == status.HTTP_200_OK

    @patch("src.routes.s3.upload_object_to_s3")
    @patch("src.routes.s3.get_async_db")
    def test_s3_upload_failure_no_file(self, mock_get_async_db, mock_upload):
        mock_db = Mock()
        mock_get_async_db.return_value = mock_db

        response = client.post("/s3/s3-upload")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("src.routes.s3.upload_object_to_s3")
    @patch("src.routes.s3.get_async_db")
    def test_s3_upload_failure_upload_fails(self, mock_get_async_db, mock_upload):
        mock_db = Mock()
        mock_get_async_db.return_value = mock_db
        mock_upload.return_value = None

        file_content = b"test file content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post("/s3/s3-upload", files=files)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"result": "fail"}

    @skip_s3_integration
    def test_s3_objects_list(self):
        """Test S3 objects list - requires S3 service."""
        response = client.get("/s3/s3-objects")
        assert response.status_code == status.HTTP_200_OK


class TestMainRoutes:
    def test_test_endpoint(self):
        response = client.get("/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"] == "success"
        assert "msg" in data
        assert "It works!" in data["msg"]

    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"
