"""
Transcript provider interface and implementations.
Uses Tor proxy exclusively for reliable transcript fetching.
"""
import random
import re
import time
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, Optional

import requests

from .tor_transcript_fetcher import TorTranscriptFetcher


class TranscriptProvider(Protocol):
    """
    Protocol (structural typing) - like TypeScript interfaces.
    Any class that implements these methods automatically satisfies this interface.
    No inheritance required!
    """

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Get transcript data for a video ID."""
        ...

    def get_video_title(self, video_id: str) -> str:
        """Get video title for a video ID."""
        ...


class AbstractTranscriptProvider(ABC):
    """
    Abstract Base Class (inheritance-based) - traditional OOP approach.
    Subclasses MUST implement abstract methods.
    """

    @abstractmethod
    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Get transcript data for a video ID."""
        pass

    @abstractmethod
    def get_video_title(self, video_id: str) -> str:
        """Get video title for a video ID."""
        pass

    def get_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL - common implementation."""
        patterns = [
            r'(?:v=|/v/|youtu\.be/|/embed/|/watch\?.*v=)([^&\n?#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


class TorTranscriptProvider(AbstractTranscriptProvider):
    """Tor proxy-based transcript provider - bypasses IP blocks via Tor network."""

    def __init__(self, tor_host: str = '127.0.0.1', tor_port: int = 9050, use_tor_first: bool = True):
        """
        Initialize Tor-based transcript provider.

        Args:
            tor_host: Tor SOCKS proxy host (default: 127.0.0.1)
            tor_port: Tor SOCKS proxy port (default: 9050)
            use_tor_first: Try Tor first, fallback to direct if it fails (default: True)
        """
        self.tor_fetcher = TorTranscriptFetcher(tor_host=tor_host, tor_port=tor_port)
        self.use_tor_first = use_tor_first
        self._tor_verified = False

    def verify_tor_connection(self) -> bool:
        """
        Check if Tor connection is working.

        Returns:
            True if Tor is working, False otherwise
        """
        if not self._tor_verified:
            print("Verifying Tor connection...")
            self._tor_verified = self.tor_fetcher.check_tor_connection()
            if self._tor_verified:
                print("✓ Tor connection verified")
            else:
                print("⚠ Tor connection not available, will use direct connection")
        return self._tor_verified

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """
        Get transcript using Tor proxy with fallback to direct connection.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with transcript data

        Raises:
            Exception: If all methods fail to fetch transcript
        """
        try:
            # Add small random delay to avoid appearing automated
            time.sleep(random.uniform(0.5, 1.5))

            # Fetch transcript with fallback logic
            result = self.tor_fetcher.fetch_with_fallback(
                video_id=video_id,
                use_tor_first=self.use_tor_first,
                languages=['en']
            )

            if result:
                return result
            else:
                raise Exception("Both Tor and direct connection failed")

        except Exception as e:
            # Check if it's a rate limiting error and retry
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"  Rate limited, attempting retry with backoff...")
                return self._retry_with_backoff(video_id, max_retries=3)
            else:
                raise Exception(f"Could not get transcript: {e}")

    def get_video_title(self, video_id: str) -> str:
        """
        Get video title using Tor proxy with fallback.

        Args:
            video_id: YouTube video ID

        Returns:
            Video title cleaned for filename use
        """
        try:
            # Try via Tor first if enabled
            if self.use_tor_first and self.verify_tor_connection():
                title = self.tor_fetcher.get_video_title(video_id)
                if title and not title.startswith("Video_"):
                    return title

            # Fallback to direct connection
            url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', f'Video_{video_id}')
                # Clean title for filename
                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                return clean_title[:100]

        except Exception as e:
            print(f"Warning: Could not fetch video title: {e}")

        return f"Video_{video_id}"

    def _retry_with_backoff(self, video_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Retry transcript fetching with exponential backoff.

        Args:
            video_id: YouTube video ID
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary with transcript data

        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(max_retries):
            try:
                wait_time = 5 * (2 ** attempt)
                print(f"    Retry {attempt + 1}/{max_retries} - waiting {wait_time} seconds...")
                time.sleep(wait_time)
                time.sleep(random.uniform(1, 3))

                result = self.tor_fetcher.fetch_with_fallback(
                    video_id=video_id,
                    use_tor_first=self.use_tor_first,
                    languages=['en']
                )

                if result:
                    print(f"    ✓ Retry successful!")
                    return result
                else:
                    raise Exception("Fetch returned None")

            except Exception as retry_e:
                if attempt == max_retries - 1:
                    raise Exception(f"All retry attempts failed. Last error: {retry_e}")
                else:
                    print(f"    Retry {attempt + 1} failed: {retry_e}")

        raise Exception("All retry attempts exhausted")


# Factory function for creating providers
def create_transcript_provider(provider_type: str = "tor", **kwargs) -> TranscriptProvider:
    """
    Factory function that returns a TranscriptProvider.
    Now uses Tor exclusively for reliable transcript fetching.

    Args:
        provider_type: Type of provider (must be 'tor')
        **kwargs: Additional arguments passed to provider constructor
            - tor_host: Tor proxy host (default: '127.0.0.1')
            - tor_port: Tor proxy port (default: 9050)
            - use_tor_first: Try Tor first, fallback to direct (default: True)

    Returns:
        TorTranscriptProvider instance
    """
    if provider_type == "tor":
        return TorTranscriptProvider(**kwargs)
    else:
        raise ValueError(f"Only 'tor' provider is supported. Got: {provider_type}")


# Type checking example
def process_with_provider(provider: TranscriptProvider, video_id: str) -> None:
    """
    This function accepts ANY object that implements the TranscriptProvider protocol.
    No inheritance required - just the right methods (duck typing + type hints).
    """
    transcript_data = provider.get_transcript(video_id)
    title = provider.get_video_title(video_id)
    print(f"Processed '{title}': {transcript_data['length']} characters")