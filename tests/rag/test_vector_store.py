"""Unit tests for vector store module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from yt_study_buddy.rag.vector_store import VectorStore, SearchResult
from yt_study_buddy.rag.document_chunker import Chunk, ChunkMetadata


class TestSearchResult:
    """Tests for SearchResult dataclass."""
    
    def test_create_search_result(self):
        """Test creating a search result."""
        result = SearchResult(
            chunk_id="test123_abc",
            content="Test content",
            metadata={"video_id": "test123"},
            similarity_score=0.85,
            distance=0.15,
        )
        
        assert result.chunk_id == "test123_abc"
        assert result.content == "Test content"
        assert result.metadata["video_id"] == "test123"
        assert result.similarity_score == 0.85
        assert result.distance == 0.15


class TestVectorStore:
    """Tests for VectorStore class."""
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_init(self, mock_client):
        """Test initializing vector store."""
        store = VectorStore(
            persist_dir="/test/dir",
            collection_name="test_collection",
        )
        
        assert store.persist_dir == Path("/test/dir")
        assert store.collection_name == "test_collection"
        assert store._client is None  # Lazy loading
        assert store._collection is None
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_lazy_client_loading(self, mock_client_class):
        """Test that client is loaded lazily."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        # Client should not be loaded yet
        assert store._client is None
        
        # Access client property
        client = store.client
        
        # Now client should be loaded
        assert client == mock_client
        mock_client_class.assert_called_once()
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_client_loading_failure(self, mock_client_class):
        """Test handling of client loading failure."""
        mock_client_class.side_effect = Exception("ChromaDB error")
        
        store = VectorStore("/test/dir", "test_collection")
        
        with pytest.raises(RuntimeError, match="Could not initialize ChromaDB"):
            _ = store.client
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_lazy_collection_loading(self, mock_client_class):
        """Test that collection is loaded lazily."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        # Collection should not be loaded yet
        assert store._collection is None
        
        # Access collection property
        collection = store.collection
        
        # Now collection should be loaded
        assert collection == mock_collection
        mock_client.get_or_create_collection.assert_called_once_with(
            name="test_collection",
            metadata={"description": "YouTube study notes embeddings"},
        )
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_collection_loading_failure(self, mock_client_class):
        """Test handling of collection loading failure."""
        mock_client = Mock()
        mock_client.get_or_create_collection.side_effect = Exception("Collection error")
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        with pytest.raises(RuntimeError, match="Could not access collection"):
            _ = store.collection
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_add_chunks_success(self, mock_client_class):
        """Test successfully adding chunks."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        # Create test chunks
        chunks = [
            Chunk(
                chunk_id="test123_abc",
                content="Test content 1",
                metadata=ChunkMetadata(
                    video_id="test123",
                    video_title="Test Video",
                    subject="Testing",
                    section_title="Introduction",
                    section_level=2,
                    token_count=50,
                    created_at="2025-01-01T00:00:00",
                ),
            ),
            Chunk(
                chunk_id="test123_def",
                content="Test content 2",
                metadata=ChunkMetadata(
                    video_id="test123",
                    video_title="Test Video",
                    subject="Testing",
                    section_title="Conclusion",
                    section_level=2,
                    token_count=60,
                    created_at="2025-01-01T00:00:00",
                ),
            ),
        ]
        
        result = store.add_chunks(chunks)
        
        assert result is True
        mock_collection.add.assert_called_once()
        
        # Check call arguments
        call_args = mock_collection.add.call_args[1]
        assert len(call_args['ids']) == 2
        assert len(call_args['documents']) == 2
        assert len(call_args['metadatas']) == 2
        assert call_args['ids'][0] == "test123_abc"
        assert call_args['documents'][0] == "Test content 1"
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_add_chunks_empty_list(self, mock_client_class):
        """Test adding empty chunks list."""
        store = VectorStore("/test/dir", "test_collection")
        
        with pytest.raises(ValueError, match="Chunks list cannot be empty"):
            store.add_chunks([])
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_add_chunks_failure(self, mock_client_class):
        """Test handling of add chunks failure."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Add error")
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        chunks = [
            Chunk(
                chunk_id="test123_abc",
                content="Test content",
                metadata=ChunkMetadata(
                    video_id="test123",
                    video_title="Test Video",
                    subject="Testing",
                    section_title="Introduction",
                    section_level=2,
                    token_count=50,
                    created_at="2025-01-01T00:00:00",
                ),
            ),
        ]
        
        result = store.add_chunks(chunks)
        
        assert result is False
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_add_chunks_with_embeddings_success(self, mock_client_class):
        """Test adding chunks with pre-computed embeddings."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        chunks = [
            Chunk(
                chunk_id="test123_abc",
                content="Test content",
                metadata=ChunkMetadata(
                    video_id="test123",
                    video_title="Test Video",
                    subject="Testing",
                    section_title="Introduction",
                    section_level=2,
                    token_count=50,
                    created_at="2025-01-01T00:00:00",
                ),
            ),
        ]
        
        embeddings = np.array([[0.1, 0.2, 0.3]])
        
        result = store.add_chunks_with_embeddings(chunks, embeddings)
        
        assert result is True
        mock_collection.add.assert_called_once()
        
        # Check embeddings are converted to list
        call_args = mock_collection.add.call_args[1]
        assert 'embeddings' in call_args
        assert call_args['embeddings'][0] == [0.1, 0.2, 0.3]
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_add_chunks_with_embeddings_mismatch(self, mock_client_class):
        """Test error when chunks and embeddings don't match."""
        store = VectorStore("/test/dir", "test_collection")
        
        chunks = [Mock(), Mock()]
        embeddings = np.array([[0.1, 0.2, 0.3]])  # Only 1 embedding for 2 chunks
        
        with pytest.raises(ValueError, match="must match number of embeddings"):
            store.add_chunks_with_embeddings(chunks, embeddings)
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_search_similar_success(self, mock_client_class):
        """Test successful similarity search."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'ids': [['chunk1', 'chunk2']],
            'documents': [['Content 1', 'Content 2']],
            'metadatas': [[{'video_id': 'test123'}, {'video_id': 'test456'}]],
            'distances': [[0.1, 0.3]],
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        query_embedding = np.array([0.5, 0.6, 0.7])
        results = store.search_similar(query_embedding, top_k=2)
        
        assert len(results) == 2
        assert results[0].chunk_id == 'chunk1'
        assert results[0].content == 'Content 1'
        assert results[0].metadata['video_id'] == 'test123'
        assert results[0].distance == 0.1
        # Similarity score should be calculated from distance
        assert results[0].similarity_score > 0
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_search_similar_with_filters(self, mock_client_class):
        """Test search with metadata filters."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'documents': [['Content 1']],
            'metadatas': [[{'video_id': 'test123'}]],
            'distances': [[0.1]],
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        query_embedding = np.array([0.5, 0.6, 0.7])
        filters = {"subject": "AI", "video_id": {"$ne": "exclude123"}}
        results = store.search_similar(query_embedding, filters=filters, top_k=5)
        
        # Check that filters were passed correctly
        call_args = mock_collection.query.call_args[1]
        assert call_args['where'] is not None
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_search_similar_empty_embedding(self, mock_client_class):
        """Test search with empty embedding."""
        store = VectorStore("/test/dir", "test_collection")
        
        with pytest.raises(ValueError, match="Query embedding cannot be empty"):
            store.search_similar(np.array([]))
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_search_similar_no_results(self, mock_client_class):
        """Test search when no results are found."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        query_embedding = np.array([0.5, 0.6, 0.7])
        results = store.search_similar(query_embedding, top_k=5)
        
        assert results == []
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_build_where_clause(self, mock_client_class):
        """Test building where clause from filters."""
        store = VectorStore("/test/dir", "test_collection")
        
        # Simple equality filter
        where = store._build_where_clause({"subject": "AI"})
        assert where == {"subject": {"$eq": "AI"}}
        
        # Operator filter
        where = store._build_where_clause({"video_id": {"$ne": "test123"}})
        assert where == {"video_id": {"$ne": "test123"}}
        
        # Mixed filters
        where = store._build_where_clause({"subject": "AI", "video_id": {"$ne": "test123"}})
        assert where["subject"] == {"$eq": "AI"}
        assert where["video_id"] == {"$ne": "test123"}
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_delete_by_video_id_success(self, mock_client_class):
        """Test deleting chunks by video ID."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.return_value = {'ids': ['chunk1', 'chunk2', 'chunk3']}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        result = store.delete_by_video_id("test123")
        
        assert result is True
        mock_collection.get.assert_called_once()
        mock_collection.delete.assert_called_once_with(ids=['chunk1', 'chunk2', 'chunk3'])
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_delete_by_video_id_no_chunks(self, mock_client_class):
        """Test deleting when no chunks exist for video."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.return_value = {'ids': []}
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        result = store.delete_by_video_id("test123")
        
        assert result is True
        mock_collection.delete.assert_not_called()
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_delete_by_video_id_failure(self, mock_client_class):
        """Test handling of delete failure."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.side_effect = Exception("Delete error")
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        result = store.delete_by_video_id("test123")
        
        assert result is False
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_collection_stats(self, mock_client_class):
        """Test getting collection statistics."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.return_value = 100
        mock_collection.get.return_value = {
            'metadatas': [
                {'video_id': 'vid1', 'subject': 'AI'},
                {'video_id': 'vid2', 'subject': 'ML'},
                {'video_id': 'vid1', 'subject': 'AI'},
            ]
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        stats = store.collection_stats()
        
        assert stats['collection_name'] == 'test_collection'
        assert stats['total_chunks'] == 100
        assert 'persist_dir' in stats
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_collection_stats_failure(self, mock_client_class):
        """Test handling of stats retrieval failure."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.side_effect = Exception("Stats error")
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        stats = store.collection_stats()
        
        assert 'error' in stats
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_health_check_success(self, mock_client_class):
        """Test successful health check."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.return_value = 50
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        result = store.health_check()
        
        assert result is True
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_health_check_failure(self, mock_client_class):
        """Test health check failure."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.side_effect = Exception("Health check error")
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        
        result = store.health_check()
        
        assert result is False
    
    @patch('yt_study_buddy.rag.vector_store.chromadb.Client')
    def test_reset_collection(self, mock_client_class):
        """Test resetting collection."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        store = VectorStore("/test/dir", "test_collection")
        _ = store.collection  # Load collection
        
        result = store.reset_collection()
        
        assert result is True
        mock_client.delete_collection.assert_called_once_with(name="test_collection")
        # Collection should be reset to None
        assert store._collection is None
