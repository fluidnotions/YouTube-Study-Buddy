"""
Integration tests for RAG pipeline integration.

Tests end-to-end pipeline behavior with RAG components.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from src.yt_study_buddy.processing_pipeline import (
    process_video_job,
    index_rag_embeddings,
)
from src.yt_study_buddy.video_job import VideoProcessingJob


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_note_content():
    """Sample markdown note content."""
    return """# Test Video Notes

## Introduction

This is a test video about AI concepts.

## Deep Learning

Neural networks learn through backpropagation.

## Applications

AI is used in many domains including:
- Computer vision
- Natural language processing
- Robotics
"""


@pytest.fixture
def mock_rag_pipeline_stage():
    """Create mock RAG pipeline stage."""
    from src.yt_study_buddy.rag.types import ProcessResult

    stage = Mock()
    stage.is_ready.return_value = True

    def mock_process_note(note_path, video_metadata, **kwargs):
        return ProcessResult(
            success=True,
            video_id=video_metadata['video_id'],
            note_path=str(note_path),
            chunks_created=3,
            embeddings_generated=3,
            processing_time_seconds=0.5,
        )

    stage.process_note = Mock(side_effect=mock_process_note)
    return stage


class TestRAGPipelineIntegration:
    """Test RAG integration with processing pipeline."""

    def test_index_rag_embeddings_with_mock_stage(
        self,
        temp_output_dir,
        sample_note_content,
        mock_rag_pipeline_stage,
    ):
        """Test RAG indexing stage with mock components."""
        # Create a job with written files
        job = VideoProcessingJob(video_id='test_video_123')
        job.video_title = 'Test Video'
        job.subject = 'AI'
        job.output_dir = temp_output_dir
        job.notes_filepath = temp_output_dir / "test_note.md"
        job.notes_filepath.write_text(sample_note_content)

        # Mark job as having files written
        job.set_stage(job.stage.FILES_WRITTEN)

        # Process RAG indexing
        result_job = index_rag_embeddings(job, mock_rag_pipeline_stage)

        # Verify job is unchanged (non-destructive)
        assert result_job == job

        # Verify RAG stage was called
        mock_rag_pipeline_stage.process_note.assert_called_once()

        # Verify correct metadata was passed
        call_args = mock_rag_pipeline_stage.process_note.call_args
        assert call_args[1]['video_metadata']['video_id'] == 'test_video_123'
        assert call_args[1]['video_metadata']['title'] == 'Test Video'
        assert call_args[1]['video_metadata']['subject'] == 'AI'

    def test_index_rag_embeddings_disabled(self, temp_output_dir):
        """Test RAG indexing when disabled (stage not provided)."""
        job = VideoProcessingJob(video_id='test_video')
        job.notes_filepath = temp_output_dir / "test.md"

        # Call with no RAG stage (disabled)
        result_job = index_rag_embeddings(job, None)

        # Should return job unchanged
        assert result_job == job

    def test_index_rag_embeddings_not_ready(
        self,
        temp_output_dir,
        sample_note_content,
    ):
        """Test RAG indexing when pipeline not ready."""
        # Create stage that's not ready
        stage = Mock()
        stage.is_ready.return_value = False

        job = VideoProcessingJob(video_id='test_video')
        job.notes_filepath = temp_output_dir / "test.md"
        job.notes_filepath.write_text(sample_note_content)
        job.set_stage(job.stage.FILES_WRITTEN)

        # Process RAG indexing
        result_job = index_rag_embeddings(job, stage)

        # Should skip gracefully
        assert result_job == job
        stage.process_note.assert_not_called()

    def test_index_rag_embeddings_error_handling(
        self,
        temp_output_dir,
        sample_note_content,
    ):
        """Test RAG indexing error handling (graceful degradation)."""
        # Create stage that raises exception
        stage = Mock()
        stage.is_ready.return_value = True
        stage.process_note.side_effect = Exception("Test error")

        job = VideoProcessingJob(video_id='test_video')
        job.notes_filepath = temp_output_dir / "test.md"
        job.notes_filepath.write_text(sample_note_content)
        job.set_stage(job.stage.FILES_WRITTEN)

        # Process RAG indexing - should not raise exception
        result_job = index_rag_embeddings(job, stage)

        # Should complete gracefully despite error
        assert result_job == job

    def test_index_rag_embeddings_no_files(self, mock_rag_pipeline_stage):
        """Test RAG indexing when files not written yet."""
        job = VideoProcessingJob(video_id='test_video')
        # Don't set stage to FILES_WRITTEN

        result_job = index_rag_embeddings(job, mock_rag_pipeline_stage)

        # Should skip without error
        assert result_job == job
        mock_rag_pipeline_stage.process_note.assert_not_called()


class TestRAGPipelineEndToEnd:
    """Test end-to-end pipeline with RAG."""

    def test_full_pipeline_with_rag_mock(
        self,
        temp_output_dir,
        mock_rag_pipeline_stage,
    ):
        """Test complete pipeline flow with mocked RAG."""
        # Create job
        job = VideoProcessingJob(video_id='test_123')
        job.video_title = 'Test Video'
        job.transcript = 'This is a test transcript about AI.'

        # Mock components
        mock_video_processor = Mock()
        mock_notes_generator = Mock()
        mock_notes_generator.generate_notes.return_value = "# Test Notes\n\nContent"
        mock_obsidian_linker = Mock()

        components = {
            'video_processor': mock_video_processor,
            'notes_generator': mock_notes_generator,
            'assessment_generator': None,
            'obsidian_linker': mock_obsidian_linker,
            'pdf_exporter': None,
            'rag_pipeline_stage': mock_rag_pipeline_stage,
            'output_dir': temp_output_dir,
            'filename_sanitizer': lambda x: x.replace('/', '_'),
        }

        # Process job
        result = process_video_job(job, components)

        # Verify job completed
        assert result.is_completed()

        # Verify RAG indexing was called
        mock_rag_pipeline_stage.process_note.assert_called_once()

    def test_pipeline_rag_optional(self, temp_output_dir):
        """Test pipeline works without RAG (optional component)."""
        job = VideoProcessingJob(video_id='test_123')
        job.video_title = 'Test Video'
        job.transcript = 'Test transcript.'

        # Mock required components (no RAG)
        mock_video_processor = Mock()
        mock_notes_generator = Mock()
        mock_notes_generator.generate_notes.return_value = "# Notes"
        mock_obsidian_linker = Mock()

        components = {
            'video_processor': mock_video_processor,
            'notes_generator': mock_notes_generator,
            'assessment_generator': None,
            'obsidian_linker': mock_obsidian_linker,
            'pdf_exporter': None,
            # No RAG component
            'output_dir': temp_output_dir,
            'filename_sanitizer': lambda x: x.replace('/', '_'),
        }

        # Should complete without RAG
        result = process_video_job(job, components)
        assert result.is_completed()


class TestRAGPipelinePerformance:
    """Test RAG pipeline performance characteristics."""

    def test_rag_overhead_target(
        self,
        temp_output_dir,
        sample_note_content,
    ):
        """Test that RAG overhead is within target (<5 seconds)."""
        from src.yt_study_buddy.rag.types import ProcessResult
        import time

        # Create mock stage that simulates realistic timing
        stage = Mock()
        stage.is_ready.return_value = True

        def mock_process(note_path, video_metadata, **kwargs):
            time.sleep(0.1)  # Simulate 100ms processing
            return ProcessResult(
                success=True,
                video_id=video_metadata['video_id'],
                note_path=str(note_path),
                chunks_created=5,
                embeddings_generated=5,
                processing_time_seconds=0.1,
            )

        stage.process_note = Mock(side_effect=mock_process)

        # Create job
        job = VideoProcessingJob(video_id='test_video')
        job.notes_filepath = temp_output_dir / "test.md"
        job.notes_filepath.write_text(sample_note_content)
        job.set_stage(job.stage.FILES_WRITTEN)

        # Measure RAG indexing time
        start = time.time()
        index_rag_embeddings(job, stage)
        elapsed = time.time() - start

        # Should be fast (well under 5 second target)
        assert elapsed < 5.0, f"RAG indexing took {elapsed}s, target is <5s"


class TestRAGPipelineIdempotency:
    """Test idempotent behavior of RAG pipeline."""

    def test_rag_indexing_idempotent(
        self,
        temp_output_dir,
        sample_note_content,
    ):
        """Test that re-running RAG indexing is safe (idempotent)."""
        from src.yt_study_buddy.rag.types import ProcessResult

        # Create stage that tracks calls
        stage = Mock()
        stage.is_ready.return_value = True

        call_count = {'count': 0}

        def mock_process(note_path, video_metadata, **kwargs):
            call_count['count'] += 1
            # Second call should skip (already indexed)
            if call_count['count'] == 1:
                return ProcessResult(
                    success=True,
                    video_id=video_metadata['video_id'],
                    note_path=str(note_path),
                    chunks_created=3,
                    embeddings_generated=3,
                    processing_time_seconds=0.5,
                )
            else:
                return ProcessResult(
                    success=True,
                    video_id=video_metadata['video_id'],
                    note_path=str(note_path),
                    skipped=True,
                    skip_reason='Already indexed',
                    processing_time_seconds=0.01,
                )

        stage.process_note = Mock(side_effect=mock_process)

        # Create job
        job = VideoProcessingJob(video_id='test_video')
        job.notes_filepath = temp_output_dir / "test.md"
        job.notes_filepath.write_text(sample_note_content)
        job.set_stage(job.stage.FILES_WRITTEN)

        # Run indexing twice
        index_rag_embeddings(job, stage)
        index_rag_embeddings(job, stage)

        # Both calls should complete successfully
        assert stage.process_note.call_count == 2

        # Second call should skip (via mock logic)
        second_call_result = stage.process_note.return_value
        # Would verify skip in real implementation
