"""
Job logging system for tracking video processing results.

Appends job results to a JSON array file with complete metadata and errors.
"""
import json
import threading
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .video_job import VideoProcessingJob


class JobLogger:
    """
    Thread-safe logger for video processing jobs.

    Appends job results to a JSON array file, maintaining complete history
    of all processed videos with errors, timings, and file paths.
    """

    def __init__(self, log_file: Path):
        """
        Initialize job logger.

        Args:
            log_file: Path to JSON log file (will be created if doesn't exist)
        """
        self.log_file = Path(log_file)
        self._lock = threading.Lock()
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Create log file with empty array if it doesn't exist."""
        if not self.log_file.exists():
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_jobs([])

    def _read_jobs(self) -> List[dict]:
        """Read all jobs from log file."""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_jobs(self, jobs: List[dict]):
        """Write jobs array to log file."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

    def log_job(self, job: VideoProcessingJob):
        """
        Append job to log file.

        Thread-safe: Uses lock to prevent concurrent writes.

        Args:
            job: Completed VideoProcessingJob to log
        """
        with self._lock:
            jobs = self._read_jobs()
            job_data = job.to_json()
            job_data['logged_at'] = datetime.now().isoformat()
            jobs.append(job_data)
            self._write_jobs(jobs)

    def log_jobs_batch(self, jobs: List[VideoProcessingJob]):
        """
        Append multiple jobs to log file in single write.

        More efficient than calling log_job() multiple times.

        Args:
            jobs: List of VideoProcessingJob instances to log
        """
        with self._lock:
            existing_jobs = self._read_jobs()
            logged_at = datetime.now().isoformat()

            for job in jobs:
                job_data = job.to_json()
                job_data['logged_at'] = logged_at
                existing_jobs.append(job_data)

            self._write_jobs(existing_jobs)

    def get_all_jobs(self) -> List[dict]:
        """
        Read all logged jobs.

        Returns:
            List of job dictionaries
        """
        with self._lock:
            return self._read_jobs()

    def get_failed_jobs(self) -> List[dict]:
        """
        Get all failed jobs.

        Returns:
            List of job dictionaries where success=False
        """
        with self._lock:
            jobs = self._read_jobs()
            return [j for j in jobs if not j.get('success', False)]

    def get_successful_jobs(self) -> List[dict]:
        """
        Get all successful jobs.

        Returns:
            List of job dictionaries where success=True
        """
        with self._lock:
            jobs = self._read_jobs()
            return [j for j in jobs if j.get('success', False)]

    def get_jobs_by_stage(self, stage: str) -> List[dict]:
        """
        Get jobs by processing stage.

        Args:
            stage: Stage name (e.g., 'completed', 'failed', 'transcript_fetched')

        Returns:
            List of job dictionaries at that stage
        """
        with self._lock:
            jobs = self._read_jobs()
            return [j for j in jobs if j.get('stage') == stage]

    def get_statistics(self) -> dict:
        """
        Get summary statistics across all logged jobs.

        Returns:
            Dictionary with counts, averages, and error summaries
        """
        with self._lock:
            jobs = self._read_jobs()

            if not jobs:
                return {
                    'total_jobs': 0,
                    'successful': 0,
                    'failed': 0,
                    'average_duration': None,
                    'error_types': {}
                }

            successful = [j for j in jobs if j.get('success', False)]
            failed = [j for j in jobs if not j.get('success', False)]

            # Calculate average duration for successful jobs
            durations = [j['processing_duration'] for j in successful
                        if j.get('processing_duration')]
            avg_duration = sum(durations) / len(durations) if durations else None

            # Count error types
            error_types = {}
            for job in failed:
                error = job.get('error', 'Unknown error')
                error_type = error.split(':')[0] if ':' in error else error
                error_types[error_type] = error_types.get(error_type, 0) + 1

            return {
                'total_jobs': len(jobs),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': len(successful) / len(jobs) if jobs else 0,
                'average_duration': avg_duration,
                'total_files_created': sum(j.get('total_files', 0) for j in successful),
                'error_types': error_types,
                'stages': {
                    stage: len([j for j in jobs if j.get('stage') == stage])
                    for stage in set(j.get('stage') for j in jobs)
                }
            }

    def clear_log(self):
        """Clear all logged jobs (reset to empty array)."""
        with self._lock:
            self._write_jobs([])

    def export_csv(self, output_file: Path):
        """
        Export jobs to CSV format.

        Args:
            output_file: Path to CSV file to create
        """
        import csv

        with self._lock:
            jobs = self._read_jobs()

            if not jobs:
                return

            # Define fields for CSV
            fields = [
                'video_id', 'video_title', 'url', 'subject', 'worker_id',
                'stage', 'success', 'error', 'processing_duration',
                'has_notes', 'has_assessment', 'total_files', 'logged_at'
            ]

            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()

                for job in jobs:
                    row = {field: job.get(field, '') for field in fields}
                    writer.writerow(row)


def create_default_logger(output_dir: Optional[Path] = None) -> JobLogger:
    """
    Create a JobLogger with default log file location.

    Args:
        output_dir: Base output directory (defaults to ./notes)

    Returns:
        JobLogger instance
    """
    if output_dir is None:
        output_dir = Path('notes')

    log_file = output_dir / 'processing_log.json'
    return JobLogger(log_file)
