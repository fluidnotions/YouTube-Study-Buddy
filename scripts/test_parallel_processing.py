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
speedup = sequential_time / parallel_time if parallel_time > 0 else 0
print(f"Speedup: {speedup:.2f}x")
print(f"{'='*50}")
