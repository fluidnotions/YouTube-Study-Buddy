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


def test_handle_exceptions():
    """Test that exceptions are handled gracefully."""
    def failing_process_func(url: str) -> ProcessingResult:
        if "error" in url:
            raise ValueError("Simulated error")
        return mock_process_func(url)

    processor = ParallelVideoProcessor(max_workers=2)
    urls = ["url1", "urlerror", "url3"]

    results = processor.process_videos_parallel(urls, failing_process_func)

    assert len(results) == 3
    # One should have failed with exception
    failed = [r for r in results if not r.success]
    assert len(failed) == 1
    assert "Simulated error" in failed[0].error


def test_empty_url_list():
    """Test handling of empty URL list."""
    processor = ParallelVideoProcessor(max_workers=2)
    results = processor.process_videos_parallel([], mock_process_func)
    assert results == []


def test_single_worker():
    """Test processing with single worker (effectively sequential)."""
    processor = ParallelVideoProcessor(max_workers=1, rate_limit_delay=0)
    urls = ["url1", "url2"]

    results = processor.process_videos_parallel(urls, mock_process_func)

    assert len(results) == 2
    assert all(r.success for r in results)


def test_processing_result_dataclass():
    """Test ProcessingResult dataclass."""
    result = ProcessingResult(
        url="https://youtube.com/watch?v=test",
        video_id="test",
        success=True,
        title="Test Video",
        filepath="/path/to/file.md",
        duration_seconds=30.5,
        method="tor"
    )

    assert result.url == "https://youtube.com/watch?v=test"
    assert result.video_id == "test"
    assert result.success is True
    assert result.title == "Test Video"
    assert result.filepath == "/path/to/file.md"
    assert result.duration_seconds == 30.5
    assert result.method == "tor"


def test_metrics_summary_print(capsys):
    """Test metrics summary printing."""
    metrics = ProcessingMetrics()

    results = [
        ProcessingResult("url1", "id1", True, method="tor", duration_seconds=1.0),
        ProcessingResult("url2", "id2", True, method="tor", duration_seconds=2.0),
    ]

    for result in results:
        metrics.add_result(result)

    metrics.print_summary()

    captured = capsys.readouterr()
    assert "PROCESSING METRICS" in captured.out
    assert "Total videos processed: 2" in captured.out
    assert "Success rate: 2/2" in captured.out
