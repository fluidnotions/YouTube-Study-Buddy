"""Text embedding service using sentence-transformers.

This module provides text embedding generation with lazy model loading,
batch processing, and error handling for RAG applications.
"""

import logging
from typing import Dict, List, Any, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
import torch


logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers.
    
    This service provides lazy loading of models, batch processing for efficiency,
    CPU/GPU detection, and error handling for embedding generation.
    
    Attributes:
        model_name: Name of the sentence-transformer model
        cache_dir: Directory to cache downloaded models
        device: Compute device (cuda, mps, or cpu)
    """
    
    def __init__(
        self,
        model_name: str = "all-mpnet-base-v2",
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """Initialize the embedding service.
        
        Args:
            model_name: Sentence-transformer model name (default: all-mpnet-base-v2)
            cache_dir: Directory to cache models (default: None, uses default cache)
            device: Device to run model on (default: None, auto-detect)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model: Optional[SentenceTransformer] = None
        
        # Detect device if not specified
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device
        
        logger.info(f"EmbeddingService initialized with model={model_name}, device={self.device}")
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the sentence-transformer model.
        
        Returns:
            Loaded SentenceTransformer model
        
        Raises:
            RuntimeError: If model fails to load
        """
        if self._model is None:
            try:
                logger.info(f"Loading sentence-transformer model: {self.model_name}")
                self._model = SentenceTransformer(
                    self.model_name,
                    cache_folder=self.cache_dir,
                    device=self.device,
                )
                logger.info(f"Model loaded successfully on device: {self.device}")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise RuntimeError(f"Could not load embedding model: {e}") from e
        
        return self._model
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            Numpy array containing the embedding vector
        
        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            # Generate embedding (returns numpy array)
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}") from e
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (default: 32)
            show_progress: Show progress bar (default: False)
        
        Returns:
            Numpy array of shape (n_texts, embedding_dim) containing embeddings
        
        Raises:
            ValueError: If texts list is empty or contains invalid entries
            RuntimeError: If embedding generation fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        # Filter out empty texts and track indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)
        
        if not valid_texts:
            raise ValueError("All texts are empty or invalid")
        
        if len(valid_texts) < len(texts):
            logger.warning(f"Skipped {len(texts) - len(valid_texts)} empty texts in batch")
        
        try:
            # Generate embeddings in batches
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=show_progress,
            )
            
            # If some texts were skipped, create full array with zeros for invalid entries
            if len(valid_texts) < len(texts):
                full_embeddings = np.zeros((len(texts), embeddings.shape[1]))
                for i, embedding in zip(valid_indices, embeddings):
                    full_embeddings[i] = embedding
                return full_embeddings
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise RuntimeError(f"Batch embedding generation failed: {e}") from e
    
    def get_embedding_dim(self) -> int:
        """Get the dimensionality of embeddings produced by this model.
        
        Returns:
            Embedding dimension (e.g., 768 for all-mpnet-base-v2)
        """
        # Access model to trigger lazy loading
        return self.model.get_sentence_embedding_dimension()
    
    def model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model.
        
        Returns:
            Dictionary with model information including name, device,
            embedding dimension, and max sequence length
        """
        info = {
            "model_name": self.model_name,
            "device": self.device,
            "embedding_dim": self.get_embedding_dim(),
            "cache_dir": self.cache_dir,
        }
        
        # Try to get max sequence length
        try:
            info["max_seq_length"] = self.model.max_seq_length
        except AttributeError:
            info["max_seq_length"] = None
        
        return info
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        if self._model is not None:
            logger.debug("Cleaning up EmbeddingService")
            # Free GPU memory if applicable
            if self.device in ("cuda", "mps"):
                try:
                    del self._model
                    if self.device == "cuda":
                        torch.cuda.empty_cache()
                except Exception as e:
                    logger.debug(f"Error during cleanup: {e}")
