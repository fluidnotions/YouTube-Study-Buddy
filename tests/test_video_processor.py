"""
Tests for VideoProcessor class and URL handling.
"""
import pytest

from yt_study_buddy.video_processor import VideoProcessor


class TestVideoProcessor:
    """Test VideoProcessor functionality."""

    @pytest.mark.unit
    def test_video_id_extraction(self, sample_video_urls):
        """Test video ID extraction from various URL formats."""
        processor = VideoProcessor()

        # Test standard YouTube URL
        video_id = processor.get_video_id(sample_video_urls["standard"])
        assert video_id == "dQw4w9WgXcQ"

        # Test short YouTube URL
        video_id = processor.get_video_id(sample_video_urls["short"])
        assert video_id == "dQw4w9WgXcQ"

        # Test playlist URL (should extract video ID, ignore playlist)
        video_id = processor.get_video_id(sample_video_urls["playlist"])
        assert video_id == "dQw4w9WgXcQ"

        # Test embed URL
        video_id = processor.get_video_id(sample_video_urls["embed"])
        assert video_id == "dQw4w9WgXcQ"

        # Test invalid URL
        video_id = processor.get_video_id(sample_video_urls["invalid"])
        assert video_id is None

    @pytest.mark.unit
    def test_processor_initialization(self):
        """Test VideoProcessor initialization (Tor-only)."""
        # Default should be Tor
        processor = VideoProcessor()
        assert processor.provider_type == "tor"

        # Explicit Tor should work
        processor = VideoProcessor(provider_type="tor")
        assert processor.provider_type == "tor"

        # Other providers should be forced to Tor
        processor = VideoProcessor(provider_type="api")
        assert processor.provider_type == "tor"

    @pytest.mark.unit
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test removing invalid characters
        result = VideoProcessor.sanitize_filename('Test: Video | Name?')
        assert ':' not in result
        assert '|' not in result
        assert '?' not in result

        # Test length truncation
        long_name = "a" * 200
        result = VideoProcessor.sanitize_filename(long_name)
        assert len(result) <= 100
