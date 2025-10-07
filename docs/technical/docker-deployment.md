# Single Container Deployment with Embedded Tor

YouTube Study Buddy now bundles Tor directly inside the application container, eliminating the need for a separate Tor proxy container. This simplifies deployment to a single Docker image.

## Architecture

**Previous Setup:**
- Two containers: `youtube-study-buddy` + `tor-proxy`
- Required docker-compose for orchestration
- Network communication between containers

**New Setup:**
- Single container with both Streamlit app and Tor daemon
- Can run with `docker run` or docker-compose
- Tor runs as a background process managed by entrypoint script

## Quick Start

### Option 1: Docker Run (Simplest)

```bash
# Pull the image
docker pull fluidnotions/youtube-study-buddy:latest

# Run with your API key and volume mount
docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  -e CLAUDE_API_KEY=your_api_key_here \
  -v ./notes:/app/notes \
  --restart unless-stopped \
  fluidnotions/youtube-study-buddy:latest
```

Access at: http://localhost:8501

### Option 2: Docker Compose

Create `.env` file:
```bash
CLAUDE_API_KEY=your_api_key_here
```

Run:
```bash
docker compose up -d
```

### Option 3: Build from Source

```bash
# Clone and navigate to project
cd ytstudybuddy

# Build image
docker build -t youtube-study-buddy .

# Run
docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  --env-file .env \
  -v ./notes:/app/notes \
  youtube-study-buddy
```

## How It Works

### Startup Sequence

The container uses an entrypoint script (`/app/entrypoint.sh`) that:

1. **Starts Tor daemon** in background
   ```bash
   tor &
   ```

2. **Waits for Tor readiness** (up to 30 seconds)
   - Tests connection to Tor network via check.torproject.org
   - Exits with error if Tor fails to start

3. **Starts Streamlit app**
   - Connects to localhost:9050 for Tor SOCKS5 proxy
   - Serves web interface on 0.0.0.0:8501

### Environment Variables

The following are set automatically in the Dockerfile:

```bash
TOR_HOST=127.0.0.1      # Tor runs on localhost
TOR_PORT=9050           # Standard Tor SOCKS5 port
```

You only need to provide:
```bash
CLAUDE_API_KEY=sk-...   # Required for AI features
```

### Health Check

Docker performs dual health checks:
1. **Streamlit health**: `curl http://localhost:8501/_stcore/health`
2. **Tor connectivity**: `curl -x socks5h://127.0.0.1:9050 https://check.torproject.org/`

Both must succeed for container to be marked healthy.

## Advantages Over Multi-Container Setup

| Aspect | Multi-Container | Single Container |
|--------|----------------|------------------|
| **Complexity** | Requires docker-compose | Simple `docker run` |
| **Networking** | Inter-container network | Localhost only |
| **Startup Time** | ~40s (wait for Tor container) | ~30s (integrated) |
| **Port Exposure** | 3 ports (8501, 9050, 8118) | 1 port (8501) |
| **Resource Usage** | 2 containers | 1 container |
| **Configuration** | Multiple service configs | Single Dockerfile |

## Troubleshooting

### Check Container Logs

```bash
docker logs youtube-study-buddy
```

Look for:
- `Starting Tor...`
- `Tor is ready!`
- `Starting Streamlit...`

### Verify Tor is Running

```bash
# Enter container
docker exec -it youtube-study-buddy bash

# Check Tor process
ps aux | grep tor

# Test Tor connection
curl -x socks5h://127.0.0.1:9050 https://check.torproject.org/
```

### Container Won't Start

Check health status:
```bash
docker inspect youtube-study-buddy | grep -A 10 Health
```

If Tor fails:
1. Increase start period: Edit `HEALTHCHECK --start-period=60s` in Dockerfile
2. Check Tor logs inside container: `docker exec youtube-study-buddy cat /var/log/tor/log`

### Connection Issues

If transcripts fail to fetch:
1. Verify Tor is accessible: `docker exec youtube-study-buddy curl -x socks5h://127.0.0.1:9050 https://www.youtube.com`
2. Check TOR_HOST/TOR_PORT environment variables are set correctly
3. Restart container: `docker restart youtube-study-buddy`

## Building and Publishing

### Build Multi-Platform Image

```bash
# Build for both AMD64 and ARM64
docker buildx build --platform linux/amd64,linux/arm64 \
  -t fluidnotions/youtube-study-buddy:latest \
  --push .
```

### Tag Specific Version

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t fluidnotions/youtube-study-buddy:latest \
  -t fluidnotions/youtube-study-buddy:v1.0.0 \
  --push .
```

## Migration from Multi-Container Setup

If you're running the old docker-compose setup:

```bash
# Stop old containers
docker compose down

# Remove old tor-proxy image
docker rmi dperson/torproxy:latest

# Pull new single-container image
docker pull fluidnotions/youtube-study-buddy:latest

# Update docker-compose.yml (or switch to docker run)
# Start new setup
docker compose up -d
```

Your data in `./notes` volume will be preserved.

## Performance Notes

- **Tor startup**: ~10-20 seconds
- **Streamlit startup**: ~5-10 seconds
- **Total ready time**: ~15-30 seconds
- **Memory usage**: ~300-400MB (Tor adds ~50MB)

## Security Considerations

- Tor runs as `debian-tor` user (non-root)
- Tor data directory has 700 permissions
- Only port 8501 is exposed externally
- Tor SOCKS proxy (9050) is internal to container
- All YouTube requests are routed through Tor network

## Alternative: Running without Tor

To disable Tor and use direct connections:

```bash
docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  -e CLAUDE_API_KEY=your_api_key_here \
  -e USE_TOR=false \
  -v ./notes:/app/notes \
  fluidnotions/youtube-study-buddy:latest
```

Note: This requires code modification to respect the `USE_TOR` environment variable.
