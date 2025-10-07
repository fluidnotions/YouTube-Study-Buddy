# Docker Deployment Guide

This guide covers building, publishing, and deploying the YouTube Study Buddy Docker image.

---

## Quick Links

- [Building the Docker Image](#building-the-docker-image)
- [Pushing to Docker Hub](#pushing-to-docker-hub)
- [Running with Docker Compose](#running-with-docker-compose)
- [Volume Mounts](#volume-mounts)
- [Environment Variables](#environment-variables)

---

## Building the Docker Image

### Prerequisites

- Docker installed and running
- Docker Hub account (for publishing)

### Build Command

```bash
# From the project root directory
docker buildx build -t youtube-study-buddy:latest .

# With specific version tag
docker buildx build -t youtube-study-buddy:v1.0.0 .

# Multi-platform build (for ARM64 and AMD64)
docker buildx build --platform linux/amd64,linux/arm64 -t youtube-study-buddy:latest .
```

### Build Options

**Development Build (with source changes):**
```bash
docker buildx build --no-cache -t youtube-study-buddy:dev .
```

**Production Build (optimized):**
```bash
docker buildx build \
  --build-arg PYHON_VERSION=3.13 \
  -t youtube-study-buddy:latest \
  .
```

### Verify Build

```bash
# Check image size
docker images youtube-study-buddy

# Test run locally
docker run -p 8501:8501 \
  -e CLAUDE_API_KEY=your_key_here \
  youtube-study-buddy:latest
```

---

## Pushing to Docker Hub

### Login to Docker Hub

```bash
# Login with your credentials
docker login

# Or with username
docker login -u your-username
```

### Tag Image

```bash
# Tag for your Docker Hub account
docker tag youtube-study-buddy:latest fluidnotions/youtube-study-buddy:latest

# Tag with version
docker tag youtube-study-buddy:latest fluidnotions/youtube-study-buddy:v1.0.0

# Tag as development
docker tag youtube-study-buddy:latest fluidnotions/youtube-study-buddy:dev
```

### Push to Docker Hub

```bash
# Push latest
docker push fluidnotions/youtube-study-buddy:latest

# Push versioned tag
docker push fluidnotions/youtube-study-buddy:v1.0.0

# Push all tags
docker push --all-tags fluidnotions/youtube-study-buddy
```

### Complete Build and Push Workflow

```bash
#!/bin/bash
# build-and-push.sh

# Set version
VERSION="1.0.0"

# Build image
echo "Building Docker image..."
docker buildx build -t youtube-study-buddy:${VERSION} -t youtube-study-buddy:latest .

# Tag for Docker Hub
echo "Tagging image..."
docker tag youtube-study-buddy:${VERSION} fluidnotions/youtube-study-buddy:${VERSION}
docker tag youtube-study-buddy:latest fluidnotions/youtube-study-buddy:latest

# Push to Docker Hub
echo "Pushing to Docker Hub..."
docker push fluidnotions/youtube-study-buddy:${VERSION}
docker push fluidnotions/youtube-study-buddy:latest

echo "✓ Build and push complete!"
echo "Image available at: fluidnotions/youtube-study-buddy:${VERSION}"
```

**Usage:**
```bash
chmod +x build-and-push.sh
./build-and-push.sh
```

---

## Running with Docker Compose

### Basic Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  youtube-study-buddy:
    image: fluidnotions/youtube-study-buddy:latest
    container_name: youtube-study-buddy
    ports:
      - "8501:8501"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    volumes:
      - ./notes:/app/notes
    restart: unless-stopped
```

### With Tor Proxy

```yaml
version: '3.8'

services:
  youtube-study-buddy:
    image: fluidnotions/youtube-study-buddy:latest
    container_name: youtube-study-buddy
    ports:
      - "8501:8501"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    volumes:
      - ./notes:/app/notes
    depends_on:
      - tor-proxy
    restart: unless-stopped

  tor-proxy:
    image: dperson/torproxy:latest
    container_name: tor-proxy
    ports:
      - "9050:9050"
      - "9051:9051"
    restart: unless-stopped
```

### Run Commands

```bash
# Start services
docker compose up

# Start in background
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f youtube-study-buddy

# Rebuild and restart
docker compose up --build

# Pull latest images
docker compose pull
```

---

## Volume Mounts

### Default Mount

```yaml
volumes:
  - ./notes:/app/notes
```

### Custom Output Directory

**Important**: The Streamlit web interface uses a fixed output path of `notes/` inside the container. To change where notes are saved on your host machine, modify the volume mount in `docker-compose.yml`:

```yaml
volumes:
  - /path/to/your/obsidian/vault:/app/notes
```

**Why is the path fixed?**

Docker containers can only access directories that are explicitly mounted via volumes. The Streamlit UI runs inside the container and cannot access arbitrary paths on your host filesystem. To maintain consistency and avoid confusion, the output path is fixed to `/app/notes` inside the container.

**How to customize the output location:**

1. **For Docker users**: Edit the volume mount in `docker-compose.yml` to point to your desired host directory
2. **For CLI users**: Use the `--base-dir` flag when running `youtube-study-buddy` directly

### Multiple Mounts

```yaml
volumes:
  - ./notes:/app/notes           # Output directory
  - ./.env:/app/.env:ro                      # Environment file (read-only)
  - ./custom-config.yaml:/app/config.yaml:ro # Custom config
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_API_KEY` | Claude API key for note generation | `sk-ant-...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SENTENCE_TRANSFORMER_MODEL` | ML model for auto-categorization | `all-MiniLM-L6-v2` |
| `STREAMLIT_SERVER_PORT` | Port for Streamlit app | `8501` |
| `STREAMLIT_SERVER_ADDRESS` | Bind address | `0.0.0.0` |

### Using .env File

Create `.env` file:
```bash
CLAUDE_API_KEY=your_key_here
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
```

Reference in docker-compose.yml:
```yaml
services:
  youtube-study-buddy:
    env_file:
      - .env
```

---

## Advanced Configuration

### Custom Dockerfile Build

If you want to build locally instead of pulling from Docker Hub:

```yaml
services:
  youtube-study-buddy:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    volumes:
      - ./notes:/app/notes
```

### Resource Limits

```yaml
services:
  youtube-study-buddy:
    image: fluidnotions/youtube-study-buddy:latest
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
```

### Health Check Override

```yaml
services:
  youtube-study-buddy:
    image: fluidnotions/youtube-study-buddy:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker compose logs youtube-study-buddy
```

**Common issues:**
- Missing `CLAUDE_API_KEY` environment variable
- Port 8501 already in use
- Volume mount permission issues

**Solutions:**
```bash
# Check if port is in use
lsof -i :8501

# Fix volume permissions
chmod -R 755 "notes/"

# Verify environment variables
docker-compose config
```

### Image Pull Fails

**Error: "manifest unknown"**
- Image hasn't been pushed to Docker Hub yet
- Build and push the image first

**Solution:**
```bash
# Pull latest from Docker Hub
docker pull fluidnotions/youtube-study-buddy:latest

# Or build locally with compose
docker compose build
```

### Volume Mount Issues

**Notes not saving:**

Check volume mount:
```bash
docker inspect youtube-study-buddy | grep Mounts -A 10
```

Fix permissions:
```bash
# Create directory if missing
mkdir -p "notes"

# Set permissions
chmod 755 "notes"
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/docker-publish.yml`:

```yaml
name: Docker Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: docker.io
  IMAGE_NAME: fluidnotions/youtube-study-buddy

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to Docker Hub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## Image Maintenance

### Cleanup Old Images

```bash
# Remove unused images
docker image prune -a

# Remove specific version
docker rmi fluidnotions/youtube-study-buddy:v1.0.0

# Remove all local youtube-study-buddy images
docker rmi $(docker images -q youtube-study-buddy)
```

### Update to Latest

```bash
# Pull latest image
docker compose pull

# Restart with new image
docker compose up -d
```

### Version Management

```bash
# Tag releases
git tag v1.0.0
git push origin v1.0.0

# Build for release
docker buildx build -t fluidnotions/youtube-study-buddy:v1.0.0 .
docker push fluidnotions/youtube-study-buddy:v1.0.0
```

---

## Security Best Practices

### Don't Include Secrets in Image

❌ **Bad:**
```dockerfile
ENV CLAUDE_API_KEY=sk-ant-...
```

✅ **Good:**
```yaml
environment:
  - CLAUDE_API_KEY=${CLAUDE_API_KEY}
```

### Use .dockerignore

Create `.dockerignore`:
```
.env
.git
.gitignore
*.md
tests/
docs/
.vscode/
__pycache__/
*.pyc
notes/
```

### Scan for Vulnerabilities

```bash
# Scan image
docker scan fluidnotions/youtube-study-buddy:latest

# Or use Trivy
trivy image fluidnotions/youtube-study-buddy:latest
```

---

## Need Help?

- **Docker Issues**: Check [Docker Documentation](https://docs.docker.com/)
- **Project Issues**: [GitHub Issues](https://github.com/fluidnotions/YouTube-Study-Buddy/issues)
- **General Setup**: See [Alternative Setup Guide](alternative-setup.md)
