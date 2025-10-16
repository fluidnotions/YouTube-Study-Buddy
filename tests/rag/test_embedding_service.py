"""Unit tests for embedding service module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from yt_study_buddy.rag.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Tests for EmbeddingService class."""
    
    def test_init_default_values(self):
        """Test initializing service with default values."""
        service = EmbeddingService()
        
        assert service.model_name == "all-mpnet-base-v2"
        assert service.cache_dir is None
        assert service.device in ("cuda", "mps", "cpu")
        assert service._model is None  # Lazy loading
    
    def test_init_custom_values(self):
        """Test initializing service with custom values."""
        service = EmbeddingService(
            model_name="custom-model",
            cache_dir="/custom/cache",
            device="cpu",
        )
        
        assert service.model_name == "custom-model"
        assert service.cache_dir == "/custom/cache"
        assert service.device == "cpu"
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_lazy_model_loading(self, mock_st):
        """Test that model is loaded lazily."""
        mock_model = Mock()
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        # Model should not be loaded yet
        assert service._model is None
        
        # Access model property
        model = service.model
        
        # Now model should be loaded
        assert model == mock_model
        mock_st.assert_called_once()
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_model_loading_failure(self, mock_st):
        """Test handling of model loading failure."""
        mock_st.side_effect = Exception("Model not found")
        
        service = EmbeddingService()
        
        with pytest.raises(RuntimeError, match="Could not load embedding model"):
            _ = service.model
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_text_success(self, mock_st):
        """Test successful text embedding."""
        mock_model = Mock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_model.encode.return_value = mock_embedding
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        result = service.embed_text("test text")
        
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, mock_embedding)
        mock_model.encode.assert_called_once_with(
            "test text",
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_text_empty_input(self, mock_st):
        """Test embedding with empty text."""
        mock_model = Mock()
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            service.embed_text("")
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            service.embed_text("   ")
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_text_failure(self, mock_st):
        """Test handling of embedding generation failure."""
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Encoding error")
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(RuntimeError, match="Embedding generation failed"):
            service.embed_text("test")
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_batch_success(self, mock_st):
        """Test successful batch embedding."""
        mock_model = Mock()
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ])
        mock_model.encode.return_value = mock_embeddings
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        texts = ["text 1", "text 2", "text 3"]
        result = service.embed_batch(texts)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 3)
        np.testing.assert_array_equal(result, mock_embeddings)
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_batch_with_batch_size(self, mock_st):
        """Test batch embedding with custom batch size."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_model.encode.return_value = mock_embeddings
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        texts = ["text 1", "text 2"]
        result = service.embed_batch(texts, batch_size=16, show_progress=True)
        
        mock_model.encode.assert_called_once_with(
            texts,
            batch_size=16,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_batch_empty_list(self, mock_st):
        """Test batch embedding with empty list."""
        mock_model = Mock()
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            service.embed_batch([])
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_batch_all_empty_texts(self, mock_st):
        """Test batch embedding with all empty texts."""
        mock_model = Mock()
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(ValueError, match="All texts are empty or invalid"):
            service.embed_batch(["", "   ", ""])
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_batch_with_some_empty_texts(self, mock_st):
        """Test batch embedding with some empty texts."""
        mock_model = Mock()
        mock_embeddings = np.array([
            [0.1, 0.2],
            [0.3, 0.4],
        ])
        mock_model.encode.return_value = mock_embeddings
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        texts = ["text 1", "", "text 2", "   "]
        result = service.embed_batch(texts)
        
        # Should return array with zeros for empty texts
        assert result.shape == (4, 2)
        np.testing.assert_array_equal(result[0], [0.1, 0.2])
        np.testing.assert_array_equal(result[1], [0.0, 0.0])
        np.testing.assert_array_equal(result[2], [0.3, 0.4])
        np.testing.assert_array_equal(result[3], [0.0, 0.0])
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_embed_batch_failure(self, mock_st):
        """Test handling of batch embedding failure."""
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Batch encoding error")
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(RuntimeError, match="Batch embedding generation failed"):
            service.embed_batch(["text 1", "text 2"])
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_get_embedding_dim(self, mock_st):
        """Test getting embedding dimension."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        dim = service.get_embedding_dim()
        
        assert dim == 768
        mock_model.get_sentence_embedding_dimension.assert_called_once()
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_model_info(self, mock_st):
        """Test getting model information."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.max_seq_length = 512
        mock_st.return_value = mock_model
        
        service = EmbeddingService(
            model_name="test-model",
            cache_dir="/cache",
            device="cpu",
        )
        
        info = service.model_info()
        
        assert info["model_name"] == "test-model"
        assert info["device"] == "cpu"
        assert info["embedding_dim"] == 768
        assert info["cache_dir"] == "/cache"
        assert info["max_seq_length"] == 512
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    def test_model_info_no_max_seq_length(self, mock_st):
        """Test model info when max_seq_length is not available."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        # Simulate missing max_seq_length attribute
        del mock_model.max_seq_length
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        
        info = service.model_info()
        
        assert info["max_seq_length"] is None
    
    @patch('yt_study_buddy.rag.embedding_service.torch')
    def test_device_detection_cuda(self, mock_torch):
        """Test CUDA device detection."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.backends.mps.is_available.return_value = False
        
        service = EmbeddingService()
        
        assert service.device == "cuda"
    
    @patch('yt_study_buddy.rag.embedding_service.torch')
    def test_device_detection_mps(self, mock_torch):
        """Test MPS device detection."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        
        service = EmbeddingService()
        
        assert service.device == "mps"
    
    @patch('yt_study_buddy.rag.embedding_service.torch')
    def test_device_detection_cpu(self, mock_torch):
        """Test CPU fallback."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        
        service = EmbeddingService()
        
        assert service.device == "cpu"
    
    @patch('yt_study_buddy.rag.embedding_service.SentenceTransformer')
    @patch('yt_study_buddy.rag.embedding_service.torch')
    def test_cleanup_on_delete(self, mock_torch, mock_st):
        """Test cleanup when service is deleted."""
        mock_model = Mock()
        mock_st.return_value = mock_model
        mock_torch.cuda.is_available.return_value = True
        
        service = EmbeddingService(device="cuda")
        _ = service.model  # Load model
        
        # Delete service
        del service
        
        # Should attempt to free GPU memory
        # (This test just ensures no errors are raised)
