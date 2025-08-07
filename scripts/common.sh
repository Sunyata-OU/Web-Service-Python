#!/bin/bash

# Common utilities for Web Service Template
# This file should be sourced by other scripts

# Color definitions for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

info() {
    log "${BLUE}[INFO]${NC} $1"
}

warn() {
    log "${YELLOW}[WARNING]${NC} $1"
}

error() {
    log "${RED}[ERROR]${NC} $1"
}

success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

debug() {
    if [[ "${DEBUG:-}" == "true" ]]; then
        log "${PURPLE}[DEBUG]${NC} $1"
    fi
}

# Utility functions

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate environment (local, dev, prod)
validate_env() {
    local env="$1"
    case "$env" in
        local|dev|prod)
            return 0
            ;;
        *)
            error "Invalid environment: $env. Must be one of: local, dev, prod"
            return 1
            ;;
    esac
}

# Check application health with configurable retries
check_health() {
    local url="$1"
    local max_retries="${2:-30}"
    local retry_interval="${3:-2}"
    local retries=0
    
    info "Checking health at: $url"
    
    while [[ $retries -lt $max_retries ]]; do
        if curl -f -s "$url" >/dev/null 2>&1; then
            success "Health check passed for $url"
            return 0
        fi
        
        ((retries++))
        if [[ $retries -lt $max_retries ]]; then
            debug "Health check failed, retrying in ${retry_interval}s... (attempt $retries/$max_retries)"
            sleep "$retry_interval"
        fi
    done
    
    error "Health check failed for $url after $max_retries attempts"
    return 1
}

# Calculate directory or file size
calculate_size() {
    local path="$1"
    if [[ -e "$path" ]]; then
        du -sh "$path" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# Docker compose helper with environment file support
docker_compose() {
    local env="${ENV:-local}"
    local compose_file="docker-compose.yml"
    
    # Select appropriate compose file
    case "$env" in
        debug)
            compose_file="docker-compose-debug.yml"
            ;;
        prod)
            # Use nginx profile for production
            docker-compose --profile nginx "$@"
            return $?
            ;;
    esac
    
    docker-compose -f "$compose_file" "$@"
}

# Wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local max_wait="${2:-60}"
    local waited=0
    
    info "Waiting for service: $service_name"
    
    while [[ $waited -lt $max_wait ]]; do
        if docker-compose ps "$service_name" | grep -q "Up"; then
            local health_status=$(docker-compose ps "$service_name" | grep "$service_name" | awk '{print $4}')
            if [[ "$health_status" == "Up" || "$health_status" =~ ^Up.*healthy ]]; then
                success "Service $service_name is ready"
                return 0
            fi
        fi
        
        sleep 2
        ((waited+=2))
        debug "Waiting for $service_name... (${waited}s/${max_wait}s)"
    done
    
    error "Service $service_name not ready after ${max_wait}s"
    return 1
}

# Check if Docker and Docker Compose are available
check_docker_requirements() {
    local missing_deps=()
    
    if ! command_exists docker; then
        missing_deps+=("docker")
    fi
    
    if ! command_exists docker-compose; then
        missing_deps+=("docker-compose")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        info "Please install Docker and Docker Compose:"
        info "  - Docker: https://docs.docker.com/get-docker/"
        info "  - Docker Compose: https://docs.docker.com/compose/install/"
        return 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running"
        info "Please start Docker and try again"
        return 1
    fi
    
    return 0
}

# Load environment variables from .env file
load_env() {
    local env_file="${1:-.env}"
    
    if [[ -f "$env_file" ]]; then
        debug "Loading environment from: $env_file"
        # Export variables from .env file, ignoring comments and empty lines
        set -a
        source <(grep -v '^#' "$env_file" | grep -v '^$')
        set +a
        success "Environment loaded from $env_file"
    else
        warn "Environment file not found: $env_file"
        return 1
    fi
}

# Get service status
get_service_status() {
    local service="$1"
    docker-compose ps -q "$service" >/dev/null 2>&1 && echo "running" || echo "stopped"
}

# Check if port is available
check_port() {
    local port="$1"
    local host="${2:-localhost}"
    
    if command_exists nc; then
        nc -z "$host" "$port" >/dev/null 2>&1
    elif command_exists telnet; then
        timeout 1 telnet "$host" "$port" >/dev/null 2>&1
    else
        # Fallback using /dev/tcp if available
        timeout 1 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null
    fi
}

# Wait for port to be available
wait_for_port() {
    local host="$1"
    local port="$2"
    local max_wait="${3:-60}"
    local waited=0
    
    info "Waiting for $host:$port to be available"
    
    while [[ $waited -lt $max_wait ]]; do
        if check_port "$port" "$host"; then
            success "Port $host:$port is available"
            return 0
        fi
        
        sleep 2
        ((waited+=2))
        debug "Waiting for $host:$port... (${waited}s/${max_wait}s)"
    done
    
    error "Port $host:$port not available after ${max_wait}s"
    return 1
}

# Backup directory with timestamp
backup_directory() {
    local source_dir="$1"
    local backup_base="${2:-./backups}"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_name=$(basename "$source_dir")_backup_$timestamp
    local backup_path="$backup_base/$backup_name"
    
    if [[ ! -d "$source_dir" ]]; then
        error "Source directory does not exist: $source_dir"
        return 1
    fi
    
    mkdir -p "$backup_base"
    
    info "Creating backup of $source_dir"
    if cp -r "$source_dir" "$backup_path"; then
        success "Backup created: $backup_path"
        echo "$backup_path"
        return 0
    else
        error "Failed to create backup"
        return 1
    fi
}

# Clean old backups (keep last N)
cleanup_old_backups() {
    local backup_dir="$1"
    local keep_count="${2:-5}"
    
    if [[ ! -d "$backup_dir" ]]; then
        debug "Backup directory does not exist: $backup_dir"
        return 0
    fi
    
    info "Cleaning up old backups in $backup_dir (keeping last $keep_count)"
    
    # Find and remove old backups
    local backup_files=($(find "$backup_dir" -maxdepth 1 -type d -name "*backup*" | sort -r))
    local total_backups=${#backup_files[@]}
    
    if [[ $total_backups -gt $keep_count ]]; then
        local to_remove=$((total_backups - keep_count))
        info "Found $total_backups backups, removing oldest $to_remove"
        
        for ((i=keep_count; i<total_backups; i++)); do
            local backup_to_remove="${backup_files[$i]}"
            info "Removing old backup: $(basename "$backup_to_remove")"
            rm -rf "$backup_to_remove"
        done
        
        success "Cleanup complete"
    else
        info "No cleanup needed (found $total_backups backups, keeping $keep_count)"
    fi
}

# Print separator line
separator() {
    local char="${1:--}"
    local length="${2:-60}"
    printf "%*s\n" "$length" | tr ' ' "$char"
}

# Print banner
banner() {
    local text="$1"
    local char="${2:-=}"
    local padding=4
    local text_length=${#text}
    local total_length=$((text_length + padding * 2))
    
    echo
    printf "%*s\n" "$total_length" | tr ' ' "$char"
    printf "%*s%s%*s\n" $padding '' "$text" $padding ''
    printf "%*s\n" "$total_length" | tr ' ' "$char"
    echo
}

# Export functions so they can be used in other scripts
export -f log info warn error success debug
export -f command_exists validate_env check_health calculate_size
export -f docker_compose wait_for_service check_docker_requirements
export -f load_env get_service_status check_port wait_for_port
export -f backup_directory cleanup_old_backups separator banner