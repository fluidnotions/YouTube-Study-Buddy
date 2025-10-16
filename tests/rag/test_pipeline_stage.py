"""
Unit tests for RAGPipelineStage module.

Tests pipeline integration, idempotency, and error handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest
import numpy as np

from src.yt_study_buddy.rag.pipeline_stage import RAGPipelineStage
from src.yt_study_buddy.rag.config import RAGConfig
from src.yt_study_buddy.rag.document_chunker import Chunk, ChunkMetadata
from src.yt_study_buddy.rag.types import ProcessResult


@pytest.fixture
def mock_config():
    """Create a mock RAG configuration."""
    return RAGConfig(
        enabled=True,
        model_name="test-model",
        chunk_size=1000,
        chunk_overlap=50,
        min_chunk_size=50,
    )


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = Mock()
    service.embed_text.return_value = np.zeros(768)
    service.embed_batch.return_value = np.zeros((3, 768))
    return service


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock()
    store.add_chunks.return_value = True
    store.add_chunks_with_embeddings.return_value = True
    store.collection_stats.return_value = {'total_chunks': 0}
    store.health_check.return_value = True
    return store


@pytest.fixture
def mock_chunker():
    """Create a mock document chunker."""
    chunker = Mock()

    # Create mock chunks
    def create_mock_chunks(content, metadata):
        chunks = []
        for i in range(3):
            chunk = Chunk(
                chunk_id=f"{metadata['video_id']}_chunk_{i}",
                content=f"Section {i} content",
                metadata=ChunkMetadata(
                    video_id=metadata['video_id'],
                    video_title=metadata.get('title', 'Test Video'),
                    subject=metadata.get('subject', 'General'),
                    section_title=f"Section {i}",
                    section_level=2,
                    token_count=100,
                    created_at='2025-01-01T00:00:00',
                ),
            )
            chunks.append(chunk)
        return chunks

    chunker.chunk_markdown.side_effect = create_mock_chunks
    return chunker


@pytest.fixture
def mock_index_tracker():
    """Create a mock index tracker."""
    tracker = Mock()
    tracker.needs_reindex.return_value = True
    tracker.get_indexed_videos.return_value = set()
    tracker.mark_indexed.return_value = None
    tracker.get_stats.return_value = {'total_videos_indexed': 0}
    return tracker


@pytest.fixture
def temp_note_file():
    """Create a temporary note file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Test Note

## Section 1

Content for section 1.

## Section 2

Content for section 2.
""")
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestRAGPipelineStageInit:
    """Test RAGPipelineStage initialization."""

    def test_init_with_all_components(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
    ):
        """Test initialization with all components provided."""
        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        assert stage.config == mock_config
        assert stage.embedding_service == mock_embedding_service
        assert stage.vector_store == mock_vector_store
        assert stage.chunker == mock_chunker
        assert stage.index_tracker == mock_index_tracker

    def test_is_ready_all_components(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
    ):
        """Test is_ready when all components are available."""
        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        assert stage.is_ready() is True

    def test_is_ready_missing_components(self, mock_config):
        """Test is_ready when components are missing."""
        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=None,
            vector_store=None,
            chunker=Mock(),  # Chunker is always created
            index_tracker=Mock(),  # IndexTracker is always created
        )

        assert stage.is_ready() is False


class TestRAGPipelineStageProcessNote:
    """Test note processing functionality."""

    def test_process_note_success(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
        temp_note_file,
    ):
        """Test successful note processing."""
        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        video_metadata = {
            'video_id': 'test_video',
            'title': 'Test Video',
            'subject': 'AI',
        }

        result = stage.process_note(temp_note_file, video_metadata)

        assert result.success is True
        assert result.video_id == 'test_video'
        assert result.chunks_created == 3
        assert result.embeddings_generated == 3
        assert not result.skipped

        # Verify components were called
        mock_chunker.chunk_markdown.assert_called_once()
        mock_embedding_service.embed_batch.assert_called_once()
        mock_vector_store.add_chunks_with_embeddings.assert_called_once()
        mock_index_tracker.mark_indexed.assert_called_once()

    def test_process_note_file_not_found(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
    ):
        """Test processing non-existent file."""
        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        result = stage.process_note(
            Path('/nonexistent/file.md'),
            {'video_id': 'test'},
        )

        assert result.success is False
        assert 'does not exist' in result.error_message

    def test_process_note_already_indexed(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
        temp_note_file,
    ):
        """Test processing already-indexed note."""
        # Configure tracker to say note is already indexed
        mock_index_tracker.needs_reindex.return_value = False

        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        result = stage.process_note(
            temp_note_file,
            {'video_id': 'test_video'},
        )

        assert result.success is True
        assert result.skipped is True
        assert 'Already indexed' in result.skip_reason

        # Verify processing was skipped
        mock_chunker.chunk_markdown.assert_not_called()
        mock_embedding_service.embed_batch.assert_not_called()

    def test_process_note_force_reindex(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
        temp_note_file,
    ):
        """Test force reindexing."""
        # Configure tracker to say note is already indexed
        mock_index_tracker.needs_reindex.return_value = False

        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        result = stage.process_note(
            temp_note_file,
            {'video_id': 'test_video'},
            force_reindex=True,
        )

        assert result.success is True
        assert not result.skipped

        # Verify processing happened despite being indexed
        mock_chunker.chunk_markdown.assert_called_once()

    def test_process_note_no_chunks_created(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_index_tracker,
        temp_note_file,
    ):
        """Test when chunker returns no chunks."""
        # Create a fresh chunker mock that returns empty list
        empty_chunker = Mock()
        empty_chunker.chunk_markdown.return_value = []

        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=empty_chunker,
            index_tracker=mock_index_tracker,
        )

        result = stage.process_note(
            temp_note_file,
            {'video_id': 'test_video'},
        )

        assert result.success is True
        assert result.skipped is True
        assert 'No valid chunks' in result.skip_reason
        assert result.chunks_created == 0

    def test_process_note_vector_store_failure(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
        temp_note_file,
    ):
        """Test handling vector store failure."""
        # Configure vector store to fail
        mock_vector_store.add_chunks_with_embeddings.return_value = False

        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        result = stage.process_note(
            temp_note_file,
            {'video_id': 'test_video'},
        )

        assert result.success is False
        assert 'Failed to store chunks' in result.error_message

    def test_process_note_exception_handling(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
        temp_note_file,
    ):
        """Test exception handling during processing."""
        # Configure chunker to raise exception
        mock_chunker.chunk_markdown.side_effect = Exception("Test error")

        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        result = stage.process_note(
            temp_note_file,
            {'video_id': 'test_video'},
        )

        assert result.success is False
        assert 'Test error' in result.error_message


class TestRAGPipelineStageBatchProcessing:
    """Test batch processing functionality."""

    def test_process_batch(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
    ):
        """Test batch processing of multiple notes."""
        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        # Create temporary notes
        notes = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                note_path = Path(tmpdir) / f"note{i}.md"
                note_path.write_text(f"# Note {i}\n\nContent")
                metadata = {
                    'video_id': f'video_{i}',
                    'title': f'Video {i}',
                }
                notes.append((note_path, metadata))

            results = stage.process_batch(notes)

            assert len(results) == 3
            assert all(r.success for r in results)

    def test_process_batch_mixed_results(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
    ):
        """Test batch with some failures."""
        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        notes = []
        with tempfile.TemporaryDirectory() as tmpdir:
            # Valid note
            note1 = Path(tmpdir) / "note1.md"
            note1.write_text("# Note 1")
            notes.append((note1, {'video_id': 'video_1'}))

            # Invalid note (doesn't exist)
            notes.append((Path('/nonexistent.md'), {'video_id': 'video_2'}))

            results = stage.process_batch(notes)

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False


class TestRAGPipelineStageUtilities:
    """Test utility methods."""

    def test_is_note_indexed(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
    ):
        """Test checking if note is indexed."""
        mock_index_tracker.get_indexed_videos.return_value = {'video_1', 'video_2'}

        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        assert stage.is_note_indexed('video_1') is True
        assert stage.is_note_indexed('video_3') is False

    def test_get_stats(
        self,
        mock_config,
        mock_embedding_service,
        mock_vector_store,
        mock_chunker,
        mock_index_tracker,
    ):
        """Test getting statistics."""
        mock_index_tracker.get_stats.return_value = {
            'total_videos_indexed': 5,
            'total_chunks_created': 15,
        }
        mock_vector_store.collection_stats.return_value = {
            'total_chunks': 15,
        }

        stage = RAGPipelineStage(
            config=mock_config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunker=mock_chunker,
            index_tracker=mock_index_tracker,
        )

        stats = stage.get_stats()

        assert stats['ready'] is True
        assert stats['tracker']['total_videos_indexed'] == 5
        assert stats['vector_store']['total_chunks'] == 15
        assert stats['config']['enabled'] is True
