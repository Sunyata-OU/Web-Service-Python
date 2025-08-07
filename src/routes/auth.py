"""
Authentication and user management routes.
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.config import get_settings
from src.models.user import (
    User, APIKey, RefreshToken,
    UserCreate, UserLogin, UserResponse, UserUpdate,
    TokenResponse, APIKeyCreate, APIKeyResponse
)
from src.auth import (
    get_current_user, get_optional_user, require_admin,
    create_access_token, create_refresh_token, verify_token,
    AuthenticationError, AuthorizationError, InvalidTokenError,
    TokenType, check_rate_limit
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Register a new user account."""
    if not settings.enable_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is disabled"
        )
    
    # Check if user already exists
    existing_user = await User.get_by_email_or_username(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Check username separately to give specific error
    existing_username = await User.get_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = await User.create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    await db.commit()
    
    return UserResponse.model_validate(user.to_dict())


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Authenticate user and return tokens."""
    
    # Basic rate limiting by IP
    client_ip = request.client.host
    if not check_rate_limit(f"login:{client_ip}", max_requests=10, window_seconds=300):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Get user
    user = await User.get_by_email_or_username(db, credentials.identifier)
    if not user:
        raise AuthenticationError("Invalid credentials")
    
    # Check if account is locked
    if user.is_locked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to failed login attempts"
        )
    
    # Verify password
    if not user.verify_password(credentials.password):
        await user.record_failed_login(db, settings.max_login_attempts)
        await db.commit()
        raise AuthenticationError("Invalid credentials")
    
    # Check if user is active
    if not user.is_active:
        raise AuthenticationError("Account is disabled")
    
    # Create tokens
    access_token = create_access_token(
        subject=user.email,
        user_id=user.id,
        role=user.role
    )
    
    refresh_token = create_refresh_token(subject=user.email, user_id=user.id)
    
    # Store refresh token
    from jose import jwt
    refresh_payload = jwt.decode(
        refresh_token, settings.secret_key, algorithms=[settings.algorithm]
    )
    
    await RefreshToken.create_for_user(
        db=db,
        user_id=user.id,
        token_jti=refresh_payload["jti"],
        expires_at=datetime.fromtimestamp(refresh_payload["exp"])
    )
    
    # Record successful login
    await user.record_login(db)
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, TokenType.REFRESH)
        user_id = payload.get("user_id")
        token_jti = payload.get("jti")
        
        if not user_id or not token_jti:
            raise InvalidTokenError("Invalid token payload")
        
        # Check if refresh token exists and is active
        stored_token = await RefreshToken.get_by_jti(db, token_jti)
        if not stored_token or stored_token.user_id != user_id:
            raise InvalidTokenError("Token not found or invalid")
        
        # Get user
        user = await User.get(db, user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Create new access token
        access_token = create_access_token(
            subject=user.email,
            user_id=user.id,
            role=user.role
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep same refresh token
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except (InvalidTokenError, AuthenticationError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    refresh_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Logout user and revoke refresh token."""
    try:
        # Decode refresh token to get JTI
        payload = verify_token(refresh_token, TokenType.REFRESH)
        token_jti = payload.get("jti")
        
        if token_jti:
            # Revoke the refresh token
            stored_token = await RefreshToken.get_by_jti(db, token_jti)
            if stored_token and stored_token.user_id == current_user.id:
                await stored_token.revoke(db)
                await db.commit()
        
    except Exception:
        # Don't fail logout if token is already invalid
        pass
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse.model_validate(current_user.to_dict())


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update current user profile."""
    # Update user fields
    update_data = user_update.model_dump(exclude_unset=True)
    if update_data:
        await current_user.update(db, **update_data)
        await db.commit()
    
    return UserResponse.model_validate(current_user.to_dict())


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Change user password."""
    # Verify current password
    if not current_user.verify_password(current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(new_password) < settings.password_min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {settings.password_min_length} characters long"
        )
    
    # Update password
    await current_user.update_password(db, new_password)
    await db.commit()
    
    return {"message": "Password updated successfully"}


# API Key management
@router.post("/api-keys", response_model=dict)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new API key for the current user."""
    api_key_obj, raw_key = await APIKey.create_for_user(
        db=db,
        user_id=current_user.id,
        name=api_key_data.name,
        expires_in_days=api_key_data.expires_in_days,
        scopes=api_key_data.scopes
    )
    
    await db.commit()
    
    # Return the raw key only once - it won't be stored or shown again
    return {
        "api_key": raw_key,
        "name": api_key_obj.name,
        "expires_at": api_key_obj.expires_at,
        "message": "Store this API key securely. It will not be shown again."
    }


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List user's API keys."""
    api_keys = await APIKey.get_multi(
        db,
        filters={"user_id": current_user.id},
        order_by="created_at"
    )
    
    return [
        APIKeyResponse(
            **api_key.to_dict(),
            scopes=api_key.get_scopes()
        )
        for api_key in api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete an API key."""
    api_key = await APIKey.get(db, key_id)
    
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    await api_key.delete(db)
    await db.commit()
    
    return {"message": "API key deleted successfully"}


# Admin routes
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db)
):
    """List all users (admin only)."""
    users = await User.get_multi(db, skip=skip, limit=limit)
    
    return [
        UserResponse.model_validate(user.to_dict())
        for user in users
    ]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db)
):
    """Update any user (admin only)."""
    user = await User.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    update_data = user_update.model_dump(exclude_unset=True)
    if update_data:
        await user.update(db, **update_data)
        await db.commit()
    
    return UserResponse.model_validate(user.to_dict())


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db)
):
    """Activate a user account (admin only)."""
    user = await User.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await user.update(db, is_active=True)
    await db.commit()
    
    return {"message": f"User {user.username} has been activated"}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_async_db)
):
    """Deactivate a user account (admin only)."""
    user = await User.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Don't allow deactivating yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    await user.update(db, is_active=False)
    await db.commit()
    
    return {"message": f"User {user.username} has been deactivated"}