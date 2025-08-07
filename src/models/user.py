"""
User model with authentication and authorization.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from src.auth import UserRole, generate_api_key, get_password_hash, hash_api_key, verify_password
from src.models.base import AsyncBaseModel, BaseSchema, TimestampedSchema


class User(AsyncBaseModel):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    # Basic info
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # Status and permissions
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(20), default=UserRole.USER, nullable=False)

    # Profile
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)

    # Authentication tracking
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Email verification
    email_verified_at = Column(DateTime, nullable=True)
    email_verification_token = Column(String(255), nullable=True, index=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires_at = Column(DateTime, nullable=True)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index("ix_user_email_active", "email", "is_active"),
        Index("ix_user_role", "role"),
    )

    @classmethod
    async def create_user(
        cls,
        db: AsyncSession,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> "User":
        """Create a new user with hashed password."""
        hashed_password = get_password_hash(password)

        user = await cls.create(
            db,
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role.value,
            password_changed_at=datetime.utcnow(),
        )

        return user

    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str) -> Optional["User"]:
        """Get user by email."""
        result = await db.execute(select(cls).where(cls.email == email))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_username(cls, db: AsyncSession, username: str) -> Optional["User"]:
        """Get user by username."""
        result = await db.execute(select(cls).where(cls.username == username))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_email_or_username(cls, db: AsyncSession, identifier: str) -> Optional["User"]:
        """Get user by email or username."""
        result = await db.execute(select(cls).where((cls.email == identifier) | (cls.username == identifier)))
        return result.scalar_one_or_none()

    def verify_password(self, password: str) -> bool:
        """Verify user password."""
        return verify_password(password, self.hashed_password)

    async def update_password(self, db: AsyncSession, new_password: str):
        """Update user password."""
        hashed_password = get_password_hash(new_password)
        await self.update(
            db,
            hashed_password=hashed_password,
            password_changed_at=datetime.utcnow(),
            password_reset_token=None,
            password_reset_expires_at=None,
        )

    async def record_login(self, db: AsyncSession):
        """Record successful login."""
        await self.update(db, last_login_at=datetime.utcnow(), failed_login_attempts=0, locked_until=None)

    async def record_failed_login(self, db: AsyncSession, max_attempts: int = 5):
        """Record failed login attempt."""
        new_attempts = self.failed_login_attempts + 1

        # Lock account after max attempts
        locked_until = None
        if new_attempts >= max_attempts:
            locked_until = datetime.utcnow() + timedelta(minutes=30)

        await self.update(db, failed_login_attempts=new_attempts, locked_until=locked_until)

    def is_locked(self) -> bool:
        """Check if account is locked."""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until

    async def verify_email(self, db: AsyncSession):
        """Mark email as verified."""
        await self.update(db, is_verified=True, email_verified_at=datetime.utcnow(), email_verification_token=None)

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN

    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has required permission level."""
        role_hierarchy = {UserRole.GUEST: 0, UserRole.USER: 1, UserRole.ADMIN: 2}

        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level


class APIKey(AsyncBaseModel):
    """API Key model for programmatic access."""

    __tablename__ = "api_keys"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # Human-readable name
    key_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 hash

    # Permissions and restrictions
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Scope limitations (JSON string for flexibility)
    scopes = Column(Text, nullable=True)  # JSON array of scopes
    ip_whitelist = Column(Text, nullable=True)  # JSON array of IPs

    # Relationship
    user = relationship("User", back_populates="api_keys")

    @classmethod
    async def create_for_user(
        cls,
        db: AsyncSession,
        user_id: int,
        name: str,
        expires_in_days: Optional[int] = None,
        scopes: Optional[List[str]] = None,
    ) -> tuple["APIKey", str]:
        """Create new API key for user and return both the model and raw key."""
        import json

        # Generate raw API key
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)

        # Set expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create API key record
        api_key = await cls.create(
            db,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            expires_at=expires_at,
            scopes=json.dumps(scopes) if scopes else None,
        )

        return api_key, raw_key

    @classmethod
    async def get_by_hash(cls, db: AsyncSession, key_hash: str) -> Optional["APIKey"]:
        """Get API key by hash."""
        result = await db.execute(select(cls).where(cls.key_hash == key_hash))
        return result.scalar_one_or_none()

    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    def get_scopes(self) -> List[str]:
        """Get API key scopes."""
        if not self.scopes:
            return []

        import json

        try:
            return json.loads(self.scopes)
        except (json.JSONDecodeError, TypeError):
            return []


class RefreshToken(AsyncBaseModel):
    """Refresh token model for JWT token refresh."""

    __tablename__ = "refresh_tokens"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_jti = Column(String(32), unique=True, index=True, nullable=False)  # JWT ID
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationship
    user = relationship("User", back_populates="refresh_tokens")

    @classmethod
    async def create_for_user(
        cls, db: AsyncSession, user_id: int, token_jti: str, expires_at: datetime
    ) -> "RefreshToken":
        """Create refresh token record."""
        return await cls.create(db, user_id=user_id, token_jti=token_jti, expires_at=expires_at)

    @classmethod
    async def get_by_jti(cls, db: AsyncSession, token_jti: str) -> Optional["RefreshToken"]:
        """Get refresh token by JTI."""
        result = await db.execute(select(cls).where(cls.token_jti == token_jti, cls.is_active))
        return result.scalar_one_or_none()

    async def revoke(self, db: AsyncSession):
        """Revoke refresh token."""
        await self.update(db, is_active=False)


# Pydantic schemas
class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)

        if not (has_letter and has_number):
            raise ValueError("Password must contain at least one letter and one number")

        return v


class UserUpdate(BaseModel):
    """Schema for user updates."""

    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=1000)


class UserResponse(UserBase, TimestampedSchema):
    """Schema for user responses."""

    is_active: bool
    is_verified: bool
    role: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    last_login_at: Optional[datetime] = None


class UserLogin(BaseModel):
    """Schema for user login."""

    identifier: str = Field(..., description="Email or username")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class APIKeyCreate(BaseModel):
    """Schema for API key creation."""

    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(None, gt=0, le=365)
    scopes: Optional[List[str]] = None


class APIKeyResponse(TimestampedSchema):
    """Schema for API key response."""

    name: str
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    scopes: List[str] = []

    # Note: Never return the actual key or hash in responses
