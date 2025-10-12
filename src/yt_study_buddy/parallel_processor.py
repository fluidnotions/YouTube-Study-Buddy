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
        process_func: Callable[[str], ProcessingResult],
        worker_factory: Optional[Callable[[], Any]] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple videos in parallel with optional per-worker instances.

        Args:
            urls: List of YouTube URLs to process
            process_func: Function that processes a single URL and returns ProcessingResult
                         Should accept (url, worker_instance) if worker_factory is provided
            worker_factory: Optional factory function to create per-worker instances
                          (e.g., VideoProcessor instances for independent Tor connections)

        Returns:
            List of ProcessingResult objects
        """
        if not urls:
            return []

        print(f"\n{'='*50}")
        print(f"PARALLEL PROCESSING: {len(urls)} videos with {self.max_workers} workers")
        if worker_factory:
            print(f"Per-worker instances: ENABLED (independent Tor connections)")
        else:
            print(f"Per-worker instances: DISABLED (shared connections)")
        print(f"{'='*50}\n")

        results = []
        completed_count = 0
        start_time = time.time()

        # Create wrapper function that creates per-worker instance if needed
        def worker_wrapper(url: str) -> ProcessingResult:
            if worker_factory:
                worker_instance = worker_factory()
                return process_func(url, worker_instance)
            else:
                return process_func(url)

        # Use ThreadPoolExecutor for I/O-bound tasks
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_url = {}
            for i, url in enumerate(urls):
                # Add rate limiting between submissions
                if i > 0 and self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

                future = executor.submit(worker_wrapper, url)
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
                if count > 0:
                    print(f"  {method}: {count} ({count/self.successful*100:.1f}%)")

        if self.total_videos > 0:
            print(f"\nAverage processing time: {self.total_time/self.total_videos:.1f}s per video")

        print(f"{'='*50}\n")
