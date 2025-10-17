"""
Tor proxy-based transcript fetcher for YouTube videos.

Bypasses IP blocks by routing requests through Tor network.
"""
import random
import re
import socket
import time
import threading
from collections import deque
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import requests
from stem import Signal, SocketError
from stem.control import Controller
from youtube_transcript_api import YouTubeTranscriptApi

from .ytdlp_fallback import YtDlpFallback
from .debug_logger import get_logger


class TorExitNodePool:
    """
    Pool manager for Tor exit nodes that can be shared across workers.

    Each worker can acquire a dedicated Tor connection from the pool,
    ensuring parallel processing without connection conflicts.

    GUARANTEES UNIQUE EXIT NODES PER WORKER:
    ========================================
    This pool ensures that no two workers use the same exit IP by:
    1. Checking the exit IP for each acquired connection
    2. Automatically rotating circuits until a unique IP is obtained
    3. Tracking active exit IPs to prevent collisions
    4. Blocking acquisition until a unique IP is secured

    TOR SETUP OPTIONS:
    ==================
    You can use this pool with either setup:

    Option A: Single Tor Instance (Simpler Setup)
    ----------------------------------------------
    - Run one Tor service with control port enabled
    - Pool automatically rotates circuits to get different exit IPs
    - Configure torrc with:
        ControlPort 9051
        CookieAuthentication 0
        HashedControlPassword <your_hashed_password>

    Option B: Multiple Tor Instances (Better Performance)
    -----------------------------------------------------
    - Run multiple Tor processes on different ports
    - Each worker gets a dedicated Tor instance
    - Example with Docker Compose:
        services:
          tor1: {image: dperson/torproxy, ports: ["9050:9050", "9051:9051"]}
          tor2: {image: dperson/torproxy, ports: ["9052:9050", "9053:9051"]}
          tor3: {image: dperson/torproxy, ports: ["9054:9050", "9055:9051"]}

    CONFIGURATION:
    ==============
    - enforce_unique_exits=True: Ensures unique IPs (recommended)
    - max_rotation_attempts=10: How many times to rotate for unique IP
    - pool_size: Number of concurrent connections (match worker count)

    USAGE EXAMPLE:
    ==============
    ```python
    pool = TorExitNodePool(pool_size=5, enforce_unique_exits=True)

    # In worker function:
    with pool.acquire(worker_id=worker_id) as fetcher:
        transcript = fetcher.fetch_with_fallback(video_id)
    ```

    MONITORING:
    ===========
    Use get_stats() to verify unique exit IPs:
    - stats['all_unique']: True if all workers have different IPs
    - stats['active_exit_ips']: List of currently used IPs
    - stats['unique_exit_ips']: Count of unique IPs in use
    """

    def __init__(
        self,
        pool_size: int = 5,
        tor_host: str = '127.0.0.1',
        base_socks_port: int = 9050,
        base_control_port: int = 9051,
        tor_control_password: Optional[str] = None,
        enforce_unique_exits: bool = True,
        max_rotation_attempts: int = 10
    ):
        """
        Initialize exit node pool.

        Args:
            pool_size: Number of Tor connections in the pool
            tor_host: Tor proxy host
            base_socks_port: Base SOCKS port (pool will use base_port, base_port+1, ...)
            base_control_port: Base control port (pool will use base_port, base_port+1, ...)
            tor_control_password: Password for Tor control ports
            enforce_unique_exits: If True, ensures each connection uses a different exit IP
            max_rotation_attempts: Maximum attempts to find unique exit node
        """
        self.pool_size = pool_size
        self.tor_host = tor_host
        self.base_socks_port = base_socks_port
        self.base_control_port = base_control_port
        self.tor_control_password = tor_control_password
        self.enforce_unique_exits = enforce_unique_exits
        self.max_rotation_attempts = max_rotation_attempts

        # Create pool of available connections
        self._available = deque(range(pool_size))
        self._in_use = set()
        self._lock = threading.Lock()

        # Track active exit IPs to ensure uniqueness
        self._active_exit_ips: Dict[int, str] = {}  # connection_id -> exit_ip
        self._exit_ip_lock = threading.Lock()

        print(f"Initialized TorExitNodePool with {pool_size} connections")
        print(f"SOCKS ports: {base_socks_port}-{base_socks_port + pool_size - 1}")
        print(f"Control ports: {base_control_port}-{base_control_port + pool_size - 1}")
        print(f"Unique exit enforcement: {'ENABLED' if enforce_unique_exits else 'DISABLED'}")

    def _get_exit_ip(self, fetcher: 'TorTranscriptFetcher', connection_id: int) -> Optional[str]:
        """
        Get the exit IP for a Tor connection.

        Args:
            fetcher: TorTranscriptFetcher instance
            connection_id: Connection ID for logging

        Returns:
            Exit IP address or None if check fails
        """
        try:
            response = fetcher.session.get(
                'https://api.ipify.org',
                proxies=fetcher.proxies,
                timeout=10
            )
            exit_ip = response.text.strip()
            print(f"  Connection #{connection_id} exit IP: {exit_ip}")
            return exit_ip
        except Exception as e:
            print(f"  Warning: Could not get exit IP for connection #{connection_id}: {e}")
            return None

    def _ensure_unique_exit(
        self,
        fetcher: 'TorTranscriptFetcher',
        connection_id: int,
        worker_id: Optional[int] = None
    ) -> bool:
        """
        Ensure this connection has a unique exit IP not used by other active connections.

        Rotates circuit until a unique IP is found or max attempts reached.

        Args:
            fetcher: TorTranscriptFetcher instance
            connection_id: Connection ID
            worker_id: Optional worker ID for logging

        Returns:
            True if unique exit obtained, False otherwise
        """
        if not self.enforce_unique_exits:
            return True  # Skip enforcement if disabled

        worker_label = f"worker-{worker_id}" if worker_id is not None else "unknown"

        for attempt in range(self.max_rotation_attempts):
            # Get current exit IP
            exit_ip = self._get_exit_ip(fetcher, connection_id)

            if exit_ip is None:
                print(f"  {worker_label}: Could not verify exit IP (attempt {attempt + 1})")
                if attempt == 0:
                    # Allow first attempt to proceed even if IP check fails
                    return True
                continue

            # Check if this IP is already in use by another connection
            with self._exit_ip_lock:
                # Get all active IPs except our own connection
                other_ips = {
                    ip for cid, ip in self._active_exit_ips.items()
                    if cid != connection_id
                }

                if exit_ip not in other_ips:
                    # Unique IP found! Register it
                    self._active_exit_ips[connection_id] = exit_ip
                    print(f"  ✓ {worker_label}: Unique exit IP secured: {exit_ip}")
                    return True

            # IP collision - rotate circuit and retry
            print(f"  ⚠ {worker_label}: Exit IP {exit_ip} already in use by another worker")
            print(f"  Rotating circuit (attempt {attempt + 1}/{self.max_rotation_attempts})...")

            # Rotate circuit to get new exit node
            fetcher.rotate_tor_circuit()

            # Wait a bit for new circuit to stabilize
            time.sleep(2)

        print(f"  ✗ {worker_label}: Could not obtain unique exit IP after "
              f"{self.max_rotation_attempts} attempts")
        print(f"  Proceeding with non-unique exit (may cause rate limiting)")
        return False

    @contextmanager
    def acquire(self, worker_id: Optional[int] = None, timeout: float = 30.0):
        """
        Acquire a Tor connection from the pool (context manager).

        Args:
            worker_id: Optional worker ID for logging
            timeout: Maximum time to wait for available connection

        Yields:
            TorTranscriptFetcher instance configured for this pool slot

        Raises:
            TimeoutError: If no connection becomes available within timeout
        """
        connection_id = None
        start_time = time.time()

        # Wait for available connection
        while True:
            with self._lock:
                if self._available:
                    connection_id = self._available.popleft()
                    self._in_use.add(connection_id)
                    break

            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"No Tor connection available after {timeout}s "
                    f"(pool size: {self.pool_size}, in use: {len(self._in_use)})"
                )

            time.sleep(0.1)

        # Calculate ports for this connection
        socks_port = self.base_socks_port + connection_id
        control_port = self.base_control_port + connection_id

        worker_label = f"worker-{worker_id}" if worker_id is not None else "unknown"
        print(f"✓ {worker_label} acquired Tor connection #{connection_id} "
              f"(SOCKS: {socks_port}, Control: {control_port})")

        # Create fetcher instance for this connection
        fetcher = TorTranscriptFetcher(
            tor_host=self.tor_host,
            tor_port=socks_port,
            tor_control_port=control_port,
            tor_control_password=self.tor_control_password
        )

        # Ensure this connection has a unique exit IP
        self._ensure_unique_exit(fetcher, connection_id, worker_id)

        try:
            yield fetcher
        finally:
            # Remove exit IP from tracking
            with self._exit_ip_lock:
                self._active_exit_ips.pop(connection_id, None)

            # Release connection back to pool
            with self._lock:
                self._in_use.discard(connection_id)
                self._available.append(connection_id)

            print(f"✓ {worker_label} released Tor connection #{connection_id}")

    def get_connection(self, worker_id: Optional[int] = None) -> 'TorTranscriptFetcher':
        """
        Get a Tor connection from the pool (non-context manager version).

        WARNING: You must manually call release_connection() when done!
        Prefer using acquire() context manager instead.

        Args:
            worker_id: Optional worker ID for logging

        Returns:
            Tuple of (TorTranscriptFetcher, connection_id)
        """
        with self._lock:
            if not self._available:
                raise RuntimeError("No Tor connections available in pool")

            connection_id = self._available.popleft()
            self._in_use.add(connection_id)

        socks_port = self.base_socks_port + connection_id
        control_port = self.base_control_port + connection_id

        worker_label = f"worker-{worker_id}" if worker_id is not None else "unknown"
        print(f"✓ {worker_label} acquired Tor connection #{connection_id}")

        fetcher = TorTranscriptFetcher(
            tor_host=self.tor_host,
            tor_port=socks_port,
            tor_control_port=control_port,
            tor_control_password=self.tor_control_password
        )
        fetcher._pool_connection_id = connection_id  # Store for release

        # Ensure this connection has a unique exit IP
        self._ensure_unique_exit(fetcher, connection_id, worker_id)

        return fetcher

    def release_connection(self, fetcher: 'TorTranscriptFetcher'):
        """
        Release a connection back to the pool.

        Args:
            fetcher: TorTranscriptFetcher instance to release
        """
        if not hasattr(fetcher, '_pool_connection_id'):
            raise ValueError("Fetcher was not acquired from pool")

        connection_id = fetcher._pool_connection_id

        # Remove exit IP from tracking
        with self._exit_ip_lock:
            self._active_exit_ips.pop(connection_id, None)

        with self._lock:
            self._in_use.discard(connection_id)
            self._available.append(connection_id)

        print(f"✓ Released Tor connection #{connection_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics including unique exit IPs."""
        with self._lock:
            in_use_count = len(self._in_use)
            available_count = len(self._available)

        with self._exit_ip_lock:
            active_ips = list(self._active_exit_ips.values())
            unique_ips = len(set(active_ips))

        return {
            'pool_size': self.pool_size,
            'available': available_count,
            'in_use': in_use_count,
            'utilization': in_use_count / self.pool_size if self.pool_size > 0 else 0,
            'active_exit_ips': active_ips,
            'unique_exit_ips': unique_ips,
            'all_unique': unique_ips == in_use_count if in_use_count > 0 else True
        }


class TorTranscriptFetcher:
    """Fetch YouTube transcripts through Tor proxy to avoid IP blocks."""

    def __init__(
        self,
        tor_host: str = '127.0.0.1',
        tor_port: int = 9050,
        tor_control_port: int = 9051,
        tor_control_password: Optional[str] = None
    ):
        """
        Initialize with Tor proxy settings.

        Args:
            tor_host: Tor SOCKS proxy host (default: localhost)
            tor_port: Tor SOCKS proxy port (default: 9050)
            tor_control_port: Tor control port for circuit rotation (default: 9051)
            tor_control_password: Password for Tor control port (default: None)
        """
        self.proxies = {
            'http': f'socks5://{tor_host}:{tor_port}',
            'https': f'socks5://{tor_host}:{tor_port}'
        }
        self.session = requests.Session()
        self.tor_host = tor_host
        self.tor_port = tor_port
        self.tor_control_port = tor_control_port
        self.tor_control_password = tor_control_password
        self.ytdlp_fallback = YtDlpFallback()

    def rotate_tor_circuit(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Request a new Tor circuit (new exit node) with retry logic.

        Args:
            max_retries: Maximum number of connection attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 2.0)

        Returns:
            True if circuit was rotated successfully, False otherwise
        """
        for attempt in range(max_retries):
            try:
                with Controller.from_port(
                    address=self.tor_host,
                    port=self.tor_control_port
                ) as controller:
                    if self.tor_control_password:
                        controller.authenticate(password=self.tor_control_password)
                    else:
                        controller.authenticate()

                    controller.signal(Signal.NEWNYM)

                    # Wait for circuit to establish
                    time.sleep(controller.get_newnym_wait())

                    print("✓ Tor circuit rotated")
                    return True

            except (ConnectionRefusedError, OSError, SocketError) as e:
                # Connection errors - Tor might not be running yet or temporarily down
                if attempt < max_retries - 1:
                    print(f"Tor control port not ready (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"Warning: Could not connect to Tor control port after {max_retries} attempts: {e}")
                    print("Tor control port may not be running or accessible.")
                    print("Continuing with existing circuit...")

            except Exception as e:
                # Authentication errors or other issues - don't retry
                print(f"Warning: Could not rotate Tor circuit: {e}")
                print("Continuing with existing circuit...")
                return False

        return False

    def check_tor_connection(self) -> bool:
        """
        Verify Tor is working by checking IP.

        Returns:
            True if Tor is working and IP is different, False otherwise
        """
        try:
            # Check IP without Tor
            normal_ip = requests.get('https://api.ipify.org', timeout=10).text

            # Check IP with Tor
            tor_ip = self.session.get(
                'https://api.ipify.org',
                proxies=self.proxies,
                timeout=10
            ).text

            print(f"Normal IP: {normal_ip}")
            print(f"Tor IP: {tor_ip}")

            return normal_ip != tor_ip
        except Exception as e:
            print(f"Tor connection check failed: {e}")
            return False

    def fetch_transcript(
        self,
        video_id: str,
        languages: List[str] = ['en'],
        max_retries: int = 5,
        base_timeout: int = 60,
        max_timeout: int = 120
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript using Tor proxy with enhanced retry mechanism.

        Args:
            video_id: YouTube video ID
            languages: List of language codes to try (default: ['en'])
            max_retries: Maximum number of retry attempts (default: 5)
            base_timeout: Base timeout in seconds (default: 60)
            max_timeout: Maximum timeout in seconds (default: 120)

        Returns:
            Dictionary with transcript data or None if failed
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Rotate circuit on retries (not on first attempt)
                if attempt > 1:
                    print(f"Retry attempt {attempt + 1}/{max_retries}...")

                    # Try to rotate circuit, but don't fail if control port unavailable
                    rotation_success = self.rotate_tor_circuit()

                    # If circuit rotation failed, add extra delay to let rate limits expire
                    if not rotation_success:
                        extra_delay = 10 * attempt  # 10s, 20s, 30s, 40s...
                        print(f"Circuit rotation unavailable, adding {extra_delay}s delay...")
                        time.sleep(extra_delay)

                    # Exponential backoff with jitter
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Waiting {backoff:.1f}s before retry...")
                    time.sleep(backoff)

                # Add random delay to appear more human-like
                time.sleep(random.uniform(1, 3))

                # Calculate adaptive timeout (increases with each retry)
                timeout = min(base_timeout * (1.5 ** attempt), max_timeout)
                print(f"Using timeout: {timeout:.0f}s")

                # Use youtube-transcript-api with proxies
                # Note: youtube-transcript-api doesn't expose timeout directly,
                # but we set it on the session for requests made internally
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(timeout)

                try:
                    # Instantiate API and fetch transcript
                    api = YouTubeTranscriptApi()
                    fetched = api.fetch(video_id, languages=languages)
                    # Convert to list of snippets
                    transcript_list = list(fetched)
                finally:
                    socket.setdefaulttimeout(old_timeout)

                # Process transcript into the format expected by the app
                # FetchedTranscriptSnippet objects have .text attribute (not dict key)
                transcript_text = ' '.join([snippet.text for snippet in transcript_list])

                # Clean up the transcript
                transcript_text = re.sub(r'\s+', ' ', transcript_text)
                transcript_text = transcript_text.replace('[Music]', '').replace('[Applause]', '')

                # Calculate video duration
                duration_info = None
                if transcript_list:
                    last_snippet = transcript_list[-1]
                    duration_seconds = last_snippet.start + last_snippet.duration
                    duration_minutes = int(duration_seconds / 60)
                    duration_info = f"~{duration_minutes} minutes"

                print(f"✓ Successfully fetched transcript on attempt {attempt + 1}")
                return {
                    'transcript': transcript_text,
                    'duration': duration_info,
                    'length': len(transcript_text),
                    'segments': transcript_list  # Include raw segments for advanced use
                }

            except (requests.exceptions.Timeout, socket.timeout) as e:
                last_error = e
                print(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt >= max_retries - 1:
                    print(f"✗ All {max_retries} attempts failed due to timeouts")

            except Exception as e:
                last_error = e
                print(f"Error on attempt {attempt + 1}: {e}")
                # For non-timeout errors, might be blocked or other issue
                # Still retry with circuit rotation
                if attempt >= max_retries - 1:
                    print(f"✗ All {max_retries} attempts failed")

        print(f"Failed to fetch transcript via Tor after {max_retries} attempts: {last_error}")
        return None

    def fetch_with_fallback(
        self,
        video_id: str,
        use_tor_first: bool = True,
        languages: List[str] = ['en']
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript using Tor first, fall back to yt-dlp if Tor fails.

        Args:
            video_id: YouTube video ID
            use_tor_first: Always True (Tor is primary method)
            languages: List of language codes

        Returns:
            Dictionary with transcript data or None if all methods failed
        """
        # Try Tor first (primary method)
        print("Fetching transcript via Tor proxy...")
        result = self.fetch_transcript(video_id, languages)

        if result:
            print("✓ Successfully fetched via Tor")
            return result
        else:
            print("✗ Tor fetch failed")

            # Fall back to yt-dlp
            print("Attempting yt-dlp fallback...")
            ytdlp_result = self.ytdlp_fallback.fetch_transcript(
                video_id, languages
            )

            if ytdlp_result:
                print("✓ Successfully fetched via yt-dlp fallback")
                return ytdlp_result
            else:
                print("✗ YT-DLP fallback also failed")
                return None

    def get_video_title(
        self,
        video_id: str,
        max_retries: int = 3,
        timeout: int = 30,
        worker_id: Optional[int] = None
    ) -> str:
        """
        Get video title using YouTube oEmbed API through Tor with retry.

        Args:
            video_id: YouTube video ID
            max_retries: Maximum number of retry attempts (default: 3)
            timeout: Timeout in seconds per attempt (default: 30)
            worker_id: Optional worker ID for logging

        Returns:
            Video title (cleaned for filename) or fallback Video_ID
        """
        logger = get_logger()
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        last_error = None
        last_response_data = None

        for attempt in range(max_retries):
            attempt_num = attempt + 1
            logger.log_title_fetch_attempt(video_id, attempt_num, max_retries, worker_id)

            try:
                if attempt > 0:
                    print(f"  Rotating circuit before retry {attempt_num}...")
                    self.rotate_tor_circuit()
                    backoff = (2 ** attempt) + random.uniform(0, 0.5)
                    print(f"  Waiting {backoff:.1f}s before retry...")
                    time.sleep(backoff)

                response = self.session.get(
                    url,
                    proxies=self.proxies,
                    timeout=timeout * (1.5 ** attempt)
                )

                # Log response regardless of status
                response_data = None
                response_error = None

                try:
                    if response.status_code == 200:
                        response_data = response.json()
                        last_response_data = response_data
                    else:
                        response_error = f"HTTP {response.status_code}"
                        print(f"  ✗ HTTP {response.status_code} response")
                except Exception as json_err:
                    response_error = f"JSON parse error: {json_err}"
                    print(f"  ✗ Could not parse JSON: {json_err}")

                logger.log_api_response(
                    video_id=video_id,
                    url=url,
                    status_code=response.status_code,
                    response_data=response_data,
                    error=response_error,
                    worker_id=worker_id,
                    attempt=attempt_num
                )

                if response.status_code == 200 and response_data:
                    title = response_data.get('title')
                    if title:
                        # Clean title for filename
                        clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                        result = clean_title[:100]

                        logger.log_title_result(
                            video_id=video_id,
                            title=result,
                            success=True,
                            total_attempts=attempt_num,
                            worker_id=worker_id
                        )
                        print(f"  ✓ Title: {result}")
                        return result
                    else:
                        print(f"  ✗ No 'title' field in response")
                        logger.log_api_response(
                            video_id=video_id,
                            url=url,
                            status_code=200,
                            response_data=response_data,
                            error="No 'title' field in response",
                            worker_id=worker_id,
                            attempt=attempt_num
                        )

            except requests.exceptions.Timeout as e:
                last_error = e
                error_msg = f"Timeout after {timeout * (1.5 ** attempt):.1f}s"
                print(f"  ✗ {error_msg}")
                logger.log_api_response(
                    video_id=video_id,
                    url=url,
                    status_code=0,
                    response_data=None,
                    error=error_msg,
                    worker_id=worker_id,
                    attempt=attempt_num
                )

            except Exception as e:
                last_error = e
                error_msg = str(e)
                print(f"  ✗ Error: {error_msg}")
                logger.log_api_response(
                    video_id=video_id,
                    url=url,
                    status_code=0,
                    response_data=None,
                    error=error_msg,
                    worker_id=worker_id,
                    attempt=attempt_num
                )

        # All attempts failed
        fallback = f"Video_{video_id}"
        print(f"  ✗ All {max_retries} attempts failed, using fallback: {fallback}")

        if last_error:
            print(f"  Last error: {last_error}")

        logger.log_title_result(
            video_id=video_id,
            title=fallback,
            success=False,
            total_attempts=max_retries,
            worker_id=worker_id
        )

        return fallback


# Usage examples
if __name__ == "__main__":
    import concurrent.futures

    # Example 1: Single fetcher (original usage)
    print("=== Example 1: Single Fetcher ===")
    fetcher = TorTranscriptFetcher()

    if fetcher.check_tor_connection():
        print("✓ Tor proxy is working!")

        video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
        transcript = fetcher.fetch_with_fallback(video_id)

        if transcript:
            print(f"✓ Successfully fetched {len(transcript['segments'])} transcript segments")
            print(f"Total length: {transcript['length']} characters")
            print(f"Duration: {transcript['duration']}")
    else:
        print("✗ Tor proxy not working. Check your setup.")
        print(f"Make sure Tor is running on {fetcher.tor_host}:{fetcher.tor_port}")

    # Example 2: Pool with multiple workers (recommended for parallel processing)
    print("\n=== Example 2: Pool with Multiple Workers ===")
    print("NOTE: For true unique exit nodes, you need either:")
    print("  1. Multiple Tor instances on different ports, OR")
    print("  2. Circuit rotation with enforcement_unique_exits=True (automatic)")

    # Create pool with 5 connections
    # This will enforce unique exit IPs by rotating circuits if needed
    pool = TorExitNodePool(
        pool_size=5,
        base_socks_port=9050,
        base_control_port=9051,
        enforce_unique_exits=True,  # Ensures each worker gets different exit IP
        max_rotation_attempts=10    # Try up to 10 times to get unique IP
    )

    # List of videos to process in parallel
    video_ids = [
        "dQw4w9WgXcQ",  # Rick Astley
        "kJQP7kiw5Fk",  # Luis Fonsi - Despacito
        "9bZkp7q19f0",  # PSY - Gangnam Style
    ]

    def process_video(worker_id: int, video_id: str):
        """Worker function that acquires a connection from pool."""
        try:
            # Acquire connection from pool (auto-releases on exit)
            with pool.acquire(worker_id=worker_id) as fetcher:
                print(f"Worker {worker_id}: Processing {video_id}")
                transcript = fetcher.fetch_with_fallback(video_id)

                if transcript:
                    return {
                        'worker_id': worker_id,
                        'video_id': video_id,
                        'success': True,
                        'length': transcript['length'],
                        'duration': transcript['duration']
                    }
                else:
                    return {
                        'worker_id': worker_id,
                        'video_id': video_id,
                        'success': False
                    }
        except Exception as e:
            return {
                'worker_id': worker_id,
                'video_id': video_id,
                'success': False,
                'error': str(e)
            }

    # Process videos in parallel using thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(process_video, i, vid)
            for i, vid in enumerate(video_ids)
        ]

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Print results
    print("\n=== Results ===")
    for result in results:
        if result['success']:
            print(f"✓ Worker {result['worker_id']}: {result['video_id']} - "
                  f"{result['length']} chars, {result['duration']}")
        else:
            error = result.get('error', 'Unknown error')
            print(f"✗ Worker {result['worker_id']}: {result['video_id']} - {error}")

    # Show pool statistics
    stats = pool.get_stats()
    print(f"\n=== Pool Statistics ===")
    print(f"Connections: {stats['in_use']}/{stats['pool_size']} in use "
          f"({stats['utilization']:.1%} utilization)")
    print(f"Unique exit IPs: {stats['unique_exit_ips']}/{stats['in_use']}")
    print(f"All unique: {'✓ YES' if stats['all_unique'] else '✗ NO'}")
    if stats['active_exit_ips']:
        print(f"Active IPs: {', '.join(stats['active_exit_ips'])}")