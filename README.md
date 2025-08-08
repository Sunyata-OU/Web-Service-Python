# Web-Service-Python

[![CI Status](https://github.com/YOUR_USERNAME/Web-Service-Python/workflows/CI/badge.svg)](https://github.com/YOUR_USERNAME/Web-Service-Python/actions)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/Web-Service-Python/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/Web-Service-Python)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?&logo=docker&logoColor=white)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?&logo=redis&logoColor=white)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Tests](https://img.shields.io/badge/tests-51%2B%20passing-brightgreen)](https://github.com/YOUR_USERNAME/Web-Service-Python/tree/main/src/tests)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checking](https://img.shields.io/badge/type%20checking-mypy-blue)](http://mypy-lang.org/)
[![Security](https://img.shields.io/badge/security-bandit-yellow)](https://bandit.readthedocs.io/)

## Description

A comprehensive Python web service template using FastAPI with a full-featured Docker-based stack. This template provides both REST API endpoints and web interface via Jinja2 templating, complete with authentication, file storage, background tasks, and production-ready deployment features.
## Features

### Core Stack
- [x] **FastAPI** - Modern, fast web framework for building APIs
- [x] **Jinja2** - Template engine for web interface
- [x] **PostgreSQL** - Primary database with async support
- [x] **Redis** - Caching and session storage
- [x] **Celery** - Background task processing
- [x] **MinIO** - S3-compatible object storage
- [x] **Nginx** - Reverse proxy with SSL/TLS support
- [x] **Certbot** - Automated SSL certificate management

### Development & Deployment
- [x] **uv** - Ultra-fast Python package management
- [x] **Ruff** - Modern Python linter and formatter
- [x] **MyPy** - Static type checking
- [x] **GitHub Actions** - CI/CD pipeline with automated testing
- [x] **Docker & Docker Compose** - Full containerization
- [x] **Makefile** - Easy setup and common tasks
- [x] **VS Code Debugger** - Development debugging support
- [x] **SSH Support** - Private repository access
- [x] **Comprehensive Testing** - 51+ automated tests covering all components

### Authentication & Security
- [x] **JWT Authentication** - Secure token-based auth
- [x] **Password Security** - Bcrypt hashing with policies
- [x] **CORS Support** - Cross-origin resource sharing
- [x] **Security Middleware** - Request validation and protection
- [x] **Structured Logging** - Enhanced logging with context

### Data & Storage
- [x] **Async Database Operations** - Non-blocking database access
- [x] **Database Migrations** - Alembic for schema management
- [x] **File Upload/Management** - S3-compatible storage integration
- [x] **Multi-Database Support** - Multiple database configurations
- [x] **Data Validation** - Pydantic models with validation

## Installation

### Docker

1. Install Docker and Docker-compose
2.Copy the .env-copy file to .env and fill in the variables
1. If the docker requires access to a private repository you need to load your ssh key to your ssh-agent using `ssh-add` command.

   ```bash
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/<your-ssh-key> #set the path to your ssh key
    ```

2. Build the docker compose file

```bash
docker-compose build
```

4. Run the docker compose file

```bash
docker-compose up
```

5. The webserver should be running on localhost on the port defined in the .env file
6. Create a bucket in the minio server with the name defined in the .env file
7. The project uses alemic to manage the database. To create the database run the following command

```bash
alemic upgrade head
```

### Use makefile

1. Install Docker and Docker-compose
2. Copy the .env-copy file to .env and fill in the variables
3.If the docker requires access to a private repository you need to load your ssh key to your ssh-agent using `ssh-add` command.
   ```bash
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/<your-ssh-key> #set the path to your ssh key
    ```

4. Run the makefile

```bash
make init
```

5. The webserver should be running on localhost on the port defined in the .env file

## Development

The project uses **uv** for ultra-fast Python dependency management.

### Prerequisites

- **uv** (latest version) [Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
- **Python 3.10+**
- **Docker** (for full stack development)
- **docker-compose** (for orchestration)

### Development Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd Web-Service-Python
   cp .env-copy .env  # Edit with your settings
   ```

3. **Install dependencies**:
   ```bash
   uv sync --dev  # Install all dependencies including dev tools
   ```

4. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate  # Or use uv run <command>
   ```

### Package Management

#### Add new packages
```bash
uv add package-name              # Production dependency
uv add --dev package-name        # Development dependency
uv add package-name==1.2.3       # Specific version
```

#### Remove packages
```bash
uv remove package-name
```

#### Update dependencies
```bash
uv sync                  # Sync with uv.lock
uv lock --upgrade        # Update lock file with latest versions
uv add package-name@latest --dev  # Upgrade specific package
```

### Testing

The project includes comprehensive testing with **51+ automated tests**:

```bash
# Run all working tests
uv run pytest src/tests/test_basic.py \
              src/tests/test_config.py \
              src/tests/test_utils.py \
              src/tests/test_s3.py \
              src/tests/test_celery.py -v

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest src/tests/test_config.py -v

# Run with environment variables
POSTGRES_USER=test_user POSTGRES_PASSWORD=test_pass \
S3_ACCESS_KEY_ID=test_key S3_ACCESS_KEY=test_secret \
uv run pytest src/tests/ -v
```

### Code Quality

```bash
uv run ruff check .              # Lint code
uv run ruff format .             # Format code
uv run mypy src/                 # Type checking
uv run pre-commit run --all-files # Run all hooks
```

## CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow that automatically:

- **Tests across Python versions** (3.10, 3.11, 3.12)
- **Runs code quality checks** (linting, formatting, type checking)
- **Executes all test suites** with coverage reporting
- **Builds and tests Docker images**
- **Uploads coverage to Codecov**
- **Runs on pull requests and pushes** to main/develop branches

The CI pipeline ensures code quality and prevents regressions before merging changes.

### Setting up pre-commit

Pre-commit hooks run code quality checks before each commit:

```bash
uv run pre-commit install    # Install git commit hooks
uv run pre-commit run --all-files  # Run on all files manually
```

This will automatically run `ruff` (linting and formatting) and `mypy` (type checking) before each commit.

### Using alembic

To create a new migration run the following command

```bash
alembic revision --autogenerate -m "migration message"
```

To apply the migration run the following command

```bash
alembic upgrade head
```

To downgrade the migration run the following command

```bash
alembic downgrade -1
```

### Using VS Code Debugger
1. Install the python extension for VS Code.
2. Use the included `launch.json` file to run the debugger.
3. Use the custom docker compose file to run the debugger.
```bash
docker-compose -f docker-compose.debug.yml up
```
4. Set breakpoints in the code and run the debugger vs code(Wait for debugpy to be installed).
5. The debugger should be running on port 5678.

### Other editors
Comment out the `debugpy` `start-debug.sh` file and run the docker compose file above.

## 🏷️ Version Management & Releases

This project uses **semantic versioning** (SemVer) with automated releases through GitHub Actions.

### Version Format
- **Major**: Breaking changes (1.0.0 → 2.0.0)
- **Minor**: New features, backward compatible (1.0.0 → 1.1.0)
- **Patch**: Bug fixes, backward compatible (1.0.0 → 1.0.1)
- **Prerelease**: Alpha/beta versions (1.0.0-alpha.1)

### Manual Version Bumping

Use the convenient Make targets for version management:

```bash
# Check current version
make version

# Bump version (creates commit + tag + triggers release)
make bump-patch      # 1.0.0 → 1.0.1 (bug fixes)
make bump-minor      # 1.0.0 → 1.1.0 (new features)
make bump-major      # 1.0.0 → 2.0.0 (breaking changes)
make bump-prerelease # 1.0.0 → 1.0.1-alpha.0 (pre-release)

# Generate release notes
make release-notes   # Show changes since last release
make changelog       # Update CHANGELOG.md
```

### Automated Releases

The project supports **automated releases** based on commit messages using conventional commits:

- `feat:` triggers **minor** release (new feature)
- `fix:` triggers **patch** release (bug fix)
- `feat!:` or `BREAKING CHANGE:` triggers **major** release
- Other commits don't trigger releases

**Example commits:**
```bash
git commit -m "feat: add user authentication"     # → Minor release
git commit -m "fix: resolve database connection"  # → Patch release
git commit -m "feat!: redesign API endpoints"     # → Major release
```

### Release Process

When you push a version tag or use automated releases:

1. **Automated testing** runs (all 84+ tests must pass)
2. **Python package** is built and attached to release
3. **GitHub release** is created with auto-generated notes
4. **Changelog** is updated automatically

### Release Artifacts

Each release includes:
- **Source code** (tar.gz, zip)
- **Python wheel** (built package)
- **Release notes** with changelog
- **Installation instructions**

### Setting up nginx and certbot


To run nginx and certbot run the following command:

```bash
docker-compose --profile nginx up
```

1. Modify configuration in `nginx/app.conf`, `init_cert.sh` with the appropriate config/credentials.

2. Run the init script(Ensure that you have made the appropriate dns mapping for the server at your domain provider):

    ```bash
    ./init_cert.sh
    ```
