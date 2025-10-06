# Tor Proxy Setup for YouTube Study Buddy

This document explains how to set up and use Tor proxy to bypass YouTube IP blocks when fetching transcripts.

## Why Use Tor?

YouTube may block your IP address if:
- You make too many API requests during testing
- You're running from a cloud provider IP (AWS, GCP, Azure)
- Your IP has been flagged for automated requests

Tor routes your requests through the Tor network, changing your apparent IP address and bypassing these blocks.

## Quick Start with Docker (Recommended)

### 1. Start Tor Proxy

```bash
docker-compose up -d tor-proxy
```

This starts a Tor SOCKS5 proxy on `localhost:9050`.

### 2. Verify Tor is Running

```bash
docker-compose ps
```

You should see `ytstudybuddy-tor-proxy` running.

### 3. Use Tor Method

```bash
# Process single URL with Tor
python main.py --method tor "https://youtube.com/watch?v=..."

# Process batch with Tor
python main.py --method tor --batch

# With subject organization
python main.py --method tor --subject "Machine Learning" --batch
```

## CLI Options

### Tor-Specific Flags

- `--method tor` - Use Tor proxy for transcript fetching
- `--tor-host <host>` - Tor SOCKS proxy host (default: 127.0.0.1)
- `--tor-port <port>` - Tor SOCKS proxy port (default: 9050)
- `--no-tor-fallback` - Disable fallback to direct connection if Tor fails

### Examples

```bash
# Basic Tor usage
python main.py --method tor https://youtube.com/watch?v=dQw4w9WgXcQ

# Tor with custom port
python main.py --method tor --tor-port 9050 --batch

# Tor without fallback (strict mode)
python main.py --method tor --no-tor-fallback --batch

# Combine with other options
python main.py --method tor --subject "AI" --batch --file my_urls.txt
```

## Alternative: Local Tor Installation

If you don't want to use Docker:

### Linux
```bash
sudo apt-get install tor
sudo systemctl start tor
# Tor will run on localhost:9050
```

### macOS
```bash
brew install tor
brew services start tor
# Tor will run on localhost:9050
```

### Windows
1. Download Tor Browser from https://www.torproject.org/
2. Run Tor Browser (it starts a local Tor proxy)
3. Or install Tor Expert Bundle for standalone Tor daemon

## Environment Variables

You can set default Tor configuration in `.env`:

```bash
TOR_HOST=127.0.0.1
TOR_PORT=9050
USE_TOR=false  # Set to true to use Tor by default
```

## Testing Tor Connection

The application automatically verifies Tor connection when using `--method tor`. You'll see:

```
Verifying Tor connection...
Normal IP: 1.2.3.4
Tor IP: 5.6.7.8
✓ Tor connection verified
```

If IPs are different, Tor is working correctly.

## Troubleshooting

### "Tor connection check failed"

**Problem**: Cannot connect to Tor proxy

**Solutions**:
1. Check if Tor is running: `docker-compose ps` or `systemctl status tor`
2. Verify port is correct: `--tor-port 9050` (default)
3. Check firewall settings
4. Restart Tor: `docker-compose restart tor-proxy`

### "Tor provider failed: Could not get transcript"

**Problem**: Tor connected but transcript fetch failed

**Solutions**:
1. Try again - Tor exit nodes can be slow
2. Enable fallback (remove `--no-tor-fallback`)
3. Check if video has captions available
4. Try a different video to test

### "Make sure Tor proxy is running"

**Problem**: Tor service not started

**Solution**:
```bash
docker-compose up -d tor-proxy
# Wait 30 seconds for Tor to establish circuits
docker-compose logs tor-proxy
```

### Slow Performance

**Problem**: Tor requests are slower than direct

**Explanation**: This is normal - Tor routes through multiple nodes
- Direct connection: ~200ms
- Tor connection: ~1-5 seconds

**Mitigation**: Use `--delay 5` to add extra time between requests

## Docker Compose Configuration

The `docker-compose.yml` includes:

```yaml
tor-proxy:
  image: dperson/torproxy:latest
  ports:
    - "8118:8118"  # HTTP proxy (Privoxy)
    - "9050:9050"  # SOCKS5 proxy (Tor)
  environment:
    - LOCATION=US  # Prefer US exit nodes
  volumes:
    - tor-data:/var/lib/tor
```

### Changing Exit Node Location

Edit `docker-compose.yml` and change `LOCATION`:

```yaml
environment:
  - LOCATION=DE  # Germany
  - LOCATION=GB  # United Kingdom
  - LOCATION=US  # United States
```

Then restart:
```bash
docker-compose down
docker-compose up -d tor-proxy
```

## When to Use Each Method

| Method | Use Case | Speed | Reliability |
|--------|----------|-------|-------------|
| `api` | Default - few requests | Fast | May hit rate limits |
| `scraper` | Rate limited but direct access | Medium | Good |
| `tor` | IP blocked or heavy testing | Slow | Best for avoiding blocks |

## Security Notes

- Tor provides anonymity by routing through multiple nodes
- Your real IP is hidden from YouTube
- Docker Tor proxy is isolated and easy to restart
- Data is encrypted within the Tor network
- Exit node sees unencrypted traffic (but not your real IP)

## Performance Tips

1. **Cache Results**: The app already caches transcript data
2. **Batch Processing**: Use `--batch` for multiple videos
3. **Increase Delays**: Use `--delay 5` or higher with Tor
4. **Fallback Enabled**: Keep fallback enabled for resilience
5. **Restart Tor**: Periodically restart to get new circuits

## Integration with CI/CD

For automated testing with Tor:

```yaml
# .github/workflows/test.yml
services:
  tor:
    image: dperson/torproxy:latest
    ports:
      - 9050:9050
    env:
      LOCATION: US

jobs:
  test:
    steps:
      - name: Test with Tor
        run: |
          python main.py --method tor --batch
        env:
          TOR_HOST: localhost
          TOR_PORT: 9050
```

## Additional Resources

- [Tor Project Official Site](https://www.torproject.org/)
- [YouTube Transcript API Docs](https://github.com/jdepoix/youtube-transcript-api)
- [dperson/torproxy Docker Image](https://hub.docker.com/r/dperson/torproxy)

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs tor-proxy`
2. Test Tor connection manually
3. Try direct method as fallback
4. Open an issue on GitHub with error details