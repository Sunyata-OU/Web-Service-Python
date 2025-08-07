"""
Tests for S3/file storage functionality.
"""

import pytest
from unittest.mock import patch
from fastapi import status
from httpx import AsyncClient
from io import BytesIO

from src.models.s3 import S3Object


class TestS3Upload:
    """Test file upload functionality."""
    
    @patch('src.s3.upload_object_to_s3')
    async def test_upload_file_success(self, mock_upload, async_client: AsyncClient, sample_text_file):
        """Test successful file upload."""
        mock_upload.return_value = "test-file-123.txt"
        
        files = {"file": ("test.txt", sample_text_file, "text/plain")}
        response = await async_client.post("/s3/upload", files=files)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["file_name"] == "test.txt"
        assert data["file_type"] == "text/plain"
        assert data["bucket_name"] == "test-bucket"
        assert data["object_name"] == "test-file-123.txt"
        assert "url" in data
        
        mock_upload.assert_called_once()
    
    async def test_upload_no_file(self, async_client: AsyncClient):
        """Test upload without file fails."""
        response = await async_client.post("/s3/upload")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_upload_empty_filename(self, async_client: AsyncClient):
        """Test upload with empty filename fails."""
        files = {"file": ("", BytesIO(b"content"), "text/plain")}
        response = await async_client.post("/s3/upload", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestS3ObjectList:
    """Test listing S3 objects."""
    
    async def test_list_objects(self, async_client: AsyncClient, test_s3_object: S3Object):
        """Test listing S3 objects."""
        response = await async_client.get("/s3/objects")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
    
    async def test_list_objects_pagination(self, async_client: AsyncClient):
        """Test pagination in object listing."""        
        response = await async_client.get("/s3/objects?page=1&size=3")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 3


class TestS3ObjectDetail:
    """Test getting individual S3 object details."""
    
    async def test_get_object_detail(self, async_client: AsyncClient, test_s3_object: S3Object):
        """Test getting object details."""
        response = await async_client.get(f"/s3/objects/{test_s3_object.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_s3_object.id
        assert data["file_name"] == test_s3_object.file_name
        assert "url" in data
    
    async def test_get_nonexistent_object(self, async_client: AsyncClient):
        """Test getting nonexistent object returns 404."""
        response = await async_client.get("/s3/objects/99999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND