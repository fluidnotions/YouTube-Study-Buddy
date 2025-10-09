# Scraper Implementation Plan - yt-dlp + Playwright Fallback

## Current Status

**Good news:** Transcripts ARE being fetched successfully via Tor! ✅

```
✓ Successfully fetched transcript on attempt 1
✓ Successfully fetched via Tor
```

**The actual problem:** Claude API model name typo causing note generation to fail ❌
- Wrong: `claude-sonnet-4-5-2025092`
- Correct: `claude-sonnet-4-5-20250929`

**Fixed in:** `src/yt_study_buddy/study_notes_generator.py`

## Why Add Scraper Fallbacks Anyway?

Even though Tor is working now, it's unreliable:
1. Some videos have "Subtitles disabled"
2. YouTube may block Tor exits at any time
3. Rate limiting can still occur
4. Redundancy is good practice

## Implementation Plan

### Phase 1: Add yt-dlp Fallback (Priority: HIGH)

**Why yt-dlp first?**
- Fast (no browser needed)
- Lightweight
- Well-maintained
- Already handles subtitle formats
- FREE

**Implementation:**

```python
# New file: src/yt_study_buddy/ytdlp_fetcher.py

import yt_dlp
from typing import Optional, Dict, Any
import re

class YtDlpTranscriptFetcher:
    """Fetch YouTube transcripts using yt-dlp."""

    def fetch_transcript(
        self,
        video_id: str,
        languages: list = ['en']
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript using yt-dlp.

        Args:
            video_id: YouTube video ID
            languages: List of language codes

        Returns:
            Dictionary with transcript data or None
        """
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': languages,
                'quiet': True,
                'no_warnings': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f'https://youtube.com/watch?v={video_id}'
                info = ydl.extract_info(url, download=False)

                # Try manual subtitles first
                subtitles = None
                if 'subtitles' in info and languages[0] in info['subtitles']:
                    subtitles = info['subtitles'][languages[0]]
                # Fallback to auto-generated
                elif 'automatic_captions' in info and languages[0] in info['automatic_captions']:
                    subtitles = info['automatic_captions'][languages[0]]

                if not subtitles:
                    return None

                # Find JSON3 format (contains timing + text)
                subtitle_data = None
                for sub in subtitles:
                    if sub.get('ext') == 'json3':
                        subtitle_data = ydl.urlopen(sub['url']).read()
                        break

                if not subtitle_data:
                    return None

                # Parse JSON3 format
                import json
                data = json.loads(subtitle_data)

                segments = []
                full_text = []

                for event in data.get('events', []):
                    if 'segs' not in event:
                        continue

                    start_time = event.get('tStartMs', 0) / 1000
                    text = ''.join(seg.get('utf8', '') for seg in event['segs'])

                    if text.strip():
                        full_text.append(text.strip())
                        segments.append({
                            'start': start_time,
                            'text': text.strip()
                        })

                transcript_text = ' '.join(full_text)
                # Clean up
                transcript_text = re.sub(r'\s+', ' ', transcript_text)

                # Calculate duration
                duration_seconds = info.get('duration', 0)
                duration_minutes = int(duration_seconds / 60)
                duration_info = f"~{duration_minutes} minutes"

                return {
                    'transcript': transcript_text,
                    'duration': duration_info,
                    'length': len(transcript_text),
                    'segments': segments
                }

        except Exception as e:
            print(f"yt-dlp fetch failed: {e}")
            return None

    def get_video_title(self, video_id: str) -> str:
        """Get video title using yt-dlp."""
        try:
            ydl_opts = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f'https://youtube.com/watch?v={video_id}'
                info = ydl.extract_info(url, download=False)
                title = info.get('title', f'Video_{video_id}')

                # Clean title for filename
                title = re.sub(r'[<>:"/\\|?*]', '', title)
                return title

        except Exception as e:
            print(f"yt-dlp title fetch failed: {e}")
            return f'Video_{video_id}'
```

**Update transcript_provider.py:**

```python
# In transcript_provider.py

from yt_study_buddy.ytdlp_fetcher import YtDlpTranscriptFetcher

class TranscriptProvider:
    def __init__(self, ...):
        # ... existing code ...
        self.ytdlp_fetcher = YtDlpTranscriptFetcher()

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch transcript with fallback chain:
        1. Try Tor (fast)
        2. Try yt-dlp (reliable)
        3. Raise error
        """
        try:
            # Try Tor first
            result = self.tor_fetcher.fetch_with_fallback(video_id)
            if result:
                return result
        except Exception as e:
            print(f"Tor fetch failed: {e}")

        # Try yt-dlp
        print("Trying yt-dlp fallback...")
        result = self.ytdlp_fetcher.fetch_transcript(video_id)
        if result:
            print("✓ Successfully fetched via yt-dlp")
            return result

        raise Exception("All transcript fetch methods failed")
```

**Add to pyproject.toml:**

```toml
dependencies = [
    # ... existing ...
    "yt-dlp>=2025.9.26",
]
```

### Phase 2: Add Playwright Fallback (Priority: MEDIUM)

**When to use:**
- yt-dlp fails
- Video has transcript but API/yt-dlp can't access it
- Ultimate fallback (always works if transcript exists)

**Implementation:**

```python
# New file: src/yt_study_buddy/playwright_fetcher.py

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from typing import Optional, Dict, Any
import re
import time

class PlaywrightTranscriptFetcher:
    """Fetch YouTube transcripts using browser automation."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def fetch_transcript(
        self,
        video_id: str,
        timeout: int = 30000
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript by automating browser interaction.

        Args:
            video_id: YouTube video ID
            timeout: Timeout in milliseconds

        Returns:
            Dictionary with transcript data or None
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()

                # Load video
                url = f'https://www.youtube.com/watch?v={video_id}'
                page.goto(url, wait_until='networkidle', timeout=timeout)

                # Wait a bit for page to fully load
                time.sleep(2)

                # Click "More actions" menu
                try:
                    page.click('button[aria-label="More actions"]', timeout=5000)
                    time.sleep(1)
                except:
                    # Try alternative selector
                    page.click('yt-button-shape button[aria-label="More actions"]', timeout=5000)
                    time.sleep(1)

                # Click "Show transcript"
                try:
                    page.click('text="Show transcript"', timeout=5000)
                except:
                    print("Transcript button not found - may not be available")
                    browser.close()
                    return None

                # Wait for transcript to load
                time.sleep(2)
                page.wait_for_selector('ytd-transcript-segment-renderer', timeout=10000)

                # Extract all transcript segments
                segments = page.query_selector_all('ytd-transcript-segment-renderer')

                transcript_data = []
                full_text = []

                for segment in segments:
                    try:
                        # Get timestamp
                        timestamp_elem = segment.query_selector('.segment-timestamp')
                        timestamp_text = timestamp_elem.inner_text() if timestamp_elem else '0:00'

                        # Get text
                        text_elem = segment.query_selector('.segment-text')
                        text = text_elem.inner_text() if text_elem else ''

                        if text.strip():
                            # Convert timestamp to seconds
                            time_parts = timestamp_text.split(':')
                            if len(time_parts) == 2:
                                seconds = int(time_parts[0]) * 60 + int(time_parts[1])
                            else:
                                seconds = 0

                            transcript_data.append({
                                'start': seconds,
                                'text': text.strip()
                            })
                            full_text.append(text.strip())

                    except Exception as e:
                        print(f"Error parsing segment: {e}")
                        continue

                browser.close()

                if not transcript_data:
                    return None

                transcript_text = ' '.join(full_text)
                transcript_text = re.sub(r'\s+', ' ', transcript_text)

                # Estimate duration
                if transcript_data:
                    last_segment = transcript_data[-1]
                    duration_seconds = last_segment['start']
                    duration_minutes = int(duration_seconds / 60)
                    duration_info = f"~{duration_minutes} minutes"
                else:
                    duration_info = "unknown"

                return {
                    'transcript': transcript_text,
                    'duration': duration_info,
                    'length': len(transcript_text),
                    'segments': transcript_data
                }

        except PlaywrightTimeout:
            print("Playwright timeout - page took too long to load")
            return None
        except Exception as e:
            print(f"Playwright fetch failed: {e}")
            return None

    def get_video_title(self, video_id: str) -> str:
        """Get video title using Playwright."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()

                url = f'https://www.youtube.com/watch?v={video_id}'
                page.goto(url, wait_until='domcontentloaded', timeout=15000)

                # Get title from meta tag or h1
                title = page.title()
                if ' - YouTube' in title:
                    title = title.replace(' - YouTube', '')

                browser.close()

                # Clean for filename
                title = re.sub(r'[<>:"/\\|?*]', '', title)
                return title

        except Exception as e:
            print(f"Playwright title fetch failed: {e}")
            return f'Video_{video_id}'
```

**Add to pyproject.toml:**

```toml
[project.optional-dependencies]
browser = [
    "playwright>=1.50.0",
]
```

**Dockerfile update for Playwright:**

```dockerfile
# Install Playwright browsers
RUN pip install playwright && \
    playwright install --with-deps chromium
```

### Phase 3: Complete Fallback Chain

**Final transcript_provider.py:**

```python
def get_transcript(self, video_id: str) -> Dict[str, Any]:
    """
    Fetch transcript with comprehensive fallback chain:
    1. Try Tor (fastest, works most of the time)
    2. Try yt-dlp (reliable, lightweight)
    3. Try Playwright (slow but always works)
    """
    errors = []

    # Try 1: Tor
    try:
        print("  Trying Tor...")
        result = self.tor_fetcher.fetch_with_fallback(video_id)
        if result:
            print("  ✓ Fetched via Tor")
            return result
    except Exception as e:
        errors.append(f"Tor: {e}")
        print(f"  ✗ Tor failed: {e}")

    # Try 2: yt-dlp
    try:
        print("  Trying yt-dlp...")
        result = self.ytdlp_fetcher.fetch_transcript(video_id)
        if result:
            print("  ✓ Fetched via yt-dlp")
            return result
    except Exception as e:
        errors.append(f"yt-dlp: {e}")
        print(f"  ✗ yt-dlp failed: {e}")

    # Try 3: Playwright (if available)
    if hasattr(self, 'playwright_fetcher'):
        try:
            print("  Trying Playwright (browser automation)...")
            result = self.playwright_fetcher.fetch_transcript(video_id)
            if result:
                print("  ✓ Fetched via Playwright")
                return result
        except Exception as e:
            errors.append(f"Playwright: {e}")
            print(f"  ✗ Playwright failed: {e}")

    # All methods failed
    raise Exception(f"All transcript methods failed: {'; '.join(errors)}")
```

## Implementation Steps

### Step 1: Add yt-dlp (Easy, Fast)
1. Add `yt-dlp` to pyproject.toml dependencies
2. Create `ytdlp_fetcher.py`
3. Update `transcript_provider.py` to use yt-dlp as fallback
4. Test with videos
5. Rebuild Docker image

**Time estimate:** 30 minutes
**Difficulty:** Easy
**Value:** HIGH - catches most failures

### Step 2: Add Playwright (Medium Difficulty)
1. Add `playwright` to optional dependencies
2. Create `playwright_fetcher.py`
3. Update Dockerfile to install Chromium
4. Update `transcript_provider.py` for 3-level fallback
5. Test with difficult videos
6. Rebuild Docker image

**Time estimate:** 2 hours (including Docker setup)
**Difficulty:** Medium
**Value:** MEDIUM - ultimate fallback but heavy

### Step 3: Testing
Test with various video types:
- ✅ Normal videos with transcripts
- ✅ Auto-generated captions only
- ✅ Multiple languages
- ❌ Videos with disabled subtitles
- ✅ Age-restricted videos
- ✅ Long videos (2+ hours)

## Docker Considerations

### Current Dockerfile (App-only)
- Size: ~1.89GB
- No browser included

### With yt-dlp
- Size: ~1.90GB (+10MB)
- No additional dependencies

### With Playwright
- Size: ~2.5GB (+600MB for Chromium)
- Requires browser binaries
- More memory usage

**Recommendation:**
- **Default:** Include yt-dlp (minimal overhead)
- **Optional:** Playwright as separate build target or optional install

## Next Steps

1. **Fix Claude model name** (DONE ✅)
2. **Test current setup** - see if transcripts work now
3. **Add yt-dlp** - quick win, minimal overhead
4. **Consider Playwright** - only if yt-dlp still fails often

Want me to implement yt-dlp fallback now?
