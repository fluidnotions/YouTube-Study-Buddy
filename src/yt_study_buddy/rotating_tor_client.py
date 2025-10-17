"""
Rotating Tor HTTP client that ensures fresh exit IPs for YouTube requests.

Automatically rotates Tor circuit and validates exit IP hasn't been used recently
before making YouTube API calls. Enforces 24-hour cooldown on exit IPs.
"""
import time
import requests
from typing import Optional, Dict, Any
from stem import Signal
from stem.control import Controller

from .exit_node_tracker import get_tracker


class RotatingTorClient:
    """
    HTTP client that routes through Tor with automatic exit IP rotation.

    Ensures each YouTube request uses a fresh exit IP that hasn't been used
    in the last 24 hours, dramatically improving success rate.

    Features:
    - Automatic circuit rotation when exit IP is in cooldown
    - 24-hour exit IP cooldown (configurable)
    - Validates exit IP before making request
    - Retries with new exit IP if current one is blocked
    - Compatible with requests.Session interface

    Usage:
        ```python
        client = RotatingTorClient(cooldown_hours=24)

        # Automatically rotates to fresh exit IP
        response = client.get('https://youtube.com/api/...')
        ```
    """

    def __init__(
        self,
        tor_host: str = '127.0.0.1',
        tor_port: int = 9050,
        control_port: int = 9051,
        tor_password: Optional[str] = None,
        cooldown_hours: float = 24.0,
        max_rotation_attempts: int = 5
    ):
        """
        Initialize rotating Tor client.

        Args:
            tor_host: Tor SOCKS proxy host (default: 127.0.0.1)
            tor_port: Tor SOCKS proxy port (default: 9050)
            control_port: Tor control port (default: 9051)
            tor_password: Tor control password (default: None)
            cooldown_hours: Hours to wait before reusing exit IP (default: 24)
            max_rotation_attempts: Max rotations to find fresh IP (default: 5)
        """
        self.tor_host = tor_host
        self.tor_port = tor_port
        self.control_port = control_port
        self.tor_password = tor_password
        self.cooldown_hours = cooldown_hours
        self.max_rotation_attempts = max_rotation_attempts

        # Initialize exit node tracker with 24-hour cooldown
        self.tracker = get_tracker(cooldown_hours=cooldown_hours)

        # Create requests session configured for Tor
        self.session = requests.Session()
        self.session.proxies = {
            'http': f'socks5h://{tor_host}:{tor_port}',
            'https': f'socks5h://{tor_host}:{tor_port}'
        }

        self.current_exit_ip: Optional[str] = None

    def _get_exit_ip(self) -> str:
        """
        Get current Tor exit IP.

        Returns:
            Exit IP address
        """
        try:
            response = self.session.get(
                'https://api.ipify.org?format=json',
                timeout=10
            )
            return response.json()['ip']
        except Exception as e:
            raise RuntimeError(f"Failed to get exit IP: {e}")

    def _rotate_circuit(self):
        """Rotate Tor circuit to get new exit IP."""
        try:
            with Controller.from_port(
                address=self.tor_host,
                port=self.control_port
            ) as controller:
                if self.tor_password:
                    controller.authenticate(password=self.tor_password)
                else:
                    controller.authenticate()

                # Send NEWNYM signal
                controller.signal(Signal.NEWNYM)

                # Wait for Tor to be ready
                wait_time = controller.get_newnym_wait()
                if wait_time > 0:
                    print(f"  Waiting {wait_time:.0f}s for Tor cooldown...")
                    time.sleep(wait_time)
                else:
                    # Default wait if no cooldown
                    time.sleep(2)

        except Exception as e:
            print(f"⚠️  Circuit rotation failed: {e}")
            time.sleep(2)  # Wait anyway

    def _ensure_fresh_exit_ip(self, force_rotation: bool = False) -> str:
        """
        Ensure current exit IP is fresh (not in cooldown).

        Rotates circuit as needed until a fresh IP is obtained.

        Args:
            force_rotation: Force rotation even if current IP is fresh

        Returns:
            Fresh exit IP address

        Raises:
            RuntimeError: If unable to get fresh IP after max attempts
        """
        for attempt in range(self.max_rotation_attempts):
            # Get current exit IP
            exit_ip = self._get_exit_ip()

            # Check if IP is available (not in cooldown)
            if not force_rotation and self.tracker.is_available(exit_ip):
                # Fresh IP found!
                self.current_exit_ip = exit_ip
                remaining = self.tracker.get_cooldown_remaining(exit_ip)

                if remaining is None:
                    print(f"✓ Fresh exit IP: {exit_ip} (never used)")
                else:
                    print(f"✓ Fresh exit IP: {exit_ip}")

                # Record usage
                self.tracker.record_use(exit_ip)
                return exit_ip

            # IP is in cooldown, need to rotate
            cooldown_remaining = self.tracker.get_cooldown_remaining(exit_ip)
            if cooldown_remaining:
                hours_remaining = cooldown_remaining / 3600
                print(f"  Exit IP {exit_ip} in cooldown ({hours_remaining:.1f}h remaining)")
            else:
                print(f"  Exit IP {exit_ip} was used recently")

            # Rotate to new circuit
            print(f"  Rotating circuit (attempt {attempt + 1}/{self.max_rotation_attempts})...")
            self._rotate_circuit()

        # Failed to get fresh IP
        raise RuntimeError(
            f"Failed to get fresh exit IP after {self.max_rotation_attempts} attempts. "
            f"All attempted IPs are in {self.cooldown_hours}-hour cooldown."
        )

    def get(
        self,
        url: str,
        ensure_fresh_ip: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Make GET request through Tor with fresh exit IP.

        Args:
            url: URL to request
            ensure_fresh_ip: Ensure fresh exit IP before request (default: True)
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            Response object
        """
        if ensure_fresh_ip:
            self._ensure_fresh_exit_ip()

        return self.session.get(url, **kwargs)

    def post(
        self,
        url: str,
        ensure_fresh_ip: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Make POST request through Tor with fresh exit IP.

        Args:
            url: URL to request
            ensure_fresh_ip: Ensure fresh exit IP before request (default: True)
            **kwargs: Additional arguments passed to requests.post()

        Returns:
            Response object
        """
        if ensure_fresh_ip:
            self._ensure_fresh_exit_ip()

        return self.session.post(url, **kwargs)

    def request(
        self,
        method: str,
        url: str,
        ensure_fresh_ip: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request through Tor with fresh exit IP.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            ensure_fresh_ip: Ensure fresh exit IP before request (default: True)
            **kwargs: Additional arguments passed to requests.request()

        Returns:
            Response object
        """
        if ensure_fresh_ip:
            self._ensure_fresh_exit_ip()

        return self.session.request(method, url, **kwargs)

    def get_status(self) -> Dict[str, Any]:
        """
        Get client status information.

        Returns:
            Dictionary with current exit IP and tracker stats
        """
        try:
            current_ip = self._get_exit_ip()
        except Exception:
            current_ip = None

        tracker_stats = self.tracker.get_stats()

        return {
            'current_exit_ip': current_ip,
            'exit_ip_fresh': self.tracker.is_available(current_ip) if current_ip else False,
            'cooldown_hours': self.cooldown_hours,
            'tracker_stats': tracker_stats
        }

    def force_rotation(self):
        """Force circuit rotation to get new exit IP."""
        print("🔄 Forcing circuit rotation...")
        self._ensure_fresh_exit_ip(force_rotation=True)
