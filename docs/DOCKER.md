# Docker Setup and Workflow

## Image Naming Convention

The official Docker image is: **`fluidnotions/youtube-study-buddy:latest`**

## Quick Start (Production)

```bash
# 1. Pull and run the pre-built image
docker-compose pull
docker-compose up -d

# 2. Check logs
docker-compose logs -f youtube-study-buddy

# 3. Access the web interface
open http://localhost:8501
```

## Development Workflow

### Building from Source

```bash
# Build new image using dev compose file
docker-compose -f docker-compose.dev.yml build

# Or use the build script (recommended)
./scripts/build-image.sh

# With version tag
./scripts/build-image.sh v1.0.0
```

### Running Development Build

```bash
# Run with live source mounting (hot reload)
docker-compose -f docker-compose.dev.yml up

# Run in background
docker-compose -f docker-compose.dev.yml up -d
```

## Cleanup Old Images

Over time, you may accumulate old images with different names. Clean them up:

```bash
# Run the cleanup script
./scripts/cleanup-docker-images.sh

# This will remove:
# - tor-debugging-youtube-study-buddy:latest
# - ytstudybuddy-youtube-study-buddy:latest
# - youtube-study-buddy:python-tor
# - Other old builds
```

## File Structure

```
.
├── docker-compose.yml          # Production (uses pre-built image)
├── docker-compose.dev.yml      # Development (builds from source)
├── Dockerfile                  # Build definition
└── scripts/
    ├── build-image.sh         # Build and tag helper script
    ├── cleanup-docker-images.sh   # Cleanup old images
    └── fix_permissions.sh     # Fix Docker file permissions
```

## Configuration Files

### `docker-compose.yml` (Production)
- Uses pre-built image from Docker Hub: `fluidnotions/youtube-study-buddy:latest`
- Does NOT build on every run
- Fast startup
- For end users

### `docker-compose.dev.yml` (Development)
- Builds from local Dockerfile
- Mounts source code for live development
- Tags as both `:latest` and `:dev`
- For developers

## Publishing to Docker Hub

```bash
# 1. Build the image
./scripts/build-image.sh v1.0.0

# 2. Login to Docker Hub
docker login

# 3. Push the image
docker push fluidnotions/youtube-study-buddy:v1.0.0
docker push fluidnotions/youtube-study-buddy:latest
```

## Environment Variables

Required in `.env` file:

```bash
# Claude API key
CLAUDE_API_KEY=your_key_here

# Docker user mapping (prevents root-owned files)
USER_ID=1000
GROUP_ID=1000

# Optional: Custom Tor settings
# TOR_HOST=tor-proxy
# TOR_PORT=9050
```

## Volumes

- `./notes:/app/notes` - Study notes output (persisted on host)
- `tor-data` - Tor data (Docker volume)

### Development Additional Volumes

When using `docker-compose.dev.yml`:
- `./src:/app/src` - Live source code
- `./streamlit_app.py:/app/streamlit_app.py` - Live Streamlit app

## Troubleshooting

### Permission Issues

Files created as root? Run:
```bash
./scripts/fix_permissions.sh
```

Ensure `.env` has:
```bash
USER_ID=1000
GROUP_ID=1000
```

### Wrong Image Name

If you see weird image names like `tor-debugging-youtube-study-buddy`:
```bash
./scripts/cleanup-docker-images.sh
docker-compose pull
```

### Rebuild from Scratch

```bash
# Remove everything
docker-compose down -v
docker system prune -a

# Rebuild
./scripts/build-image.sh
```

## Container Names

- Production: `youtube-study-buddy`
- Development: `youtube-study-buddy-dev`
- Tor Proxy (prod): `ytstudybuddy-tor-proxy`
- Tor Proxy (dev): `ytstudybuddy-tor-proxy-dev`

## Best Practices

1. **Production Users**: Always use `docker-compose.yml` (pre-built image)
2. **Developers**: Use `docker-compose.dev.yml` for local changes
3. **After Code Changes**: Rebuild with `./scripts/build-image.sh`
4. **Before Commits**: Test with production compose file
5. **Version Tags**: Use semantic versioning (v1.0.0, v1.1.0, etc.)

## Image Metadata

The Docker image includes these labels:
- `org.opencontainers.image.title`: YouTube Study Buddy
- `org.opencontainers.image.description`: Transform YouTube videos into AI-powered study notes
- `org.opencontainers.image.authors`: fluidnotions
- `org.opencontainers.image.source`: https://github.com/fluidnotions/YouTube-Study-Buddy

View with:
```bash
docker inspect fluidnotions/youtube-study-buddy:latest | grep -A 10 Labels
```
