"""Tests for RAG cross-referencer module."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from src.yt_study_buddy.rag.cross_referencer import RAGCrossReferencer, CrossReference
from src.yt_study_buddy.rag.config import RAGConfig
from src.yt_study_buddy.rag.vector_store import SearchResult


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = Mock()
    service.embed_text = Mock(return_value=np.random.rand(768))
    service.embed_batch = Mock(return_value=np.random.rand(10, 768))
    service.get_embedding_dim = Mock(return_value=768)
    return service


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    store = Mock()
    store.search_similar = Mock(return_value=[])
    store.collection_stats = Mock(return_value={'total_chunks': 100})
    store.health_check = Mock(return_value=True)
    return store


@pytest.fixture
def rag_config():
    """Sample RAG configuration."""
    return RAGConfig(
        enabled=True,
        model_name="all-mpnet-base-v2",
        similarity_threshold=0.3,
        max_results=5,
    )


@pytest.fixture
def cross_referencer(mock_embedding_service, mock_vector_store, rag_config):
    """Create cross-referencer with mocked dependencies."""
    return RAGCrossReferencer(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        config=rag_config,
    )


class TestCrossReference:
    """Test CrossReference dataclass."""

    def test_creates_obsidian_link(self):
        """Test that obsidian link is generated correctly."""
        ref = CrossReference(
            target_section="Introduction",
            target_video_id="abc123",
            target_video_title="Machine Learning Basics",
            similarity_score=0.85,
            preview_text="This section covers...",
        )

        assert ref.obsidian_link == "[[Machine Learning Basics#Introduction]]"

    def test_handles_special_characters_in_title(self):
        """Test that special characters are handled correctly."""
        ref = CrossReference(
            target_section="What is [[AI]]?",
            target_video_id="xyz789",
            target_video_title="AI & Machine Learning",
            similarity_score=0.75,
            preview_text="Preview text",
        )

        # Should strip nested [[]] from section name
        assert "[[" in ref.obsidian_link
        assert ref.target_video_title in ref.obsidian_link


class TestRAGCrossReferencer:
    """Test RAGCrossReferencer class."""

    def test_initialization(self, cross_referencer):
        """Test cross-referencer initializes correctly."""
        assert cross_referencer is not None
        assert cross_referencer.config.similarity_threshold == 0.3
        assert cross_referencer.config.max_results == 5

    def test_find_references_short_text(self, cross_referencer):
        """Test that short text returns empty results."""
        results = cross_referencer.find_references(
            section_text="Short",
            current_video_id="test123",
        )

        assert results == []

    def test_find_references_no_results(self, cross_referencer, mock_vector_store):
        """Test finding references when no results from vector store."""
        mock_vector_store.search_similar.return_value = []

        results = cross_referencer.find_references(
            section_text="This is a test section about machine learning algorithms.",
            current_video_id="test123",
        )

        assert results == []
        assert mock_vector_store.search_similar.called

    def test_find_references_with_results(self, cross_referencer, mock_vector_store):
        """Test finding references with mock results."""
        # Create mock search results
        mock_results = [
            SearchResult(
                chunk_id="chunk1",
                content="This is related content about neural networks.",
                metadata={
                    'video_id': 'video1',
                    'video_title': 'Deep Learning Introduction',
                    'section_title': 'Neural Networks',
                    'subject': 'AI',
                },
                similarity_score=0.85,
                distance=0.15,
            ),
            SearchResult(
                chunk_id="chunk2",
                content="Another related section about backpropagation.",
                metadata={
                    'video_id': 'video2',
                    'video_title': 'Neural Network Training',
                    'section_title': 'Backpropagation',
                    'subject': 'AI',
                },
                similarity_score=0.75,
                distance=0.25,
            ),
        ]

        mock_vector_store.search_similar.return_value = mock_results

        results = cross_referencer.find_references(
            section_text="This section discusses gradient descent and neural network training methods.",
            current_video_id="test123",
        )

        assert len(results) == 2
        assert isinstance(results[0], CrossReference)
        assert results[0].target_video_title == "Deep Learning Introduction"
        assert results[0].similarity_score == 0.85
        assert results[1].target_video_title == "Neural Network Training"

    def test_find_references_filters_by_threshold(self, cross_referencer, mock_vector_store):
        """Test that results below threshold are filtered out."""
        # Create mock results with varying similarity scores
        mock_results = [
            SearchResult(
                chunk_id="chunk1",
                content="High similarity content",
                metadata={
                    'video_id': 'video1',
                    'video_title': 'High Similarity Video',
                    'section_title': 'Section 1',
                    'subject': 'AI',
                },
                similarity_score=0.85,
                distance=0.15,
            ),
            SearchResult(
                chunk_id="chunk2",
                content="Low similarity content",
                metadata={
                    'video_id': 'video2',
                    'video_title': 'Low Similarity Video',
                    'section_title': 'Section 2',
                    'subject': 'AI',
                },
                similarity_score=0.2,  # Below threshold (0.3)
                distance=0.8,
            ),
        ]

        mock_vector_store.search_similar.return_value = mock_results

        results = cross_referencer.find_references(
            section_text="Test section content for similarity filtering.",
            current_video_id="test123",
        )

        # Should only include the high similarity result
        assert len(results) == 1
        assert results[0].similarity_score == 0.85

    def test_find_references_deduplicates(self, cross_referencer, mock_vector_store):
        """Test that duplicate videos are removed."""
        # Create mock results with same video ID
        mock_results = [
            SearchResult(
                chunk_id="chunk1",
                content="First section from video",
                metadata={
                    'video_id': 'video1',
                    'video_title': 'Test Video',
                    'section_title': 'Section A',
                    'subject': 'AI',
                },
                similarity_score=0.85,
                distance=0.15,
            ),
            SearchResult(
                chunk_id="chunk2",
                content="Second section from same video",
                metadata={
                    'video_id': 'video1',  # Same video
                    'video_title': 'Test Video',
                    'section_title': 'Section B',
                    'subject': 'AI',
                },
                similarity_score=0.75,
                distance=0.25,
            ),
        ]

        mock_vector_store.search_similar.return_value = mock_results

        results = cross_referencer.find_references(
            section_text="Test section for deduplication.",
            current_video_id="test123",
        )

        # Should only keep first result from each video
        assert len(results) == 1
        assert results[0].target_section == "Section A"

    def test_find_references_with_subject_filter(self, cross_referencer, mock_vector_store):
        """Test finding references with subject filter."""
        results = cross_referencer.find_references(
            section_text="Test content about AI and machine learning.",
            current_video_id="test123",
            subject="AI",
            global_context=False,
        )

        # Verify that search_similar was called with subject filter
        call_args = mock_vector_store.search_similar.call_args
        assert call_args[1]['filters']['subject'] == 'AI'

    def test_find_references_global_context(self, cross_referencer, mock_vector_store):
        """Test finding references with global context (no subject filter)."""
        results = cross_referencer.find_references(
            section_text="Test content for global search.",
            current_video_id="test123",
            subject="AI",
            global_context=True,
        )

        # Verify that search_similar was called without subject filter
        call_args = mock_vector_store.search_similar.call_args
        filters = call_args[1]['filters']
        assert 'subject' not in filters or filters.get('subject') is None

    def test_format_as_obsidian_link(self, cross_referencer):
        """Test formatting cross-reference as Obsidian link."""
        ref = CrossReference(
            target_section="Introduction",
            target_video_id="abc123",
            target_video_title="Machine Learning",
            similarity_score=0.8,
            preview_text="Preview",
        )

        link = cross_referencer.format_as_obsidian_link(ref)
        assert link == "[[Machine Learning#Introduction]]"

    def test_batch_find_references(self, cross_referencer, mock_vector_store):
        """Test batch processing of multiple sections."""
        sections = [
            ("Section 1", "Content about neural networks and deep learning."),
            ("Section 2", "Content about supervised learning algorithms."),
            ("Section 3", "Content about reinforcement learning methods."),
        ]

        mock_vector_store.search_similar.return_value = []

        results = cross_referencer.batch_find_references(
            sections=sections,
            current_video_id="test123",
        )

        assert isinstance(results, dict)
        assert len(results) == 3
        assert "Section 1" in results
        assert "Section 2" in results
        assert "Section 3" in results

    def test_error_handling(self, cross_referencer, mock_vector_store):
        """Test error handling when vector store fails."""
        mock_vector_store.search_similar.side_effect = Exception("Database error")

        results = cross_referencer.find_references(
            section_text="Test content that will cause an error.",
            current_video_id="test123",
        )

        # Should return empty list on error
        assert results == []
