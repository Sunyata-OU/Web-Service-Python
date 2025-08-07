"""
Tests for database models.
"""

import pytest
from datetime import datetime

from src.models.user import User, APIKey
from src.models.s3 import S3Object
from src.auth import UserRole, get_password_hash


class TestUserModel:
    """Test User model functionality."""
    
    async def test_create_user(self, async_db_session):
        """Test creating a user."""
        user = await User.create_user(
            db=async_db_session,
            email="model_test@example.com",
            username="modeltest",
            password="testpass123",
            full_name="Model Test User"
        )
        
        assert user.id is not None
        assert user.email == "model_test@example.com"
        assert user.username == "modeltest"
        assert user.full_name == "Model Test User"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.role == UserRole.USER
        assert user.hashed_password != "testpass123"  # Should be hashed
        assert user.password_changed_at is not None
    
    def test_verify_password(self, test_user: User):
        """Test password verification."""
        assert test_user.verify_password("testpass123") is True
        assert test_user.verify_password("wrongpass") is False
    
    def test_is_admin(self, test_user: User, admin_user: User):
        """Test admin role checking."""
        assert test_user.is_admin() is False
        assert admin_user.is_admin() is True


class TestS3ObjectModel:
    """Test S3Object model functionality."""
    
    def test_s3_object_url(self, test_s3_object: S3Object):
        """Test S3 object URL generation."""
        url = test_s3_object.url
        assert isinstance(url, str)
        assert len(url) > 0
        
        full_url = test_s3_object.get_full_url()
        assert url == full_url