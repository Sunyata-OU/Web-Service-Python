#!/bin/bash

# Web Service Template - Monitoring Script
# Performs comprehensive health checks and system monitoring

set -e

# Import common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Default values
ENV="${1:-local}"
VERBOSE=${VERBOSE:-false}
LOG_FILE="/var/log/webapp-monitor-${ENV}.log"

# Usage information
usage() {
    cat << EOF
Usage: $0 [ENVIRONMENT] [OPTIONS]

Monitor Web Service Template health and performance

ENVIRONMENT:
    local       Local development environment (default)
    dev         Development environment  
    prod        Production environment

OPTIONS:
    --verbose   Enable verbose output
    --log-file  Custom log file path
    --help      Show this help message

Examples:
    $0 local
    $0 prod --verbose
    VERBOSE=true $0 dev

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        local|dev|prod)
            ENV="$1"
            shift
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Configuration based on environment
setup_environment() {
    validate_env "$ENV" || exit 1
    
    case "$ENV" in
        local)
            BASE_URL="http://localhost:${SERVICE_PORT:-8000}"
            DB_HOST="localhost"
            REDIS_HOST="localhost"
            MINIO_HOST="localhost"
            USE_SSL=false
            ;;
        dev)
            BASE_URL="https://${DOMAIN:-localhost}"
            DB_HOST="${DOMAIN:-localhost}"
            REDIS_HOST="${DOMAIN:-localhost}" 
            MINIO_HOST="${DOMAIN:-localhost}"
            USE_SSL=true
            ;;
        prod)
            BASE_URL="https://${DOMAIN}"
            DB_HOST="${DOMAIN}"
            REDIS_HOST="${DOMAIN}"
            MINIO_HOST="${DOMAIN}"
            USE_SSL=true
            if [[ -z "$DOMAIN" ]]; then
                error "DOMAIN environment variable required for production monitoring"
                exit 1
            fi
            ;;
    esac
    
    info "Monitoring environment: $ENV"
    info "Base URL: $BASE_URL"
}

# Log monitoring results
log_result() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Log to file if directory exists
    if [[ -d "$(dirname "$LOG_FILE")" ]]; then
        echo "$timestamp - $message" >> "$LOG_FILE"
    fi
    
    # Always log to stdout in verbose mode
    if [[ "$VERBOSE" == "true" ]]; then
        echo "$message"
    fi
}

# Check Docker environment
check_docker_environment() {
    banner "Docker Environment Check"
    
    check_docker_requirements || return 1
    
    info "Checking Docker containers..."
    
    # Get container status
    local containers
    if [[ "$ENV" == "prod" ]]; then
        containers=$(docker-compose --profile nginx ps -q 2>/dev/null || true)
    else
        containers=$(docker-compose ps -q 2>/dev/null || true)
    fi
    
    if [[ -z "$containers" ]]; then
        error "No containers found running"
        return 1
    fi
    
    # Check each service
    local services=("fastapi" "db" "redis_db" "minio")
    if [[ "$ENV" == "prod" ]]; then
        services+=("nginx" "certbot")
    fi
    
    local failed_services=()
    
    for service in "${services[@]}"; do
        local status=$(get_service_status "$service")
        if [[ "$status" == "running" ]]; then
            success "Service $service: $status"
            
            # Check container health if available
            local health=$(docker-compose ps "$service" 2>/dev/null | grep "$service" | awk '{print $4}' || echo "unknown")
            if [[ "$health" =~ healthy ]]; then
                success "Service $service: healthy"
            elif [[ "$health" =~ unhealthy ]]; then
                warn "Service $service: unhealthy"
                failed_services+=("$service (unhealthy)")
            fi
        else
            error "Service $service: $status"
            failed_services+=("$service")
        fi
        
        log_result "Service $service: $status"
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        error "Failed services: ${failed_services[*]}"
        return 1
    fi
    
    success "All Docker services are running"
    return 0
}

# Check application endpoints
check_application_health() {
    banner "Application Health Check"
    
    # Health endpoint
    info "Checking application health endpoint..."
    if check_health "$BASE_URL/health" 3 2; then
        success "Health endpoint responding"
        log_result "Health endpoint: OK"
    else
        error "Health endpoint not responding"
        log_result "Health endpoint: FAILED"
        return 1
    fi
    
    # Main application endpoint
    info "Checking main application endpoint..."
    if curl -f -s "$BASE_URL/" >/dev/null 2>&1; then
        success "Main endpoint responding"
        log_result "Main endpoint: OK"
    else
        error "Main endpoint not responding"
        log_result "Main endpoint: FAILED"
        return 1
    fi
    
    # API endpoint (if exists)
    info "Checking API endpoint..."
    if curl -f -s "$BASE_URL/api/" >/dev/null 2>&1; then
        success "API endpoint responding"
        log_result "API endpoint: OK"
    else
        warn "API endpoint not available (this may be expected)"
        log_result "API endpoint: N/A"
    fi
    
    return 0
}

# Check SSL certificate (production only)
check_ssl_certificate() {
    if [[ "$USE_SSL" != "true" ]]; then
        return 0
    fi
    
    banner "SSL Certificate Check"
    
    info "Checking SSL certificate..."
    
    # Check if certificate files exist
    local cert_path="./certbot/conf/live/$DOMAIN/fullchain.pem"
    if [[ -f "$cert_path" ]]; then
        # Check certificate expiration
        local expiry_date=$(openssl x509 -enddate -noout -in "$cert_path" 2>/dev/null | cut -d= -f 2)
        if [[ -n "$expiry_date" ]]; then
            local expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s 2>/dev/null)
            local current_timestamp=$(date +%s)
            local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
            
            if [[ $days_until_expiry -gt 30 ]]; then
                success "SSL certificate expires in $days_until_expiry days"
                log_result "SSL certificate: OK ($days_until_expiry days remaining)"
            elif [[ $days_until_expiry -gt 0 ]]; then
                warn "SSL certificate expires in $days_until_expiry days - renewal recommended"
                log_result "SSL certificate: WARNING ($days_until_expiry days remaining)"
            else
                error "SSL certificate has expired!"
                log_result "SSL certificate: EXPIRED"
                return 1
            fi
        fi
    else
        warn "SSL certificate file not found: $cert_path"
        log_result "SSL certificate: NOT FOUND"
    fi
    
    # Test HTTPS connection
    info "Testing HTTPS connection..."
    if curl -f -s --max-time 10 "https://$DOMAIN/health" >/dev/null 2>&1; then
        success "HTTPS connection working"
        log_result "HTTPS connection: OK"
    else
        error "HTTPS connection failed"
        log_result "HTTPS connection: FAILED"
        return 1
    fi
    
    # Test HTTP to HTTPS redirect
    info "Testing HTTP to HTTPS redirect..."
    local redirect_response=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/" 2>/dev/null)
    if [[ "$redirect_response" == "301" || "$redirect_response" == "302" ]]; then
        success "HTTP to HTTPS redirect working"
        log_result "HTTP redirect: OK"
    else
        warn "HTTP to HTTPS redirect may not be working (got: $redirect_response)"
        log_result "HTTP redirect: WARNING"
    fi
    
    return 0
}

# Check system resources
check_system_resources() {
    banner "System Resource Check"
    
    # Disk usage
    info "Checking disk usage..."
    local disk_usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -lt 80 ]]; then
        success "Disk usage: ${disk_usage}%"
        log_result "Disk usage: OK (${disk_usage}%)"
    elif [[ $disk_usage -lt 90 ]]; then
        warn "Disk usage: ${disk_usage}% - monitor closely"
        log_result "Disk usage: WARNING (${disk_usage}%)"
    else
        error "Disk usage: ${disk_usage}% - critical level"
        log_result "Disk usage: CRITICAL (${disk_usage}%)"
    fi
    
    # Memory usage
    info "Checking memory usage..."
    if command_exists free; then
        local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
        if [[ $mem_usage -lt 80 ]]; then
            success "Memory usage: ${mem_usage}%"
            log_result "Memory usage: OK (${mem_usage}%)"
        elif [[ $mem_usage -lt 90 ]]; then
            warn "Memory usage: ${mem_usage}% - monitor closely"
            log_result "Memory usage: WARNING (${mem_usage}%)"
        else
            error "Memory usage: ${mem_usage}% - critical level"
            log_result "Memory usage: CRITICAL (${mem_usage}%)"
        fi
    else
        warn "Memory usage check not available on this system"
        log_result "Memory usage: N/A"
    fi
    
    # Load average (if available)
    if [[ -r /proc/loadavg ]]; then
        local load_avg=$(awk '{print $1}' /proc/loadavg)
        local cpu_cores=$(nproc 2>/dev/null || echo 1)
        local load_pct=$(echo "scale=0; $load_avg * 100 / $cpu_cores" | bc 2>/dev/null || echo "unknown")
        
        if [[ "$load_pct" != "unknown" ]]; then
            if [[ $load_pct -lt 80 ]]; then
                success "Load average: $load_avg (${load_pct}%)"
                log_result "Load average: OK ($load_avg)"
            else
                warn "Load average: $load_avg (${load_pct}%) - high load"
                log_result "Load average: WARNING ($load_avg)"
            fi
        else
            info "Load average: $load_avg"
            log_result "Load average: $load_avg"
        fi
    fi
    
    return 0
}

# Check database connectivity
check_database_connectivity() {
    banner "Database Connectivity Check"
    
    # PostgreSQL
    info "Checking PostgreSQL connectivity..."
    if wait_for_port "$DB_HOST" "${POSTGRES_PORT:-5432}" 5; then
        success "PostgreSQL is accessible"
        log_result "PostgreSQL: OK"
    else
        error "PostgreSQL is not accessible"
        log_result "PostgreSQL: FAILED"
        return 1
    fi
    
    # Redis
    info "Checking Redis connectivity..."
    if wait_for_port "$REDIS_HOST" "${REDIS_PORT:-6379}" 5; then
        success "Redis is accessible"
        log_result "Redis: OK"
    else
        error "Redis is not accessible"
        log_result "Redis: FAILED"
        return 1
    fi
    
    # MinIO
    info "Checking MinIO connectivity..."
    if wait_for_port "$MINIO_HOST" "${S3_PORT:-9002}" 5; then
        success "MinIO is accessible"
        log_result "MinIO: OK"
    else
        error "MinIO is not accessible"
        log_result "MinIO: FAILED"
        return 1
    fi
    
    return 0
}

# Check log files
check_logs() {
    banner "Log File Check"
    
    local log_paths=(
        "./data/web/logs"
        "/var/log/nginx"
    )
    
    for log_path in "${log_paths[@]}"; do
        if [[ -d "$log_path" ]]; then
            local log_size=$(calculate_size "$log_path")
            info "Log directory $log_path: $log_size"
            log_result "Log directory $log_path: $log_size"
            
            # Check for recent errors in application logs
            if [[ -f "$log_path/error.log" ]]; then
                local recent_errors=$(grep -c "ERROR\|CRITICAL" "$log_path/error.log" 2>/dev/null | tail -100 || echo 0)
                if [[ $recent_errors -gt 0 ]]; then
                    warn "Found $recent_errors recent errors in application logs"
                    log_result "Application errors: $recent_errors recent entries"
                else
                    success "No recent errors in application logs"
                    log_result "Application errors: None"
                fi
            fi
        else
            debug "Log directory not found: $log_path"
        fi
    done
    
    return 0
}

# Main monitoring function
main() {
    banner "Web Service Template Health Monitor" "="
    
    # Load environment if .env exists
    load_env 2>/dev/null || warn "Could not load .env file"
    
    # Setup environment configuration
    setup_environment
    
    local failed_checks=()
    local total_checks=0
    
    # Run all checks
    local checks=(
        "check_docker_environment"
        "check_application_health" 
        "check_ssl_certificate"
        "check_system_resources"
        "check_database_connectivity"
        "check_logs"
    )
    
    for check in "${checks[@]}"; do
        ((total_checks++))
        if ! $check; then
            failed_checks+=("$check")
        fi
        separator
    done
    
    # Summary
    banner "Monitoring Summary" "="
    
    local passed_checks=$((total_checks - ${#failed_checks[@]}))
    
    info "Total checks: $total_checks"
    success "Passed: $passed_checks"
    
    if [[ ${#failed_checks[@]} -gt 0 ]]; then
        error "Failed: ${#failed_checks[@]}"
        error "Failed checks: ${failed_checks[*]}"
        log_result "MONITORING SUMMARY: $passed_checks/$total_checks passed - FAILED"
        exit 1
    else
        success "All checks passed!"
        log_result "MONITORING SUMMARY: $total_checks/$total_checks passed - OK"
        exit 0
    fi
}

# Run main function
main "$@"