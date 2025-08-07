"""
Authentication and authorization utilities.
"""

import hashlib
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from time import time
from typing import Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_async_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Get settings
settings = get_settings()


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class TokenType(str, Enum):
    """Token types."""

    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


# Exception classes
class AuthenticationError(HTTPException):
    """Authentication failed."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AuthorizationError(HTTPException):
    """Authorization failed."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail=detail)


class InvalidTokenError(AuthenticationError):
    """Token is invalid."""

    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail)


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


# JWT token utilities
def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    token_type: TokenType = TokenType.ACCESS,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"exp": expire, "iat": datetime.now(timezone.utc), "sub": str(subject), "type": token_type.value}

    if user_id:
        to_encode["user_id"] = user_id
    if role:
        to_encode["role"] = role

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: Union[str, Any], user_id: Optional[int] = None) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(subject),
        "user_id": user_id,
        "type": TokenType.REFRESH.value,
        "jti": generate_secure_token(16),  # JWT ID for invalidation
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str, token_type: Optional[TokenType] = None) -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Check token type if specified
        if token_type and payload.get("type") != token_type.value:
            raise InvalidTokenError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError:
        raise InvalidTokenError()


# API Key utilities
def generate_api_key() -> str:
    """Generate a new API key."""
    return f"ws_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return hashlib.sha256(api_key.encode()).hexdigest() == hashed_key


# Authentication dependencies
async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_async_db)
):
    """Get current user from JWT token."""
    from src.models.user import User  # Import here to avoid circular imports

    try:
        payload = verify_token(credentials.credentials, TokenType.ACCESS)
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise InvalidTokenError("Token missing user_id")

        user = await User.get(db, user_id)
        if user is None:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        return user

    except (InvalidTokenError, TokenExpiredError, AuthenticationError):
        raise
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")


async def get_current_user_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_async_db)
):
    """Get current user from API key."""
    from src.models.user import APIKey, User  # Import here to avoid circular imports

    try:
        api_key = credentials.credentials
        if not api_key.startswith("ws_"):
            raise InvalidTokenError("Invalid API key format")

        # Hash the provided API key
        hashed_key = hash_api_key(api_key)

        # Find the API key in database
        api_key_obj = await APIKey.get_by_hash(db, hashed_key)
        if not api_key_obj or not api_key_obj.is_active:
            raise AuthenticationError("Invalid or inactive API key")

        # Check expiration
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
            raise AuthenticationError("API key has expired")

        # Get associated user
        user = await User.get(db, api_key_obj.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Update last used timestamp
        await api_key_obj.update(db, last_used_at=datetime.utcnow())

        return user

    except (InvalidTokenError, AuthenticationError):
        raise
    except Exception as e:
        raise AuthenticationError(f"API key authentication failed: {str(e)}")


# Flexible authentication - tries both token and API key
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_async_db)
):
    """Get current user from either JWT token or API key."""
    try:
        # Try JWT token first
        return await get_current_user_from_token(credentials, db)
    except AuthenticationError:
        # If JWT fails, try API key
        try:
            return await get_current_user_from_api_key(credentials, db)
        except AuthenticationError:
            raise AuthenticationError("Invalid authentication credentials")


def require_role(required_role: UserRole):
    """Dependency to require specific role."""

    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise AuthorizationError(f"Role '{required_role}' required")
        return current_user

    return role_checker


def require_admin():
    """Dependency to require admin role."""
    return require_role(UserRole.ADMIN)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_async_db),
):
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except (AuthenticationError, AuthorizationError):
        return None


# Rate limiting helper (simple in-memory implementation)

_rate_limit_cache = defaultdict(list)


def check_rate_limit(identifier: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
    """Simple in-memory rate limiting."""
    now = time()
    window_start = now - window_seconds

    # Clean old entries
    _rate_limit_cache[identifier] = [
        timestamp for timestamp in _rate_limit_cache[identifier] if timestamp > window_start
    ]

    # Check if under limit
    if len(_rate_limit_cache[identifier]) >= max_requests:
        return False

    # Add current request
    _rate_limit_cache[identifier].append(now)
    return True


def require_rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Dependency for rate limiting."""

    async def rate_limiter(credentials: HTTPAuthorizationCredentials = Depends(security)):
        # Use token/api key as identifier
        if not check_rate_limit(credentials.credentials, max_requests, window_seconds):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        return True

    return rate_limiter
