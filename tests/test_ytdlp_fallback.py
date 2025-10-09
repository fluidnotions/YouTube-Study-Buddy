"""Tests for yt-dlp fallback functionality."""
import pytest
from src.yt_study_buddy.ytdlp_fallback import YtDlpFallback


@pytest.fixture
def fallback():
    """Create YtDlpFallback instance."""
    return YtDlpFallback()


def test_fetch_transcript_success(fallback):
    """Test successful transcript fetch."""
    # Rick Astley - Never Gonna Give You Up (has captions)
    video_id = "dQw4w9WgXcQ"

    result = fallback.fetch_transcript(video_id)

    assert result is not None
    assert 'transcript' in result
    assert 'duration' in result
    assert 'length' in result
    assert result['method'] == 'yt-dlp'
    assert len(result['transcript']) > 0


def test_fetch_transcript_invalid_video(fallback):
    """Test handling of invalid video ID."""
    result = fallback.fetch_transcript("INVALID_VIDEO_ID")
    assert result is None


def test_get_video_title(fallback):
    """Test video title fetching."""
    video_id = "dQw4w9WgXcQ"
    title = fallback.get_video_title(video_id)

    assert title is not None
    assert len(title) > 0
    assert not title.startswith("Video_")


@pytest.mark.integration
def test_fallback_integration(fallback):
    """Integration test with real YouTube video."""
    # Use the same video as the first test since we know it works
    video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up

    result = fallback.fetch_transcript(video_id)

    assert result is not None
    assert result['length'] > 100  # Should have substantial content
    assert result['method'] == 'yt-dlp'
