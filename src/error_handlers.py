"""
Error handlers for FastAPI application.
"""

import traceback
import uuid

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.exceptions import BaseAppException, create_error_response, map_app_exception_to_http
from src.logger import logger


def generate_request_id() -> str:
    """Generate a unique request ID for error tracking."""
    return str(uuid.uuid4())


async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """Handle application-specific exceptions."""
    request_id = generate_request_id()

    logger.error(
        f"Application error [{request_id}]: {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "details": exc.details,
            "url": str(request.url),
            "method": request.method,
        },
    )

    # Map to HTTP exception
    http_exc = map_app_exception_to_http(exc)

    error_response = create_error_response(message=exc.message, error_code=exc.error_code, request_id=request_id)

    return JSONResponse(status_code=http_exc.status_code, content=error_response)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent response format."""
    request_id = generate_request_id()

    # Log based on status code severity
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code} error [{request_id}]: {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "url": str(request.url),
                "method": request.method,
            },
        )
    else:
        logger.warning(
            f"HTTP {exc.status_code} error [{request_id}]: {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "url": str(request.url),
                "method": request.method,
            },
        )

    error_response = create_error_response(
        message=exc.detail, error_code=f"HTTP_{exc.status_code}", request_id=request_id
    )

    return JSONResponse(status_code=exc.status_code, content=error_response, headers=exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = generate_request_id()

    logger.warning(
        f"Validation error [{request_id}]: {str(exc)}",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
            "validation_errors": exc.errors(),
        },
    )

    # Format validation errors
    field_errors = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = error["msg"]

    error_response = create_error_response(
        message="Validation failed", error_code="VALIDATION_ERROR", field_errors=field_errors, request_id=request_id
    )

    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response)


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database exceptions."""
    request_id = generate_request_id()

    logger.error(
        f"Database error [{request_id}]: {str(exc)}",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )

    # Don't expose detailed database errors to users
    error_response = create_error_response(
        message="A database error occurred. Please try again later.", error_code="DATABASE_ERROR", request_id=request_id
    )

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = generate_request_id()

    logger.error(
        f"Unexpected error [{request_id}]: {str(exc)}",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
            "error_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )

    error_response = create_error_response(
        message="An unexpected error occurred. Please try again later.",
        error_code="INTERNAL_ERROR",
        request_id=request_id,
    )

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response)


async def not_found_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle 404 Not Found errors."""
    request_id = generate_request_id()

    logger.info(
        f"Not found [{request_id}]: {request.url.path}",
        extra={"request_id": request_id, "url": str(request.url), "method": request.method},
    )

    error_response = create_error_response(
        message="The requested resource was not found.", error_code="NOT_FOUND", request_id=request_id
    )

    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=error_response)


async def method_not_allowed_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle 405 Method Not Allowed errors."""
    request_id = generate_request_id()

    logger.info(
        f"Method not allowed [{request_id}]: {request.method} {request.url.path}",
        extra={"request_id": request_id, "url": str(request.url), "method": request.method},
    )

    error_response = create_error_response(
        message=f"Method {request.method} is not allowed for this endpoint.",
        error_code="METHOD_NOT_ALLOWED",
        request_id=request_id,
    )

    return JSONResponse(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, content=error_response)


# Rate limiting error handler
async def rate_limit_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle rate limiting errors."""
    request_id = generate_request_id()

    logger.warning(
        f"Rate limit exceeded [{request_id}]: {request.client.host}",
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
            "client_ip": request.client.host,
        },
    )

    error_response = create_error_response(
        message="Too many requests. Please slow down and try again later.",
        error_code="RATE_LIMIT_EXCEEDED",
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response,
        headers={"Retry-After": "60"},  # Suggest retry after 60 seconds
    )


def setup_error_handlers(app):
    """Set up all error handlers for the FastAPI application."""

    # Application-specific exceptions
    app.add_exception_handler(BaseAppException, app_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # Database errors
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)

    # Specific HTTP status codes
    @app.exception_handler(404)
    async def not_found_404(request: Request, exc: HTTPException):
        return await not_found_handler(request, exc)

    @app.exception_handler(405)
    async def method_not_allowed_405(request: Request, exc: HTTPException):
        return await method_not_allowed_handler(request, exc)

    @app.exception_handler(429)
    async def rate_limit_429(request: Request, exc: HTTPException):
        return await rate_limit_handler(request, exc)

    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Error handlers configured successfully")
