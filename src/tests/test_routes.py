import pytest
from fastapi import status
from unittest.mock import Mock, patch
from io import BytesIO

from src.tests.utils import client


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
    @patch('src.routes.s3.upload_object_to_s3')
    @patch('src.routes.s3.get_db')
    def test_s3_upload_success(self, mock_get_db, mock_upload):
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_upload.return_value = "test-filename.txt"
        
        file_content = b"test file content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        
        response = client.post("/s3-upload", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"result": "success"}
        mock_upload.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('src.routes.s3.upload_object_to_s3')
    @patch('src.routes.s3.get_db')
    def test_s3_upload_failure_no_file(self, mock_get_db, mock_upload):
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.post("/s3-upload")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('src.routes.s3.upload_object_to_s3')
    @patch('src.routes.s3.get_db')
    def test_s3_upload_failure_upload_fails(self, mock_get_db, mock_upload):
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_upload.return_value = None
        
        file_content = b"test file content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        
        response = client.post("/s3-upload", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"result": "fail"}

    @patch('src.routes.s3.get_db')
    def test_s3_objects_list(self, mock_get_db):
        mock_db = Mock()
        mock_s3_object = Mock()
        mock_s3_object.id = 1
        mock_s3_object.file_name = "test.txt"
        mock_db.query().all.return_value = [mock_s3_object]
        mock_get_db.return_value = mock_db
        
        response = client.get("/s3-objects")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "s3_objects" in data
        assert len(data["s3_objects"]) == 1


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