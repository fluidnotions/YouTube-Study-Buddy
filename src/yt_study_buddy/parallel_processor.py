"""
Parallel video processing for batch URL handling.

Uses ThreadPoolExecutor for concurrent I/O operations.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from loguru import logger


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
    """
    Process multiple YouTube videos concurrently or sequentially.

    When max_workers=1, processes sequentially with same interface as parallel mode.
    This provides unified behavior regardless of processing mode.
    """

    def __init__(
        self,
        max_workers: int = 3,
        rate_limit_delay: float = 1.0,
        sequential_delay: float = 3.0,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        """
        Initialize parallel processor.

        Args:
            max_workers: Maximum concurrent video processing tasks (default: 3)
                        Set to 1 for sequential processing
            rate_limit_delay: Minimum delay between starting new tasks in seconds (parallel mode)
            sequential_delay: Delay between videos in sequential mode (default: 3.0)
            progress_callback: Optional callback(status, completed, total)
        """
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.sequential_delay = sequential_delay
        self.progress_callback = progress_callback
        self.is_sequential = (max_workers == 1)

    def process_videos_parallel(
        self,
        urls: List[str],
        process_func: Callable[[str], ProcessingResult],
        worker_factory: Optional[Callable[[], Any]] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple videos in parallel or sequential mode.

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

        # Route to appropriate processing method
        if self.is_sequential:
            return self._process_sequential(urls, process_func, worker_factory)
        else:
            return self._process_parallel(urls, process_func, worker_factory)

    def _process_sequential(
        self,
        urls: List[str],
        process_func: Callable[[str], ProcessingResult],
        worker_factory: Optional[Callable[[], Any]] = None
    ) -> List[ProcessingResult]:
        """
        Process videos sequentially with same interface as parallel mode.

        Args:
            urls: List of YouTube URLs to process
            process_func: Function that processes a single URL and returns ProcessingResult
            worker_factory: Optional factory function to create worker instance

        Returns:
            List of ProcessingResult objects
        """
        logger.info(f"\n{'='*50}")
        logger.debug(f"SEQUENTIAL PROCESSING: {len(urls)} videos")
        logger.info(f"{'='*50}\n")

        results = []
        start_time = time.time()

        # Create single worker instance if factory provided
        worker_instance = worker_factory() if worker_factory else None

        for i, url in enumerate(urls, 1):
            logger.debug(f"\n[{i}/{len(urls)}] Processing: {url}")

            # Apply delay between videos (skip first)
            if i > 1 and self.sequential_delay > 0:
                logger.info(f"  Waiting {self.sequential_delay}s to avoid rate limiting...")
                time.sleep(self.sequential_delay)

            try:
                # Process video
                if worker_instance:
                    result = process_func(url, worker_processor=worker_instance, worker_id=0)
                else:
                    result = process_func(url, worker_id=0)

                results.append(result)

                # Progress update
                status = "✓" if result.success else "✗"
                if result.title:
                    logger.info(f"    {status} Title: {result.title}")
                if result.method:
                    logger.info(f"    Method: {result.method}")
                if result.error:
                    logger.error(f"    Error: {result.error}")

                # Call progress callback if provided
                if self.progress_callback:
                    self.progress_callback(
                        "success" if result.success else "failed",
                        i,
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
                logger.error(f"    ✗ Unexpected error: {e}")

        # Summary
        elapsed_time = time.time() - start_time
        success_count = sum(1 for r in results if r.success)

        logger.info(f"\n{'='*50}")
        logger.success(f"SEQUENTIAL PROCESSING COMPLETE")
        logger.info(f"{'='*50}")
        logger.info(f"Total videos: {len(urls)}")
        logger.success(f"Successful: {success_count}")
        logger.error(f"Failed: {len(urls) - success_count}")
        logger.info(f"Total time: {elapsed_time:.1f}s")
        logger.info(f"Average time per video: {elapsed_time/len(urls):.1f}s")
        logger.info(f"{'='*50}\n")

        return results

    def _process_parallel(
        self,
        urls: List[str],
        process_func: Callable[[str], ProcessingResult],
        worker_factory: Optional[Callable[[], Any]] = None
    ) -> List[ProcessingResult]:
        """
        Process videos in parallel using ThreadPoolExecutor.

        Args:
            urls: List of YouTube URLs to process
            process_func: Function that processes a single URL and returns ProcessingResult
            worker_factory: Optional factory function to create per-worker instances

        Returns:
            List of ProcessingResult objects
        """
        logger.info(f"\n{'='*50}")
        logger.debug(f"PARALLEL PROCESSING: {len(urls)} videos with {self.max_workers} workers")
        if worker_factory:
            logger.debug(f"Per-worker instances: ENABLED (independent Tor connections)")
        else:
            logger.debug(f"Per-worker instances: DISABLED (shared connections)")
        logger.info(f"{'='*50}\n")

        results = []
        completed_count = 0
        start_time = time.time()

        # Create wrapper function that creates per-worker instance if needed
        def worker_wrapper(url_and_id: tuple) -> ProcessingResult:
            url, worker_id = url_and_id
            if worker_factory:
                worker_instance = worker_factory()
                return process_func(url, worker_instance, worker_id=worker_id)
            else:
                return process_func(url, worker_id=worker_id)

        # Use ThreadPoolExecutor for I/O-bound tasks
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks with worker IDs
            future_to_url = {}
            for i, url in enumerate(urls):
                # Add rate limiting between submissions
                if i > 0 and self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

                worker_id = i % self.max_workers  # Assign worker ID based on worker pool
                future = executor.submit(worker_wrapper, (url, worker_id))
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
                    logger.success(f"[{completed_count}/{len(urls)}] {status} {url}")
                    if result.title:
                        logger.info(f"    Title: {result.title}")
                    if result.method:
                        logger.info(f"    Method: {result.method}")
                    if result.error:
                        logger.error(f"    Error: {result.error}")

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
                    logger.error(f"[{completed_count}/{len(urls)}] ✗ {url}")
                    logger.error(f"    Unexpected error: {e}")

        # Summary
        elapsed_time = time.time() - start_time
        success_count = sum(1 for r in results if r.success)

        logger.info(f"\n{'='*50}")
        logger.success(f"PARALLEL PROCESSING COMPLETE")
        logger.info(f"{'='*50}")
        logger.info(f"Total videos: {len(urls)}")
        logger.success(f"Successful: {success_count}")
        logger.error(f"Failed: {len(urls) - success_count}")
        logger.info(f"Total time: {elapsed_time:.1f}s")
        logger.info(f"Average time per video: {elapsed_time/len(urls):.1f}s")
        logger.info(f"{'='*50}\n")

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
        logger.info(f"\n{'='*50}")
        logger.debug("PROCESSING METRICS")
        logger.info(f"{'='*50}")
        logger.info(f"Total videos processed: {self.total_videos}")
        logger.success(f"Success rate: {self.successful}/{self.total_videos} ({self.successful/self.total_videos*100:.1f}%)")
        logger.error(f"Failed: {self.failed}")

        if self.method_counts:
            logger.info(f"\nMethods used:")
            for method, count in self.method_counts.items():
                if count > 0:
                    logger.success(f"  {method}: {count} ({count/self.successful*100:.1f}%)")

        if self.total_videos > 0:
            logger.debug(f"\nAverage processing time: {self.total_time/self.total_videos:.1f}s per video")

        logger.info(f"{'='*50}\n")
