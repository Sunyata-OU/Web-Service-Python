#!/bin/bash
set -e

# Changelog update script for Web Service Python Template
# Updates CHANGELOG.md with commits since last release

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if CHANGELOG.md exists
if [ ! -f "CHANGELOG.md" ]; then
    log_error "CHANGELOG.md not found"
    exit 1
fi

# Get current version and last tag
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

log_info "Current version: $CURRENT_VERSION"
if [ -n "$LAST_TAG" ]; then
    log_info "Last tag: $LAST_TAG"
else
    log_info "No previous tags found"
fi

# Create temporary file for new changelog
TEMP_CHANGELOG=$(mktemp)

# Write header
cat << 'EOF' > "$TEMP_CHANGELOG"
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

EOF

# Add unreleased changes if there are commits since last tag
if [ -n "$LAST_TAG" ]; then
    # Check if there are commits since last tag
    if git log --oneline "$LAST_TAG"..HEAD | grep -q .; then
        echo "### Added" >> "$TEMP_CHANGELOG"
        echo "" >> "$TEMP_CHANGELOG"

        # Get commits and categorize them
        git log --oneline "$LAST_TAG"..HEAD --grep="^feat" --pretty=format:"- %s" >> "$TEMP_CHANGELOG" || true
        if ! git log --oneline "$LAST_TAG"..HEAD --grep="^feat" --pretty=format:"- %s" | grep -q .; then
            echo "- No new features" >> "$TEMP_CHANGELOG"
        fi

        echo "" >> "$TEMP_CHANGELOG"
        echo "### Changed" >> "$TEMP_CHANGELOG"
        echo "" >> "$TEMP_CHANGELOG"

        git log --oneline "$LAST_TAG"..HEAD --grep="^change\|^update\|^improve" --pretty=format:"- %s" >> "$TEMP_CHANGELOG" || true
        if ! git log --oneline "$LAST_TAG"..HEAD --grep="^change\|^update\|^improve" --pretty=format:"- %s" | grep -q .; then
            echo "- No changes" >> "$TEMP_CHANGELOG"
        fi

        echo "" >> "$TEMP_CHANGELOG"
        echo "### Fixed" >> "$TEMP_CHANGELOG"
        echo "" >> "$TEMP_CHANGELOG"

        git log --oneline "$LAST_TAG"..HEAD --grep="^fix\|^bug" --pretty=format:"- %s" >> "$TEMP_CHANGELOG" || true
        if ! git log --oneline "$LAST_TAG"..HEAD --grep="^fix\|^bug" --pretty=format:"- %s" | grep -q .; then
            echo "- No fixes" >> "$TEMP_CHANGELOG"
        fi

        echo "" >> "$TEMP_CHANGELOG"
        echo "### All Changes" >> "$TEMP_CHANGELOG"
        echo "" >> "$TEMP_CHANGELOG"
        git log --oneline "$LAST_TAG"..HEAD --pretty=format:"- %s (%h)" >> "$TEMP_CHANGELOG"
        echo "" >> "$TEMP_CHANGELOG"
    else
        echo "- No unreleased changes" >> "$TEMP_CHANGELOG"
        echo "" >> "$TEMP_CHANGELOG"
    fi
else
    echo "- Initial development in progress" >> "$TEMP_CHANGELOG"
    echo "" >> "$TEMP_CHANGELOG"
fi

# Append existing changelog content (skip the header and first unreleased section)
if grep -q "^## \[.*\]" CHANGELOG.md; then
    # Find the first release section and append everything from there
    sed -n '/^## \[[0-9]/,$p' CHANGELOG.md >> "$TEMP_CHANGELOG"
else
    # If no release sections exist, just append the template
    cat >> "$TEMP_CHANGELOG" << 'EOF'

## [0.1.0] - TBD

### Added
- Initial release
EOF
fi

# Replace the original changelog
mv "$TEMP_CHANGELOG" CHANGELOG.md

log_success "Updated CHANGELOG.md with unreleased changes"
log_info "Review the changes and commit when ready:"
echo "  git add CHANGELOG.md"
echo "  git commit -m 'Update changelog'"
