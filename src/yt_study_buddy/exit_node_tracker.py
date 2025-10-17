"""
Persistent exit node usage tracker with 1-hour cooldown.

Ensures exit nodes aren't reused within 1 hour, even across app restarts.
"""
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set


def humanize_timedelta(td: timedelta) -> str:
    """
    Convert timedelta to human-readable format.

    Examples:
        - "2 months 3 days ago"
        - "5 hours ago"
        - "just now"

    Args:
        td: Time delta to humanize

    Returns:
        Human-readable string
    """
    seconds = int(td.total_seconds())

    if seconds < 60:
        return "just now"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"

    months = days // 30
    remaining_days = days % 30

    if months < 12:
        if remaining_days > 0:
            return f"{months} month{'s' if months != 1 else ''} {remaining_days} day{'s' if remaining_days != 1 else ''} ago"
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = months // 12
    remaining_months = months % 12

    if remaining_months > 0:
        return f"{years} year{'s' if years != 1 else ''} {remaining_months} month{'s' if remaining_months != 1 else ''} ago"
    return f"{years} year{'s' if years != 1 else ''} ago"


class ExitNodeTracker:
    """
    Thread-safe persistent tracker for Tor exit node usage.

    Maintains a JSON log of exit IP usage with timestamps to enforce
    a 1-hour cooldown period between uses of the same exit node.

    Features:
    - Persistent across app restarts
    - Thread-safe for parallel processing
    - Automatic cleanup of expired entries
    - 1-hour cooldown enforcement

    File format (exit_nodes.json):
    {
        "185.220.101.1": {
            "last_used": "2025-10-17T14:30:45.123456",
            "first_seen": "2025-10-17T12:15:30.000000",
            "use_count": 5,
            "last_worker_id": 2
        },
        ...
    }
    """

    def __init__(
        self,
        log_path: Optional[Path] = None,
        cooldown_hours: float = 1.0,
        auto_cleanup: bool = True
    ):
        """
        Initialize exit node tracker.

        Args:
            log_path: Path to JSON log file (default: notes/exit_nodes.json)
            cooldown_hours: Hours to wait before reusing an exit node (default: 1.0)
            auto_cleanup: Automatically cleanup expired entries (default: True)
        """
        self.log_path = log_path or Path("notes/exit_nodes.json")
        self.cooldown_seconds = cooldown_hours * 3600
        self.auto_cleanup = auto_cleanup
        self._lock = threading.Lock()

        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data
        self._data: Dict[str, Dict] = self._load()

        print(f"📊 ExitNodeTracker initialized")
        print(f"   Log file: {self.log_path}")
        print(f"   Cooldown: {cooldown_hours} hour(s)")
        print(f"   Tracked nodes: {len(self._data)}")

    def _load(self) -> Dict[str, Dict]:
        """Load exit node data from JSON file."""
        if not self.log_path.exists():
            return {}

        try:
            with open(self.log_path, 'r') as f:
                data = json.load(f)

            # Validate structure
            if not isinstance(data, dict):
                print(f"⚠️  Invalid log format, starting fresh")
                return {}

            return data

        except json.JSONDecodeError as e:
            print(f"⚠️  Corrupted log file, starting fresh: {e}")
            return {}

        except Exception as e:
            print(f"⚠️  Error loading log: {e}")
            return {}

    def _save(self) -> None:
        """Save exit node data to JSON file (must be called with lock held)."""
        try:
            # Write atomically: write to temp file, then rename
            temp_path = self.log_path.with_suffix('.json.tmp')

            with open(temp_path, 'w') as f:
                json.dump(self._data, f, indent=2, sort_keys=True)

            # Atomic rename
            temp_path.replace(self.log_path)

        except Exception as e:
            print(f"⚠️  Error saving log: {e}")

    def _cleanup_expired(self) -> int:
        """
        Remove expired entries (older than cooldown period).

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.cooldown_seconds)

        expired_ips = []
        for ip, info in self._data.items():
            try:
                last_used = datetime.fromisoformat(info['last_used'])
                if last_used < cutoff:
                    expired_ips.append(ip)
            except (KeyError, ValueError):
                # Invalid entry, remove it
                expired_ips.append(ip)

        for ip in expired_ips:
            del self._data[ip]

        return len(expired_ips)

    def is_available(self, exit_ip: str) -> bool:
        """
        Check if an exit IP is available (not in cooldown).

        Args:
            exit_ip: Exit IP address to check

        Returns:
            True if IP is available (not used recently), False if in cooldown
        """
        with self._lock:
            if exit_ip not in self._data:
                return True  # Never used, available

            try:
                last_used = datetime.fromisoformat(self._data[exit_ip]['last_used'])
                elapsed = (datetime.now() - last_used).total_seconds()
                return elapsed >= self.cooldown_seconds

            except (KeyError, ValueError):
                # Invalid entry, consider it available
                return True

    def get_cooldown_remaining(self, exit_ip: str) -> Optional[float]:
        """
        Get remaining cooldown time in seconds for an exit IP.

        Args:
            exit_ip: Exit IP address

        Returns:
            Remaining seconds in cooldown, or None if available
        """
        with self._lock:
            if exit_ip not in self._data:
                return None

            try:
                last_used = datetime.fromisoformat(self._data[exit_ip]['last_used'])
                elapsed = (datetime.now() - last_used).total_seconds()
                remaining = self.cooldown_seconds - elapsed
                return max(0, remaining) if remaining > 0 else None

            except (KeyError, ValueError):
                return None

    def get_time_since_last_use(self, exit_ip: str) -> Optional[str]:
        """
        Get human-readable time since IP was last used.

        Args:
            exit_ip: Exit IP address

        Returns:
            Human-readable string like "2 hours ago" or None if never used
        """
        with self._lock:
            if exit_ip not in self._data:
                return None

            try:
                last_used = datetime.fromisoformat(self._data[exit_ip]['last_used'])
                time_since = datetime.now() - last_used
                return humanize_timedelta(time_since)

            except (KeyError, ValueError):
                return None

    def record_use(
        self,
        exit_ip: str,
        worker_id: Optional[int] = None,
        force: bool = False
    ) -> bool:
        """
        Record usage of an exit IP.

        Args:
            exit_ip: Exit IP address being used
            worker_id: Worker ID using this exit
            force: If True, record even if in cooldown (default: False)

        Returns:
            True if recorded successfully, False if IP is in cooldown and force=False
        """
        with self._lock:
            # Check cooldown
            if not force and not self.is_available(exit_ip):
                remaining = self.get_cooldown_remaining(exit_ip)
                print(f"⚠️  Exit IP {exit_ip} still in cooldown "
                      f"({remaining:.0f}s remaining)")
                return False

            now = datetime.now().isoformat()

            if exit_ip in self._data:
                # Update existing entry
                self._data[exit_ip]['last_used'] = now
                self._data[exit_ip]['use_count'] = self._data[exit_ip].get('use_count', 0) + 1
                if worker_id is not None:
                    self._data[exit_ip]['last_worker_id'] = worker_id
            else:
                # New entry
                self._data[exit_ip] = {
                    'first_seen': now,
                    'last_used': now,
                    'use_count': 1,
                    'last_worker_id': worker_id
                }

            # Auto-cleanup expired entries
            if self.auto_cleanup:
                self._cleanup_expired()

            # Save to disk
            self._save()

            return True

    def get_available_ips(self, candidate_ips: List[str]) -> List[str]:
        """
        Filter a list of candidate IPs to only available ones.

        Args:
            candidate_ips: List of IP addresses to check

        Returns:
            List of IPs that are not in cooldown
        """
        return [ip for ip in candidate_ips if self.is_available(ip)]

    def get_unavailable_ips(self) -> Set[str]:
        """
        Get set of all IPs currently in cooldown.

        Returns:
            Set of IP addresses in cooldown period
        """
        with self._lock:
            now = datetime.now()
            unavailable = set()

            for ip, info in self._data.items():
                try:
                    last_used = datetime.fromisoformat(info['last_used'])
                    elapsed = (now - last_used).total_seconds()
                    if elapsed < self.cooldown_seconds:
                        unavailable.add(ip)
                except (KeyError, ValueError):
                    pass

            return unavailable

    def get_stats(self) -> Dict:
        """
        Get tracker statistics.

        Returns:
            Dictionary with tracking statistics
        """
        with self._lock:
            unavailable = self.get_unavailable_ips()

            stats = {
                'total_tracked': len(self._data),
                'in_cooldown': len(unavailable),
                'available': len(self._data) - len(unavailable),
                'cooldown_hours': self.cooldown_seconds / 3600,
                'log_path': str(self.log_path)
            }

            # Add most recently used
            if self._data:
                sorted_by_time = sorted(
                    self._data.items(),
                    key=lambda x: x[1].get('last_used', ''),
                    reverse=True
                )
                stats['most_recent'] = {
                    'ip': sorted_by_time[0][0],
                    'last_used': sorted_by_time[0][1].get('last_used'),
                    'use_count': sorted_by_time[0][1].get('use_count', 0)
                }

            return stats

    def cleanup(self) -> int:
        """
        Manually trigger cleanup of expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            removed = self._cleanup_expired()
            if removed > 0:
                self._save()
            return removed

    def reset(self) -> None:
        """Clear all tracked data (use with caution!)."""
        with self._lock:
            self._data.clear()
            self._save()
            print("⚠️  Tracker reset - all data cleared")


# Global singleton instance (lazy initialized)
_tracker_instance: Optional[ExitNodeTracker] = None
_tracker_lock = threading.Lock()


def get_tracker(
    log_path: Optional[Path] = None,
    cooldown_hours: float = 1.0
) -> ExitNodeTracker:
    """
    Get or create the global exit node tracker instance.

    Args:
        log_path: Path to JSON log file (only used on first call)
        cooldown_hours: Cooldown period in hours (only used on first call)

    Returns:
        Global ExitNodeTracker instance
    """
    global _tracker_instance

    with _tracker_lock:
        if _tracker_instance is None:
            _tracker_instance = ExitNodeTracker(
                log_path=log_path,
                cooldown_hours=cooldown_hours
            )
        return _tracker_instance
