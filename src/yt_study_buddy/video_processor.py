"""
Video processing utilities for YouTube transcript and metadata extraction.
Uses Tor proxy exclusively for reliable transcript fetching.
"""
import re
from typing import Optional

from .transcript_provider import TranscriptProvider, create_transcript_provider
from loguru import logger


class VideoProcessor:
    """Handles YouTube video processing using Tor-based transcript provider."""

    def __init__(self, provider_type: str = "tor", **provider_kwargs):
        """
        Initialize with Tor transcript provider.

        Args:
            provider_type: Must be "tor" (default and only option)
            **provider_kwargs: Additional arguments passed to provider (e.g., tor_host, tor_port)
        """
        if provider_type != "tor":
            provider_type = "tor"  # Force Tor as only option
        self.provider: TranscriptProvider = create_transcript_provider(provider_type, **provider_kwargs)
        self.provider_type = provider_type

    def get_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from any YouTube URL format."""
        patterns = [
            r'(?:v=|/v/|youtu\.be/|/embed/|/watch\?.*v=)([^&\n?#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_title(self, video_id: str, worker_id=None) -> str:
        """Get video title using the configured provider.

        Args:
            video_id: YouTube video ID
            worker_id: Optional worker ID for logging/debugging (not used by provider)
        """
        return self.provider.get_video_title(video_id)

    def get_transcript(self, video_id: str) -> dict:
        """Get transcript using Tor provider."""
        try:
            logger.info(f"  Using Tor provider...")
            return self.provider.get_transcript(video_id)
        except Exception as e:
            logger.error(f"  Tor provider failed: {e}")
            logger.info("  Make sure Tor proxy is running (docker-compose up -d tor-proxy)")
            raise

    @staticmethod
    def sanitize_filename(filename):
        """Sanitize filename for cross-platform compatibility."""
        # Remove/replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        return filename or "unnamed_video"