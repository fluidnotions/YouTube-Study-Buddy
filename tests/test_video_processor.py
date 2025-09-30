"""
Tests for VideoProcessor class and URL handling.
"""
import pytest
from unittest.mock import patch, Mock
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
        """Test VideoProcessor initialization with different providers."""
        # Test default API provider
        processor = VideoProcessor()
        assert processor.provider_type == "api"

        # Test scraper provider
        processor = VideoProcessor(provider_type="scraper")
        assert processor.provider_type == "scraper"

        # Test invalid provider
        with pytest.raises(ValueError):
            VideoProcessor(provider_type="invalid")

    @pytest.mark.unit
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test with problematic characters
        dirty_filename = 'Test Video: "Quotes" & <Brackets> | Pipes'
        clean_filename = VideoProcessor.sanitize_filename(dirty_filename)
        assert '<' not in clean_filename
        assert '>' not in clean_filename
        assert '"' not in clean_filename
        assert '|' not in clean_filename

        # Test empty filename
        clean_filename = VideoProcessor.sanitize_filename("")
        assert clean_filename == "unnamed_video"

        # Test very long filename
        long_filename = "a" * 200
        clean_filename = VideoProcessor.sanitize_filename(long_filename)
        assert len(clean_filename) <= 100


class TestAPIProvider:
    """Test API transcript provider."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_api_provider_get_transcript(self, sample_video_id, mock_youtube_transcript_api):
        """Test API provider transcript extraction."""
        processor = VideoProcessor(provider_type="api")

        result = processor.get_transcript(sample_video_id)

        assert "transcript" in result
        assert "duration" in result
        assert "length" in result
        assert len(result["transcript"]) > 0
        assert result["length"] == len(result["transcript"])

    @pytest.mark.integration
    @pytest.mark.api
    def test_api_provider_get_title(self, sample_video_id):
        """Test API provider title extraction."""
        processor = VideoProcessor(provider_type="api")

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"title": "Test Video Title"}
            mock_get.return_value = mock_response

            title = processor.get_video_title(sample_video_id)
            assert title == "Test Video Title"

    @pytest.mark.integration
    @pytest.mark.api
    def test_api_provider_rate_limiting(self, sample_video_id):
        """Test API provider rate limiting handling."""
        processor = VideoProcessor(provider_type="api")

        with patch.object(processor.provider.api, 'fetch') as mock_fetch:
            # Simulate rate limiting error
            mock_fetch.side_effect = Exception("429 Too Many Requests")

            with pytest.raises(Exception) as exc_info:
                processor.get_transcript(sample_video_id)

            assert "429" in str(exc_info.value)


class TestScraperProvider:
    """Test scraper transcript provider."""

    @pytest.mark.integration
    @pytest.mark.scraper
    @pytest.mark.network
    def test_scraper_provider_initialization(self):
        """Test scraper provider initialization."""
        processor = VideoProcessor(provider_type="scraper")
        assert processor.provider_type == "scraper"
        assert hasattr(processor.provider, 'session')

    @pytest.mark.integration
    @pytest.mark.scraper
    def test_scraper_provider_get_title(self, sample_video_id, mock_requests):
        """Test scraper provider title extraction."""
        processor = VideoProcessor(provider_type="scraper")

        title = processor.get_video_title(sample_video_id)
        assert "Test Video" in title

    @pytest.mark.integration
    @pytest.mark.scraper
    def test_scraper_provider_user_agent(self):
        """Test scraper provider sets realistic user agent."""
        processor = VideoProcessor(provider_type="scraper")
        user_agent = processor.provider.session.headers.get('User-Agent', '')

        # Should contain browser-like user agent
        assert 'Mozilla' in user_agent
        assert 'Chrome' in user_agent or 'Firefox' in user_agent

    @pytest.mark.unit
    def test_scraper_provider_html_parsing(self):
        """Test HTML parsing for transcript extraction."""
        processor = VideoProcessor(provider_type="scraper")

        # Test with sample HTML containing timedtext URL
        sample_html = '''
        <html>
            <script>
                "baseUrl":"https://www.youtube.com/api/timedtext?v=test&lang=en"
            </script>
        </html>
        '''

        result = processor.provider._extract_transcript_from_html(sample_html, "test_id")
        assert isinstance(result, dict)
        assert "transcript" in result
        assert "duration" in result
        assert "length" in result


class TestProviderSwitching:
    """Test switching between providers."""

    @pytest.mark.unit
    def test_provider_error_messages(self, sample_video_id):
        """Test helpful error messages when providers fail."""
        # Test API provider failure
        processor = VideoProcessor(provider_type="api")

        with patch.object(processor.provider, 'get_transcript') as mock_get:
            mock_get.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                processor.get_transcript(sample_video_id)

        # Test scraper provider failure
        processor = VideoProcessor(provider_type="scraper")

        with patch.object(processor.provider, 'get_transcript') as mock_get:
            mock_get.side_effect = Exception("Scraper Error")

            with pytest.raises(Exception):
                processor.get_transcript(sample_video_id)

    @pytest.mark.unit
    def test_provider_type_consistency(self):
        """Test that provider type remains consistent."""
        api_processor = VideoProcessor(provider_type="api")
        assert api_processor.provider_type == "api"

        scraper_processor = VideoProcessor(provider_type="scraper")
        assert scraper_processor.provider_type == "scraper"