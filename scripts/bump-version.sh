#!/bin/bash
set -e

# Version bumping script for Web Service Python Template
# Usage: ./scripts/bump-version.sh [major|minor|patch|prerelease] [message]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Default values
BUMP_TYPE=${1:-patch}
COMMIT_MESSAGE=${2:-""}

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

# Validate bump type
case $BUMP_TYPE in
    major|minor|patch|prerelease)
        log_info "Bumping version: $BUMP_TYPE"
        ;;
    *)
        log_error "Invalid bump type: $BUMP_TYPE"
        log_info "Usage: $0 [major|minor|patch|prerelease] [message]"
        exit 1
        ;;
esac

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff --quiet; then
    log_error "There are uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Make sure we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    log_warning "You're on branch '$CURRENT_BRANCH', not 'main'. Continue? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        log_info "Aborted."
        exit 0
    fi
fi

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
if [ -z "$CURRENT_VERSION" ]; then
    log_error "Could not find version in pyproject.toml"
    exit 1
fi

log_info "Current version: $CURRENT_VERSION"

# Calculate new version
calculate_new_version() {
    local current=$1
    local bump_type=$2

    # Split version into parts (assuming semantic versioning)
    if [[ $current =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-(.+))?$ ]]; then
        major=${BASH_REMATCH[1]}
        minor=${BASH_REMATCH[2]}
        patch=${BASH_REMATCH[3]}
        prerelease=${BASH_REMATCH[5]}
    else
        log_error "Invalid version format: $current"
        exit 1
    fi

    case $bump_type in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "${major}.$((minor + 1)).0"
            ;;
        patch)
            echo "${major}.${minor}.$((patch + 1))"
            ;;
        prerelease)
            if [ -n "$prerelease" ]; then
                # Extract prerelease number and increment
                if [[ $prerelease =~ ^(.+)\.([0-9]+)$ ]]; then
                    pre_name=${BASH_REMATCH[1]}
                    pre_num=${BASH_REMATCH[2]}
                    echo "${major}.${minor}.${patch}-${pre_name}.$((pre_num + 1))"
                else
                    echo "${major}.${minor}.${patch}-${prerelease}.1"
                fi
            else
                echo "${major}.${minor}.$((patch + 1))-alpha.0"
            fi
            ;;
    esac
}

NEW_VERSION=$(calculate_new_version "$CURRENT_VERSION" "$BUMP_TYPE")
log_info "New version: $NEW_VERSION"

# Confirm the version bump
log_warning "This will:"
echo "  • Update version in pyproject.toml from $CURRENT_VERSION to $NEW_VERSION"
echo "  • Create a git commit"
echo "  • Create a git tag v$NEW_VERSION"
echo "  • Push to origin"
echo ""
echo "Continue? (y/n)"
read -r response
if [ "$response" != "y" ]; then
    log_info "Aborted."
    exit 0
fi

# Update version in pyproject.toml
log_info "Updating pyproject.toml..."
sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
rm pyproject.toml.bak

# Verify the change
UPDATED_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
if [ "$UPDATED_VERSION" != "$NEW_VERSION" ]; then
    log_error "Failed to update version in pyproject.toml"
    exit 1
fi

log_success "Updated version in pyproject.toml"

# Create commit message
if [ -z "$COMMIT_MESSAGE" ]; then
    COMMIT_MESSAGE="Bump version to $NEW_VERSION"
fi

# Create git commit
log_info "Creating git commit..."
git add pyproject.toml
git commit -m "$COMMIT_MESSAGE"
log_success "Created commit: $COMMIT_MESSAGE"

# Create git tag
log_info "Creating git tag..."
git tag -a "v$NEW_VERSION" -m "Release $NEW_VERSION"
log_success "Created tag: v$NEW_VERSION"

# Push changes
log_info "Pushing changes to origin..."
git push origin
git push origin "v$NEW_VERSION"
log_success "Pushed changes and tag to origin"

log_success "Version bump complete! 🎉"
log_info "The release workflow will automatically:"
echo "  • Run tests"
echo "  • Build the package"
echo "  • Create a GitHub release"
echo "  • Build and push Docker images"
echo ""
log_info "Check the Actions tab on GitHub to monitor the release process."
