"""Application middleware for FastAPI."""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings
from src.logger import logger
from src.cache import perf_monitor, rate_limiter, get_session_cache


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for request logging, performance monitoring, and request ID tracking."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with enhanced logging and monitoring."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Record start time
        start_time = time.perf_counter()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Get user ID if available from request state
        user_id = getattr(request.state, 'user_id', None)
        
        # Log request with structured data
        logger.log_request(
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        # Record performance metrics
        endpoint = f"{request.method} {request.url.path}"
        perf_monitor.record_response_time(endpoint, duration_ms)
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(duration_ms, 2))
        response.headers["X-API-Version"] = "0.1.0"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for forwarded headers from load balancers/proxies
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP from the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests by IP address."""
    
    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for health checks and static files
        if self._should_skip_rate_limit(request):
            return await call_next(request)
        
        # Check minute-based rate limit
        minute_allowed = rate_limiter.is_allowed(
            identifier=f"ip:{client_ip}",
            max_requests=self.requests_per_minute,
            window_seconds=60,
            action="minute_limit"
        )
        
        # Check burst rate limit (short window)
        burst_allowed = rate_limiter.is_allowed(
            identifier=f"ip:{client_ip}",
            max_requests=self.burst_limit,
            window_seconds=10,
            action="burst_limit"
        )
        
        if not minute_allowed or not burst_allowed:
            # Log rate limit violation
            logger.log_security_event(
                event="rate_limit_exceeded",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="medium"
            )
            
            # Return rate limit error
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Window": "60"
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        current_usage = rate_limiter.get_current_usage(f"ip:{client_ip}", "minute_limit")
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.requests_per_minute - current_usage))
        response.headers["X-RateLimit-Window"] = "60"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/static"]
        return any(request.url.path.startswith(path) for path in skip_paths)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response


def setup_middleware(app):
    """Set up all middleware for the FastAPI application."""
    settings = get_settings()
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add rate limiting middleware (before request logging)
    if settings.environment == "production":
        app.add_middleware(RateLimitingMiddleware, requests_per_minute=100, burst_limit=20)
    else:
        # More lenient rate limits for development
        app.add_middleware(RateLimitingMiddleware, requests_per_minute=300, burst_limit=50)
    
    # Add request logging middleware (should be last for accurate timing)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add CORS middleware
    from fastapi.middleware.cors import CORSMiddleware
    
    cors_origins = ["*"]  # Configure based on environment
    if settings.cors_origins:
        cors_origins = settings.cors_origins
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for production
    if settings.environment == "production" and settings.allowed_hosts:
        from fastapi.middleware.trustedhost import TrustedHostMiddleware
        
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    logger.info("✅ Middleware setup completed")