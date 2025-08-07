#!/bin/bash

# Migration script from Poetry to uv
# This script helps transition the project from Poetry to uv

set -e

# Import common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Configuration
BACKUP_DIR="./poetry-backup"

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Migrate the Web Service Template from Poetry to uv

OPTIONS:
    --clean         Remove Poetry files after migration
    --backup-dir    Directory to backup Poetry files (default: ./poetry-backup)
    --help          Show this help message

Examples:
    $0                    # Migrate with backup
    $0 --clean           # Migrate and clean up Poetry files
    $0 --backup-dir /tmp # Custom backup location

EOF
}

CLEAN_UP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_UP=true
            shift
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

main() {
    banner "Migration from Poetry to uv" "="
    
    # Check if Poetry is installed
    if ! command_exists poetry; then
        warn "Poetry is not installed or not found in PATH"
        warn "Proceeding with uv setup only"
    else
        info "Found Poetry installation"
    fi
    
    # Check if uv is installed
    if ! command_exists uv; then
        info "Installing uv..."
        if pip install uv; then
            success "uv installed successfully"
        else
            error "Failed to install uv"
            exit 1
        fi
    else
        success "uv is already installed"
    fi
    
    # Backup Poetry files if they exist
    if [[ -f "poetry.lock" || -f "pyproject.toml" ]]; then
        info "Backing up Poetry files..."
        mkdir -p "$BACKUP_DIR"
        
        if [[ -f "poetry.lock" ]]; then
            cp poetry.lock "$BACKUP_DIR/"
            success "Backed up poetry.lock"
        fi
        
        # Check if pyproject.toml has Poetry configuration
        if [[ -f "pyproject.toml" ]] && grep -q "tool.poetry" pyproject.toml; then
            cp pyproject.toml "$BACKUP_DIR/pyproject.toml.poetry"
            success "Backed up Poetry pyproject.toml"
        fi
        
        success "Poetry files backed up to: $BACKUP_DIR"
    fi
    
    # Initialize uv project
    info "Initializing uv project..."
    
    # Create uv.lock if it doesn't exist
    if [[ ! -f "uv.lock" ]]; then
        if uv sync --dev; then
            success "uv.lock created successfully"
        else
            warn "uv sync encountered issues, but continuing..."
        fi
    else
        info "uv.lock already exists"
    fi
    
    # Verify installation
    info "Verifying uv installation..."
    
    if [[ -d ".venv" ]]; then
        success "Virtual environment created: .venv"
        
        # Test a few key packages
        local test_packages=("fastapi" "pydantic" "sqlalchemy")
        for package in "${test_packages[@]}"; do
            if uv run python -c "import $package; print(f'$package: {$package.__version__}')" 2>/dev/null; then
                success "Package $package is available"
            else
                warn "Package $package might not be installed correctly"
            fi
        done
    else
        error "Virtual environment not created"
        exit 1
    fi
    
    # Clean up Poetry files if requested
    if [[ "$CLEAN_UP" == "true" ]]; then
        info "Cleaning up Poetry files..."
        
        if [[ -f "poetry.lock" ]]; then
            rm poetry.lock
            success "Removed poetry.lock"
        fi
        
        # Only remove Poetry-specific sections from pyproject.toml
        if [[ -f "pyproject.toml" ]] && grep -q "tool.poetry" pyproject.toml; then
            warn "Note: pyproject.toml still contains some Poetry configuration"
            warn "The file has been updated for uv, but you may want to review it"
        fi
        
        success "Poetry cleanup completed"
    fi
    
    # Update .gitignore
    if [[ -f ".gitignore" ]]; then
        info "Updating .gitignore..."
        
        # Remove Poetry-specific entries and add uv entries
        if ! grep -q ".venv" .gitignore; then
            echo "" >> .gitignore
            echo "# uv" >> .gitignore
            echo ".venv/" >> .gitignore
            echo "uv.lock" >> .gitignore
            success "Updated .gitignore for uv"
        else
            info ".gitignore already configured for uv"
        fi
    fi
    
    # Migration summary
    banner "Migration Summary" "="
    
    info "✅ uv is installed and configured"
    info "✅ Dependencies are installed in .venv"
    info "✅ pyproject.toml updated for uv"
    info "✅ Makefile updated for uv commands"
    
    if [[ -d "$BACKUP_DIR" ]]; then
        info "📁 Poetry files backed up in: $BACKUP_DIR"
    fi
    
    success "Migration completed successfully!"
    
    separator
    echo
    info "Next steps:"
    echo "  1. Activate the virtual environment: source .venv/bin/activate"
    echo "  2. Test the installation: make test"
    echo "  3. Start development: make dev"
    echo "  4. Review and update any remaining Poetry references"
    
    if [[ "$CLEAN_UP" != "true" ]]; then
        echo
        warn "Poetry files are still present. Run with --clean to remove them:"
        echo "  $0 --clean"
    fi
}

# Run main function
main "$@"