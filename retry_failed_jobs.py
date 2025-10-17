#!/usr/bin/env python3
"""
Retry failed video processing jobs.

Loads failed jobs from processing_log.json, classifies them as retryable or not,
and retries retryable jobs that haven't been attempted recently.

Usage:
    # Check status of failed jobs
    python retry_failed_jobs.py --status

    # Retry all eligible failed jobs once
    python retry_failed_jobs.py

    # Run continuously, retrying every 15 minutes
    python retry_failed_jobs.py --watch

    # Custom retry interval
    python retry_failed_jobs.py --watch --interval 30
"""
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.yt_study_buddy.video_job import VideoProcessingJob, create_job_from_url
from src.yt_study_buddy.processing_pipeline import process_video_job
from src.yt_study_buddy.video_processor import VideoProcessor
from src.yt_study_buddy.study_notes_generator import StudyNotesGenerator
from src.yt_study_buddy.assessment_generator import AssessmentGenerator
from src.yt_study_buddy.obsidian_linker import ObsidianLinker
from src.yt_study_buddy.job_logger import JobLogger


class RetryScheduler:
    """Manages retrying failed video processing jobs."""

    def __init__(self, log_path: str = "notes/processing_log.json", retry_interval_minutes: int = 15):
        """
        Initialize retry scheduler.

        Args:
            log_path: Path to processing log JSON file
            retry_interval_minutes: Minutes to wait between retries (default: 15)
        """
        self.log_path = Path(log_path)
        self.retry_interval_minutes = retry_interval_minutes
        self.retry_interval_seconds = retry_interval_minutes * 60

    def load_failed_jobs(self) -> List[Dict[str, Any]]:
        """Load failed jobs from processing log."""
        if not self.log_path.exists():
            print(f"Processing log not found: {self.log_path}")
            return []

        with open(self.log_path) as f:
            all_jobs = json.load(f)

        # Filter to failed jobs only
        failed = [j for j in all_jobs if not j.get('success', False)]
        return failed

    def classify_failed_jobs(self, failed_jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Classify failed jobs into retryable and non-retryable.

        Returns:
            Dictionary with 'retryable' and 'non_retryable' lists
        """
        retryable = []
        non_retryable = []

        for job_data in failed_jobs:
            error = job_data.get('error', '').lower()

            # Check if explicitly marked as non-retryable
            if job_data.get('is_retryable') is False:
                non_retryable.append(job_data)
                continue

            # Classify based on error message
            non_retryable_patterns = [
                'no subtitle',
                'no transcript',
                'video unavailable',
                'video is private',
                'deleted',
                'invalid video id',
                'members-only'
            ]

            is_retryable = True
            for pattern in non_retryable_patterns:
                if pattern in error:
                    is_retryable = False
                    break

            if is_retryable:
                retryable.append(job_data)
            else:
                non_retryable.append(job_data)

        return {
            'retryable': retryable,
            'non_retryable': non_retryable
        }

    def get_jobs_ready_for_retry(self, retryable_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter retryable jobs to those ready for retry now.

        Args:
            retryable_jobs: List of retryable job data dicts

        Returns:
            List of jobs that should be retried now
        """
        ready = []
        current_time = time.time()

        for job_data in retryable_jobs:
            next_retry_time = job_data.get('next_retry_time')

            # If never retried, schedule it for immediate retry
            if next_retry_time is None:
                ready.append(job_data)
            # If retry time has passed, it's ready
            elif current_time >= next_retry_time:
                ready.append(job_data)

        return ready

    def schedule_retry(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update job data with retry scheduling info.

        Args:
            job_data: Job data dictionary

        Returns:
            Updated job data with retry fields
        """
        current_time = time.time()

        # Increment retry count
        retry_count = job_data.get('retry_count', 0) + 1

        # Schedule next retry
        next_retry_time = current_time + self.retry_interval_seconds

        job_data['retry_count'] = retry_count
        job_data['last_retry_time'] = current_time
        job_data['next_retry_time'] = next_retry_time
        job_data['is_retryable'] = True

        return job_data

    def print_status(self):
        """Print status of all failed jobs."""
        failed_jobs = self.load_failed_jobs()

        if not failed_jobs:
            print("✓ No failed jobs found")
            return

        classified = self.classify_failed_jobs(failed_jobs)
        retryable = classified['retryable']
        non_retryable = classified['non_retryable']
        ready = self.get_jobs_ready_for_retry(retryable)

        print(f"\n📊 FAILED JOBS STATUS")
        print(f"{'='*60}")
        print(f"Total failed:        {len(failed_jobs)}")
        print(f"Retryable:           {len(retryable)}")
        print(f"Non-retryable:       {len(non_retryable)}")
        print(f"Ready to retry now:  {len(ready)}")
        print()

        if retryable:
            print(f"🔄 RETRYABLE JOBS ({len(retryable)})")
            print(f"{'-'*60}")
            for job_data in retryable:
                video_id = job_data['video_id']
                error = job_data.get('error', 'Unknown error')[:60]
                retry_count = job_data.get('retry_count', 0)
                next_retry = job_data.get('next_retry_time')

                print(f"  {video_id}")
                print(f"    Error: {error}")
                print(f"    Retries: {retry_count}")

                if next_retry:
                    time_until = next_retry - time.time()
                    if time_until > 0:
                        mins = int(time_until / 60)
                        print(f"    Next retry: in {mins} minutes")
                    else:
                        print(f"    Next retry: READY NOW")
                else:
                    print(f"    Next retry: Not yet scheduled")
                print()

        if non_retryable:
            print(f"❌ NON-RETRYABLE JOBS ({len(non_retryable)})")
            print(f"{'-'*60}")
            for job_data in non_retryable:
                video_id = job_data['video_id']
                error = job_data.get('error', 'Unknown error')[:80]
                print(f"  {video_id}: {error}")
            print()

    def retry_job(self, job_data: Dict[str, Any], components: Dict) -> bool:
        """
        Retry a single failed job.

        Args:
            job_data: Job data from processing log
            components: Processing components dict

        Returns:
            True if retry succeeded, False otherwise
        """
        # Create new job from logged data
        job = create_job_from_url(
            url=job_data['url'],
            video_id=job_data['video_id'],
            subject=job_data.get('subject'),
            worker_id=0  # Single-threaded retry
        )

        # Restore retry metadata
        job.retry_count = job_data.get('retry_count', 0)
        job.last_retry_time = job_data.get('last_retry_time')
        job.next_retry_time = job_data.get('next_retry_time')
        job.is_retryable = job_data.get('is_retryable', True)

        print(f"\n🔄 Retrying: {job.video_id}")
        print(f"   Attempt #{job.retry_count + 1}")

        # Process the job
        processed_job = process_video_job(job, components)

        return processed_job.success

    def retry_all_ready(self):
        """Retry all jobs that are ready for retry."""
        failed_jobs = self.load_failed_jobs()
        classified = self.classify_failed_jobs(failed_jobs)
        retryable = classified['retryable']
        ready = self.get_jobs_ready_for_retry(retryable)

        if not ready:
            print("No jobs ready for retry at this time")
            return

        print(f"\n🔄 RETRYING {len(ready)} JOBS")
        print(f"{'='*60}")

        # Setup processing components
        components = self._setup_components()

        successes = 0
        failures = 0

        for job_data in ready:
            # Schedule retry metadata before attempt
            job_data = self.schedule_retry(job_data)

            # Attempt retry
            success = self.retry_job(job_data, components)

            if success:
                successes += 1
            else:
                failures += 1

            # Small delay between retries to avoid rate limiting
            if job_data != ready[-1]:  # Not the last one
                print(f"  Waiting 10 seconds before next retry...")
                time.sleep(10)

        print(f"\n{'='*60}")
        print(f"✓ Successful: {successes}")
        print(f"✗ Failed:     {failures}")
        print(f"{'='*60}\n")

    def watch(self):
        """Run continuously, retrying failed jobs every interval."""
        print(f"👁️  WATCHING FOR FAILED JOBS")
        print(f"Retry interval: {self.retry_interval_minutes} minutes")
        print(f"Press Ctrl+C to stop\n")

        try:
            iteration = 0
            while True:
                iteration += 1
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Check #{iteration}")

                self.retry_all_ready()

                print(f"Sleeping for {self.retry_interval_minutes} minutes...")
                time.sleep(self.retry_interval_seconds)

        except KeyboardInterrupt:
            print("\n\nStopped watching. Goodbye!")

    def _setup_components(self) -> Dict:
        """Setup processing components."""
        video_processor = VideoProcessor("tor")
        notes_generator = StudyNotesGenerator()

        # Setup assessment generator with Claude client
        assessment_generator = None
        if notes_generator.client:  # Reuse Claude client from notes generator
            assessment_generator = AssessmentGenerator(notes_generator.client)

        obsidian_linker = ObsidianLinker()
        job_logger = JobLogger(log_file=str(self.log_path))

        return {
            'video_processor': video_processor,
            'notes_generator': notes_generator,
            'assessment_generator': assessment_generator,
            'obsidian_linker': obsidian_linker,
            'job_logger': job_logger,
            'pdf_exporter': None,  # Disabled for retries
            'output_dir': Path("notes"),
            'filename_sanitizer': VideoProcessor.sanitize_filename
        }


def main():
    parser = argparse.ArgumentParser(description="Retry failed video processing jobs")
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show status of failed jobs without retrying'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Run continuously, retrying every interval'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=15,
        help='Retry interval in minutes (default: 15)'
    )
    parser.add_argument(
        '--log',
        default='notes/processing_log.json',
        help='Path to processing log (default: notes/processing_log.json)'
    )

    args = parser.parse_args()

    scheduler = RetryScheduler(
        log_path=args.log,
        retry_interval_minutes=args.interval
    )

    if args.status:
        scheduler.print_status()
    elif args.watch:
        scheduler.watch()
    else:
        # One-time retry
        scheduler.retry_all_ready()


if __name__ == '__main__':
    main()
