"""
YT-DLP fallback for transcript fetching.

Used when Tor-based fetching fails due to IP blocking or other issues.
"""
import re
from typing import Optional, List, Dict, Any
import yt_dlp
from loguru import logger
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
                    logger.info("No subtitles found for requested languages")
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
            logger.error(f"YT-DLP fallback failed: {simplified}")
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

        # Separate VTT formats into direct API URLs and M3U playlists
        # Prefer direct API URLs as they're simpler to parse
        direct_vtt = []
        m3u_vtt = []

        for fmt in subtitle_formats:
            if fmt.get('ext') == 'vtt':
                url = fmt.get('url', '')
                if 'manifest.googlevideo.com' in url or 'hls_timedtext_playlist' in url:
                    m3u_vtt.append(fmt)
                else:
                    direct_vtt.append(fmt)

        # Try direct VTT URLs first, then M3U playlists as fallback
        for fmt in direct_vtt + m3u_vtt:
            try:
                subtitle_url = fmt.get('url')
                if not subtitle_url:
                    continue

                # Download VTT file (or M3U playlist)
                response = requests.get(subtitle_url, timeout=30)
                if response.status_code == 200:
                    content = response.text

                    # Check if it's an M3U playlist instead of direct VTT
                    if content.startswith('#EXTM3U'):
                        # Parse M3U playlist to get VTT segment URLs
                        text_parts = self._parse_m3u_playlist(content)
                        if text_parts:
                            return ' '.join(text_parts)
                    else:
                        # Direct VTT content - parse it
                        text_parts = self._parse_vtt_content(content)
                        if text_parts:
                            return ' '.join(text_parts)
            except Exception as e:
                logger.error(f"  Failed to extract from VTT: {e}")
                continue

        return None

    def _parse_vtt_content(self, vtt_content: str) -> List[str]:
        """
        Parse VTT content and extract text lines.

        Args:
            vtt_content: VTT file content

        Returns:
            List of text lines
        """
        text_parts = []
        for line in vtt_content.split('\n'):
            line = line.strip()
            # Skip empty lines, timestamps, and WEBVTT header
            if line and not line.startswith('WEBVTT') and not '-->' in line and not line.isdigit():
                # Skip cue identifiers (lines that are just numbers)
                if not re.match(r'^\d+$', line):
                    text_parts.append(line)
        return text_parts

    def _parse_m3u_playlist(self, m3u_content: str) -> List[str]:
        """
        Parse M3U playlist, download VTT segments, and extract text.

        Args:
            m3u_content: M3U playlist content

        Returns:
            List of text lines from all segments
        """
        import requests

        text_parts = []

        # Extract VTT segment URLs from M3U playlist
        for line in m3u_content.split('\n'):
            line = line.strip()
            # Skip M3U directives (lines starting with #)
            if line and not line.startswith('#'):
                # This is a segment URL
                try:
                    response = requests.get(line, timeout=30)
                    if response.status_code == 200:
                        # Parse VTT segment
                        segment_text = self._parse_vtt_content(response.text)
                        text_parts.extend(segment_text)
                except Exception as e:
                    logger.error(f"  Failed to download M3U segment {line[:50]}...: {e}")
                    continue

        return text_parts

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
            logger.error(f"YT-DLP title fetch failed: {e}")
            return f"Video_{video_id}"
