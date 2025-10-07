# Docker Deployment Guide

YouTube Study Buddy runs as a single Docker container with Tor bundled inside.

## Quick Start

### Docker Run

```bash
docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  -e CLAUDE_API_KEY=your_api_key_here \
  -v ./notes:/app/notes \
  --restart unless-stopped \
  fluidnotions/youtube-study-buddy:latest
```

Access at: http://localhost:8501

### Docker Compose

Create `.env` file:
```bash
CLAUDE_API_KEY=your_api_key_here
```

Run:
```bash
docker compose up -d
```

### Build from Source

```bash
cd ytstudybuddy

docker build -t youtube-study-buddy .

docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  --env-file .env \
  -v ./notes:/app/notes \
  youtube-study-buddy
```

## How It Works

The container startup sequence:

1. Tor daemon launches → binds to 127.0.0.1:9050
2. Health check loop → verifies Tor connectivity (up to 30s)
3. Streamlit launches → connects to Tor on localhost
4. Container marked healthy → both services running

## Environment Variables

**Required:**
- `CLAUDE_API_KEY` - Your Claude API key

**Automatic (set in Dockerfile):**
- `TOR_HOST=127.0.0.1`
- `TOR_PORT=9050`
- `STREAMLIT_SERVER_PORT=8501`
- `STREAMLIT_SERVER_ADDRESS=0.0.0.0`

## Troubleshooting

### View Logs

```bash
docker logs youtube-study-buddy
```

Expected output:
```
Starting Tor...
Waiting for Tor to be ready...
Tor is ready!
Starting Streamlit...
```

### Check Tor Connection

```bash
docker exec -it youtube-study-buddy bash
curl -x socks5h://127.0.0.1:9050 https://check.torproject.org/
```

### Container Won't Start

```bash
# Check health status
docker inspect youtube-study-buddy --format='{{.State.Health.Status}}'

# Check for port conflicts
lsof -i :8501

# Check logs for errors
docker logs youtube-study-buddy
```

## Multi-Platform Builds

```bash
docker build --platform linux/amd64,linux/arm64 \
  -t fluidnotions/youtube-study-buddy:latest \
  --push .
```

## Volume Mounts

The Streamlit UI uses `/app/notes` inside the container. To change where notes are saved on your host:

```yaml
volumes:
  - /path/to/your/obsidian/vault:/app/notes
```

For CLI usage outside Docker, use the `--base-dir` flag.

## Performance

- **Tor startup**: ~10-20 seconds
- **Streamlit startup**: ~5-10 seconds
- **Total ready time**: ~15-30 seconds
- **Memory usage**: ~350-400MB (Tor adds ~50MB)

## Security

- Tor runs as `debian-tor` user (non-root)
- Tor data directory has 700 permissions
- Only port 8501 is exposed externally
- Tor SOCKS proxy (9050) is internal to container
- All YouTube requests are routed through Tor network
