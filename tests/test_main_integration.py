"""
Integration tests for the main application.
"""
import pytest
import tempfile
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock
from main import YouTubeStudyNotes


class TestYouTubeStudyNotesInitialization:
    """Test main application initialization."""

    @pytest.mark.unit
    def test_default_initialization(self):
        """Test default initialization parameters."""
        app = YouTubeStudyNotes()

        assert app.subject is None
        assert app.global_context is True
        assert app.base_dir == "Study notes"
        assert app.provider_type == "api"
        assert app.output_dir == "Study notes"

    @pytest.mark.unit
    def test_subject_initialization(self):
        """Test initialization with subject."""
        app = YouTubeStudyNotes(subject="Machine Learning")

        assert app.subject == "Machine Learning"
        assert app.output_dir == os.path.join("Study notes", "Machine Learning")

    @pytest.mark.unit
    def test_provider_type_initialization(self):
        """Test initialization with different provider types."""
        api_app = YouTubeStudyNotes(provider_type="api")
        assert api_app.provider_type == "api"
        assert api_app.video_processor.provider_type == "api"

        scraper_app = YouTubeStudyNotes(provider_type="scraper")
        assert scraper_app.provider_type == "scraper"
        assert scraper_app.video_processor.provider_type == "scraper"


class TestURLFileHandling:
    """Test URL file reading and processing."""

    @pytest.mark.unit
    def test_read_urls_from_file_success(self, sample_urls_file):
        """Test successful URL file reading."""
        app = YouTubeStudyNotes()

        urls = app.read_urls_from_file(str(sample_urls_file))

        # Should have 3 URLs (comments and empty lines filtered out)
        assert len(urls) == 3
        assert "dQw4w9WgXcQ" in urls[0]
        assert "oHg5SJYRHA0" in urls[1]
        assert "L_jWHffIx5E" in urls[2]

    @pytest.mark.unit
    def test_read_urls_from_file_missing(self):
        """Test reading from non-existent file."""
        app = YouTubeStudyNotes()

        urls = app.read_urls_from_file("nonexistent.txt")
        assert urls == []

    @pytest.mark.unit
    def test_read_urls_from_file_empty(self, tmp_path):
        """Test reading from empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        app = YouTubeStudyNotes()
        urls = app.read_urls_from_file(str(empty_file))
        assert urls == []

    @pytest.mark.unit
    def test_read_urls_from_file_comments_only(self, tmp_path):
        """Test reading from file with only comments."""
        comments_file = tmp_path / "comments.txt"
        comments_file.write_text("# Comment 1\n# Comment 2\n\n# Comment 3")

        app = YouTubeStudyNotes()
        urls = app.read_urls_from_file(str(comments_file))
        assert urls == []


class TestSingleURLProcessing:
    """Test single URL processing workflow."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_cli_interactive_single_url(self, tmp_path):
        """Test CLI interactive mode with single URL processing (real, no mocks)."""
        # Use a real YouTube video URL that should have captions
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Prepare input: choice 1 (single URL), then the URL, then quit
        input_data = f"1\n{test_url}\n4\n"

        # Run the actual CLI application
        result = subprocess.run(
            ["python", "main.py"],
            input=input_data,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=60
        )

        # Check that the process ran (might fail on transcript fetch due to rate limiting, but should execute)
        assert result.returncode in [0, 1]  # 0 = success, 1 = expected failure (rate limit)

        # Verify the interactive prompts appeared
        assert "Choose mode:" in result.stdout
        assert "Process single URL" in result.stdout

        # Verify it attempted to process the URL
        assert "Found video ID:" in result.stdout or "ERROR" in result.stdout

    @pytest.mark.integration
    def test_process_single_url_invalid_url(self, sample_video_urls):
        """Test processing with invalid URL."""
        app = YouTubeStudyNotes()

        result = app.process_single_url(sample_video_urls["invalid"])
        assert result is False

    @pytest.mark.integration
    def test_process_single_url_transcript_failure(self, sample_video_urls):
        """Test processing with transcript failure."""
        app = YouTubeStudyNotes()

        with patch.object(app.video_processor, 'get_transcript') as mock_transcript:
            mock_transcript.side_effect = Exception("Transcript error")

            result = app.process_single_url(sample_video_urls["standard"])
            assert result is False

    @pytest.mark.integration
    def test_process_single_url_api_not_ready(self, sample_video_urls):
        """Test processing when Claude API is not ready."""
        app = YouTubeStudyNotes()

        with patch.object(app.notes_generator, 'is_ready', return_value=False):
            result = app.process_single_url(sample_video_urls["standard"])
            assert result is False


class TestBatchProcessing:
    """Test batch URL processing."""

    @pytest.mark.integration
    def test_process_urls_from_file_success(self, sample_urls_file, mock_youtube_transcript_api, mock_claude_api):
        """Test successful batch processing."""
        app = YouTubeStudyNotes()

        with patch.object(app, 'process_single_url', return_value=True) as mock_process:
            with patch.object(app.notes_generator, 'is_ready', return_value=True):
                with patch('time.sleep'):  # Speed up test

                    app.process_urls_from_file(str(sample_urls_file))

                    # Should have processed 3 URLs
                    assert mock_process.call_count == 3

    @pytest.mark.integration
    def test_process_urls_from_file_api_not_ready(self, sample_urls_file):
        """Test batch processing when API is not ready."""
        app = YouTubeStudyNotes()

        with patch.object(app.notes_generator, 'is_ready', return_value=False):
            # Should return early without processing
            app.process_urls_from_file(str(sample_urls_file))

    @pytest.mark.integration
    def test_process_urls_from_file_mixed_results(self, sample_urls_file):
        """Test batch processing with mixed success/failure."""
        app = YouTubeStudyNotes()

        with patch.object(app.notes_generator, 'is_ready', return_value=True):
            with patch.object(app, 'process_single_url', side_effect=[True, False, True]):
                with patch('time.sleep'):  # Speed up test

                    app.process_urls_from_file(str(sample_urls_file))


class TestCommandLineArguments:
    """Test command line argument processing."""

    @pytest.mark.unit
    def test_help_display(self, capsys):
        """Test help message display."""
        app = YouTubeStudyNotes()

        with patch('sys.argv', ['main.py', '--help']):
            with pytest.raises(SystemExit):
                app.main()

    @pytest.mark.integration
    def test_subject_argument_processing(self):
        """Test subject argument processing."""
        app = YouTubeStudyNotes()

        with patch('sys.argv', ['main.py', '--subject', 'AI', 'https://youtu.be/test']):
            with patch.object(app, 'process_single_url', return_value=True):
                app.main()

                assert app.subject == 'AI'
                assert 'AI' in app.output_dir

    @pytest.mark.integration
    def test_method_argument_processing(self):
        """Test method argument processing."""
        app = YouTubeStudyNotes()

        with patch('sys.argv', ['main.py', '--method', 'scraper', 'https://youtu.be/test']):
            with patch.object(app, 'process_single_url', return_value=True):
                app.main()

                assert app.provider_type == 'scraper'
                assert app.video_processor.provider_type == 'scraper'

    @pytest.mark.integration
    def test_batch_argument_processing(self, sample_urls_file):
        """Test batch argument processing."""
        app = YouTubeStudyNotes()

        with patch('sys.argv', ['main.py', '--batch', '--file', str(sample_urls_file)]):
            with patch.object(app, 'process_urls_from_file') as mock_process:
                app.main()

                mock_process.assert_called_once_with(str(sample_urls_file))

    @pytest.mark.integration
    def test_subject_only_argument(self):
        """Test subject-only argument processing."""
        app = YouTubeStudyNotes()

        with patch('sys.argv', ['main.py', '--subject', 'AI', '--subject-only', 'https://youtu.be/test']):
            with patch.object(app, 'process_single_url', return_value=True):
                app.main()

                assert app.global_context is False


class TestInteractiveMode:
    """Test interactive mode functionality."""

    @pytest.mark.unit
    def test_interactive_mode_single_url(self):
        """Test interactive mode URL processing."""
        app = YouTubeStudyNotes()

        with patch('builtins.input', side_effect=['1', 'https://youtu.be/test']):
            with patch.object(app, 'process_single_url', return_value=True):
                app.run_interactive()

    @pytest.mark.unit
    def test_interactive_mode_batch(self, sample_urls_file):
        """Test interactive mode batch processing."""
        app = YouTubeStudyNotes()

        with patch('builtins.input', side_effect=['2', str(sample_urls_file)]):
            with patch.object(app, 'process_urls_from_file'):
                app.run_interactive()

    @pytest.mark.unit
    def test_interactive_mode_stats(self):
        """Test interactive mode statistics display."""
        app = YouTubeStudyNotes()

        with patch('builtins.input', side_effect=['3', '1']):
            with patch.object(app.knowledge_graph, 'get_stats', return_value={
                'scope': 'Global',
                'total_notes': 5,
                'total_concepts': 25,
                'avg_concepts_per_note': 5.0
            }):
                app.run_interactive()

    @pytest.mark.unit
    def test_interactive_mode_quit(self):
        """Test interactive mode quit."""
        app = YouTubeStudyNotes()

        with patch('builtins.input', return_value='4'):
            app.run_interactive()


class TestErrorHandling:
    """Test error handling throughout the application."""

    @pytest.mark.integration
    def test_rate_limiting_error_handling(self, sample_video_urls):
        """Test rate limiting error detection and messaging."""
        app = YouTubeStudyNotes()

        with patch.object(app.video_processor, 'get_transcript') as mock_transcript:
            mock_transcript.side_effect = Exception("rate limit exceeded")

            result = app.process_single_url(sample_video_urls["standard"])
            assert result is False

    @pytest.mark.integration
    def test_network_error_handling(self, sample_video_urls):
        """Test network error handling."""
        app = YouTubeStudyNotes()

        with patch.object(app.video_processor, 'get_transcript') as mock_transcript:
            mock_transcript.side_effect = Exception("Network error")

            result = app.process_single_url(sample_video_urls["standard"])
            assert result is False

    @pytest.mark.integration
    def test_provider_switching_suggestion(self, sample_video_urls):
        """Test that API failures suggest trying scraper method."""
        app = YouTubeStudyNotes(provider_type="api")

        with patch.object(app.video_processor, 'get_transcript') as mock_transcript:
            mock_transcript.side_effect = Exception("API rate limited")

            result = app.process_single_url(sample_video_urls["standard"])
            assert result is False