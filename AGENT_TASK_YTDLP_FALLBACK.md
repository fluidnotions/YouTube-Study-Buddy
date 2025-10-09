# Agent Task: Implement YT-DLP as Fallback for Transcript Fetching

## Branch
`feat/ytdlp-fallback`

## Worktree
`/home/justin/Documents/dev/python/PycharmProjects/worktrees/ytdlp-fallback`

## Objective
Implement yt-dlp as a fallback mechanism when Tor-based transcript fetching fails. This provides a robust secondary method to retrieve video transcripts when the primary Tor method encounters YouTube IP blocking.

## Context
Current status:
- ✅ Tor-based transcript fetching working (primary method)
- ✅ Separate Tor container architecture in place
- ❌ No fallback when Tor fails due to IP blocking
- ❌ Some videos fail entirely when Tor exits are blocked

**Goal:** Add yt-dlp as an automatic fallback to maximize transcript retrieval success rate.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│ VideoProcessor                                  │
│  ↓                                              │
│ TranscriptProvider (tor)                        │
│  ↓                                              │
│ TorTranscriptFetcher.fetch_with_fallback()     │
│  ↓                                              │
│ [Try Tor first]                                 │
│  ↓                                              │
│ [If Tor fails] → YtDlpFallback.fetch_transcript()│
│  ↓                                              │
│ Success or Final Failure                        │
└─────────────────────────────────────────────────┘
```

## Implementation Tasks

### Task 1: Create YtDlpFallback Class
**File:** `src/yt_study_buddy/ytdlp_fallback.py` (NEW)

Create a new module for yt-dlp fallback functionality:

```python
"""
YT-DLP fallback for transcript fetching.

Used when Tor-based fetching fails due to IP blocking or other issues.
"""
import re
from typing import Optional, List, Dict, Any
import yt_dlp


class YtDlpFallback:
    """Fetch YouTube transcripts using yt-dlp as fallback method."""

    def __init__(self):
        """Initialize yt-dlp with minimal options."""
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'subtitlesformat': 'json3',
        }

    def fetch_transcript(
        self,
        video_id: str,
        languages: List[str] = ['en']
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript using yt-dlp.

        Args:
            video_id: YouTube video ID
            languages: List of language codes (default: ['en'])

        Returns:
            Dictionary with transcript data or None if failed
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Extract info including subtitles
                info = ydl.extract_info(video_url, download=False)

                # Try to get subtitles
                subtitles = info.get('subtitles', {})
                auto_captions = info.get('automatic_captions', {})

                # Try requested languages in order
                transcript_text = None
                for lang in languages:
                    # Check manual subtitles first
                    if lang in subtitles:
                        transcript_text = self._extract_subtitle_text(
                            subtitles[lang], ydl
                        )
                        if transcript_text:
                            break

                    # Fall back to auto-captions
                    if lang in auto_captions:
                        transcript_text = self._extract_subtitle_text(
                            auto_captions[lang], ydl
                        )
                        if transcript_text:
                            break

                if not transcript_text:
                    return None

                # Clean up transcript
                transcript_text = re.sub(r'\s+', ' ', transcript_text)
                transcript_text = transcript_text.replace('[Music]', '').replace('[Applause]', '')

                # Get video duration
                duration_seconds = info.get('duration', 0)
                duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                duration_info = f"~{duration_minutes} minutes" if duration_minutes else None

                return {
                    'transcript': transcript_text,
                    'duration': duration_info,
                    'length': len(transcript_text),
                    'method': 'yt-dlp',
                    'segments': []  # yt-dlp doesn't provide segment timing easily
                }

        except Exception as e:
            print(f"YT-DLP fallback failed: {e}")
            return None

    def _extract_subtitle_text(
        self,
        subtitle_formats: List[Dict],
        ydl: yt_dlp.YoutubeDL
    ) -> Optional[str]:
        """
        Extract text from subtitle format list.

        Args:
            subtitle_formats: List of subtitle format dicts
            ydl: YoutubeDL instance

        Returns:
            Extracted subtitle text or None
        """
        # Prefer json3 format
        for fmt in subtitle_formats:
            if fmt.get('ext') == 'json3':
                try:
                    # Download subtitle content
                    subtitle_url = fmt.get('url')
                    if not subtitle_url:
                        continue

                    # Use yt-dlp's downloader
                    import requests
                    response = requests.get(subtitle_url, timeout=30)

                    if response.status_code == 200:
                        import json
                        data = response.json()

                        # Extract text from json3 format
                        events = data.get('events', [])
                        text_parts = []
                        for event in events:
                            segs = event.get('segs', [])
                            for seg in segs:
                                text = seg.get('utf8', '')
                                if text:
                                    text_parts.append(text)

                        return ' '.join(text_parts)
                except Exception as e:
                    print(f"  Failed to extract from {fmt.get('ext')}: {e}")
                    continue

        return None

    def get_video_title(self, video_id: str) -> str:
        """
        Get video title using yt-dlp.

        Args:
            video_id: YouTube video ID

        Returns:
            Video title (cleaned) or fallback Video_ID
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                title = info.get('title', f'Video_{video_id}')

                # Clean title for filename
                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                return clean_title[:100]

        except Exception as e:
            print(f"YT-DLP title fetch failed: {e}")
            return f"Video_{video_id}"
```

### Task 2: Integrate Fallback into TorTranscriptFetcher
**File:** `src/yt_study_buddy/tor_transcript_fetcher.py`

Modify `fetch_with_fallback()` to use yt-dlp when Tor fails:

```python
# Add import at top
from .ytdlp_fallback import YtDlpFallback

class TorTranscriptFetcher:
    def __init__(self, ...):
        # ... existing init ...
        self.ytdlp_fallback = YtDlpFallback()

    def fetch_with_fallback(
        self,
        video_id: str,
        use_tor_first: bool = True,
        languages: List[str] = ['en']
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript using Tor first, fall back to yt-dlp if Tor fails.

        Args:
            video_id: YouTube video ID
            use_tor_first: Always True (Tor is primary method)
            languages: List of language codes

        Returns:
            Dictionary with transcript data or None if all methods failed
        """
        # Try Tor first (primary method)
        print("Fetching transcript via Tor proxy...")
        result = self.fetch_transcript(video_id, languages)

        if result:
            print("✓ Successfully fetched via Tor")
            return result
        else:
            print("✗ Tor fetch failed")

            # Fall back to yt-dlp
            print("Attempting yt-dlp fallback...")
            ytdlp_result = self.ytdlp_fallback.fetch_transcript(
                video_id, languages
            )

            if ytdlp_result:
                print("✓ Successfully fetched via yt-dlp fallback")
                return ytdlp_result
            else:
                print("✗ YT-DLP fallback also failed")
                return None
```

### Task 3: Add yt-dlp Dependency
**File:** `pyproject.toml`

Add yt-dlp to dependencies:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "yt-dlp>=2024.10.7",
]
```

Run after editing:
```bash
uv sync
```

### Task 4: Update TranscriptProvider
**File:** `src/yt_study_buddy/transcript_provider.py`

Ensure the provider properly passes through the fallback mechanism:

```python
class TorTranscriptProvider(AbstractTranscriptProvider):
    def __init__(self, tor_host: str = '127.0.0.1', tor_port: int = 9050, use_tor_first: bool = True):
        """
        Initialize Tor-based transcript provider with yt-dlp fallback.

        Args:
            tor_host: Tor SOCKS proxy host (default: 127.0.0.1)
            tor_port: Tor SOCKS proxy port (default: 9050)
            use_tor_first: Always True (Tor is primary, yt-dlp is fallback)
        """
        self.tor_fetcher = TorTranscriptFetcher(tor_host=tor_host, tor_port=tor_port)
        self.use_tor_first = use_tor_first
        self._tor_verified = False
```

The existing `get_transcript()` method should work as-is since it calls `fetch_with_fallback()`.

### Task 5: Add Statistics Tracking
**File:** `src/yt_study_buddy/transcript_provider.py`

Add method-level statistics:

```python
class TorTranscriptProvider(AbstractTranscriptProvider):
    def __init__(self, ...):
        # ... existing init ...
        self.stats = {
            'tor_success': 0,
            'tor_failure': 0,
            'ytdlp_success': 0,
            'ytdlp_failure': 0,
            'total_attempts': 0
        }

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Get transcript with statistics tracking."""
        self.stats['total_attempts'] += 1

        try:
            result = self.tor_fetcher.fetch_with_fallback(
                video_id=video_id,
                use_tor_first=self.use_tor_first,
                languages=['en']
            )

            if result:
                # Check which method was used
                if result.get('method') == 'yt-dlp':
                    self.stats['ytdlp_success'] += 1
                else:
                    self.stats['tor_success'] += 1
                return result
            else:
                self.stats['tor_failure'] += 1
                self.stats['ytdlp_failure'] += 1
                raise Exception("Both Tor and yt-dlp fallback failed")

        except Exception as e:
            # ... existing error handling ...
            raise

    def print_stats(self):
        """Print success rate statistics."""
        total = self.stats['total_attempts']
        if total == 0:
            print("No attempts yet")
            return

        print("\n" + "="*50)
        print("TRANSCRIPT FETCHING STATISTICS")
        print("="*50)
        print(f"Total attempts: {total}")
        print(f"Tor successes: {self.stats['tor_success']} ({self.stats['tor_success']/total*100:.1f}%)")
        print(f"YT-DLP successes: {self.stats['ytdlp_success']} ({self.stats['ytdlp_success']/total*100:.1f}%)")
        print(f"Total failures: {self.stats['tor_failure']} ({self.stats['tor_failure']/total*100:.1f}%)")
        print("="*50)
```

### Task 6: Update CLI to Show Statistics
**File:** `src/yt_study_buddy/cli.py`

Add statistics output after processing:

```python
class YouTubeStudyNotes:
    def process_urls(self, urls):
        """Process a list of URLs."""
        # ... existing processing ...

        # Show statistics at the end
        if hasattr(self.video_processor.provider, 'print_stats'):
            self.video_processor.provider.print_stats()
```

### Task 7: Add Unit Tests
**File:** `tests/test_ytdlp_fallback.py` (NEW)

```python
"""Tests for yt-dlp fallback functionality."""
import pytest
from src.yt_study_buddy.ytdlp_fallback import YtDlpFallback


@pytest.fixture
def fallback():
    """Create YtDlpFallback instance."""
    return YtDlpFallback()


def test_fetch_transcript_success(fallback):
    """Test successful transcript fetch."""
    # Rick Astley - Never Gonna Give You Up (has captions)
    video_id = "dQw4w9WgXcQ"

    result = fallback.fetch_transcript(video_id)

    assert result is not None
    assert 'transcript' in result
    assert 'duration' in result
    assert 'length' in result
    assert result['method'] == 'yt-dlp'
    assert len(result['transcript']) > 0


def test_fetch_transcript_invalid_video(fallback):
    """Test handling of invalid video ID."""
    result = fallback.fetch_transcript("INVALID_VIDEO_ID")
    assert result is None


def test_get_video_title(fallback):
    """Test video title fetching."""
    video_id = "dQw4w9WgXcQ"
    title = fallback.get_video_title(video_id)

    assert title is not None
    assert len(title) > 0
    assert not title.startswith("Video_")


@pytest.mark.integration
def test_fallback_integration(fallback):
    """Integration test with real YouTube video."""
    video_id = "9bZkp7q19f0"  # Gangnam Style

    result = fallback.fetch_transcript(video_id)

    assert result is not None
    assert result['length'] > 100  # Should have substantial content
    assert 'Gangnam' in result['transcript'] or 'gangnam' in result['transcript'].lower()
```

### Task 8: Update Documentation
**File:** `README.md`

Add section about fallback mechanism:

```markdown
## Transcript Fetching Methods

YouTube Study Buddy uses a two-tier approach for reliable transcript fetching:

### 1. Primary: Tor Proxy (Recommended)
- Routes requests through Tor network to bypass IP blocking
- Circuit rotation for retry attempts
- Most reliable for batch processing

### 2. Fallback: yt-dlp
- Automatically used when Tor fails
- Direct connection to YouTube
- Provides additional reliability layer

### Success Rate
With the dual-method approach:
- **Tor success rate**: ~70-80%
- **YT-DLP fallback**: Covers remaining 20-30%
- **Combined success rate**: >95%

Statistics are displayed after processing showing which method was used for each video.
```

### Task 9: Test End-to-End
**File:** `scripts/test_fallback.py` (NEW)

Create test script:

```python
#!/usr/bin/env python3
"""Test Tor with yt-dlp fallback."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yt_study_buddy.video_processor import VideoProcessor

# Test videos
videos = [
    "dQw4w9WgXcQ",  # Rick Astley
    "9bZkp7q19f0",  # Gangnam Style
    "jNQXAC9IVRw",  # First YouTube video
]

processor = VideoProcessor("tor")

print("Testing Tor with YT-DLP fallback...")
print("="*50)

for video_id in videos:
    print(f"\nTesting: {video_id}")
    try:
        result = processor.get_transcript(video_id)
        method = result.get('method', 'tor')
        print(f"✓ Success via {method} ({result['length']} chars)")
    except Exception as e:
        print(f"✗ Failed: {e}")

print("\n" + "="*50)
processor.provider.print_stats()
```

Run with:
```bash
uv run python scripts/test_fallback.py
```

## Testing Plan

### Phase 1: Unit Tests (30 min)
1. Test YtDlpFallback class independently
2. Verify transcript extraction works
3. Verify title fetching works
4. Test error handling

### Phase 2: Integration Tests (30 min)
1. Test TorTranscriptFetcher with fallback
2. Verify fallback is triggered on Tor failure
3. Verify statistics tracking
4. Test with known-good videos

### Phase 3: End-to-End Tests (30 min)
1. Process batch of videos with mixed success rates
2. Verify some use Tor, some use yt-dlp
3. Check statistics output
4. Verify study notes generation works with both methods

### Phase 4: Edge Cases (30 min)
1. Test videos without transcripts
2. Test private/deleted videos
3. Test rate limiting scenarios
4. Test with Tor proxy down (should use yt-dlp)

## Success Criteria

- ✅ YtDlpFallback class implemented and tested
- ✅ Integration with TorTranscriptFetcher working
- ✅ Fallback triggers automatically when Tor fails
- ✅ Statistics tracking shows method used
- ✅ Unit tests passing
- ✅ Integration tests passing
- ✅ Combined success rate >95% on test videos
- ✅ Documentation updated

## Estimated Time
2-3 hours

## Difficulty
Medium - requires integration with existing Tor implementation

## Value
HIGH - significantly improves overall success rate, provides redundancy

## Dependencies
- yt-dlp package
- Existing Tor implementation
- No changes to Docker setup needed

## Files to Create
- `src/yt_study_buddy/ytdlp_fallback.py`
- `tests/test_ytdlp_fallback.py`
- `scripts/test_fallback.py`

## Files to Modify
- `src/yt_study_buddy/tor_transcript_fetcher.py`
- `src/yt_study_buddy/transcript_provider.py`
- `src/yt_study_buddy/cli.py`
- `pyproject.toml`
- `README.md`

## When Complete

1. Run full test suite: `uv run pytest`
2. Run integration test: `uv run python scripts/test_fallback.py`
3. Process test playlist to verify statistics
4. Update CHANGES_SUMMARY.md with results
5. Commit: "Add yt-dlp fallback for transcript fetching"
6. Create PR targeting main branch

## Notes

- yt-dlp will make direct connections to YouTube (no Tor)
- This is acceptable as a fallback - Tor is still primary
- yt-dlp may be slower than Tor but is more reliable for blocked IPs
- Statistics will show which method was used for transparency
