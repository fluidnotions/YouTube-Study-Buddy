"""
Video processing utilities for YouTube transcript and metadata extraction.
Now uses pluggable transcript providers for flexibility.
"""
import re
from typing import Optional
from .transcript_provider import TranscriptProvider, create_transcript_provider


class VideoProcessor:
    """Handles YouTube video processing using pluggable transcript providers."""

    def __init__(self, provider_type: str = "api", **provider_kwargs):
        """
        Initialize with a specific transcript provider.

        Args:
            provider_type: "api" for YouTube Transcript API, "scraper" for web scraping, "tor" for Tor proxy
            **provider_kwargs: Additional arguments passed to provider (e.g., tor_host, tor_port for 'tor')
        """
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

    def get_video_title(self, video_id: str) -> str:
        """Get video title using the configured provider."""
        return self.provider.get_video_title(video_id)

    def get_transcript(self, video_id: str) -> dict:
        """Get transcript using the configured provider."""
        try:
            print(f"  Using {self.provider_type} provider...")
            return self.provider.get_transcript(video_id)
        except Exception as e:
            # If API provider fails, suggest alternatives
            if self.provider_type == "api":
                print(f"  API provider failed: {e}")
                print("  Consider trying --method tor (with Tor proxy) or --method scraper")
            elif self.provider_type == "tor":
                print(f"  Tor provider failed: {e}")
                print("  Make sure Tor proxy is running (docker-compose up -d tor-proxy)")
            else:
                print(f"  Scraper provider failed: {e}")
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