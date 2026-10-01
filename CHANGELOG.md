# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- SSH agent forwarding for builds is opt-in again (`make build-ssh`); plain builds no longer require an agent
- Container could not write to `/var/log/webapp` (root-owned named volume); log dir is now owned by the app user

### Changed
- Replaced MinIO with RustFS as the S3-compatible service (MinIO no longer publishes Docker images)
- Upgraded dependency stack (FastAPI, Starlette, SQLAlchemy 2.1, Jupyter, etc.) to resolve open security advisories
- Replaced `python-jose` with `PyJWT` (drops the unpatched `ecdsa` dependency) and `passlib` with `bcrypt`; missing bearer credentials now return 401
- Fixed Docker build; CI now tests Python 3.13

### Added
- Comprehensive test suite with 84 passing tests
- Pre-commit hooks for code quality
- Docker containerization with production-ready configuration
- Automated versioning and release system
- GitHub Actions CI/CD pipeline

### Changed
- Migrated from Poetry to uv for faster dependency management
- Updated to latest versions of all dependencies
- Improved error handling and validation

### Fixed
- Database session management in tests
- Redis connection handling in test environments
- Linting and formatting issues

## [0.1.0] - 2025-01-08

### Added
- Initial FastAPI web service template
- PostgreSQL database with SQLAlchemy ORM
- Redis caching and session management
- RustFS S3-compatible object storage (replaces MinIO, whose Docker images are no longer published)
- Celery background task processing
- JWT authentication and authorization
- Docker Compose orchestration
- Nginx reverse proxy with SSL support
- Comprehensive logging and monitoring
- Alembic database migrations
- API documentation with OpenAPI/Swagger

### Infrastructure
- Multi-service Docker setup with health checks
- Automated SSL certificate generation with Let's Encrypt
- Development and production configurations
- Container resource limits and logging
- Network isolation and security headers

### Documentation
- Comprehensive README with setup instructions
- API documentation
- Docker deployment guides
- Development environment setup
- Contributing guidelines
