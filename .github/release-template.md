# Release Template

This template is used for creating consistent GitHub releases.

## What's Changed

<!-- Auto-generated release notes will be inserted here -->

## 📦 Installation

### Using Git
```bash
git clone https://github.com/{OWNER}/{REPO}.git
cd Web-Service-Python
git checkout v{VERSION}
uv sync
```

### Using Docker
```bash
docker pull ghcr.io/{OWNER}/{REPO}:{VERSION}
```

## 🚀 Quick Start

### Development Setup
```bash
# Clone and setup
git clone https://github.com/{OWNER}/{REPO}.git
cd Web-Service-Python
cp .env-copy .env

# Install dependencies
uv sync --dev

# Start development server
uv run uvicorn src.main:app --reload
```

### Production Deployment
```bash
# Clone and configure
git clone https://github.com/{OWNER}/{REPO}.git
cd Web-Service-Python
cp .env-copy .env

# Edit .env with your production settings
# Then start with Docker Compose
docker compose up -d
```

## 🧪 Testing

All releases are tested with:
- **Unit Tests**: 84+ passing tests covering core functionality
- **Integration Tests**: End-to-end API testing
- **Code Quality**: Linting, formatting, and type checking
- **Docker Build**: Multi-platform container builds

## 📋 Requirements

- **Python**: 3.10+ (for local development)
- **Docker**: 20.10+ & Docker Compose v2 (for containerized deployment)
- **System**: Linux, macOS, or Windows with WSL2

## 🆘 Support

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)

## 🔄 Migration Notes

<!-- Add any breaking changes or migration steps here -->

---

**Full Changelog**: {COMPARE_URL}
