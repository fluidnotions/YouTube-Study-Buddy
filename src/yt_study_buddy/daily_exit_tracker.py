"""
Daily exit node tracker for recording successes and failures.

Tracks all exit node attempts for the current day and prevents
rotation to nodes that failed today.
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class DailyExitTracker:
    """Track daily exit node successes and failures."""

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize daily exit tracker.

        Args:
            data_dir: Directory for storing daily tracking data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.tracking_file = self.data_dir / "daily_exit_tracking.json"
        self.lock = threading.Lock()

        # In-memory tracking for current session
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.attempts: List[Dict] = []  # [{exitNodeIp, videoId, attempt, success, timestamp}]

        # Load existing data for today if available
        self._load_today_data()

    def _load_today_data(self):
        """Load existing tracking data for today's date."""
        if not self.tracking_file.exists():
            logger.debug(f"No existing daily tracking file, starting fresh")
            return

        try:
            with open(self.tracking_file, 'r') as f:
                data = json.load(f)

            # Check if data is for today
            if data.get('date') == self.today_date:
                self.attempts = data.get('attempts', [])
                logger.info(f"Loaded {len(self.attempts)} attempts from today's tracking")
            else:
                logger.info(f"Previous tracking was for {data.get('date')}, starting fresh for {self.today_date}")
                self.attempts = []

        except Exception as e:
            logger.error(f"Failed to load daily tracking: {e}")
            self.attempts = []

    def record_attempt(
        self,
        exit_ip: str,
        video_id: str,
        attempt: int,
        success: bool
    ):
        """
        Record an exit node attempt (success or failure).

        Args:
            exit_ip: Exit node IP address
            video_id: YouTube video ID being processed
            attempt: Attempt number (1-based)
            success: Whether the attempt succeeded
        """
        with self.lock:
            attempt_record = {
                'exitNodeIp': exit_ip,
                'videoId': video_id,
                'attempt': attempt,
                'success': success,
                'timestamp': datetime.now().isoformat()
            }

            self.attempts.append(attempt_record)

            status = "✓ success" if success else "✗ failure"
            logger.debug(f"Recorded attempt: {exit_ip} for {video_id} (attempt {attempt}) - {status}")

    def get_failed_ips_today(self) -> List[str]:
        """
        Get list of exit IPs that failed today.

        Returns:
            List of IP addresses that had failures today
        """
        with self.lock:
            failed_ips = set()
            for attempt in self.attempts:
                if not attempt['success']:
                    failed_ips.add(attempt['exitNodeIp'])

            return list(failed_ips)

    def has_failed_today(self, exit_ip: str) -> bool:
        """
        Check if an exit IP has any failures today.

        Args:
            exit_ip: Exit node IP to check

        Returns:
            True if this IP failed at least once today
        """
        with self.lock:
            for attempt in self.attempts:
                if attempt['exitNodeIp'] == exit_ip and not attempt['success']:
                    return True
            return False

    def get_stats(self) -> Dict:
        """
        Get statistics about today's attempts.

        Returns:
            Dictionary with success/failure counts and IP lists
        """
        with self.lock:
            total = len(self.attempts)
            successes = sum(1 for a in self.attempts if a['success'])
            failures = total - successes

            unique_ips = set(a['exitNodeIp'] for a in self.attempts)
            failed_ips = set(a['exitNodeIp'] for a in self.attempts if not a['success'])

            return {
                'date': self.today_date,
                'total_attempts': total,
                'successes': successes,
                'failures': failures,
                'success_rate': (successes / total * 100) if total > 0 else 0,
                'unique_ips_tried': len(unique_ips),
                'failed_ips_count': len(failed_ips),
                'failed_ips': list(failed_ips)
            }

    def save(self):
        """Save current tracking data to disk (thread-safe)."""
        with self.lock:
            data = {
                'date': self.today_date,
                'attempts': self.attempts
            }

            try:
                # Write to temp file first, then rename (atomic on Unix)
                temp_file = self.tracking_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(data, f, indent=2)

                temp_file.replace(self.tracking_file)
                logger.debug(f"Saved {len(self.attempts)} attempts to {self.tracking_file}")

            except Exception as e:
                logger.error(f"Failed to save daily tracking: {e}")

    def print_summary(self):
        """Print a summary of today's tracking."""
        stats = self.get_stats()

        logger.info(f"\n{'='*60}")
        logger.info(f"DAILY EXIT NODE TRACKING - {stats['date']}")
        logger.info(f"{'='*60}")
        logger.info(f"Total attempts: {stats['total_attempts']}")
        logger.success(f"Successes: {stats['successes']} ({stats['success_rate']:.1f}%)")
        logger.error(f"Failures: {stats['failures']}")
        logger.info(f"Unique IPs tried: {stats['unique_ips_tried']}")
        logger.warning(f"Failed IPs today: {stats['failed_ips_count']}")

        if stats['failed_ips']:
            logger.info("\nFailed IPs (blocked today):")
            for ip in stats['failed_ips']:
                logger.error(f"  ✗ {ip}")

        logger.info(f"{'='*60}\n")


# Global instance
_global_tracker: Optional[DailyExitTracker] = None
_tracker_lock = threading.Lock()


def get_daily_tracker() -> DailyExitTracker:
    """Get or create the global daily exit tracker instance."""
    global _global_tracker

    with _tracker_lock:
        if _global_tracker is None:
            _global_tracker = DailyExitTracker()
        return _global_tracker
