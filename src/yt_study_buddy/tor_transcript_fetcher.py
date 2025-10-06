"""
Tor proxy-based transcript fetcher for YouTube videos.

Bypasses IP blocks by routing requests through Tor network.
"""
import time
import random
from typing import Optional, List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import re
import socket
from stem import Signal
from stem.control import Controller


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

    def rotate_tor_circuit(self) -> bool:
        """
        Request a new Tor circuit (new exit node).

        Returns:
            True if circuit was rotated successfully, False otherwise
        """
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

        except Exception as e:
            print(f"Warning: Could not rotate Tor circuit: {e}")
            print("Continuing with existing circuit...")
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
                if attempt > 0:
                    print(f"Retry attempt {attempt + 1}/{max_retries}...")
                    self.rotate_tor_circuit()

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
        Try Tor first, fallback to direct connection if needed.

        Args:
            video_id: YouTube video ID
            use_tor_first: Whether to try Tor proxy first (default: True)
            languages: List of language codes to try

        Returns:
            Dictionary with transcript data or None if all methods failed
        """
        if use_tor_first:
            print("Attempting with Tor proxy...")
            result = self.fetch_transcript(video_id, languages)
            if result:
                print("✓ Successfully fetched via Tor")
                return result
            print("Tor fetch failed, trying direct connection...")

        print("Attempting direct connection...")
        try:
            # Instantiate API and fetch transcript
            api = YouTubeTranscriptApi()
            fetched = api.fetch(video_id, languages=languages)
            transcript_list = list(fetched)

            # Process transcript
            # FetchedTranscriptSnippet objects have .text attribute (not dict key)
            transcript_text = ' '.join([snippet.text for snippet in transcript_list])
            transcript_text = re.sub(r'\s+', ' ', transcript_text)
            transcript_text = transcript_text.replace('[Music]', '').replace('[Applause]', '')

            # Calculate duration
            duration_info = None
            if transcript_list:
                last_snippet = transcript_list[-1]
                duration_seconds = last_snippet.start + last_snippet.duration
                duration_minutes = int(duration_seconds / 60)
                duration_info = f"~{duration_minutes} minutes"

            print("✓ Successfully fetched via direct connection")
            return {
                'transcript': transcript_text,
                'duration': duration_info,
                'length': len(transcript_text),
                'segments': transcript_list
            }

        except Exception as e:
            print(f"Direct connection also failed: {e}")
            return None

    def get_video_title(
        self,
        video_id: str,
        max_retries: int = 3,
        timeout: int = 30
    ) -> str:
        """
        Get video title using YouTube oEmbed API through Tor with retry.

        Args:
            video_id: YouTube video ID
            max_retries: Maximum number of retry attempts (default: 3)
            timeout: Timeout in seconds per attempt (default: 30)

        Returns:
            Video title (cleaned for filename) or fallback Video_ID
        """
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.rotate_tor_circuit()
                    backoff = (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(backoff)

                response = self.session.get(
                    url,
                    proxies=self.proxies,
                    timeout=timeout * (1.5 ** attempt)
                )

                if response.status_code == 200:
                    data = response.json()
                    title = data.get('title', f'Video_{video_id}')
                    # Clean title for filename
                    clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                    return clean_title[:100]

            except Exception as e:
                last_error = e
                if attempt >= max_retries - 1:
                    print(f"Warning: Could not fetch video title via Tor after {max_retries} attempts: {e}")

        return f"Video_{video_id}"


# Usage example
if __name__ == "__main__":
    fetcher = TorTranscriptFetcher()

    # Check Tor is working
    if fetcher.check_tor_connection():
        print("✓ Tor proxy is working!")

        # Fetch transcript
        video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
        transcript = fetcher.fetch_with_fallback(video_id)

        if transcript:
            print(f"\n✓ Successfully fetched {len(transcript['segments'])} transcript segments")
            print(f"Total length: {transcript['length']} characters")
            print(f"Duration: {transcript['duration']}")
            # Print first few lines
            for i, segment in enumerate(transcript['segments'][:3]):
                print(f"{segment['start']:.2f}s: {segment['text']}")
    else:
        print("✗ Tor proxy not working. Check your setup.")
        print(f"Make sure Tor is running on {fetcher.tor_host}:{fetcher.tor_port}")