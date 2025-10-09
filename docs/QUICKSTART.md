# Quick Start - Docker with Separate Tor Container

## Docker Deployment (Two Containers)

This guide shows how to run YouTube Study Buddy with a separate Tor proxy container for reliable YouTube rate limiting bypass.

**Why separate containers?** See [Why Separate Containers Work Better](WHY_SEPARATE_CONTAINERS.md)

## Quick Start (Easiest)

```bash
# Create .env file with your API key
echo "CLAUDE_API_KEY=your_key_here" > .env

# Start both containers
docker compose up -d

# Access at http://localhost:8501
```

## What You'll See

When the containers start:

```bash
# Check logs
docker logs -f youtube-study-buddy

# You'll see the Streamlit app starting:
Verifying Tor connection...
Normal IP: 123.456.789.012
Tor IP: 98.765.432.109
✓ Tor connection verified

You can now view your Streamlit app in your browser.
URL: http://0.0.0.0:8501
```

## Useful Commands

```bash
# View app logs
docker logs -f youtube-study-buddy

# View Tor logs
docker logs -f tor-proxy

# Stop all containers
docker compose down

# Restart containers
docker compose restart

# Rebuild and restart
docker compose up -d --build

# Enter app container (for debugging)
docker exec -it youtube-study-buddy bash

# Check Tor IP from app container
docker exec youtube-study-buddy curl -x socks5h://tor-proxy:9050 https://api.ipify.org

# Check Tor IP from Tor container
docker exec tor-proxy curl -x socks5h://127.0.0.1:9050 https://api.ipify.org
```

## Requirements

- Docker and Docker Compose installed
- `.env` file with `CLAUDE_API_KEY=your_key`
- Port 8501 available (or change port in docker-compose.yml)

## Architecture

This setup uses **two containers**:

1. **tor-proxy**: Dedicated Tor SOCKS proxy (`dperson/torproxy:latest`)
2. **youtube-study-buddy**: Python app with Streamlit UI

The app connects to Tor via Docker's internal network at `tor-proxy:9050`. See [Why Separate Containers Work Better](WHY_SEPARATE_CONTAINERS.md) for details.

## Troubleshooting

### Container won't start

```bash
# Check app logs
docker logs youtube-study-buddy

# Check Tor logs
docker logs tor-proxy

# Check if port is in use
sudo lsof -i :8501
```

### Tor not working

```bash
# Verify Tor is running
docker ps | grep tor-proxy

# Check Tor connection from app container
docker exec youtube-study-buddy curl -x socks5h://tor-proxy:9050 https://check.torproject.org

# Check if you're getting different IP
docker exec youtube-study-buddy bash -c 'echo "Real: $(curl -s https://api.ipify.org)" && echo "Tor: $(curl -s -x socks5h://tor-proxy:9050 https://api.ipify.org)"'
```

### YouTube still blocking

Even with working Tor, YouTube may block some exit nodes:
- Try restarting containers to get new Tor circuits: `docker compose restart`
- Circuit rotation happens automatically on retries
- Different exit locations can be configured in docker-compose.yml

## Next Steps

1. Access http://localhost:8501
2. Paste a YouTube URL
3. Click "Process Videos"
4. Check the `notes/` directory for generated markdown files
5. Open `notes/` in [Obsidian](https://obsidian.md) to see your knowledge graph

## Files

- `Dockerfile` - App container Dockerfile
- `docker-compose.yml` - Multi-container orchestration
- `.env.example` - Example environment variables
- `docs/WHY_SEPARATE_CONTAINERS.md` - Architecture explanation
