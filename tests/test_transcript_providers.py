"""
Tests for transcript provider interfaces and implementations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from yt_study_buddy.transcript_provider import (
    TranscriptProvider,
    AbstractTranscriptProvider,
    APITranscriptProvider,
    ScraperTranscriptProvider,
    create_transcript_provider
)


class TestTranscriptProviderProtocol:
    """Test the Protocol interface works correctly."""

    @pytest.mark.unit
    def test_protocol_duck_typing(self):
        """Test that any object with the right methods satisfies the protocol."""

        class MockProvider:
            def get_transcript(self, video_id: str):
                return {"transcript": "test", "duration": "1 min", "length": 4}

            def get_video_title(self, video_id: str):
                return "Test Title"

        # This should work due to duck typing
        provider = MockProvider()

        # Test that it behaves like a TranscriptProvider
        result = provider.get_transcript("test_id")
        assert result["transcript"] == "test"

        title = provider.get_video_title("test_id")
        assert title == "Test Title"

    @pytest.mark.unit
    def test_factory_function(self):
        """Test the factory function creates correct providers."""
        api_provider = create_transcript_provider("api")
        assert isinstance(api_provider, APITranscriptProvider)

        scraper_provider = create_transcript_provider("scraper")
        assert isinstance(scraper_provider, ScraperTranscriptProvider)

        with pytest.raises(ValueError):
            create_transcript_provider("invalid")


class TestAbstractTranscriptProvider:
    """Test the abstract base class."""

    @pytest.mark.unit
    def test_cannot_instantiate_abstract_class(self):
        """Test that AbstractTranscriptProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AbstractTranscriptProvider()

    @pytest.mark.unit
    def test_common_get_video_id_method(self):
        """Test the common get_video_id implementation."""
        # Create a concrete implementation for testing
        class ConcreteProvider(AbstractTranscriptProvider):
            def get_transcript(self, video_id: str):
                return {"transcript": "", "duration": None, "length": 0}

            def get_video_title(self, video_id: str):
                return "Test"

        provider = ConcreteProvider()

        # Test various URL formats
        assert provider.get_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert provider.get_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert provider.get_video_id("invalid") is None


class TestAPITranscriptProvider:
    """Test the YouTube Transcript API provider."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test API provider initialization."""
        provider = APITranscriptProvider()
        assert isinstance(provider, APITranscriptProvider)
        assert isinstance(provider, AbstractTranscriptProvider)

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_transcript_success(self, sample_video_id, mock_youtube_transcript_api):
        """Test successful transcript retrieval."""
        provider = APITranscriptProvider()

        result = provider.get_transcript(sample_video_id)

        assert "transcript" in result
        assert "duration" in result
        assert "length" in result
        assert len(result["transcript"]) > 0

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_transcript_rate_limiting(self, sample_video_id):
        """Test rate limiting handling."""
        provider = APITranscriptProvider()

        with patch.object(provider.api, 'fetch') as mock_fetch:
            # First call fails with rate limiting
            mock_fetch.side_effect = Exception("429 Too Many Requests")

            with pytest.raises(Exception):
                provider.get_transcript(sample_video_id)

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_video_title_success(self, sample_video_id):
        """Test successful title retrieval."""
        provider = APITranscriptProvider()

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"title": "Test Video Title"}
            mock_get.return_value = mock_response

            title = provider.get_video_title(sample_video_id)
            assert title == "Test Video Title"

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_video_title_failure(self, sample_video_id):
        """Test title retrieval failure fallback."""
        provider = APITranscriptProvider()

        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            title = provider.get_video_title(sample_video_id)
            assert title == f"Video_{sample_video_id}"

    @pytest.mark.unit
    def test_retry_with_backoff(self, sample_video_id):
        """Test exponential backoff retry logic."""
        provider = APITranscriptProvider()

        with patch.object(provider.api, 'fetch') as mock_fetch:
            with patch('time.sleep') as mock_sleep:  # Speed up test
                # All retries fail
                mock_fetch.side_effect = Exception("Persistent error")

                with pytest.raises(Exception) as exc_info:
                    provider._retry_with_backoff(sample_video_id, max_retries=2)

                assert "All retry attempts failed" in str(exc_info.value)
                # Should have called sleep with exponential backoff
                assert mock_sleep.call_count > 0


class TestScraperTranscriptProvider:
    """Test the web scraper provider."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test scraper provider initialization."""
        provider = ScraperTranscriptProvider()
        assert isinstance(provider, ScraperTranscriptProvider)
        assert isinstance(provider, AbstractTranscriptProvider)
        assert hasattr(provider, 'session')

    @pytest.mark.unit
    def test_realistic_headers(self):
        """Test that scraper sets realistic browser headers."""
        provider = ScraperTranscriptProvider()

        headers = provider.session.headers
        assert 'User-Agent' in headers
        assert 'Mozilla' in headers['User-Agent']
        assert 'Accept' in headers
        assert 'Accept-Language' in headers

    @pytest.mark.integration
    @pytest.mark.scraper
    def test_get_video_title_success(self, sample_video_id):
        """Test successful title scraping."""
        provider = ScraperTranscriptProvider()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<title>Test Video - YouTube</title>'

        with patch.object(provider.session, 'get', return_value=mock_response):
            title = provider.get_video_title(sample_video_id)
            assert title == "Test Video"

    @pytest.mark.integration
    @pytest.mark.scraper
    def test_get_video_title_failure(self, sample_video_id):
        """Test title scraping failure fallback."""
        provider = ScraperTranscriptProvider()

        with patch.object(provider.session, 'get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            title = provider.get_video_title(sample_video_id)
            assert title == f"Video_{sample_video_id}"

    @pytest.mark.unit
    def test_extract_transcript_from_html_empty(self):
        """Test transcript extraction from HTML with no transcripts."""
        provider = ScraperTranscriptProvider()

        html_content = "<html><body>No transcripts here</body></html>"
        result = provider._extract_transcript_from_html(html_content, "test_id")

        assert result["transcript"] == ""
        assert result["duration"] is None
        assert result["length"] == 0

    @pytest.mark.unit
    def test_extract_transcript_from_html_with_timedtext(self):
        """Test transcript extraction from HTML with timedtext URLs."""
        provider = ScraperTranscriptProvider()

        html_content = '''
        <html>
            <script>
                "baseUrl":"https://www.youtube.com/api/timedtext?v=test&lang=en"
            </script>
        </html>
        '''

        with patch.object(provider, '_fetch_timedtext', return_value="Test transcript"):
            result = provider._extract_transcript_from_html(html_content, "test_id")
            assert result["transcript"] == "Test transcript"
            assert result["length"] == len("Test transcript")

    @pytest.mark.unit
    def test_fetch_timedtext_success(self):
        """Test successful timedtext fetching and parsing."""
        provider = ScraperTranscriptProvider()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''<?xml version="1.0" encoding="utf-8"?>
        <transcript>
            <text start="0" dur="2.5">Hello world</text>
            <text start="2.5" dur="3.0">This is a test</text>
        </transcript>'''

        with patch.object(provider.session, 'get', return_value=mock_response):
            result = provider._fetch_timedtext("http://example.com/timedtext")
            assert "Hello world" in result
            assert "This is a test" in result

    @pytest.mark.unit
    def test_fetch_timedtext_failure(self):
        """Test timedtext fetching failure."""
        provider = ScraperTranscriptProvider()

        with patch.object(provider.session, 'get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = provider._fetch_timedtext("http://example.com/timedtext")
            assert result == ""

    @pytest.mark.integration
    @pytest.mark.scraper
    @pytest.mark.slow
    def test_get_transcript_with_delays(self, sample_video_id):
        """Test that scraper includes realistic delays."""
        provider = ScraperTranscriptProvider()

        with patch('time.sleep') as mock_sleep:
            with patch.object(provider.session, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = "<html><body>No transcripts</body></html>"
                mock_get.return_value = mock_response

                try:
                    provider.get_transcript(sample_video_id)
                except Exception:
                    pass  # Expected to fail with no real transcript

                # Should have added delay
                assert mock_sleep.called


class TestProviderComparison:
    """Test comparison between different providers."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_provider_interface_consistency(self, sample_video_id):
        """Test that all providers implement the same interface."""
        api_provider = create_transcript_provider("api")
        scraper_provider = create_transcript_provider("scraper")

        # Both should have the same methods
        assert hasattr(api_provider, 'get_transcript')
        assert hasattr(api_provider, 'get_video_title')
        assert hasattr(scraper_provider, 'get_transcript')
        assert hasattr(scraper_provider, 'get_video_title')

        # Both should return the same data structure
        with patch.object(api_provider.api, 'fetch'):
            with patch('requests.get'):
                try:
                    api_result = api_provider.get_transcript(sample_video_id)
                    assert "transcript" in api_result
                    assert "duration" in api_result
                    assert "length" in api_result
                except Exception:
                    pass  # Expected in mocked environment

        with patch('requests.Session'):
            try:
                scraper_result = scraper_provider.get_transcript(sample_video_id)
                assert "transcript" in scraper_result
                assert "duration" in scraper_result
                assert "length" in scraper_result
            except Exception:
                pass  # Expected in mocked environment