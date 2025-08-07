"""
Tests for main application endpoints.
"""

from fastapi import status
from httpx import AsyncClient


class TestMainEndpoints:
    """Test main application endpoints."""

    async def test_root_endpoint(self, async_client: AsyncClient):
        """Test root endpoint returns basic info."""
        response = await async_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "Web Service Template API"

    async def test_health_check(self, async_client: AsyncClient):
        """Test health check endpoint."""
        response = await async_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    async def test_test_endpoint(self, async_client: AsyncClient):
        """Test test endpoint works."""
        response = await async_client.get("/test")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"] == "success"
        assert "msg" in data
        assert "It works!" in data["msg"]
