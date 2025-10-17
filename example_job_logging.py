#!/usr/bin/env python3
"""
Example of JSON job logging with the stateless pipeline.

This demonstrates how job results (including errors) are appended to a JSON array.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from yt_study_buddy.video_job import VideoProcessingJob, create_job_from_url
from yt_study_buddy.job_logger import JobLogger, create_default_logger


def example_basic_logging():
    """Basic example: Create and log jobs."""
    print("=" * 60)
    print("BASIC JOB LOGGING EXAMPLE")
    print("=" * 60)
    print()

    # Create logger (will create notes/processing_log.json)
    logger = create_default_logger(Path('notes'))
    print(f"✓ Logger created: {logger.log_file}")
    print()

    # Create some example jobs
    jobs = [
        create_job_from_url(
            "https://youtu.be/example1",
            "example1",
            subject="AI",
            worker_id=0
        ),
        create_job_from_url(
            "https://youtu.be/example2",
            "example2",
            subject="AI",
            worker_id=1
        ),
    ]

    # Simulate processing
    print("Simulating job processing...")
    print()

    # Job 1: Success
    jobs[0].video_title = "Introduction to Machine Learning"
    jobs[0].transcript = "This is a sample transcript..."
    jobs[0].study_notes = "# Study Notes\n\nKey concepts..."
    jobs[0].notes_filepath = Path('notes/AI/Introduction_to_Machine_Learning.md')
    jobs[0].processing_duration = 45.2
    jobs[0].mark_completed(45.2)
    jobs[0].timings = {
        'fetch_transcript': 5.2,
        'generate_notes': 25.0,
        'write_files': 0.5,
        'export_pdfs': 14.5
    }

    # Job 2: Failed
    jobs[1].video_title = "Advanced Neural Networks"
    jobs[1].transcript = "Sample transcript..."
    jobs[1].processing_duration = 12.3
    jobs[1].mark_failed("API rate limit exceeded", jobs[1].stage)
    jobs[1].timings = {
        'fetch_transcript': 8.3,
        'generate_notes': 4.0
    }

    # Log jobs
    for job in jobs:
        logger.log_job(job)
        status = "✓ Success" if job.success else "✗ Failed"
        print(f"{status}: {job.video_title} ({job.processing_duration:.1f}s)")
        if job.error:
            print(f"  Error: {job.error}")

    print()
    print(f"✓ Logged {len(jobs)} jobs to {logger.log_file}")
    print()


def example_view_logs():
    """Example: Read and analyze logs."""
    print("=" * 60)
    print("VIEWING LOGGED JOBS")
    print("=" * 60)
    print()

    logger = create_default_logger(Path('notes'))

    # Get all jobs
    all_jobs = logger.get_all_jobs()
    print(f"Total jobs logged: {len(all_jobs)}")
    print()

    # Get statistics
    stats = logger.get_statistics()
    print("Statistics:")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success rate: {stats['success_rate']*100:.1f}%")
    if stats['average_duration']:
        print(f"  Average duration: {stats['average_duration']:.1f}s")
    print(f"  Total files created: {stats['total_files_created']}")
    print()

    if stats['error_types']:
        print("Error types:")
        for error_type, count in stats['error_types'].items():
            print(f"  {error_type}: {count}")
        print()

    # Show failed jobs
    failed = logger.get_failed_jobs()
    if failed:
        print(f"Failed jobs ({len(failed)}):")
        for job in failed:
            print(f"  - {job['video_title']}: {job['error']}")
        print()

    # Show successful jobs
    successful = logger.get_successful_jobs()
    if successful:
        print(f"Successful jobs ({len(successful)}):")
        for job in successful:
            files = job.get('total_files', 0)
            print(f"  - {job['video_title']} ({files} files)")
        print()


def example_json_structure():
    """Show what the JSON structure looks like."""
    print("=" * 60)
    print("JSON STRUCTURE")
    print("=" * 60)
    print()

    job = create_job_from_url(
        "https://youtu.be/example",
        "example",
        subject="AI"
    )
    job.video_title = "Example Video"
    job.transcript = "Sample transcript"
    job.study_notes = "Sample notes"
    job.notes_filepath = Path('notes/AI/Example_Video.md')
    job.processing_duration = 30.0
    job.mark_completed(30.0)

    import json
    print("Example job as JSON:")
    print(json.dumps(job.to_json(), indent=2))
    print()


def example_batch_logging():
    """Example: Log multiple jobs at once."""
    print("=" * 60)
    print("BATCH LOGGING")
    print("=" * 60)
    print()

    logger = create_default_logger(Path('notes'))

    # Create batch of jobs
    jobs = [
        create_job_from_url(f"https://youtu.be/video{i}", f"video{i}")
        for i in range(5)
    ]

    # Simulate processing
    for i, job in enumerate(jobs):
        job.video_title = f"Video {i+1}"
        job.processing_duration = 30.0 + i * 5
        if i < 4:  # 4 success, 1 failure
            job.mark_completed(job.processing_duration)
        else:
            job.mark_failed("Network timeout")

    # Log entire batch at once (more efficient)
    logger.log_jobs_batch(jobs)

    print(f"✓ Batch logged {len(jobs)} jobs")
    print()


if __name__ == '__main__':
    print()
    print("JSON JOB LOGGING EXAMPLES")
    print("=" * 60)
    print()

    # Clear existing log for clean demo
    logger = create_default_logger(Path('notes'))
    logger.clear_log()
    print("✓ Cleared existing logs for clean demo")
    print()

    # Run examples
    example_basic_logging()
    example_view_logs()
    example_json_structure()
    example_batch_logging()

    # Final stats
    example_view_logs()

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print()
    print(f"View the JSON log at: {logger.log_file}")
    print()
    print("Useful queries:")
    print("  # View all jobs")
    print(f"  cat {logger.log_file} | jq '.'")
    print()
    print("  # Count jobs by status")
    print(f"  cat {logger.log_file} | jq '[.[] | .success] | group_by(.) | map({{status: .[0], count: length}})'")
    print()
    print("  # Show failed jobs only")
    print(f"  cat {logger.log_file} | jq '[.[] | select(.success == false)]'")
    print()
    print("  # Average duration of successful jobs")
    print(f"  cat {logger.log_file} | jq '[.[] | select(.success == true) | .processing_duration] | add / length'")
    print()
