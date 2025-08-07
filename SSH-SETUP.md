# SSH Setup Guide

This template includes comprehensive SSH support for accessing private repositories and packages during both build and runtime.

## Overview

The Docker configuration supports:
- **Private GitHub, GitLab, and Bitbucket repositories**
- **Private Python packages** from git repositories
- **SSH agent forwarding** for secure key management
- **Runtime git operations** within containers

## Quick Setup

### 1. SSH Agent Setup

```bash
# Start SSH agent
eval "$(ssh-agent -s)"

# Add your SSH key
ssh-add ~/.ssh/id_rsa

# Verify key is loaded
ssh-add -l
```

### 2. Build with SSH Support

```bash
# Using Makefile (recommended)
make build-ssh

# Using docker compose directly
docker compose build --ssh default

# For production deployment with SSH
DOCKER_BUILDKIT=1 docker compose --profile nginx build --ssh default
```

### 3. Verify SSH Access

```bash
# Test GitHub access
ssh -T git@github.com

# Test GitLab access  
ssh -T git@gitlab.com

# Test Bitbucket access
ssh -T git@bitbucket.org
```

## Use Cases

### Private Python Packages

Add private packages to your `pyproject.toml`:

```toml
dependencies = [
    "private-package @ git+ssh://git@github.com/company/private-package.git",
    "another-private @ git+ssh://git@gitlab.com/org/another-private.git@v1.0.0",
]
```

### Private Git Repositories

Clone private repositories in your application code:

```python
import subprocess

# This will work at runtime with SSH keys
subprocess.run(["git", "clone", "git@github.com:company/private-repo.git"])
```

### Development Dependencies

Include private development tools:

```toml
[project.optional-dependencies]
dev = [
    "company-dev-tools @ git+ssh://git@github.com/company/dev-tools.git",
]
```

## SSH Key Management

### Using Different SSH Keys

If you need different SSH keys for different services:

```bash
# Create SSH config
cat >> ~/.ssh/config << EOF
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_rsa

Host gitlab.company.com
    HostName gitlab.company.com
    User git
    IdentityFile ~/.ssh/company_rsa
EOF

# Add both keys
ssh-add ~/.ssh/github_rsa
ssh-add ~/.ssh/company_rsa
```

### SSH Key Generation

Generate new SSH keys if needed:

```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/id_ed25519

# Start agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copy public key to add to GitHub/GitLab
cat ~/.ssh/id_ed25519.pub
```

## Docker Compose Configuration

The template's `docker-compose.yml` is already configured for SSH. The Dockerfile includes:

```dockerfile
# Build stage with SSH
RUN --mount=type=ssh uv sync --frozen --no-dev

# Runtime stage with SSH support
RUN mkdir -p -m 0700 /home/appuser/.ssh && \
    ssh-keyscan github.com gitlab.com bitbucket.org >> /home/appuser/.ssh/known_hosts
```

## Troubleshooting

### SSH Agent Not Found

```bash
# Check if agent is running
echo $SSH_AUTH_SOCK

# If empty, start agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa
```

### Permission Denied

```bash
# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
chmod 700 ~/.ssh

# Test connection
ssh -vT git@github.com
```

### Build Failures with SSH

```bash
# Enable BuildKit (required for SSH)
export DOCKER_BUILDKIT=1

# Check SSH agent is running
ssh-add -l

# Rebuild with verbose output
docker compose build --ssh default --progress=plain
```

### Container SSH Issues

If SSH doesn't work inside the running container:

```bash
# Check SSH files in container
docker compose exec fastapi ls -la ~/.ssh/

# Check SSH agent forwarding
docker compose exec fastapi ssh -T git@github.com
```

## Security Considerations

1. **SSH Agent Forwarding**: Keys are never copied into the container, only forwarded during build
2. **Known Hosts**: Pre-populated with GitHub, GitLab, and Bitbucket fingerprints
3. **Non-root User**: SSH operates under the `appuser` account for better security
4. **Runtime Access**: SSH client available for git operations during runtime

## Advanced Configuration

### Custom SSH Configuration

Mount custom SSH config for complex setups:

```yaml
# docker-compose.override.yml
services:
  fastapi:
    volumes:
      - ~/.ssh/config:/home/appuser/.ssh/config:ro
```

### Multiple SSH Keys

For organizations using multiple SSH keys:

```bash
# Use ssh-add with multiple keys
ssh-add ~/.ssh/github_rsa
ssh-add ~/.ssh/gitlab_rsa
ssh-add ~/.ssh/bitbucket_rsa

# Verify all keys loaded
ssh-add -l
```

### CI/CD Integration

For GitHub Actions or similar CI:

```yaml
# .github/workflows/build.yml
- name: Set up SSH
  uses: webfactory/ssh-agent@v0.5.3
  with:
    ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

- name: Build with SSH
  run: make build-ssh
```

This SSH setup enables your template to work seamlessly with private repositories and enterprise environments while maintaining security best practices.