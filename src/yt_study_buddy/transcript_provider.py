"""
Transcript provider interface and implementations.
Modern Python typing with Protocol for structural typing and ABC for inheritance-based interfaces.
"""
from typing import Protocol, Dict, Any, Optional
from abc import ABC, abstractmethod
import requests
import re
import time
import random
from youtube_transcript_api import YouTubeTranscriptApi


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


class APITranscriptProvider(AbstractTranscriptProvider):
    """Official YouTube Transcript API provider (original implementation)."""

    def __init__(self):
        self.api = YouTubeTranscriptApi()

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Get transcript using official YouTube Transcript API."""
        try:
            # Add small random delay to avoid appearing automated
            time.sleep(random.uniform(0.5, 1.5))

            # Try English first
            try:
                fetched = self.api.fetch(video_id, languages=['en'])
            except:
                # Fall back to any available language
                fetched = self.api.fetch(video_id)

            # FetchedTranscript is iterable and contains FetchedTranscriptSnippet objects
            # Each snippet has: text, start, duration attributes
            transcript_list = list(fetched)

            # Combine all transcript segments
            transcript = ' '.join([snippet.text for snippet in transcript_list])

            # Clean up the transcript
            transcript = re.sub(r'\s+', ' ', transcript)
            transcript = transcript.replace('[Music]', '').replace('[Applause]', '')

            # Calculate video duration
            duration_info = None
            if transcript_list:
                last_snippet = transcript_list[-1]
                duration_seconds = last_snippet.start + last_snippet.duration
                duration_minutes = int(duration_seconds / 60)
                duration_info = f"~{duration_minutes} minutes"

            return {
                'transcript': transcript,
                'duration': duration_info,
                'length': len(transcript)
            }

        except Exception as e:
            # Check if it's a rate limiting error and retry
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"  Rate limited, attempting retry with backoff...")
                return self._retry_with_backoff(video_id, max_retries=3)
            else:
                raise Exception(f"Could not get transcript: {e}")

    def get_video_title(self, video_id: str) -> str:
        """Get video title using YouTube oEmbed API."""
        try:
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
        """Retry transcript fetching with exponential backoff."""
        for attempt in range(max_retries):
            try:
                wait_time = 5 * (2 ** attempt)
                print(f"    Retry {attempt + 1}/{max_retries} - waiting {wait_time} seconds...")
                time.sleep(wait_time)
                time.sleep(random.uniform(1, 3))

                try:
                    fetched = self.api.fetch(video_id, languages=['en'])
                except:
                    fetched = self.api.fetch(video_id)

                transcript_list = list(fetched)

                transcript = ' '.join([snippet.text for snippet in transcript_list])
                transcript = re.sub(r'\s+', ' ', transcript)
                transcript = transcript.replace('[Music]', '').replace('[Applause]', '')

                duration_info = None
                if transcript_list:
                    last_snippet = transcript_list[-1]
                    duration_seconds = last_snippet.start + last_snippet.duration
                    duration_minutes = int(duration_seconds / 60)
                    duration_info = f"~{duration_minutes} minutes"

                print(f"    ✓ Retry successful!")
                return {
                    'transcript': transcript,
                    'duration': duration_info,
                    'length': len(transcript)
                }

            except Exception as retry_e:
                if attempt == max_retries - 1:
                    raise Exception(f"All retry attempts failed. Last error: {retry_e}")
                else:
                    print(f"    Retry {attempt + 1} failed: {retry_e}")

        raise Exception("All retry attempts exhausted")


class ScraperTranscriptProvider(AbstractTranscriptProvider):
    """Web scraper-based transcript provider - bypasses API rate limits."""

    def __init__(self):
        self.session = requests.Session()
        # Set realistic browser headers to avoid detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Scrape transcript from YouTube page HTML."""
        try:
            # Add delay to appear more human-like
            time.sleep(random.uniform(1, 3))

            url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                raise Exception(f"Failed to load video page: HTTP {response.status_code}")

            html_content = response.text

            # Extract transcript from the page
            transcript_data = self._extract_transcript_from_html(html_content, video_id)

            if not transcript_data['transcript']:
                raise Exception("No transcript found in page HTML")

            return transcript_data

        except Exception as e:
            raise Exception(f"Scraper failed: {e}")

    def get_video_title(self, video_id: str) -> str:
        """Extract video title from YouTube page."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                # Extract title from HTML
                title_match = re.search(r'<title>([^<]+)</title>', response.text)
                if title_match:
                    title = title_match.group(1).replace(' - YouTube', '')
                    # Clean title for filename
                    clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                    return clean_title[:100]

        except Exception as e:
            print(f"Warning: Could not scrape video title: {e}")

        return f"Video_{video_id}"

    def _extract_transcript_from_html(self, html_content: str, video_id: str) -> Dict[str, Any]:
        """Extract transcript data from YouTube page HTML."""
        try:
            # YouTube embeds transcript data in various places in the HTML
            # This is a simplified approach - in practice, you'd need more robust parsing

            # Method 1: Look for captions in initial data
            captions_match = re.search(r'"captions":\s*({.+?"videoDetails"})', html_content, re.DOTALL)
            if captions_match:
                # This would need JSON parsing to extract actual transcript
                # For now, return a placeholder
                pass

            # Method 2: Look for transcript button/timedtext URLs
            timedtext_urls = re.findall(r'"baseUrl":"([^"]*timedtext[^"]*)"', html_content)
            if timedtext_urls:
                # Decode URL and fetch transcript
                import urllib.parse
                for url in timedtext_urls[:1]:  # Try first URL
                    decoded_url = urllib.parse.unquote(url)
                    if 'lang=en' in decoded_url or 'tlang=en' in decoded_url:
                        transcript_text = self._fetch_timedtext(decoded_url)
                        if transcript_text:
                            return {
                                'transcript': transcript_text,
                                'duration': None,  # Could extract from video data
                                'length': len(transcript_text)
                            }

            # Method 3: Look for auto-generated captions in page data
            auto_caption_match = re.search(r'"captionTracks":\s*\[([^\]]+)\]', html_content)
            if auto_caption_match:
                # Parse caption tracks and find English one
                # This is simplified - real implementation would parse JSON properly
                pass

            # If no transcript found, return empty
            return {
                'transcript': '',
                'duration': None,
                'length': 0
            }

        except Exception as e:
            print(f"Warning: Error parsing HTML for transcript: {e}")
            return {
                'transcript': '',
                'duration': None,
                'length': 0
            }

    def _fetch_timedtext(self, url: str) -> str:
        """Fetch and parse timedtext transcript."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Parse XML transcript format
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)

                # Extract text from all <text> elements
                transcript_parts = []
                for text_elem in root.findall('.//text'):
                    text_content = text_elem.text
                    if text_content:
                        transcript_parts.append(text_content.strip())

                transcript = ' '.join(transcript_parts)
                # Clean up
                transcript = re.sub(r'\s+', ' ', transcript)
                transcript = transcript.replace('[Music]', '').replace('[Applause]', '')

                return transcript

        except Exception as e:
            print(f"Warning: Could not fetch timedtext: {e}")

        return ""


# Factory function for creating providers
def create_transcript_provider(provider_type: str = "api") -> TranscriptProvider:
    """
    Factory function that returns a TranscriptProvider.
    Uses Protocol typing - any object with the right methods works!
    """
    if provider_type == "api":
        return APITranscriptProvider()
    elif provider_type == "scraper":
        return ScraperTranscriptProvider()
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


# Type checking example
def process_with_provider(provider: TranscriptProvider, video_id: str) -> None:
    """
    This function accepts ANY object that implements the TranscriptProvider protocol.
    No inheritance required - just the right methods (duck typing + type hints).
    """
    transcript_data = provider.get_transcript(video_id)
    title = provider.get_video_title(video_id)
    print(f"Processed '{title}': {transcript_data['length']} characters")