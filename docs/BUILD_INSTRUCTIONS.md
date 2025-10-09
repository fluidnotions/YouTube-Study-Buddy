# Build Instructions - Single Container with Tor

## Overview

YouTube Study Buddy runs as a **single-container deployment** with integrated Tor proxy:

- Python 3.13 slim base (Debian-based)
- Tor from Debian package repository
- Circuit rotation via Tor control port (9051)
- Single container simplicity
- Health checks for both Tor and Streamlit

## Build Options

### Option 1: Python + Tor Single Container (Recommended)

```bash
# Build the image
docker build -f Dockerfile.python-tor -t youtube-study-buddy:python-tor .

# Run with docker-compose
docker compose -f docker-compose-python-tor.yml up -d

# Or run directly
docker run -d \
  --name youtube-study-buddy-python-tor \
  -p 8501:8501 \
  -v $(pwd)/notes:/app/notes \
  --env-file .env \
  youtube-study-buddy:python-tor
```

**Features:**
- Python 3.13 base (familiar, well-documented)
- Debian's Tor package (stable and maintained)
- Circuit rotation enabled
- Single container deployment
- Built-in health checks

### Option 2: Legacy Dockerfile (Without Tor)

```bash
# Build the image
docker build -t youtube-study-buddy:latest .

# Run with docker-compose
docker compose up -d

# Or run directly
docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  -v $(pwd)/notes:/app/notes \
  --env-file .env \
  youtube-study-buddy:latest
```

**Note:** This option requires external Tor proxy (not included in container).

### Option 3: Development Mode

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
