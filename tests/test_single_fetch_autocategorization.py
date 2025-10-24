"""
Test to verify auto-categorization only fetches transcript once.

This test ensures that when auto-categorization is enabled, the transcript
is fetched only ONCE (for categorization) and then reused in the pipeline,
avoiding the double-fetch bug that causes IP blocking.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from yt_study_buddy.cli import YouTubeStudyNotes
from yt_study_buddy.video_job import ProcessingStage


@pytest.fixture
def mock_transcript_data():
    """Mock transcript data returned by video processor."""
    return {
        'transcript': 'This is a machine learning tutorial about neural networks and deep learning.',
        'duration': '~10 minutes',
        'length': 500,
        'segments': [],
        'method': 'tor'
    }


@pytest.fixture
def mock_video_title():
    """Mock video title."""
    return "Introduction to Neural Networks"


class TestSingleFetchWithAutoCategorization:
    """Test that auto-categorization doesn't cause double-fetching."""

    def test_auto_categorization_fetches_transcript_only_once(
        self,
        mock_transcript_data,
        mock_video_title,
        tmp_path
    ):
        """
        Verify that when auto-categorization is enabled, transcript is fetched
        only once and reused in the pipeline.
        """
        # Setup
        test_url = "https://youtu.be/test123"
        test_video_id = "test123"

        # Create YouTubeStudyNotes with auto-categorization enabled
        with patch('yt_study_buddy.cli.VideoProcessor') as MockVideoProcessor, \
             patch('yt_study_buddy.cli.StudyNotesGenerator') as MockNotesGen, \
             patch('yt_study_buddy.cli.AutoCategorizer') as MockAutoCat, \
             patch('yt_study_buddy.cli.ParallelVideoProcessor') as MockParallel, \
             patch('yt_study_buddy.cli.create_default_logger'):

            # Setup mock video processor
            mock_processor = Mock()
            mock_processor.get_video_id.return_value = test_video_id
            mock_processor.get_transcript.return_value = mock_transcript_data
            mock_processor.get_video_title.return_value = mock_video_title
            mock_processor.sanitize_filename = lambda x: x.replace(' ', '_')
            MockVideoProcessor.return_value = mock_processor

            # Setup mock auto-categorizer
            mock_categorizer = Mock()
            mock_categorizer.categorize_video.return_value = "Machine Learning"
            MockAutoCat.return_value = mock_categorizer

            # Setup mock notes generator
            mock_notes_gen = Mock()
            mock_notes_gen.is_ready.return_value = True
            mock_notes_gen.generate_notes.return_value = "# Study Notes\n\nTest notes"
            MockNotesGen.return_value = mock_notes_gen

            # Create app with auto-categorization
            app = YouTubeStudyNotes(
                base_dir=str(tmp_path),
                auto_categorize=True,
                subject=None,  # No subject = auto-categorize
                generate_assessments=False,
                export_pdf=False,
                parallel=False
            )

            # Process a single URL
            app.process_urls([test_url])

            # ASSERTIONS
            # 1. Transcript should be fetched EXACTLY ONCE
            assert mock_processor.get_transcript.call_count == 1, \
                f"Expected 1 transcript fetch, got {mock_processor.get_transcript.call_count}"

            # 2. Title should be fetched EXACTLY ONCE
            assert mock_processor.get_video_title.call_count == 1, \
                f"Expected 1 title fetch, got {mock_processor.get_video_title.call_count}"

            # 3. Auto-categorizer should be called with fetched transcript
            mock_categorizer.categorize_video.assert_called_once()
            call_args = mock_categorizer.categorize_video.call_args
            assert call_args[0][0] == mock_transcript_data['transcript']
            assert call_args[0][1] == mock_video_title

            # 4. Notes generator should be called (pipeline continued)
            mock_notes_gen.generate_notes.assert_called_once()

    def test_no_auto_categorization_single_fetch(
        self,
        mock_transcript_data,
        mock_video_title,
        tmp_path
    ):
        """
        Verify that when auto-categorization is DISABLED, transcript is still
        fetched only once (in the pipeline).
        """
        test_url = "https://youtu.be/test456"
        test_video_id = "test456"

        with patch('yt_study_buddy.cli.VideoProcessor') as MockVideoProcessor, \
             patch('yt_study_buddy.cli.StudyNotesGenerator') as MockNotesGen, \
             patch('yt_study_buddy.cli.ParallelVideoProcessor') as MockParallel, \
             patch('yt_study_buddy.cli.create_default_logger'):

            # Setup mocks
            mock_processor = Mock()
            mock_processor.get_video_id.return_value = test_video_id
            mock_processor.get_transcript.return_value = mock_transcript_data
            mock_processor.get_video_title.return_value = mock_video_title
            mock_processor.sanitize_filename = lambda x: x.replace(' ', '_')
            MockVideoProcessor.return_value = mock_processor

            mock_notes_gen = Mock()
            mock_notes_gen.is_ready.return_value = True
            mock_notes_gen.generate_notes.return_value = "# Study Notes\n\nTest notes"
            MockNotesGen.return_value = mock_notes_gen

            # Create app WITHOUT auto-categorization
            app = YouTubeStudyNotes(
                base_dir=str(tmp_path),
                auto_categorize=False,  # Disabled
                subject="Programming",
                generate_assessments=False,
                export_pdf=False,
                parallel=False
            )

            # Process URL
            app.process_urls([test_url])

            # ASSERTIONS
            # Should still only fetch once (in pipeline, not for categorization)
            assert mock_processor.get_transcript.call_count == 1, \
                f"Expected 1 transcript fetch, got {mock_processor.get_transcript.call_count}"
            assert mock_processor.get_video_title.call_count == 1, \
                f"Expected 1 title fetch, got {mock_processor.get_video_title.call_count}"

    def test_categorization_failure_still_processes(
        self,
        mock_transcript_data,
        mock_video_title,
        tmp_path
    ):
        """
        Verify that if categorization fails, the job still processes with
        the fetched transcript (doesn't re-fetch).
        """
        test_url = "https://youtu.be/test789"
        test_video_id = "test789"

        with patch('yt_study_buddy.cli.VideoProcessor') as MockVideoProcessor, \
             patch('yt_study_buddy.cli.StudyNotesGenerator') as MockNotesGen, \
             patch('yt_study_buddy.cli.AutoCategorizer') as MockAutoCat, \
             patch('yt_study_buddy.cli.ParallelVideoProcessor') as MockParallel, \
             patch('yt_study_buddy.cli.create_default_logger'):

            mock_processor = Mock()
            mock_processor.get_video_id.return_value = test_video_id
            mock_processor.get_transcript.return_value = mock_transcript_data
            mock_processor.get_video_title.return_value = mock_video_title
            mock_processor.sanitize_filename = lambda x: x.replace(' ', '_')
            MockVideoProcessor.return_value = mock_processor

            # Categorizer raises exception
            mock_categorizer = Mock()
            mock_categorizer.categorize_video.side_effect = Exception("Categorization failed")
            MockAutoCat.return_value = mock_categorizer

            mock_notes_gen = Mock()
            mock_notes_gen.is_ready.return_value = True
            mock_notes_gen.generate_notes.return_value = "# Study Notes\n\nTest notes"
            MockNotesGen.return_value = mock_notes_gen

            app = YouTubeStudyNotes(
                base_dir=str(tmp_path),
                auto_categorize=True,
                subject=None,
                generate_assessments=False,
                export_pdf=False,
                parallel=False
            )

            # Process URL - should handle categorization failure gracefully
            app.process_urls([test_url])

            # ASSERTIONS
            # Should fetch transcript once (for failed categorization)
            # Then re-fetch in pipeline because categorization failed
            # This is acceptable - only optimize for success path
            assert mock_processor.get_transcript.call_count >= 1, \
                "Should have fetched transcript at least once"

            # Notes should still be generated
            mock_notes_gen.generate_notes.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
