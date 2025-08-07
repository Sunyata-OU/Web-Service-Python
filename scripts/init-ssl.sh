#!/bin/bash

# Enhanced SSL Certificate Setup Script
# Based on best practices from production deployments

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOMAIN=""
EMAIL=""
SKIP_STAGING=0
FORCE=0
VERBOSE=0
DRY_RUN=0
RSA_KEY_SIZE=4096
DATA_PATH="./certbot"

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Enhanced SSL certificate setup with Let's Encrypt

OPTIONS:
    --email EMAIL       Email address for Let's Encrypt registration (required)
    --domain DOMAIN     Domain name (will try to extract from .env if not provided)
    --skip-staging      Skip staging environment test and go directly to production
    --force             Force certificate renewal even if valid certificate exists
    --verbose           Enable verbose output
    --dry-run           Test the setup without making actual changes
    --rsa-key-size SIZE RSA key size (default: 4096)
    --data-path PATH    Path for certificate data (default: ./certbot)
    -h, --help          Show this help message

Examples:
    $0 --email user@example.com --domain example.com
    $0 --email user@example.com --force --verbose
    $0 --dry-run --domain example.com --email user@example.com

EOF
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [[ $VERBOSE -eq 1 ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --skip-staging)
            SKIP_STAGING=1
            shift
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --rsa-key-size)
            RSA_KEY_SIZE="$2"
            shift 2
            ;;
        --data-path)
            DATA_PATH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v dig &> /dev/null; then
        log_warning "dig is not installed. DNS validation will be skipped."
    fi
    
    log_success "All dependencies are available"
}

# Extract domain from .env file if not provided
extract_domain_from_env() {
    if [[ -z "$DOMAIN" ]]; then
        if [[ -f ".env" ]]; then
            DOMAIN=$(grep "^DOMAIN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
            if [[ -n "$DOMAIN" ]]; then
                log_info "Extracted domain from .env: $DOMAIN"
            fi
        fi
        
        if [[ -z "$DOMAIN" ]]; then
            log_error "Domain not specified and not found in .env file"
            log_error "Please provide domain using --domain option"
            exit 1
        fi
    fi
}

# Validate inputs
validate_inputs() {
    log_info "Validating inputs..."
    
    if [[ -z "$EMAIL" ]]; then
        log_error "Email is required. Use --email option."
        exit 1
    fi
    
    # Validate email format
    if [[ ! "$EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        log_error "Invalid email format: $EMAIL"
        exit 1
    fi
    
    if [[ -z "$DOMAIN" ]]; then
        log_error "Domain is required"
        exit 1
    fi
    
    # Validate domain format
    if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
        log_error "Invalid domain format: $DOMAIN"
        exit 1
    fi
    
    log_success "Input validation passed"
}

# Check DNS resolution
check_dns_resolution() {
    log_info "Checking DNS resolution for $DOMAIN..."
    
    if command -v dig &> /dev/null; then
        local ip=$(dig +short "$DOMAIN" A | tail -n1)
        if [[ -n "$ip" ]]; then
            log_success "DNS resolution successful: $DOMAIN -> $ip"
        else
            log_warning "DNS resolution failed for $DOMAIN"
            log_warning "Make sure your domain points to this server's IP address"
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        log_verbose "Skipping DNS check (dig not available)"
    fi
}

# Check if certificate already exists and is valid
check_existing_certificate() {
    local cert_path="$DATA_PATH/conf/live/$DOMAIN/fullchain.pem"
    
    if [[ -f "$cert_path" ]] && [[ $FORCE -eq 0 ]]; then
        log_info "Checking existing certificate..."
        
        # Check if certificate is valid and not expiring soon (30 days)
        if openssl x509 -checkend 2592000 -noout -in "$cert_path" &>/dev/null; then
            log_success "Valid certificate already exists for $DOMAIN"
            log_info "Certificate will expire on: $(openssl x509 -enddate -noout -in "$cert_path" | cut -d= -f 2)"
            log_info "Use --force to renew anyway"
            exit 0
        else
            log_warning "Certificate exists but is expiring soon or invalid"
        fi
    fi
}

# Download recommended TLS parameters
download_tls_parameters() {
    log_info "Downloading recommended TLS parameters..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would download TLS parameters"
        return
    fi
    
    mkdir -p "$DATA_PATH/conf"
    
    if [[ ! -e "$DATA_PATH/conf/options-ssl-nginx.conf" ]] || [[ $FORCE -eq 1 ]]; then
        log_verbose "Downloading options-ssl-nginx.conf..."
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$DATA_PATH/conf/options-ssl-nginx.conf"
        log_success "Downloaded options-ssl-nginx.conf"
    fi
    
    if [[ ! -e "$DATA_PATH/conf/ssl-dhparams.pem" ]] || [[ $FORCE -eq 1 ]]; then
        log_verbose "Downloading ssl-dhparams.pem..."
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$DATA_PATH/conf/ssl-dhparams.pem"
        log_success "Downloaded ssl-dhparams.pem"
    fi
}

# Create dummy certificate for initial nginx startup
create_dummy_certificate() {
    log_info "Creating dummy certificate for $DOMAIN..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would create dummy certificate"
        return
    fi
    
    local path="/etc/letsencrypt/live/$DOMAIN"
    mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
    
    docker-compose run --rm --entrypoint "\
        openssl req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1\
        -keyout '$path/privkey.pem' \
        -out '$path/fullchain.pem' \
        -subj '/CN=localhost'" certbot
    
    log_success "Dummy certificate created"
}

# Start nginx with dummy certificate
start_nginx() {
    log_info "Starting nginx with dummy certificate..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would start nginx"
        return
    fi
    
    docker-compose --profile nginx up --force-recreate -d nginx
    
    # Wait for nginx to be ready
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if curl -f http://localhost/.well-known/acme-challenge/test 2>/dev/null; then
            log_success "Nginx is ready"
            return
        fi
        log_verbose "Waiting for nginx to be ready... ($retries retries left)"
        sleep 2
        ((retries--))
    done
    
    log_error "Nginx failed to start properly"
    exit 1
}

# Delete dummy certificate
delete_dummy_certificate() {
    log_info "Deleting dummy certificate for $DOMAIN..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would delete dummy certificate"
        return
    fi
    
    docker-compose run --rm --entrypoint "\
        rm -Rf /etc/letsencrypt/live/$DOMAIN && \
        rm -Rf /etc/letsencrypt/archive/$DOMAIN && \
        rm -Rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot
    
    log_success "Dummy certificate deleted"
}

# Test with staging environment
test_staging_certificate() {
    if [[ $SKIP_STAGING -eq 1 ]]; then
        log_info "Skipping staging environment test"
        return
    fi
    
    log_info "Testing certificate issuance with staging environment..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would test with staging environment"
        return
    fi
    
    docker-compose run --rm --entrypoint "\
        certbot certonly --webroot -w /var/www/certbot \
        --staging \
        --email $EMAIL \
        -d $DOMAIN \
        --rsa-key-size $RSA_KEY_SIZE \
        --agree-tos \
        --force-renewal \
        --non-interactive" certbot
    
    if [[ $? -eq 0 ]]; then
        log_success "Staging certificate test passed"
        # Clean up staging certificate
        delete_dummy_certificate
    else
        log_error "Staging certificate test failed"
        exit 1
    fi
}

# Request production certificate
request_production_certificate() {
    log_info "Requesting Let's Encrypt certificate for $DOMAIN..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would request production certificate"
        return
    fi
    
    docker-compose run --rm --entrypoint "\
        certbot certonly --webroot -w /var/www/certbot \
        --email $EMAIL \
        -d $DOMAIN \
        --rsa-key-size $RSA_KEY_SIZE \
        --agree-tos \
        --force-renewal \
        --non-interactive" certbot
    
    if [[ $? -eq 0 ]]; then
        log_success "Production certificate obtained successfully"
    else
        log_error "Failed to obtain production certificate"
        exit 1
    fi
}

# Reload nginx with new certificate
reload_nginx() {
    log_info "Reloading nginx with new certificate..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would reload nginx"
        return
    fi
    
    docker-compose exec nginx nginx -s reload
    
    if [[ $? -eq 0 ]]; then
        log_success "Nginx reloaded successfully"
    else
        log_error "Failed to reload nginx"
        exit 1
    fi
}

# Verify HTTPS functionality
verify_https() {
    log_info "Verifying HTTPS functionality..."
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_info "[DRY RUN] Would verify HTTPS"
        return
    fi
    
    # Test HTTPS connection
    if curl -f "https://$DOMAIN" &>/dev/null; then
        log_success "HTTPS is working correctly"
    else
        log_warning "HTTPS verification failed. Check your nginx configuration."
    fi
    
    # Check certificate details
    local cert_info=$(openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
    if [[ -n "$cert_info" ]]; then
        log_info "Certificate details:"
        echo "$cert_info"
    fi
}

# Main execution
main() {
    log_info "Starting SSL certificate setup for production deployment"
    
    if [[ $DRY_RUN -eq 1 ]]; then
        log_warning "Running in DRY RUN mode - no actual changes will be made"
    fi
    
    check_dependencies
    extract_domain_from_env
    validate_inputs
    check_dns_resolution
    check_existing_certificate
    
    log_info "Domain: $DOMAIN"
    log_info "Email: $EMAIL"
    log_info "RSA Key Size: $RSA_KEY_SIZE"
    log_info "Data Path: $DATA_PATH"
    
    download_tls_parameters
    create_dummy_certificate
    start_nginx
    delete_dummy_certificate
    test_staging_certificate
    request_production_certificate
    reload_nginx
    verify_https
    
    log_success "SSL certificate setup completed successfully!"
    log_info "Your site should now be accessible via HTTPS at https://$DOMAIN"
    log_info "Certificate will auto-renew via the certbot container"
}

# Run main function
main "$@"