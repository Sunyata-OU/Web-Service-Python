"""
Tests for authentication and authorization.
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from src.models.user import User, APIKey
from src.auth import create_access_token, verify_password, get_password_hash
from .conftest import UserFactory


class TestAuthentication:
    """Test authentication endpoints."""
    
    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "testpass123",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "password" not in data
    
    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registration with duplicate email fails."""
        user_data = {
            "email": test_user.email,
            "username": "different",
            "password": "testpass123"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["message"]
    
    async def test_register_duplicate_username(self, async_client: AsyncClient, test_user: User):
        """Test registration with duplicate username fails."""
        user_data = {
            "email": "different@example.com",
            "username": test_user.username,
            "password": "testpass123"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already taken" in response.json()["message"]
    
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email fails."""
        user_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password fails."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "weak"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        login_data = {
            "identifier": test_user.email,
            "password": "testpass123"
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    async def test_login_with_username(self, async_client: AsyncClient, test_user: User):
        """Test login with username."""
        login_data = {
            "identifier": test_user.username,
            "password": "testpass123"
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
    
    async def test_login_invalid_credentials(self, async_client: AsyncClient, test_user: User):
        """Test login with invalid credentials fails."""
        login_data = {
            "identifier": test_user.email,
            "password": "wrongpassword"
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with nonexistent user fails."""
        login_data = {
            "identifier": "nonexistent@example.com",
            "password": "testpass123"
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_get_current_user(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting current user information."""
        response = await async_client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
    
    async def test_get_current_user_unauthorized(self, async_client: AsyncClient):
        """Test getting current user without auth fails."""
        response = await async_client.get("/api/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_update_profile(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating user profile."""
        update_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio"
        }
        
        response = await async_client.patch("/api/auth/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["bio"] == "Updated bio"
    
    async def test_change_password(self, async_client: AsyncClient, auth_headers: dict):
        """Test changing password."""
        change_data = {
            "current_password": "testpass123",
            "new_password": "newtestpass456"
        }
        
        response = await async_client.post("/api/auth/change-password", json=change_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "successfully" in response.json()["message"]
    
    async def test_change_password_wrong_current(self, async_client: AsyncClient, auth_headers: dict):
        """Test changing password with wrong current password fails."""
        change_data = {
            "current_password": "wrongpass",
            "new_password": "newtestpass456"
        }
        
        response = await async_client.post("/api/auth/change-password", json=change_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAPIKeys:
    """Test API key management."""
    
    async def test_create_api_key(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating API key."""
        key_data = {
            "name": "Test API Key",
            "expires_in_days": 30
        }
        
        response = await async_client.post("/api/auth/api-keys", json=key_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test API Key"
        assert data["api_key"].startswith("ws_")
        assert "Store this API key securely" in data["message"]
    
    async def test_list_api_keys(self, async_client: AsyncClient, auth_headers: dict, test_api_key):
        """Test listing API keys."""
        response = await async_client.get("/api/auth/api-keys", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Test API Key"
        # API key value should not be in response
        assert "api_key" not in data[0]
    
    async def test_delete_api_key(self, async_client: AsyncClient, auth_headers: dict, test_api_key):
        """Test deleting API key."""
        api_key, _ = test_api_key
        
        response = await async_client.delete(f"/api/auth/api-keys/{api_key.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "successfully" in response.json()["message"]
    
    async def test_api_key_authentication(self, async_client: AsyncClient, test_api_key):
        """Test authentication with API key."""
        _, raw_key = test_api_key
        api_headers = {"Authorization": f"Bearer {raw_key}"}
        
        response = await async_client.get("/api/auth/me", headers=api_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"


class TestAdminEndpoints:
    """Test admin-only endpoints."""
    
    async def test_list_users_admin(self, async_client: AsyncClient, admin_auth_headers: dict):
        """Test listing users as admin."""
        response = await async_client.get("/api/auth/users", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    async def test_list_users_non_admin(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing users as non-admin fails."""
        response = await async_client.get("/api/auth/users", headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_deactivate_user_admin(self, async_client: AsyncClient, admin_auth_headers: dict, test_user: User):
        """Test deactivating user as admin."""
        response = await async_client.patch(
            f"/api/auth/users/{test_user.id}/deactivate",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "deactivated" in response.json()["message"]
    
    async def test_activate_user_admin(self, async_client: AsyncClient, admin_auth_headers: dict, test_user: User):
        """Test activating user as admin."""
        response = await async_client.patch(
            f"/api/auth/users/{test_user.id}/activate",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "activated" in response.json()["message"]


class TestPasswordUtils:
    """Test password utility functions."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_token_creation(self, test_user: User):
        """Test JWT token creation."""
        token = create_access_token(
            subject=test_user.email,
            user_id=test_user.id,
            role=test_user.role
        )
        
        assert isinstance(token, str)
        assert len(token) > 0


@pytest.mark.integration
class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""
    
    async def test_complete_registration_login_flow(self, async_client: AsyncClient):
        """Test complete flow from registration to authenticated request."""
        # Register user
        user_data = {
            "email": "flowtest@example.com",
            "username": "flowtest",
            "password": "testpass123",
            "full_name": "Flow Test User"
        }
        
        register_response = await async_client.post("/api/auth/register", json=user_data)
        assert register_response.status_code == status.HTTP_201_CREATED
        
        # Login
        login_data = {
            "identifier": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = await async_client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == status.HTTP_200_OK
        
        # Extract token
        tokens = login_response.json()
        access_token = tokens["access_token"]
        
        # Use token for authenticated request
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await async_client.get("/api/auth/me", headers=auth_headers)
        
        assert me_response.status_code == status.HTTP_200_OK
        user_info = me_response.json()
        assert user_info["email"] == user_data["email"]
        assert user_info["username"] == user_data["username"]