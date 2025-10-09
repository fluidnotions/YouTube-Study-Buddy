# Agent Task: Implement Parallel Video Processing

## Branch
`feat/parallel`

## Worktree
`/home/justin/Documents/dev/python/PycharmProjects/worktrees/parallel`

## Objective
Implement parallel processing for multiple YouTube videos to significantly reduce total processing time when handling playlists or batches of URLs. Use Python's `concurrent.futures` to process videos concurrently while respecting rate limits and resource constraints.

## Context
Current status:
- ✅ Sequential processing working (one video at a time)
- ✅ Each video takes 30-90 seconds (transcript fetch + AI processing)
- ❌ Processing 10 videos takes 5-15 minutes sequentially
- ❌ No parallelization - CPU/network underutilized

**Goal:** Process multiple videos simultaneously to reduce total batch processing time by 60-80%.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│ CLI: process_urls(urls)                         │
│  ↓                                              │
│ ParallelVideoProcessor                          │
│  ↓                                              │
│ ThreadPoolExecutor / ProcessPoolExecutor        │
│  ↓                                              │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│ │ Worker 1 │  │ Worker 2 │  │ Worker 3 │       │
│ │ Video A  │  │ Video B  │  │ Video C  │       │
│ └──────────┘  └──────────┘  └──────────┘       │
│  ↓             ↓             ↓                  │
│ Results collected & processed                   │
└─────────────────────────────────────────────────┘
```

## Design Considerations

### Threading vs Multiprocessing
- **ThreadPoolExecutor**: Better for I/O-bound tasks (network calls, API requests)
  - Video transcript fetching (Tor/HTTP requests)
  - Claude API calls for note generation
  - Recommended: Start with threads

- **ProcessPoolExecutor**: Better for CPU-bound tasks
  - Heavy computation (if any)
  - True parallelism (bypass GIL)
  - Consider if thread performance insufficient

### Rate Limiting
- Tor exit nodes: Don't want too many concurrent requests from same exit
- Claude API: Has rate limits (check current tier)
- YouTube: Rate limiting on transcript requests

**Strategy:** Limit max workers to 3-5 to balance speed vs rate limiting

### Resource Management
- Memory: Each worker holds video data + transcript + generated notes
- Network: Each worker has active connections
- File I/O: Writing notes to disk (add file locks if needed)

## Implementation Tasks

### Task 1: Create ParallelVideoProcessor
**File:** `src/yt_study_buddy/parallel_processor.py` (NEW)

```python
"""
Parallel video processing for batch URL handling.

Uses ThreadPoolExecutor for concurrent I/O operations.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """Result from processing a single video."""
    url: str
    video_id: str
    success: bool
    title: Optional[str] = None
    filepath: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    method: Optional[str] = None  # 'tor' or 'yt-dlp'


class ParallelVideoProcessor:
    """Process multiple YouTube videos concurrently."""

    def __init__(
        self,
        max_workers: int = 3,
        rate_limit_delay: float = 1.0,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        """
        Initialize parallel processor.

        Args:
            max_workers: Maximum concurrent video processing tasks (default: 3)
            rate_limit_delay: Minimum delay between starting new tasks in seconds
            progress_callback: Optional callback(status, completed, total)
        """
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.progress_callback = progress_callback

    def process_videos_parallel(
        self,
        urls: List[str],
        process_func: Callable[[str], ProcessingResult]
    ) -> List[ProcessingResult]:
        """
        Process multiple videos in parallel.

        Args:
            urls: List of YouTube URLs to process
            process_func: Function that processes a single URL and returns ProcessingResult

        Returns:
            List of ProcessingResult objects
        """
        if not urls:
            return []

        print(f"\n{'='*50}")
        print(f"PARALLEL PROCESSING: {len(urls)} videos with {self.max_workers} workers")
        print(f"{'='*50}\n")

        results = []
        completed_count = 0
        start_time = time.time()

        # Use ThreadPoolExecutor for I/O-bound tasks
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_url = {}
            for i, url in enumerate(urls):
                # Add rate limiting between submissions
                if i > 0 and self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

                future = executor.submit(process_func, url)
                future_to_url[future] = url

            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                completed_count += 1

                try:
                    result = future.result()
                    results.append(result)

                    # Progress update
                    status = "✓" if result.success else "✗"
                    print(f"[{completed_count}/{len(urls)}] {status} {url}")
                    if result.title:
                        print(f"    Title: {result.title}")
                    if result.method:
                        print(f"    Method: {result.method}")
                    if result.error:
                        print(f"    Error: {result.error}")

                    # Call progress callback if provided
                    if self.progress_callback:
                        self.progress_callback(
                            "success" if result.success else "failed",
                            completed_count,
                            len(urls)
                        )

                except Exception as e:
                    # Handle unexpected errors
                    error_result = ProcessingResult(
                        url=url,
                        video_id="unknown",
                        success=False,
                        error=str(e)
                    )
                    results.append(error_result)
                    print(f"[{completed_count}/{len(urls)}] ✗ {url}")
                    print(f"    Unexpected error: {e}")

        # Summary
        elapsed_time = time.time() - start_time
        success_count = sum(1 for r in results if r.success)

        print(f"\n{'='*50}")
        print(f"PARALLEL PROCESSING COMPLETE")
        print(f"{'='*50}")
        print(f"Total videos: {len(urls)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(urls) - success_count}")
        print(f"Total time: {elapsed_time:.1f}s")
        print(f"Average time per video: {elapsed_time/len(urls):.1f}s")
        print(f"{'='*50}\n")

        return results


class ProcessingMetrics:
    """Track metrics across parallel processing runs."""

    def __init__(self):
        self.total_videos = 0
        self.successful = 0
        self.failed = 0
        self.total_time = 0.0
        self.method_counts = {'tor': 0, 'yt-dlp': 0}

    def add_result(self, result: ProcessingResult):
        """Add a processing result to metrics."""
        self.total_videos += 1
        if result.success:
            self.successful += 1
            if result.method:
                self.method_counts[result.method] = self.method_counts.get(result.method, 0) + 1
        else:
            self.failed += 1
        self.total_time += result.duration_seconds

    def print_summary(self):
        """Print metrics summary."""
        print(f"\n{'='*50}")
        print("PROCESSING METRICS")
        print(f"{'='*50}")
        print(f"Total videos processed: {self.total_videos}")
        print(f"Success rate: {self.successful}/{self.total_videos} ({self.successful/self.total_videos*100:.1f}%)")
        print(f"Failed: {self.failed}")

        if self.method_counts:
            print(f"\nMethods used:")
            for method, count in self.method_counts.items():
                print(f"  {method}: {count} ({count/self.successful*100:.1f}%)")

        if self.total_videos > 0:
            print(f"\nAverage processing time: {self.total_time/self.total_videos:.1f}s per video")

        print(f"{'='*50}\n")
```

### Task 2: Modify YouTubeStudyNotes CLI Class
**File:** `src/yt_study_buddy/cli.py`

Update the `YouTubeStudyNotes` class to support parallel processing:

```python
# Add import at top
from .parallel_processor import ParallelVideoProcessor, ProcessingResult, ProcessingMetrics

class YouTubeStudyNotes:
    """Main application class for processing YouTube videos into study notes."""

    def __init__(self, subject=None, global_context=True, base_dir="notes",
                 generate_assessments=True, auto_categorize=True,
                 parallel=False, max_workers=3):
        # ... existing init code ...
        self.parallel = parallel
        self.max_workers = max_workers

        # Add parallel processor
        if self.parallel:
            self.parallel_processor = ParallelVideoProcessor(
                max_workers=max_workers,
                rate_limit_delay=1.0
            )
            self.metrics = ProcessingMetrics()

    def process_single_url(self, url):
        """Process a single YouTube URL and generate study notes."""
        start_time = time.time()

        # Extract video ID
        video_id = self.video_processor.get_video_id(url)
        if not video_id:
            return ProcessingResult(
                url=url,
                video_id="invalid",
                success=False,
                error="Invalid YouTube URL"
            )

        print(f"\nFound video ID: {video_id}")

        try:
            # Get transcript
            print("Fetching transcript from YouTube via Tor...")
            transcript_data = self.video_processor.get_transcript(video_id)
            transcript = transcript_data['transcript']
            method = transcript_data.get('method', 'tor')

            # ... rest of existing processing logic ...

            duration = time.time() - start_time
            return ProcessingResult(
                url=url,
                video_id=video_id,
                success=True,
                title=video_title,
                filepath=filepath,
                duration_seconds=duration,
                method=method
            )

        except Exception as e:
            duration = time.time() - start_time
            print(f"\nERROR processing {url}: {e}")
            return ProcessingResult(
                url=url,
                video_id=video_id,
                success=False,
                error=str(e),
                duration_seconds=duration
            )

    def process_urls(self, urls):
        """Process a list of URLs (sequential or parallel)."""
        if not urls:
            print("No URLs provided")
            return

        # Check if API is ready
        if not self.notes_generator.is_ready():
            return

        print(f"\nProcessing {len(urls)} URL(s)...")
        if self.subject:
            print(f"Subject: {self.subject}")

        if self.parallel:
            # Parallel processing
            results = self.parallel_processor.process_videos_parallel(
                urls,
                self.process_single_url
            )

            # Collect metrics
            for result in results:
                if hasattr(self, 'metrics'):
                    self.metrics.add_result(result)

            # Show statistics
            if hasattr(self, 'metrics'):
                self.metrics.print_summary()

            successful = sum(1 for r in results if r.success)
            print(f"\n{'='*50}")
            print(f"COMPLETE: {successful}/{len(urls)} URL(s) processed successfully")
            print(f"{'='*50}")

        else:
            # Sequential processing (existing logic)
            successful = 0
            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] Processing: {url}")

                # Add delay between requests
                if i > 1:
                    print("  Waiting 3 seconds to avoid rate limiting...")
                    time.sleep(3)

                result = self.process_single_url(url)
                if result.success:
                    successful += 1

            print(f"\n{'='*50}")
            print(f"COMPLETE: {successful}/{len(urls)} URL(s) processed successfully")
            print(f"{'='*50}")

        # Show knowledge graph stats
        stats = self.knowledge_graph.get_stats()
        print(f"Knowledge Graph: {stats['total_notes']} notes, {stats['total_concepts']} concepts")
```

### Task 3: Add CLI Arguments for Parallel Processing
**File:** `src/yt_study_buddy/cli.py`

Update `main()` function to accept parallel processing flags:

```python
def main():
    """Main CLI entry point."""
    # ... existing header ...

    parser = argparse.ArgumentParser(...)
    # ... existing arguments ...

    # Add parallel processing arguments
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='Enable parallel processing of videos')
    parser.add_argument('--workers', '-w', type=int, default=3,
                       help='Number of parallel workers (default: 3)')

    args = parser.parse_args()

    # ... existing argument handling ...

    # Create app instance with parallel configuration
    app = YouTubeStudyNotes(
        subject=args.subject,
        global_context=not args.subject_only,
        generate_assessments=not args.no_assessments,
        auto_categorize=not args.no_auto_categorize,
        parallel=args.parallel,
        max_workers=args.workers
    )

    # ... rest of existing code ...
```

### Task 4: Thread-Safe File Writing
**File:** `src/yt_study_buddy/cli.py`

Add file locking to prevent concurrent write conflicts:

```python
import threading
from pathlib import Path

class YouTubeStudyNotes:
    def __init__(self, ...):
        # ... existing init ...
        self._file_lock = threading.Lock()
        self._kg_lock = threading.Lock()

    def process_single_url(self, url):
        """Process a single YouTube URL (thread-safe)."""
        # ... existing processing ...

        # Thread-safe file writing
        with self._file_lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(linked_notes)
            print(f"✓ Study notes saved to {filename}")

            # Save assessment if enabled
            if self.assessment_generator:
                # ... assessment generation ...
                with open(assessment_path, 'w', encoding='utf-8') as f:
                    f.write(assessment_content)
                print(f"  Assessment saved to {assessment_filename}")

        # Thread-safe knowledge graph update
        with self._kg_lock:
            self.knowledge_graph.add_note(video_title, linked_notes)
            self.knowledge_graph.refresh_cache()

        return result
```

### Task 5: Add Progress Indicator for Streamlit
**File:** `streamlit_app.py`

Update Streamlit UI to show parallel processing progress:

```python
import streamlit as st
from src.yt_study_buddy.parallel_processor import ParallelVideoProcessor

# Add parallel processing toggle
use_parallel = st.sidebar.checkbox("Enable Parallel Processing", value=True)
max_workers = st.sidebar.slider("Max Workers", min_value=1, max_value=5, value=3) if use_parallel else 1

# ... existing code ...

if st.button("Process Videos"):
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_callback(status, completed, total):
        """Update Streamlit progress."""
        progress = completed / total
        progress_bar.progress(progress)
        status_text.text(f"Processing: {completed}/{total} videos ({status})")

    # Initialize app with parallel settings
    app = YouTubeStudyNotes(
        subject=subject,
        parallel=use_parallel,
        max_workers=max_workers
    )

    if use_parallel:
        app.parallel_processor.progress_callback = progress_callback

    # Process videos
    app.process_urls(urls)

    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
```

### Task 6: Add Unit Tests
**File:** `tests/test_parallel_processor.py` (NEW)

```python
"""Tests for parallel video processing."""
import pytest
import time
from unittest.mock import Mock
from src.yt_study_buddy.parallel_processor import (
    ParallelVideoProcessor,
    ProcessingResult,
    ProcessingMetrics
)


def mock_process_func(url: str) -> ProcessingResult:
    """Mock processing function that simulates work."""
    # Simulate processing time
    time.sleep(0.1)

    # Simulate some failures
    success = not url.endswith("fail")

    return ProcessingResult(
        url=url,
        video_id=url.split("/")[-1],
        success=success,
        title=f"Video {url}" if success else None,
        error="Mock failure" if not success else None,
        duration_seconds=0.1,
        method="tor"
    )


def test_parallel_processor_basic():
    """Test basic parallel processing."""
    processor = ParallelVideoProcessor(max_workers=2)

    urls = [
        "https://youtube.com/watch?v=video1",
        "https://youtube.com/watch?v=video2",
        "https://youtube.com/watch?v=video3",
    ]

    results = processor.process_videos_parallel(urls, mock_process_func)

    assert len(results) == 3
    assert all(r.success for r in results)


def test_parallel_faster_than_sequential():
    """Test that parallel is faster than sequential."""
    urls = ["url1", "url2", "url3", "url4"]

    # Sequential timing
    start = time.time()
    for url in urls:
        mock_process_func(url)
    sequential_time = time.time() - start

    # Parallel timing
    processor = ParallelVideoProcessor(max_workers=2, rate_limit_delay=0)
    start = time.time()
    processor.process_videos_parallel(urls, mock_process_func)
    parallel_time = time.time() - start

    # Parallel should be at least 1.5x faster
    assert parallel_time < sequential_time * 0.7


def test_processing_metrics():
    """Test metrics tracking."""
    metrics = ProcessingMetrics()

    results = [
        ProcessingResult("url1", "id1", True, method="tor", duration_seconds=1.0),
        ProcessingResult("url2", "id2", True, method="yt-dlp", duration_seconds=2.0),
        ProcessingResult("url3", "id3", False, error="Failed", duration_seconds=0.5),
    ]

    for result in results:
        metrics.add_result(result)

    assert metrics.total_videos == 3
    assert metrics.successful == 2
    assert metrics.failed == 1
    assert metrics.method_counts["tor"] == 1
    assert metrics.method_counts["yt-dlp"] == 1


def test_progress_callback():
    """Test progress callback is called."""
    callback_calls = []

    def callback(status, completed, total):
        callback_calls.append((status, completed, total))

    processor = ParallelVideoProcessor(max_workers=2, progress_callback=callback)
    urls = ["url1", "url2", "url3"]

    processor.process_videos_parallel(urls, mock_process_func)

    assert len(callback_calls) == 3
    assert callback_calls[-1][1] == 3  # Last call shows 3 completed
```

### Task 7: Add Integration Test
**File:** `scripts/test_parallel_processing.py` (NEW)

```python
#!/usr/bin/env python3
"""Test parallel video processing with real videos."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yt_study_buddy.video_processor import VideoProcessor
from yt_study_buddy.parallel_processor import ParallelVideoProcessor, ProcessingResult

# Test videos (known to have transcripts)
test_urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley
    "https://www.youtube.com/watch?v=9bZkp7q19f0",  # Gangnam Style
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # First YouTube video
]

# Create processor
video_processor = VideoProcessor("tor")


def process_video(url: str) -> ProcessingResult:
    """Process a single video."""
    start_time = time.time()
    video_id = video_processor.get_video_id(url)

    try:
        transcript_data = video_processor.get_transcript(video_id)
        title = video_processor.get_video_title(video_id)

        duration = time.time() - start_time
        return ProcessingResult(
            url=url,
            video_id=video_id,
            success=True,
            title=title,
            duration_seconds=duration,
            method=transcript_data.get('method', 'tor')
        )
    except Exception as e:
        duration = time.time() - start_time
        return ProcessingResult(
            url=url,
            video_id=video_id,
            success=False,
            error=str(e),
            duration_seconds=duration
        )


print("Testing Sequential Processing")
print("="*50)
start = time.time()
sequential_results = [process_video(url) for url in test_urls]
sequential_time = time.time() - start
print(f"Sequential time: {sequential_time:.1f}s\n")

print("Testing Parallel Processing (3 workers)")
print("="*50)
parallel_processor = ParallelVideoProcessor(max_workers=3, rate_limit_delay=1.0)
start = time.time()
parallel_results = parallel_processor.process_videos_parallel(test_urls, process_video)
parallel_time = time.time() - start

print(f"\n{'='*50}")
print("COMPARISON")
print(f"{'='*50}")
print(f"Sequential: {sequential_time:.1f}s")
print(f"Parallel: {parallel_time:.1f}s")
speedup = sequential_time / parallel_time
print(f"Speedup: {speedup:.2f}x")
print(f"{'='*50}")
```

Run with:
```bash
uv run python scripts/test_parallel_processing.py
```

### Task 8: Update Documentation
**File:** `README.md`

Add section on parallel processing:

```markdown
## Parallel Processing

Process multiple videos simultaneously for faster batch operations:

### CLI Usage
```bash
# Sequential (default)
youtube-study-buddy --file urls.txt

# Parallel with 3 workers (recommended)
youtube-study-buddy --parallel --file urls.txt

# Parallel with 5 workers (faster but more rate limiting risk)
youtube-study-buddy --parallel --workers 5 --file urls.txt
```

### Performance
- **Sequential**: ~60s per video → 10 videos = 10 minutes
- **Parallel (3 workers)**: ~25s per video → 10 videos = 4 minutes
- **Speedup**: 2-3x faster for batches

### Considerations
- **Rate Limiting**: More workers = higher risk of YouTube rate limits
- **Recommended**: 3-5 workers for optimal balance
- **Memory**: Each worker holds video data simultaneously
- **API Limits**: Claude API rate limits apply

### Streamlit UI
The web interface automatically uses parallel processing when available.
```

### Task 9: Update Help Text
**File:** `src/yt_study_buddy/cli.py`

Update `show_help()` function:

```python
def show_help():
    """Display help information."""
    print("""
YouTube Study Buddy - Transform YouTube videos into AI-powered study notes

Usage:
  youtube-study-buddy <url1> <url2> ...                    # Process URLs sequentially
  youtube-study-buddy --parallel --file urls.txt           # Process URLs in parallel
  youtube-study-buddy --workers 5 -p --file urls.txt      # Parallel with 5 workers

Options:
  --subject <name>         Organize notes by subject
  --subject-only           Cross-reference only within subject
  --file <filename>        Read URLs from file
  --parallel, -p           Enable parallel processing (faster for batches)
  --workers, -w <num>      Number of parallel workers (default: 3, max: 10)
  --no-assessments         Disable assessment generation
  --no-auto-categorize     Disable auto-categorization
  --help, -h               Show this help message

Examples:
  # Sequential processing
  youtube-study-buddy https://youtube.com/watch?v=xyz

  # Parallel processing (3 workers)
  youtube-study-buddy --parallel --file playlist.txt

  # Parallel with 5 workers
  youtube-study-buddy -p -w 5 --file large-playlist.txt

Performance:
  Sequential: ~60s per video
  Parallel (3 workers): ~25s per video (2.5x faster)
  Parallel (5 workers): ~20s per video (3x faster, higher rate limit risk)

For interactive GUI: streamlit run streamlit_app.py
    """)
```

## Testing Plan

### Phase 1: Unit Tests (30 min)
1. Test ParallelVideoProcessor class
2. Test ProcessingMetrics tracking
3. Test progress callbacks
4. Verify thread safety mechanisms

### Phase 2: Integration Tests (45 min)
1. Test with mock processing functions
2. Verify parallel is faster than sequential
3. Test with 1, 3, and 5 workers
4. Test error handling in parallel context

### Phase 3: End-to-End Tests (45 min)
1. Process 5-10 real videos sequentially
2. Process same videos in parallel
3. Compare results (should be identical)
4. Verify speedup (should be 2-3x)
5. Check for file conflicts (shouldn't occur)

### Phase 4: Stress Tests (30 min)
1. Process 20+ videos in parallel
2. Monitor for rate limiting
3. Check memory usage
4. Verify knowledge graph integrity

## Success Criteria

- ✅ ParallelVideoProcessor implemented and tested
- ✅ CLI accepts --parallel and --workers flags
- ✅ Thread-safe file operations
- ✅ Knowledge graph updates thread-safe
- ✅ Parallel 2-3x faster than sequential for 10+ videos
- ✅ Results identical between parallel and sequential
- ✅ Progress tracking works
- ✅ No file conflicts or data corruption
- ✅ Unit tests passing
- ✅ Integration tests passing
- ✅ Documentation updated

## Estimated Time
3-4 hours

## Difficulty
Medium-High - requires thread safety and concurrent programming

## Value
HIGH - significant time savings for batch processing, better user experience

## Risks & Mitigations

### Risk: Rate Limiting
**Mitigation:**
- Limit default workers to 3
- Add configurable delays between task submissions
- Document recommended worker counts

### Risk: Thread Safety Issues
**Mitigation:**
- Use locks for file I/O and knowledge graph updates
- Test extensively with concurrent operations
- Use ThreadPoolExecutor (simpler than multiprocessing)

### Risk: Memory Usage
**Mitigation:**
- Limit max workers (avoid unbounded parallelism)
- Process in chunks for very large batches
- Monitor memory in stress tests

### Risk: Error Handling
**Mitigation:**
- Wrap all worker code in try-except
- Return ProcessingResult for all outcomes
- Don't let one failure crash entire batch

## Files to Create
- `src/yt_study_buddy/parallel_processor.py`
- `tests/test_parallel_processor.py`
- `scripts/test_parallel_processing.py`

## Files to Modify
- `src/yt_study_buddy/cli.py` (major changes)
- `streamlit_app.py` (add parallel UI controls)
- `README.md` (add parallel processing docs)

## Dependencies
- `concurrent.futures` (stdlib, no new dependencies needed)
- Thread-safe modifications to existing code

## When Complete

1. Run unit tests: `uv run pytest tests/test_parallel_processor.py`
2. Run integration test: `uv run python scripts/test_parallel_processing.py`
3. Process test playlist with --parallel flag
4. Verify 2-3x speedup
5. Check for any file conflicts or issues
6. Update CHANGES_SUMMARY.md with performance metrics
7. Commit: "Implement parallel video processing"
8. Create PR targeting main branch

## Future Enhancements

- **Adaptive worker count**: Auto-adjust based on success rate
- **Retry queue**: Failed videos retry automatically
- **Batch chunking**: Process very large playlists in manageable chunks
- **Progress persistence**: Resume interrupted batch processing
- **ProcessPoolExecutor option**: For CPU-intensive scenarios
