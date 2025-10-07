"""
Quick smoke tests to verify basic functionality.
These tests run fast and don't require external dependencies.
"""
import sys
from pathlib import Path

import pytest

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.mark.unit
def test_imports():
    """Test that all main modules can be imported."""
    try:
        from yt_study_buddy.video_processor import VideoProcessor
        from yt_study_buddy.transcript_provider import create_transcript_provider
        from yt_study_buddy.knowledge_graph import KnowledgeGraph
        from yt_study_buddy.study_notes_generator import StudyNotesGenerator
        from yt_study_buddy.obsidian_linker import ObsidianLinker
        from main import YouTubeStudyNotes

        # Basic instantiation
        app = YouTubeStudyNotes()
        assert app is not None

    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


@pytest.mark.unit
def test_video_id_extraction():
    """Quick test of video ID extraction."""
    from yt_study_buddy.video_processor import VideoProcessor

    processor = VideoProcessor()

    test_cases = [
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("invalid_url", None)
    ]

    for url, expected in test_cases:
        result = processor.get_video_id(url)
        assert result == expected, f"Failed for URL: {url}"


@pytest.mark.unit
def test_provider_factory():
    """Test transcript provider factory."""
    from yt_study_buddy.transcript_provider import create_transcript_provider

    api_provider = create_transcript_provider("api")
    scraper_provider = create_transcript_provider("scraper")

    assert api_provider is not None
    assert scraper_provider is not None
    assert type(api_provider).__name__ == "APITranscriptProvider"
    assert type(scraper_provider).__name__ == "ScraperTranscriptProvider"


@pytest.mark.unit
def test_file_sanitization():
    """Test filename sanitization."""
    from yt_study_buddy.video_processor import VideoProcessor

    test_cases = [
        ("Valid Filename", "Valid Filename"),
        ("Invalid: <chars>", "Invalid_ _chars_"),
        ("", "unnamed_video"),
        ("a" * 200, "a" * 100)  # Length limit
    ]

    for input_name, expected_pattern in test_cases:
        result = VideoProcessor.sanitize_filename(input_name)
        if expected_pattern == "unnamed_video":
            assert result == expected_pattern
        elif "chars" in expected_pattern:
            assert "<" not in result and ">" not in result
        elif len(expected_pattern) == 100:
            assert len(result) <= 100


@pytest.mark.unit
def test_app_initialization():
    """Test main app initialization with different parameters."""
    from main import YouTubeStudyNotes

    # Default initialization
    app1 = YouTubeStudyNotes()
    assert app1.provider_type == "api"
    assert app1.global_context is True

    # With subject
    app2 = YouTubeStudyNotes(subject="Test Subject")
    assert app2.subject == "Test Subject"
    assert "Test Subject" in app2.output_dir

    # With scraper provider
    app3 = YouTubeStudyNotes(provider_type="scraper")
    assert app3.provider_type == "scraper"


@pytest.mark.unit
def test_project_structure():
    """Test that required files and directories exist."""
    project_root = Path(__file__).parent.parent

    required_files = [
        "main.py",
        "requirements.txt",
        "pytest.ini",
        "src/__init__.py",
        "src/video_processor.py",
        "src/transcript_provider.py",
        "tests/__init__.py",
        "tests/conftest.py"
    ]

    missing_files = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        pytest.fail(f"Missing required files: {missing_files}")


@pytest.mark.unit
def test_help_message():
    """Test that help message can be generated."""
    from main import YouTubeStudyNotes

    app = YouTubeStudyNotes()

    # This should not raise an exception
    try:
        app.show_help()
    except Exception as e:
        pytest.fail(f"Help message generation failed: {e}")


if __name__ == "__main__":
    # Quick standalone test run
    pytest.main([__file__, "-v"])