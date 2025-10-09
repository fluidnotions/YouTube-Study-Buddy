# Agent Task: Tor Implementation Debugging & Optimization

## Branch
`feature/tor-debugging`

## Objective
Debug, optimize, and improve the current Tor-based transcript fetching to maximize success rate and minimize failures.

## Context
Current status:
- ✅ Separate Tor container working (docker-compose-separate-tor.yml)
- ✅ Tor proxy connects successfully
- ✅ Circuit rotation implemented
- ⚠️ Some videos still fail (YouTube blocking Tor exits)
- ⚠️ Control port connection issues in some setups
- ⚠️ Inconsistent success rates

**Goal:** Make Tor as reliable as possible before relying on fallbacks.

## Known Issues

### 1. Control Port Connection Failures
**Error:**
```
Tor control port not ready (attempt 1/3): [Errno 111] Connection refused
Warning: Could not connect to Tor control port after 3 attempts
```

**Root cause:** App container can't reach tor-proxy:9051

**Investigation needed:**
- Check if tor-proxy exposes control port internally
- Verify dperson/torproxy allows external control connections
- Check if control port authentication is properly configured

### 2. YouTube Still Blocking Some Requests
**Error:**
```
YouTube is blocking requests from your IP
```

**Even with circuit rotation!**

**Investigation needed:**
- Are we actually getting different exit IPs?
- Add logging to show current Tor exit IP
- Test if specific exit countries work better (US vs EU)
- Check if request patterns trigger blocking

### 3. Inconsistent Success Rates
**Observation:** Same video sometimes works, sometimes fails

**Investigation needed:**
- Is it related to specific exit nodes?
- Time-based rate limiting?
- Request fingerprinting issues?

## Implementation Tasks

### Task 1: Fix Control Port Access
**File:** `docker-compose-separate-tor.yml`

Investigate dperson/torproxy control port configuration:
```yaml
tor-proxy:
  image: dperson/torproxy:latest
  environment:
    - LOCATION=US
    - PASSWORD=your_password_here  # May need this for control port
```

Check if we need to:
- Set control port password
- Update app to authenticate with password
- Configure torproxy to allow control connections

**Test:**
```bash
# From app container
docker exec youtube-study-buddy nc -zv tor-proxy 9051
# Should connect successfully
```

### Task 2: Add IP Rotation Verification
**File:** `src/yt_study_buddy/tor_transcript_fetcher.py`

Add logging to verify IP changes:
```python
def fetch_transcript(self, ...):
    # Before each attempt, log current exit IP
    current_ip = self._get_current_exit_ip()
    print(f"  Current Tor exit IP: {current_ip}")

    # ... existing fetch logic ...

def _get_current_exit_ip(self) -> str:
    """Get current Tor exit IP."""
    try:
        response = self.session.get(
            'https://api.ipify.org',
            proxies=self.proxies,
            timeout=5
        )
        return response.text
    except:
        return "unknown"
```

This confirms if rotation actually changes IPs.

### Task 3: Test Different Exit Locations
**File:** `docker-compose-separate-tor.yml`

Test various exit node locations:
```yaml
environment:
  - LOCATION=US  # Try US
  # - LOCATION=GB  # Try UK
  # - LOCATION=DE  # Try Germany
  # - LOCATION=NL  # Try Netherlands
```

Document which locations have better success rates.

### Task 4: Add Request Fingerprinting
**File:** `src/yt_study_buddy/tor_transcript_fetcher.py`

Make requests look more human:
```python
def fetch_transcript(self, ...):
    # Rotate user agents
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...',
        # Add more
    ]

    # Add headers
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://www.youtube.com',
        'Referer': f'https://www.youtube.com/watch?v={video_id}'
    }

    # Pass headers to YouTubeTranscriptApi
```

### Task 5: Implement Smart Retry Logic
**File:** `src/yt_study_buddy/tor_transcript_fetcher.py`

Improve retry strategy:
```python
def fetch_transcript(self, ...):
    last_exit_ip = None

    for attempt in range(max_retries):
        # Rotate circuit
        if attempt > 0:
            self.rotate_tor_circuit()

            # Verify we got new IP
            new_ip = self._get_current_exit_ip()
            if new_ip == last_exit_ip:
                print(f"  ⚠️ Still same exit IP: {new_ip}")
                # Force new circuit
                time.sleep(5)
                self.rotate_tor_circuit()
            else:
                print(f"  ✓ New exit IP: {last_exit_ip} → {new_ip}")

            last_exit_ip = new_ip

        # Try fetch...
```

### Task 6: Add Tor Bridge Support
**File:** `docker-compose-separate-tor.yml` or custom torrc

Tor bridges hide that you're using Tor:
```
# In tor configuration
UseBridges 1
ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy
Bridge obfs4 [bridge-address-here]
```

Get bridges from: https://bridges.torproject.org/

**Research:** Does dperson/torproxy support bridges?

### Task 7: Monitor and Log Success Rates
**File:** `src/yt_study_buddy/transcript_provider.py`

Add metrics:
```python
class TranscriptProvider:
    def __init__(self, ...):
        self.stats = {
            'tor_success': 0,
            'tor_failure': 0,
            'ytdlp_success': 0,
            # ...
        }

    def get_transcript(self, video_id: str):
        try:
            result = self.tor_fetcher.fetch_with_fallback(video_id)
            self.stats['tor_success'] += 1
            return result
        except:
            self.stats['tor_failure'] += 1
            # try fallback...

    def print_stats(self):
        total = sum(self.stats.values())
        for method, count in self.stats.items():
            pct = (count / total * 100) if total > 0 else 0
            print(f"{method}: {count} ({pct:.1f}%)")
```

Call `print_stats()` after processing batch of videos.

### Task 8: Test with Known-Good Videos
**File:** `scripts/test_tor_reliability.py` (new)

Create test script:
```python
#!/usr/bin/env python3
"""Test Tor reliability with known videos."""

from src.yt_study_buddy.video_processor import VideoProcessor

# Videos that should have transcripts
test_videos = [
    "dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up
    "9bZkp7q19f0",  # Gangnam Style
    "jNQXAC9IVRw",  # Me at the zoo (first YouTube video)
    # Add more...
]

processor = VideoProcessor(provider_type="tor")

results = {
    'success': [],
    'failed': []
}

for video_id in test_videos:
    try:
        transcript = processor.get_transcript(video_id)
        results['success'].append(video_id)
        print(f"✓ {video_id}")
    except Exception as e:
        results['failed'].append((video_id, str(e)))
        print(f"✗ {video_id}: {e}")

# Print summary
print(f"\nSuccess: {len(results['success'])}/{len(test_videos)}")
print(f"Success rate: {len(results['success'])/len(test_videos)*100:.1f}%")
```

Run multiple times to gauge reliability.

## Investigation Questions

1. **Control Port Issue:**
   - Can app container reach tor-proxy:9051?
   - Does dperson/torproxy expose control port?
   - Do we need to configure password auth?

2. **Circuit Rotation:**
   - Are we actually getting different IPs?
   - Log IPs before/after rotation
   - Test with `curl -x socks5://tor-proxy:9050 https://api.ipify.org`

3. **Success Patterns:**
   - Which exit countries work best?
   - Time of day correlation?
   - Video characteristics (age, views, etc)?

4. **YouTube Blocking:**
   - Is it IP-based or fingerprint-based?
   - Can we make requests look more human?
   - Do delays between requests help?

## Testing Plan

### Phase 1: Control Port (30 min)
1. Test control port connectivity from app container
2. Fix connection issues
3. Verify circuit rotation works
4. Log IP changes to confirm rotation

### Phase 2: Exit Node Testing (1 hour)
1. Test different LOCATION settings (US, GB, DE, NL, etc)
2. Document success rates per location
3. Choose best default

### Phase 3: Request Fingerprinting (1 hour)
1. Add realistic headers
2. Rotate user agents
3. Add random delays
4. Test if success rate improves

### Phase 4: Metrics (30 min)
1. Add success/failure tracking
2. Run test suite multiple times
3. Document baseline success rate
4. Compare before/after optimizations

## Success Criteria

- ✅ Control port issues resolved
- ✅ Circuit rotation verified working (IPs change)
- ✅ Success rate > 70% for known-good videos
- ✅ Best exit location(s) documented
- ✅ Request fingerprinting improved
- ✅ Metrics show improvement over baseline
- ✅ Documentation updated with findings

## Estimated Time
3-4 hours

## Difficulty
Medium - debugging, testing, optimization

## Value
HIGH - improves primary fetch method, reduces reliance on fallbacks

## Reference Files

- `docs/TOR_EXIT_NODES_EXPLAINED.md` - Why blocking occurs
- `docs/WHY_SEPARATE_TOR_WORKS_BETTER.md` - Current architecture
- `docs/YOUTUBE_BLOCKING_ISSUE.md` - Known issues
- `src/yt_study_buddy/tor_transcript_fetcher.py` - Current implementation

## When Complete

1. Document findings in `docs/TOR_OPTIMIZATION_RESULTS.md`
2. Update `docker-compose-separate-tor.yml` with best settings
3. Commit: "Optimize Tor implementation and fix control port"
4. Create PR with before/after metrics
5. Tag @justin for review

## Future Considerations

- Tor bridge support (advanced)
- Exit node rotation strategies
- Adaptive retry logic based on error types
- Proxy pool (multiple Tor instances)
