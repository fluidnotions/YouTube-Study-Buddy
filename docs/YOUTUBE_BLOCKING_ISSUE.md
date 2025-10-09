# YouTube Blocking Issue - The Real Problem

## What's Actually Happening

When you process videos, you're seeing:
```
❌ Failed to generate study notes (x6)
❌ Error processing video: Could not get transcript: Both Tor and direct connection failed
```

## The Current Flow

1. Try via Tor (attempt 1) → **YouTube blocks immediately**
2. Rotate circuit → Try attempt 2 → **YouTube blocks**
3. Rotate circuit → Try attempt 3 → **YouTube blocks**
4. Rotate circuit → Try attempt 4 → **YouTube blocks**
5. Rotate circuit → Try attempt 5 → **YouTube blocks**
6. Give up on Tor, try direct → **YouTube blocks direct too**
7. Fail

## Why Circuit Rotation Isn't Helping

**YouTube is blocking ALL Tor exit nodes.**

The circuit rotation IS working (you can see `✓ Tor circuit rotated` in logs), but YouTube has blocklisted most/all Tor exit IPs. Even with fresh circuits, you're still coming from known Tor exit nodes.

Evidence:
- Tor IS working (different IPs confirmed: `169.1.137.134` → `109.70.100.2`)
- Circuit rotation IS working (`✓ Tor circuit rotated`)
- But YouTube still blocks: `YouTube is blocking requests from your IP`

## Why Videos Are Processed Sequentially

The Streamlit app processes videos one at a time in `video_processor.py`:

```python
for i, url in enumerate(urls, 1):
    result = self.process_single_video(url)  # Sequential!
```

This is intentional to:
- Avoid overwhelming Tor circuits
- Reduce chance of rate limiting
- Show progress per video

**Parallel processing wouldn't help** - YouTube would just block all requests simultaneously.

## The Real Solutions

### Option 1: Tor Bridges (Obfuscated Entry)

Use Tor bridges to hide that you're using Tor:

```dockerfile
# In Dockerfile, add bridge configuration
RUN echo "UseBridges 1" >> /etc/tor/torrc && \
    echo "ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy" >> /etc/tor/torrc && \
    echo "Bridge obfs4 [bridge-address]" >> /etc/tor/torrc
```

Get bridges from: https://bridges.torproject.org/

### Option 2: Residential Proxies (Paid)

Use residential proxy services that rotate IPs:
- Bright Data
- Smartproxy
- Oxylabs

These cost money but use real residential IPs that YouTube doesn't block.

### Option 3: yt-dlp Fallback

Some users report better success with yt-dlp for subtitle extraction:

```python
import yt_dlp

def fetch_with_ytdlp(video_id):
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'proxy': 'socks5://127.0.0.1:9050'  # Still use Tor
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f'https://youtube.com/watch?v={video_id}', download=False)
        # Extract subtitles from info
```

### Option 4: Longer Delays + Fewer Retries

Add significant delays between requests:

```python
# In tor_transcript_fetcher.py
time.sleep(random.uniform(30, 60))  # 30-60 second delay between videos
```

This might help avoid triggering rate limits, but won't help if IPs are already blocklisted.

### Option 5: Accept Limitations

Document that:
- Some videos won't work via Tor
- Users may need to use VPN instead
- Consider this a known limitation

## What You Can Test Right Now

### Test 1: Check if it's all Tor exits or specific ones

```bash
# Restart container multiple times to get different exit nodes
docker restart youtube-study-buddy
sleep 30
# Try processing a video
# Repeat 5 times and see if any work
```

### Test 2: Try without Tor

Temporarily disable Tor to see if direct connection works:

```python
# In streamlit_app.py, change:
provider_type="direct"  # instead of "tor"
```

If direct works, it confirms Tor exits are blocked.

### Test 3: Try different videos

Some videos may have transcripts disabled. Try known-good videos:
- https://www.youtube.com/watch?v=dQw4w9WgXcQ (Rick Astley)
- https://www.youtube.com/watch?v=9bZkp7q19f0 (Gangnam Style)

## Recommended Next Steps

1. **Try Tor bridges** - Easiest and free
2. **Add yt-dlp fallback** - Secondary option if transcript API fails
3. **Document limitations** - Be transparent about what works/doesn't
4. **Consider paid proxies** - If this is critical functionality

## Current Code IS Working

The circuit rotation code IS functional:
- ✅ Tor is running
- ✅ Circuit rotation works
- ✅ Getting different IPs per rotation
- ❌ YouTube blocks ALL those IPs

This is a **YouTube anti-bot** issue, not a code bug.
