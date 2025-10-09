# Build Instructions - Separate Container Architecture

## Overview

YouTube Study Buddy uses a **two-container deployment** for reliability:

1. **tor-proxy**: Dedicated Tor SOCKS proxy (`dperson/torproxy:latest`)
2. **app**: Python 3.13 app with Streamlit UI

**Why separate containers?** See [Why Separate Containers Work Better](WHY_SEPARATE_CONTAINERS.md)

## Build and Run (Recommended)

### Using Docker Compose

```bash
# Create .env file
echo "CLAUDE_API_KEY=your_key_here" > .env

# Build and start both containers
docker compose up -d --build

# View logs
docker logs -f youtube-study-buddy  # App
docker logs -f tor-proxy            # Tor

# Stop
docker compose down
```

**Features:**
- Separate Tor container for reliability
- Easy debugging with separate logs
- Independent lifecycle management
- Proven `dperson/torproxy` image
- Circuit rotation enabled

### Manual Build and Run

```bash
# Build app image
docker build -t youtube-study-buddy:latest .

# Run with docker compose
docker compose up -d
```

### Development Mode (No Docker)

```bash
# Run locally without Docker
uv sync
uv run streamlit run streamlit_app.py
```

See [Alternative Setup](technical/alternative-setup.md) for details.

## Environment Variables

Create a `.env` file with:

```bash
CLAUDE_API_KEY=your_claude_api_key_here
```

## Tor Configuration

The `Dockerfile.torproxy` build supports dperson/torproxy environment variables:

- `LOCATION`: Prefer exit nodes from specific country (e.g., `US`, `UK`, `DE`)
- `PASSWORD`: Set Tor control port password (optional)
- `BW`: Set bandwidth limit (optional)
- `TORUSER`: Tor username (optional)

Example with location preference:

```bash
docker run -d \
  --name youtube-study-buddy-tor \
  -p 8501:8501 \
  -v $(pwd)/notes:/app/notes \
  --env-file .env \
  -e LOCATION=US \
  -e PASSWORD=mysecretpassword \
  youtube-study-buddy:torproxy
```

## Testing

### Test Tor Connection

```bash
# Enter the container
docker exec -it youtube-study-buddy-tor sh

# Check Tor IP
curl -x socks5h://127.0.0.1:9050 https://api.ipify.org

# Test circuit rotation (if control port is configured)
echo -e "AUTHENTICATE\nSIGNAL NEWNYM\nQUIT" | nc 127.0.0.1 9051
```

### Test Application

Visit: http://localhost:8501

## Troubleshooting

### YouTube Still Blocking Requests

Even with Tor circuit rotation, YouTube may block requests. Try:

1. **Configure exit node location:**
   ```bash
   -e LOCATION=US
   ```

2. **Check if you're actually using Tor:**
   ```bash
   docker exec youtube-study-buddy-tor curl -x socks5h://127.0.0.1:9050 https://api.ipify.org
   ```

3. **Restart container to get new Tor circuits:**
   ```bash
   docker restart youtube-study-buddy-tor
   ```

4. **Check logs:**
   ```bash
   docker logs youtube-study-buddy-tor
   ```

### Build Fails

If the build fails on Alpine packages:

```bash
# Clear Docker cache and rebuild
docker builder prune
docker build --no-cache -f Dockerfile.torproxy -t youtube-study-buddy:torproxy .
```

## Comparison

| Feature | Dockerfile.python-tor | Dockerfile (current) | Multi-container |
|---------|---------------------|---------------------|-----------------|
| Base Image | python:3.13-slim | python:3.13-slim | Two separate images |
| Tor Source | Debian package | Debian package | dperson/torproxy |
| Container Count | 1 | 1 | 2 |
| Tor Config | Proven (based on dperson) | Custom | Proven (dperson) |
| Image Size | ~450MB | ~400MB | ~700MB total |
| Circuit Rotation | ✅ | ✅ | ✅ |
| Build Complexity | Low | Low | High |
| **Recommended** | **✅ Yes** | For local dev | Legacy |

## Recommendation

**Use `Dockerfile.python-tor` for production** as it:
- Starts with Python (no need to install it)
- Uses Debian's well-maintained Tor package
- Includes the proven Tor configuration that worked before
- Consolidates everything into a single container
- Easier to build and maintain than Alpine-based approaches
