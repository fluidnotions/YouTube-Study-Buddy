# Quick Start - Docker Single Container

## Docker Single Container Deployment

This guide shows how to run YouTube Study Buddy in a single Docker container with integrated Tor proxy for handling YouTube rate limiting.

## Three Ways to Run

### Option 1: Simple Script (Easiest)

```bash
./run-docker.sh
```

This script will:
- Build the image if needed
- Stop old container if exists
- Start new container
- Show you the logs
- Give you the URL to access

### Option 2: Docker Command (No Compose Needed!)

```bash
# Build the image
docker build -f Dockerfile.python-tor -t youtube-study-buddy:python-tor .

# Run it
docker run -d \
  --name youtube-study-buddy \
  -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/notes:/app/notes \
  youtube-study-buddy:python-tor

# Access at http://localhost:8501
```

### Option 3: Docker Compose (If You Prefer)

```bash
docker compose -f docker-compose-python-tor.yml up -d
```

## What You'll See

When the container starts, you'll see:

```
==========================================
YouTube Study Buddy with Tor
==========================================
Starting Tor...
Tor started with PID: 7
Waiting for Tor to be ready...
Bootstrapped 100% (done): Done
✓ Tor is ready!

Testing Tor connection...
Real IP:     123.456.789.012
Tor exit IP: 98.765.432.109
✓ Tor is working correctly (different IPs)

Testing circuit rotation...
✓ Tor control port accessible for circuit rotation

==========================================
Starting YouTube Study Buddy...
==========================================

You can now view your Streamlit app in your browser.
URL: http://0.0.0.0:8501
```

## Useful Commands

```bash
# View logs in real-time
docker logs -f youtube-study-buddy

# Stop the container
docker stop youtube-study-buddy

# Start it again
docker start youtube-study-buddy

# Restart
docker restart youtube-study-buddy

# Remove container
docker rm -f youtube-study-buddy

# Enter the container (for debugging)
docker exec -it youtube-study-buddy bash

# Check Tor IP from inside container
docker exec youtube-study-buddy curl -x socks5h://127.0.0.1:9050 https://api.ipify.org

# Test circuit rotation
docker exec youtube-study-buddy bash -c 'echo -e "AUTHENTICATE\nSIGNAL NEWNYM\nQUIT" | nc 127.0.0.1 9051'
```

## Requirements

- Docker installed
- `.env` file with `CLAUDE_API_KEY=your_key`
- Port 8501 available (or change `-p 8501:8501` to `-p YOUR_PORT:8501`)

## No Docker Compose Required!

This is a **single container** solution. You can use docker-compose if you want, but it's not necessary. The simple `docker run` command works perfectly.

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs youtube-study-buddy

# Check if port is in use
sudo lsof -i :8501

# Use different port
docker run -d --name youtube-study-buddy -p 8502:8501 --env-file .env youtube-study-buddy:python-tor
```

### Tor not working

```bash
# Check Tor connection from inside container
docker exec youtube-study-buddy curl -x socks5h://127.0.0.1:9050 https://check.torproject.org

# Check if you're getting different IP
docker exec youtube-study-buddy bash -c 'echo "Real: $(curl -s https://api.ipify.org)" && echo "Tor: $(curl -s -x socks5h://127.0.0.1:9050 https://api.ipify.org)"'
```

### YouTube still blocking

Even with working Tor, YouTube may block some exit nodes:
- Try restarting the container to get new Tor circuits
- Add delays between requests in the app
- Consider using Tor bridges (edit Dockerfile to add bridge config)

## Next Steps

1. Access http://localhost:8501
2. Paste a YouTube URL
3. Click "Process Videos"
4. Check the `notes/` directory for generated markdown files

## Files

- `Dockerfile.python-tor` - The main Dockerfile
- `docker-compose-python-tor.yml` - Optional compose file
- `run-docker.sh` - Convenience script
- `entrypoint-python-tor.sh` - Container startup script
