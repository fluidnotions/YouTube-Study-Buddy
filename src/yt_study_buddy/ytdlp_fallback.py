"""
YT-DLP fallback for transcript fetching.

Used when Tor-based fetching fails due to IP blocking or other issues.
"""
import re
from typing import Optional, List, Dict, Any
import yt_dlp
from .error_classifier import simplify_error


class YtDlpFallback:
    """Fetch YouTube transcripts using yt-dlp as fallback method."""

    def __init__(self):
        """Initialize yt-dlp with minimal options."""
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': False,  # Don't write to disk
            'writeautomaticsub': False,  # Don't write to disk
            'subtitleslangs': ['en'],
        }

    def fetch_transcript(
        self,
        video_id: str,
        languages: List[str] = ['en']
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript using yt-dlp.

        Args:
            video_id: YouTube video ID
            languages: List of language codes (default: ['en'])

        Returns:
            Dictionary with transcript data or None if failed
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Extract info including subtitles
                info = ydl.extract_info(video_url, download=False)

                # Try to get requested subtitles - first manual, then automatic
                transcript_text = None
                for lang in languages:
                    # Try manual subtitles first
                    subtitles = info.get('subtitles', {})
                    if lang in subtitles:
                        transcript_text = self._download_and_parse_subtitle(
                            subtitles[lang], ydl
                        )
                        if transcript_text:
                            break

                    # Fall back to auto-generated captions
                    auto_captions = info.get('automatic_captions', {})
                    if lang in auto_captions:
                        transcript_text = self._download_and_parse_subtitle(
                            auto_captions[lang], ydl
                        )
                        if transcript_text:
                            break

                if not transcript_text:
                    print("No subtitles found for requested languages")
                    return None

                # Clean up transcript
                transcript_text = re.sub(r'\s+', ' ', transcript_text)
                transcript_text = transcript_text.replace('[Music]', '').replace('[Applause]', '')

                # Get video duration
                duration_seconds = info.get('duration', 0)
                duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                duration_info = f"~{duration_minutes} minutes" if duration_minutes else None

                return {
                    'transcript': transcript_text,
                    'duration': duration_info,
                    'length': len(transcript_text),
                    'method': 'yt-dlp',
                    'segments': []  # yt-dlp doesn't provide segment timing easily
                }

        except Exception as e:
            simplified = simplify_error(str(e))
            print(f"YT-DLP fallback failed: {simplified}")
            return None

    def _download_and_parse_subtitle(
        self,
        subtitle_formats: List[Dict],
        ydl: yt_dlp.YoutubeDL
    ) -> Optional[str]:
        """
        Download and parse subtitle from format list.

        Args:
            subtitle_formats: List of subtitle format dicts
            ydl: YoutubeDL instance

        Returns:
            Extracted subtitle text or None
        """
        import requests

        # Try VTT format first (simple text format, easier to parse)
        for fmt in subtitle_formats:
            if fmt.get('ext') == 'vtt':
                try:
                    subtitle_url = fmt.get('url')
                    if not subtitle_url:
                        continue

                    # Download VTT file
                    response = requests.get(subtitle_url, timeout=30)
                    if response.status_code == 200:
                        vtt_content = response.text

                        # Parse VTT format - extract text lines only
                        text_parts = []
                        for line in vtt_content.split('\n'):
                            line = line.strip()
                            # Skip empty lines, timestamps, and WEBVTT header
                            if line and not line.startswith('WEBVTT') and not '-->' in line and not line.isdigit():
                                # Skip cue identifiers (lines that are just numbers)
                                if not re.match(r'^\d+$', line):
                                    text_parts.append(line)

                        if text_parts:
                            return ' '.join(text_parts)
                except Exception as e:
                    print(f"  Failed to extract from VTT: {e}")
                    continue

        return None

    def get_video_title(self, video_id: str) -> str:
        """
        Get video title using yt-dlp.

        Args:
            video_id: YouTube video ID

        Returns:
            Video title (cleaned) or fallback Video_ID
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                title = info.get('title', f'Video_{video_id}')

                # Clean title for filename
                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                return clean_title[:100]

        except Exception as e:
            print(f"YT-DLP title fetch failed: {e}")
            return f"Video_{video_id}"
