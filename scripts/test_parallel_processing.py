#!/usr/bin/env python3
"""Test parallel video processing with real videos - demonstrates per-worker Tor connections."""
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


def process_video_with_worker(url: str, worker_processor: VideoProcessor) -> ProcessingResult:
    """Process a single video using per-worker processor."""
    start_time = time.time()
    video_id = worker_processor.get_video_id(url)

    try:
        transcript_data = worker_processor.get_transcript(video_id)
        title = worker_processor.get_video_title(video_id)

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


# Sequential processing (for baseline)
print("Testing Sequential Processing")
print("="*50)
sequential_processor = VideoProcessor("tor")
start = time.time()
sequential_results = []
for url in test_urls:
    result = process_video_with_worker(url, sequential_processor)
    sequential_results.append(result)
sequential_time = time.time() - start
print(f"Sequential time: {sequential_time:.1f}s\n")

# Parallel processing with per-worker Tor connections
print("Testing Parallel Processing (3 workers with independent Tor connections)")
print("="*50)
parallel_processor = ParallelVideoProcessor(max_workers=3, rate_limit_delay=1.0)


def video_processor_factory():
    """Factory function to create independent VideoProcessor for each worker."""
    return VideoProcessor("tor")


start = time.time()
parallel_results = parallel_processor.process_videos_parallel(
    test_urls,
    process_video_with_worker,
    worker_factory=video_processor_factory
)
parallel_time = time.time() - start

print(f"\n{'='*50}")
print("COMPARISON")
print(f"{'='*50}")
print(f"Sequential: {sequential_time:.1f}s")
print(f"Parallel (per-worker connections): {parallel_time:.1f}s")
speedup = sequential_time / parallel_time if parallel_time > 0 else 0
print(f"Speedup: {speedup:.2f}x")
print(f"{'='*50}")
print("\nNote: Each parallel worker used an independent Tor connection,")
print("ensuring better isolation and different exit nodes.")
