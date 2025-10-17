"""
Debug logging system for analyzing API responses and title fetching issues.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class DebugLogger:
    """File-based logger for debugging title fetching and API responses."""

    def __init__(self, log_dir: str = "debug_logs", enabled: bool = True):
        """
        Initialize debug logger.

        Args:
            log_dir: Directory for log files
            enabled: Enable/disable logging
        """
        self.enabled = enabled
        self.log_dir = Path(log_dir)

        if self.enabled:
            self.log_dir.mkdir(exist_ok=True)

            # Create session log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_log = self.log_dir / f"session_{timestamp}.log"
            self.api_log = self.log_dir / f"api_responses_{timestamp}.jsonl"

            # Setup Python logging
            self.logger = logging.getLogger('yt_study_buddy_debug')
            self.logger.setLevel(logging.DEBUG)

            # File handler
            fh = logging.FileHandler(self.session_log)
            fh.setLevel(logging.DEBUG)

            # Console handler (optional)
            ch = logging.StreamHandler()
            ch.setLevel(logging.WARNING)

            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)

            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

            self.logger.info(f"Debug logging session started: {timestamp}")
            self.logger.info(f"Session log: {self.session_log}")
            self.logger.info(f"API log: {self.api_log}")

    def log_title_fetch_attempt(
        self,
        video_id: str,
        attempt: int,
        max_retries: int,
        worker_id: Optional[int] = None
    ):
        """Log title fetch attempt."""
        if not self.enabled:
            return

        worker_label = f"Worker-{worker_id}" if worker_id is not None else "Main"
        self.logger.info(
            f"[{worker_label}] Fetching title for {video_id} "
            f"(attempt {attempt}/{max_retries})"
        )

    def log_api_response(
        self,
        video_id: str,
        url: str,
        status_code: int,
        response_data: Optional[Dict[str, Any]],
        error: Optional[str] = None,
        worker_id: Optional[int] = None,
        attempt: int = 1
    ):
        """
        Log detailed API response for analysis.

        Args:
            video_id: YouTube video ID
            url: API URL that was called
            status_code: HTTP status code
            response_data: Response JSON data (if successful)
            error: Error message (if failed)
            worker_id: Worker ID for parallel processing
            attempt: Retry attempt number
        """
        if not self.enabled:
            return

        timestamp = datetime.now().isoformat()
        worker_label = f"worker-{worker_id}" if worker_id is not None else "main"

        log_entry = {
            "timestamp": timestamp,
            "video_id": video_id,
            "worker": worker_label,
            "attempt": attempt,
            "url": url,
            "status_code": status_code,
            "success": status_code == 200 and response_data is not None,
            "response": response_data,
            "error": error
        }

        # Write to JSONL file for analysis
        with open(self.api_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Also log to main logger
        if log_entry['success']:
            title = response_data.get('title', 'NO_TITLE') if response_data else 'NO_DATA'
            self.logger.info(
                f"[{worker_label}] ✓ Title fetched for {video_id}: '{title}' "
                f"(attempt {attempt}, status {status_code})"
            )
        else:
            self.logger.warning(
                f"[{worker_label}] ✗ Title fetch failed for {video_id}: "
                f"status={status_code}, error={error} (attempt {attempt})"
            )

    def log_title_result(
        self,
        video_id: str,
        title: Optional[str],
        success: bool,
        total_attempts: int,
        worker_id: Optional[int] = None
    ):
        """
        Log final title fetch result.

        Args:
            video_id: YouTube video ID
            title: Retrieved title (or None if failed)
            success: Whether fetch was successful
            total_attempts: Total number of attempts made
            worker_id: Worker ID for parallel processing
        """
        if not self.enabled:
            return

        worker_label = f"Worker-{worker_id}" if worker_id is not None else "Main"

        if success:
            self.logger.info(
                f"[{worker_label}] FINAL: {video_id} → '{title}' "
                f"(succeeded after {total_attempts} attempt(s))"
            )
        else:
            self.logger.error(
                f"[{worker_label}] FINAL: {video_id} → FAILED "
                f"(all {total_attempts} attempts failed, using fallback)"
            )

    def log_circuit_rotation(
        self,
        connection_id: int,
        success: bool,
        worker_id: Optional[int] = None
    ):
        """Log Tor circuit rotation."""
        if not self.enabled:
            return

        worker_label = f"Worker-{worker_id}" if worker_id is not None else "Main"
        status = "SUCCESS" if success else "FAILED"
        self.logger.debug(
            f"[{worker_label}] Tor circuit rotation for connection #{connection_id}: {status}"
        )

    def log_exit_ip(
        self,
        connection_id: int,
        exit_ip: str,
        unique: bool,
        worker_id: Optional[int] = None
    ):
        """Log Tor exit IP."""
        if not self.enabled:
            return

        worker_label = f"Worker-{worker_id}" if worker_id is not None else "Main"
        uniqueness = "UNIQUE" if unique else "COLLISION"
        self.logger.debug(
            f"[{worker_label}] Connection #{connection_id} exit IP: {exit_ip} ({uniqueness})"
        )

    def analyze_logs(self):
        """
        Analyze logged API responses to identify patterns.

        Returns summary of successes/failures by video, worker, attempt.
        """
        if not self.enabled or not self.api_log.exists():
            print("No API logs to analyze")
            return

        print(f"\n{'='*60}")
        print("API RESPONSE ANALYSIS")
        print(f"{'='*60}\n")

        responses = []
        with open(self.api_log, 'r', encoding='utf-8') as f:
            for line in f:
                responses.append(json.loads(line))

        if not responses:
            print("No responses logged yet")
            return

        # Overall stats
        total = len(responses)
        successes = sum(1 for r in responses if r['success'])
        failures = total - successes

        print(f"Total API calls: {total}")
        print(f"Successes: {successes} ({successes/total*100:.1f}%)")
        print(f"Failures: {failures} ({failures/total*100:.1f}%)")
        print()

        # By video
        print("By Video:")
        videos = {}
        for r in responses:
            vid = r['video_id']
            if vid not in videos:
                videos[vid] = {'success': 0, 'failure': 0, 'attempts': []}
            if r['success']:
                videos[vid]['success'] += 1
            else:
                videos[vid]['failure'] += 1
            videos[vid]['attempts'].append(r['attempt'])

        for vid, stats in videos.items():
            total_attempts = stats['success'] + stats['failure']
            print(f"  {vid}: {stats['success']}/{total_attempts} successful")
            if stats['failure'] > 0:
                print(f"    → Failed attempts: {stats['failure']}")
        print()

        # By worker
        print("By Worker:")
        workers = {}
        for r in responses:
            worker = r['worker']
            if worker not in workers:
                workers[worker] = {'success': 0, 'failure': 0}
            if r['success']:
                workers[worker]['success'] += 1
            else:
                workers[worker]['failure'] += 1

        for worker, stats in workers.items():
            total_attempts = stats['success'] + stats['failure']
            success_rate = stats['success'] / total_attempts * 100
            print(f"  {worker}: {stats['success']}/{total_attempts} ({success_rate:.1f}% success)")
        print()

        # By attempt number
        print("By Attempt Number:")
        attempts = {}
        for r in responses:
            att = r['attempt']
            if att not in attempts:
                attempts[att] = {'success': 0, 'failure': 0}
            if r['success']:
                attempts[att]['success'] += 1
            else:
                attempts[att]['failure'] += 1

        for att in sorted(attempts.keys()):
            stats = attempts[att]
            total_attempts = stats['success'] + stats['failure']
            success_rate = stats['success'] / total_attempts * 100
            print(f"  Attempt {att}: {stats['success']}/{total_attempts} ({success_rate:.1f}% success)")
        print()

        # Failed responses details
        failed = [r for r in responses if not r['success']]
        if failed:
            print(f"Failed Responses Details ({len(failed)} total):")
            for r in failed[:10]:  # Show first 10
                print(f"  {r['video_id']} (attempt {r['attempt']}, worker {r['worker']})")
                print(f"    Status: {r['status_code']}, Error: {r['error']}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
        print()

        print(f"Full logs: {self.session_log}")
        print(f"API data: {self.api_log}")
        print(f"{'='*60}\n")


# Global logger instance
_global_logger: Optional[DebugLogger] = None


def get_logger(enabled: bool = True) -> DebugLogger:
    """Get or create global debug logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = DebugLogger(enabled=enabled)
    return _global_logger


def enable_debug_logging():
    """Enable debug logging (call at start of program)."""
    global _global_logger
    _global_logger = DebugLogger(enabled=True)
    return _global_logger


def disable_debug_logging():
    """Disable debug logging."""
    global _global_logger
    if _global_logger:
        _global_logger.enabled = False
