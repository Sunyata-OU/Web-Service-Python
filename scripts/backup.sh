#!/bin/bash

# Web Service Template - Backup Script
# Creates comprehensive backups with retention policy

set -e

# Import common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Configuration
BACKUP_BASE_DIR="./backups"
BACKUP_DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_TYPE="full"
KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=12

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Create backups of the Web Service Template

OPTIONS:
    --type TYPE     Backup type: full, data, config (default: full)
    --dir DIR       Backup directory (default: ./backups)
    --keep-daily N  Keep N daily backups (default: 7)
    --keep-weekly N Keep N weekly backups (default: 4) 
    --keep-monthly N Keep N monthly backups (default: 12)
    --verbose       Enable verbose output
    --help          Show this help message

BACKUP TYPES:
    full            Complete backup (data, config, logs, certificates)
    data            Application data only (database, uploads, logs)
    config          Configuration only (nginx, SSL certificates, env files)

Examples:
    $0                           # Full backup with default settings
    $0 --type data              # Data-only backup
    $0 --dir /backup/webapp     # Custom backup directory
    $0 --keep-daily 14          # Keep 14 daily backups

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        --dir)
            BACKUP_BASE_DIR="$2"
            shift 2
            ;;
        --keep-daily)
            KEEP_DAILY="$2"
            shift 2
            ;;
        --keep-weekly)
            KEEP_WEEKLY="$2"
            shift 2
            ;;
        --keep-monthly)
            KEEP_MONTHLY="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
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

# Validate backup type
validate_backup_type() {
    case "$BACKUP_TYPE" in
        full|data|config)
            return 0
            ;;
        *)
            error "Invalid backup type: $BACKUP_TYPE"
            error "Must be one of: full, data, config"
            return 1
            ;;
    esac
}

# Create backup manifest
create_manifest() {
    local backup_dir="$1"
    local manifest_file="$backup_dir/backup_manifest.txt"
    
    info "Creating backup manifest..."
    
    cat > "$manifest_file" << EOF
# Web Service Template Backup Manifest
# Created: $(date)

Backup Type: $BACKUP_TYPE
Backup Date: $BACKUP_DATE
Backup Directory: $backup_dir
Environment: ${ENV:-unknown}

# System Information
Hostname: $(hostname)
Operating System: $(uname -a)
Docker Version: $(docker --version 2>/dev/null || echo "Not available")
Docker Compose Version: $(docker-compose --version 2>/dev/null || echo "Not available")

# Backup Contents:
EOF

    # List backup contents
    find "$backup_dir" -type f -name "*.tar.gz" -o -name "*.sql" -o -name "*.json" | while read -r file; do
        local file_size=$(calculate_size "$file")
        echo "  $(basename "$file") - $file_size" >> "$manifest_file"
    done
    
    echo "" >> "$manifest_file"
    echo "# Backup completed: $(date)" >> "$manifest_file"
    
    success "Manifest created: $manifest_file"
}

# Backup database
backup_database() {
    local backup_dir="$1"
    
    info "Backing up PostgreSQL database..."
    
    # Check if database is running
    if [[ "$(get_service_status db)" != "running" ]]; then
        warn "Database service is not running, skipping database backup"
        return 0
    fi
    
    # Load environment variables
    load_env 2>/dev/null || warn "Could not load environment variables"
    
    local db_name="${POSTGRES_DB:-webapp}"
    local db_user="${POSTGRES_USER:-postgres}"
    local backup_file="$backup_dir/database_${db_name}_${BACKUP_DATE}.sql"
    
    # Create database dump
    if docker-compose exec -T db pg_dump -U "$db_user" -d "$db_name" --clean --if-exists > "$backup_file" 2>/dev/null; then
        local backup_size=$(calculate_size "$backup_file")
        success "Database backup completed: $(basename "$backup_file") ($backup_size)"
        
        # Compress backup
        gzip "$backup_file"
        success "Database backup compressed"
    else
        error "Database backup failed"
        rm -f "$backup_file"
        return 1
    fi
    
    return 0
}

# Backup application data
backup_application_data() {
    local backup_dir="$1"
    
    info "Backing up application data..."
    
    local data_paths=(
        "./data"
        "./src/static"  
        "./src/templates"
    )
    
    for data_path in "${data_paths[@]}"; do
        if [[ -d "$data_path" ]]; then
            local path_name=$(basename "$data_path")
            local backup_file="$backup_dir/data_${path_name}_${BACKUP_DATE}.tar.gz"
            
            info "Backing up: $data_path"
            if tar -czf "$backup_file" -C "$(dirname "$data_path")" "$(basename "$data_path")" 2>/dev/null; then
                local backup_size=$(calculate_size "$backup_file")
                success "Data backup completed: $(basename "$backup_file") ($backup_size)"
            else
                error "Failed to backup: $data_path"
                rm -f "$backup_file"
            fi
        else
            debug "Data path not found: $data_path"
        fi
    done
}

# Backup logs
backup_logs() {
    local backup_dir="$1"
    
    info "Backing up log files..."
    
    local log_paths=(
        "./data/web/logs"
        "/var/log/nginx"
    )
    
    for log_path in "${log_paths[@]}"; do
        if [[ -d "$log_path" ]]; then
            local path_name=$(basename "$log_path")
            local backup_file="$backup_dir/logs_${path_name}_${BACKUP_DATE}.tar.gz"
            
            info "Backing up logs: $log_path"
            if tar -czf "$backup_file" -C "$(dirname "$log_path")" "$(basename "$log_path")" 2>/dev/null; then
                local backup_size=$(calculate_size "$backup_file")
                success "Logs backup completed: $(basename "$backup_file") ($backup_size)"
            else
                warn "Failed to backup logs: $log_path"
                rm -f "$backup_file"
            fi
        else
            debug "Log path not found: $log_path"
        fi
    done
}

# Backup configuration files
backup_configuration() {
    local backup_dir="$1"
    
    info "Backing up configuration files..."
    
    # Configuration files to backup
    local config_files=(
        ".env"
        ".env-copy"
        "docker-compose.yml"
        "docker-compose-debug.yml"
        "pyproject.toml"
        "alembic.ini"
        "Makefile"
    )
    
    # Configuration directories to backup
    local config_dirs=(
        "./nginx"
        "./docker"
        "./alembic"
        "./scripts"
    )
    
    # Backup individual config files
    local config_backup_file="$backup_dir/config_files_${BACKUP_DATE}.tar.gz"
    local temp_config_dir="/tmp/webapp_config_$$"
    mkdir -p "$temp_config_dir"
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            cp "$config_file" "$temp_config_dir/"
            debug "Added to config backup: $config_file"
        fi
    done
    
    if tar -czf "$config_backup_file" -C "/tmp" "$(basename "$temp_config_dir")" 2>/dev/null; then
        local backup_size=$(calculate_size "$config_backup_file")
        success "Config files backup completed: $(basename "$config_backup_file") ($backup_size)"
    else
        error "Failed to backup configuration files"
    fi
    
    rm -rf "$temp_config_dir"
    
    # Backup config directories
    for config_dir in "${config_dirs[@]}"; do
        if [[ -d "$config_dir" ]]; then
            local dir_name=$(basename "$config_dir")
            local backup_file="$backup_dir/config_${dir_name}_${BACKUP_DATE}.tar.gz"
            
            if tar -czf "$backup_file" -C "$(dirname "$config_dir")" "$(basename "$config_dir")" 2>/dev/null; then
                local backup_size=$(calculate_size "$backup_file")
                success "Config directory backup completed: $(basename "$backup_file") ($backup_size)"
            else
                warn "Failed to backup config directory: $config_dir"
                rm -f "$backup_file"
            fi
        fi
    done
}

# Backup SSL certificates
backup_certificates() {
    local backup_dir="$1"
    
    info "Backing up SSL certificates..."
    
    if [[ -d "./certbot" ]]; then
        local backup_file="$backup_dir/certificates_${BACKUP_DATE}.tar.gz"
        
        if tar -czf "$backup_file" -C . "certbot" 2>/dev/null; then
            local backup_size=$(calculate_size "$backup_file")
            success "Certificates backup completed: $(basename "$backup_file") ($backup_size)"
        else
            error "Failed to backup SSL certificates"
            rm -f "$backup_file"
        fi
    else
        warn "SSL certificates directory not found: ./certbot"
    fi
}

# Backup Docker volumes  
backup_docker_volumes() {
    local backup_dir="$1"
    
    info "Backing up Docker volumes..."
    
    # Get list of project volumes
    local project_volumes=$(docker volume ls -q | grep "$(basename "$PWD")" || true)
    
    if [[ -n "$project_volumes" ]]; then
        for volume in $project_volumes; do
            local backup_file="$backup_dir/volume_${volume}_${BACKUP_DATE}.tar.gz"
            
            info "Backing up Docker volume: $volume"
            
            # Create a temporary container to access the volume
            if docker run --rm -v "$volume:/volume" -v "$PWD/$backup_dir:/backup" \
                alpine tar czf "/backup/$(basename "$backup_file")" -C /volume . 2>/dev/null; then
                local backup_size=$(calculate_size "$backup_file")
                success "Volume backup completed: $(basename "$backup_file") ($backup_size)"
            else
                warn "Failed to backup Docker volume: $volume"
                rm -f "$backup_file"
            fi
        done
    else
        debug "No project-specific Docker volumes found"
    fi
}

# Perform backup based on type
perform_backup() {
    local backup_dir="$1"
    
    case "$BACKUP_TYPE" in
        full)
            info "Performing full backup..."
            backup_database "$backup_dir"
            backup_application_data "$backup_dir"
            backup_logs "$backup_dir"
            backup_configuration "$backup_dir"
            backup_certificates "$backup_dir"
            backup_docker_volumes "$backup_dir"
            ;;
        data)
            info "Performing data backup..."
            backup_database "$backup_dir"
            backup_application_data "$backup_dir"
            backup_logs "$backup_dir"
            ;;
        config)
            info "Performing configuration backup..."
            backup_configuration "$backup_dir"
            backup_certificates "$backup_dir"
            ;;
    esac
}

# Implement backup retention policy
implement_retention_policy() {
    info "Implementing backup retention policy..."
    
    local backup_pattern="backup_${BACKUP_TYPE}_"
    
    # Daily backups cleanup
    local daily_backups=($(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "${backup_pattern}*" | sort -r))
    if [[ ${#daily_backups[@]} -gt $KEEP_DAILY ]]; then
        info "Cleaning up daily backups (keeping $KEEP_DAILY most recent)"
        for ((i=$KEEP_DAILY; i<${#daily_backups[@]}; i++)); do
            local old_backup="${daily_backups[$i]}"
            # Check if backup is older than weekly retention
            local backup_age_days=$(( ($(date +%s) - $(stat -c %Y "$old_backup" 2>/dev/null || echo 0)) / 86400 ))
            
            if [[ $backup_age_days -gt 7 ]]; then
                # Check if this should be kept as a weekly backup
                local backup_day_of_week=$(date -d "@$(stat -c %Y "$old_backup" 2>/dev/null || echo 0)" +%u 2>/dev/null || echo 1)
                if [[ $backup_day_of_week -eq 7 ]]; then  # Sunday backups kept as weekly
                    debug "Keeping $(basename "$old_backup") as weekly backup"
                    continue
                fi
            fi
            
            if [[ $backup_age_days -gt 30 ]]; then
                # Check if this should be kept as a monthly backup
                local backup_day_of_month=$(date -d "@$(stat -c %Y "$old_backup" 2>/dev/null || echo 0)" +%d 2>/dev/null || echo 1)
                if [[ $backup_day_of_month -eq 1 ]]; then  # First day of month kept as monthly
                    debug "Keeping $(basename "$old_backup") as monthly backup"
                    continue
                fi
            fi
            
            info "Removing old backup: $(basename "$old_backup")"
            rm -rf "$old_backup"
        done
    fi
    
    success "Retention policy applied"
}

# Verify backup integrity
verify_backup() {
    local backup_dir="$1"
    
    info "Verifying backup integrity..."
    
    local errors=0
    
    # Verify compressed files
    find "$backup_dir" -name "*.tar.gz" | while read -r archive; do
        if tar -tzf "$archive" >/dev/null 2>&1; then
            debug "Archive OK: $(basename "$archive")"
        else
            error "Corrupted archive: $(basename "$archive")"
            ((errors++))
        fi
    done
    
    # Verify SQL files
    find "$backup_dir" -name "*.sql.gz" | while read -r sql_file; do
        if zcat "$sql_file" | head -n 1 | grep -q "PostgreSQL database dump" 2>/dev/null; then
            debug "SQL backup OK: $(basename "$sql_file")"
        else
            error "Invalid SQL backup: $(basename "$sql_file")"
            ((errors++))
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        success "Backup integrity verification passed"
        return 0
    else
        error "Backup integrity verification failed with $errors errors"
        return 1
    fi
}

# Main backup function
main() {
    banner "Web Service Template Backup" "="
    
    # Validate inputs
    validate_backup_type || exit 1
    
    # Load environment if available
    load_env 2>/dev/null || warn "Could not load .env file"
    
    # Check Docker requirements
    check_docker_requirements || exit 1
    
    # Create backup directory
    local backup_dir="$BACKUP_BASE_DIR/backup_${BACKUP_TYPE}_${BACKUP_DATE}"
    mkdir -p "$backup_dir"
    
    info "Backup type: $BACKUP_TYPE"
    info "Backup directory: $backup_dir"
    info "Retention policy: Daily=$KEEP_DAILY, Weekly=$KEEP_WEEKLY, Monthly=$KEEP_MONTHLY"
    
    # Perform backup
    if perform_backup "$backup_dir"; then
        # Create manifest
        create_manifest "$backup_dir"
        
        # Verify backup
        verify_backup "$backup_dir"
        
        # Calculate total backup size
        local total_size=$(calculate_size "$backup_dir")
        success "Backup completed successfully"
        success "Total backup size: $total_size"
        success "Backup location: $backup_dir"
        
        # Implement retention policy
        implement_retention_policy
        
        banner "Backup Summary" "="
        info "Backup type: $BACKUP_TYPE"
        info "Backup size: $total_size"
        info "Backup path: $backup_dir"
        success "✅ Backup completed successfully!"
        
        exit 0
    else
        error "Backup failed"
        # Clean up failed backup
        rm -rf "$backup_dir"
        exit 1
    fi
}

# Run main function
main "$@"