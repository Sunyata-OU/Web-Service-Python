# Deployment Guide

This guide covers deploying the Web Service Template in production with SSL certificates and proper security configurations.

## Quick Start

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd Web-Service-Python
   cp .env-copy .env
   # Edit .env file with your configuration
   # Install uv if not already installed: pip install uv
   uv sync --dev  # Install dependencies
   ```

2. **Set up SSL certificates**:
   ```bash
   ./scripts/init-ssl.sh --email your-email@domain.com --domain your-domain.com
   ```

3. **Start services**:
   ```bash
   docker compose --profile nginx up -d
   ```

### SSH Setup for Private Repositories

If your application depends on private repositories or packages, set up SSH support:

1. **Ensure SSH agent is running**:
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_rsa  # Add your private key
   ```

2. **Build with SSH support**:
   ```bash
   make build-ssh
   # OR
   docker compose build --ssh default
   ```

3. **Verify SSH access**:
   ```bash
   ssh -T git@github.com
   ```

## Detailed Setup

### 1. Environment Configuration

Edit the `.env` file with your production settings:

```bash
# Required for SSL
DOMAIN=your-domain.com

# Change all default passwords
POSTGRES_PASSWORD=your-secure-password
S3_ACCESS_KEY_ID=your-minio-user
S3_ACCESS_KEY=your-minio-password

# Update service configuration
LOG_LEVEL=INFO
WORKERS_COUNT=2  # Adjust based on your server
```

### 2. SSL Certificate Setup

The improved SSL setup script provides comprehensive certificate management:

**Basic setup:**
```bash
./scripts/init-ssl.sh --email admin@your-domain.com --domain your-domain.com
```

**With staging test (recommended for first-time setup):**
```bash
./scripts/init-ssl.sh --email admin@your-domain.com --domain your-domain.com --verbose
```

**Force renewal:**
```bash
./scripts/init-ssl.sh --email admin@your-domain.com --force --verbose
```

**Options:**
- `--email`: Your email for Let's Encrypt registration (required)
- `--domain`: Domain name (auto-extracted from .env if not provided)
- `--skip-staging`: Skip staging environment test
- `--force`: Force certificate renewal
- `--verbose`: Enable detailed logging
- `--dry-run`: Test setup without making changes

### 3. Service Architecture

The deployment includes:

- **FastAPI**: Web application server
- **PostgreSQL**: Primary database
- **Redis**: Caching and task queue
- **MinIO**: S3-compatible object storage
- **Celery**: Background task processing
- **Nginx**: Reverse proxy with SSL termination
- **Certbot**: Automatic SSL certificate renewal

### 4. Network Configuration

The deployment uses a custom Docker network with these improvements:

- **Isolated networking**: Services communicate via container names
- **No host networking**: Better security and port management
- **Resource limits**: Prevents resource exhaustion
- **Health checks**: Automatic service monitoring
- **Structured logging**: Centralized log management

### 5. Security Features

#### SSL/TLS Configuration
- Let's Encrypt certificates with auto-renewal
- TLS 1.2 and 1.3 support
- HTTP/2 enabled
- SSL stapling for performance
- Strong cipher suites

#### Security Headers
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection
- Referrer-Policy

#### Rate Limiting
- General requests: 10/second
- API endpoints: 20/second
- Authentication: 5/second
- Burst handling with proper 429 responses

#### File Protection
- Blocks access to `.env`, `.git`, `__pycache__`
- Secure static file serving
- Proper error page handling

### 6. Monitoring and Maintenance

#### Health Checks
All services include health checks with proper timeouts:
- FastAPI: HTTP health endpoint
- PostgreSQL: Connection test
- Redis: PING command
- MinIO: Health API
- Nginx: HTTP status check

#### Logging
- JSON format for structured logging
- Log rotation (10MB max, 3 files)
- Separate access and error logs
- Configurable log levels

#### Certificate Renewal
Certificates automatically renew via the certbot container:
- Runs every 12 hours
- Checks certificate expiration
- Renews when needed (30 days before expiry)
- Reloads nginx configuration

## Production Checklist

### Before Deployment
- [ ] Update all passwords in `.env`
- [ ] Set correct `DOMAIN` value
- [ ] Configure firewall (ports 80, 443)
- [ ] Set up DNS A record pointing to server
- [ ] Test domain resolution: `dig your-domain.com`

### Security Hardening
- [ ] Change default MinIO credentials
- [ ] Use strong PostgreSQL password
- [ ] Enable fail2ban (recommended)
- [ ] Configure server firewall
- [ ] Set up automated backups
- [ ] Review nginx security headers
- [ ] Test SSL configuration: [SSL Labs](https://www.ssllabs.com/ssltest/)

### Performance Optimization
- [ ] Adjust worker count based on CPU cores
- [ ] Configure resource limits for containers
- [ ] Set up monitoring (optional)
- [ ] Configure log rotation
- [ ] Test application performance

## Troubleshooting

### SSL Certificate Issues

**Certificate not working:**
```bash
# Check certificate status
openssl x509 -in ./certbot/conf/live/your-domain.com/fullchain.pem -text -noout

# Test with staging first
./scripts/init-ssl.sh --email your@email.com --verbose --dry-run

# Force renewal
./scripts/init-ssl.sh --email your@email.com --force
```

**Domain not resolving:**
```bash
# Check DNS resolution
dig your-domain.com A
nslookup your-domain.com

# Verify server accessibility
curl -I http://your-domain.com/.well-known/acme-challenge/test
```

### Service Issues

**View logs:**
```bash
# All services
docker compose logs

# Specific service
docker compose logs nginx
docker compose logs fastapi
```

**Check service status:**
```bash
docker compose ps
docker compose --profile nginx ps
```

**Restart services:**
```bash
# Restart specific service
docker compose restart nginx

# Rebuild and restart
docker compose up --build -d
```

### Network Issues

**Test internal connectivity:**
```bash
# Enter FastAPI container
docker compose exec fastapi bash

# Test database connection
nc -zv db 5432

# Test Redis connection
nc -zv redis_db 6379
```

## Migration from Legacy Setup

If upgrading from the old configuration:

1. **Backup existing certificates:**
   ```bash
   cp -r ./certbot ./certbot-backup
   ```

2. **Update Docker Compose:**
   The new configuration uses custom networks instead of `host` networking.

3. **Update environment variables:**
   Change host references from `127.0.0.1` to container names (`db`, `redis_db`, etc.)

4. **Use new SSL script:**
   The legacy `init-letsencrypt.sh` will redirect to the improved script.

5. **Test thoroughly:**
   Verify all services can communicate and SSL works properly.

## Support

For issues with the deployment:

1. Check the troubleshooting section above
2. Review Docker and Nginx logs
3. Verify DNS and firewall configuration
4. Test with staging certificates first
5. Check the GitHub repository for updates and issues

## Advanced Configuration

### Custom Nginx Configuration

To customize nginx settings, edit `nginx/app.conf` and restart:
```bash
# Edit configuration
vim nginx/app.conf

# Restart nginx
docker compose restart nginx
```

### Database Scaling

For high-traffic applications:
- Increase worker count: `WORKERS_COUNT=4`
- Add database connection pooling
- Consider read replicas
- Monitor resource usage

### Monitoring Integration

The deployment is ready for monitoring tools:
- Health check endpoints at `/health`
- Structured JSON logs
- Container resource metrics
- SSL certificate expiration monitoring