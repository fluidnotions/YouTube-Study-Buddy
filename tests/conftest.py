"""
Pytest configuration and fixtures for YouTube to Study Notes tests.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture
def sample_video_urls():
    """Sample YouTube URLs for testing."""
    return {
        "standard": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "short": "https://youtu.be/dQw4w9WgXcQ",
        "playlist": "https://youtu.be/dQw4w9WgXcQ?list=PLSomePlaylist",
        "embed": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "invalid": "https://example.com/not-a-video"
    }


@pytest.fixture
def sample_video_id():
    """Sample video ID for testing."""
    return "dQw4w9WgXcQ"


@pytest.fixture
def sample_transcript_data():
    """Sample transcript data structure."""
    return {
        "transcript": "Never gonna give you up, never gonna let you down, never gonna run around and desert you.",
        "duration": "~3 minutes",
        "length": 88
    }


@pytest.fixture
def mock_youtube_transcript_api():
    """Mock YouTube Transcript API responses."""
    with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_api:
        # Mock successful transcript response
        mock_api.get_transcript.return_value = [
            {"text": "Never gonna give you up,", "start": 0.0, "duration": 2.0},
            {"text": "never gonna let you down,", "start": 2.0, "duration": 2.0},
            {"text": "never gonna run around", "start": 4.0, "duration": 2.0},
            {"text": "and desert you.", "start": 6.0, "duration": 2.0}
        ]
        yield mock_api


@pytest.fixture
def mock_requests():
    """Mock requests for web scraping tests."""
    with patch('requests.Session') as mock_session:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Video - YouTube</title></head>
            <body>
                <script>
                    var ytInitialData = {
                        "captions": {
                            "playerCaptionsTracklistRenderer": {
                                "captionTracks": [
                                    {
                                        "baseUrl": "https://www.youtube.com/api/timedtext?v=test",
                                        "languageCode": "en"
                                    }
                                ]
                            }
                        }
                    };
                </script>
            </body>
        </html>
        """
        mock_response.json.return_value = {"title": "Test Video"}

        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        yield mock_session


@pytest.fixture
def temp_study_notes_dir(tmp_path):
    """Create a temporary directory for study notes testing."""
    study_dir = tmp_path / "Study notes"
    study_dir.mkdir()
    return study_dir


@pytest.fixture
def sample_urls_file(tmp_path):
    """Create a sample URLs file for batch testing."""
    urls_file = tmp_path / "test_urls.txt"
    urls_file.write_text("""
# Test URLs file
https://youtu.be/dQw4w9WgXcQ
https://youtu.be/oHg5SJYRHA0
# This is a comment
https://youtu.be/L_jWHffIx5E
""")
    return urls_file


@pytest.fixture
def mock_claude_api():
    """Mock Claude API responses."""
    with patch('anthropic.Anthropic') as mock_anthropic:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="# Test Study Notes\n\nThis is a test summary.")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        yield mock_client


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-api-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")


# Markers for test organization
pytest_plugins = []