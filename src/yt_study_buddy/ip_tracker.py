"""
IP attempt tracking for Tor exit nodes.

Logs each retry attempt with the exit IP used, timestamp, and error details.
"""
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class IPAttemptTracker:
    """Track IP addresses used during retry attempts."""

    def __init__(self, log_file: Path = None):
        """
        Initialize IP attempt tracker.

        Args:
            log_file: Path to JSON log file (default: notes/ip_attempts_log.json)
        """
        if log_file is None:
            # Default to notes/ip_attempts_log.json
            log_file = Path(__file__).parent.parent.parent / "notes" / "ip_attempts_log.json"

        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.log_file.exists():
            self._write_log([])

    def _read_log(self) -> List[Dict[str, Any]]:
        """Read existing log entries."""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return []

    def _write_log(self, entries: List[Dict[str, Any]]):
        """Write log entries to file."""
        with open(self.log_file, 'w') as f:
            json.dump(entries, f, indent=2)

    def log_attempt(
        self,
        ip: str,
        status: str,
        job_ref: str,
        retry_attempt: int,
        error: Optional[str] = None,
        method: str = "tor"
    ) -> None:
        """
        Log a retry attempt with IP and error details.

        Args:
            ip: Exit IP address used
            status: Status of attempt ('success', 'failed', 'blocked')
            job_ref: Video ID or job reference
            retry_attempt: Retry attempt number (1-indexed)
            error: Error message if failed
            method: Method used ('tor' or 'ytdlp')
        """
        entries = self._read_log()

        entry = {
            "ip": ip,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": status,
            "jobRef": job_ref,
            "retryAttempt": retry_attempt,
            "method": method
        }

        if error:
            entry["error"] = error

        entries.append(entry)
        self._write_log(entries)

    def get_recent_attempts(
        self,
        job_ref: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent attempts, optionally filtered by job.

        Args:
            job_ref: Optional video ID to filter by
            limit: Maximum number of entries to return

        Returns:
            List of attempt entries (most recent first)
        """
        entries = self._read_log()

        if job_ref:
            entries = [e for e in entries if e.get("jobRef") == job_ref]

        # Return most recent first
        return list(reversed(entries[-limit:]))

    def get_ip_stats(self) -> Dict[str, Any]:
        """
        Get statistics about IP usage.

        Returns:
            Dictionary with IP usage statistics
        """
        entries = self._read_log()

        if not entries:
            return {
                "total_attempts": 0,
                "unique_ips": 0,
                "blocked_ips": 0,
                "success_rate": 0.0
            }

        ips = [e.get("ip") for e in entries if e.get("ip")]
        blocked_ips = [
            e.get("ip") for e in entries
            if e.get("status") in ["failed", "blocked"] and e.get("ip")
        ]
        successful = [e for e in entries if e.get("status") == "success"]

        return {
            "total_attempts": len(entries),
            "unique_ips": len(set(ips)),
            "blocked_ips": len(set(blocked_ips)),
            "success_rate": len(successful) / len(entries) if entries else 0.0,
            "most_recent_ip": entries[-1].get("ip") if entries else None,
            "most_recent_status": entries[-1].get("status") if entries else None
        }

    def clear_old_entries(self, days: int = 7):
        """
        Remove entries older than specified days.

        Args:
            days: Number of days to keep (default: 7)
        """
        entries = self._read_log()
        cutoff_timestamp = time.time() - (days * 24 * 60 * 60)

        filtered = []
        for entry in entries:
            try:
                timestamp_str = entry.get("timestamp", "")
                # Parse ISO timestamp
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
                entry_timestamp = dt.timestamp()

                if entry_timestamp >= cutoff_timestamp:
                    filtered.append(entry)
            except (ValueError, AttributeError):
                # Keep entries with invalid timestamps
                filtered.append(entry)

        self._write_log(filtered)
        removed_count = len(entries) - len(filtered)
        if removed_count > 0:
            print(f"Removed {removed_count} old entries from IP log")


# Global tracker instance
_tracker_instance: Optional[IPAttemptTracker] = None


def get_ip_tracker(log_file: Optional[Path] = None) -> IPAttemptTracker:
    """
    Get global IP tracker instance (singleton).

    Args:
        log_file: Optional custom log file path

    Returns:
        IPAttemptTracker instance
    """
    global _tracker_instance

    if _tracker_instance is None or log_file is not None:
        _tracker_instance = IPAttemptTracker(log_file)

    return _tracker_instance
