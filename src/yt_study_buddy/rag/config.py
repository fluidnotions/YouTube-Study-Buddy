"""Configuration management for RAG features.

This module provides configuration dataclasses and environment variable loading
for RAG components including feature flags, model settings, and performance tuning.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RAGConfig:
    """Configuration for RAG (Retrieval-Augmented Generation) system.
    
    Attributes:
        enabled: Whether RAG features are enabled
        model_name: Name of the sentence-transformer model to use
        model_cache_dir: Directory to cache downloaded models
        vector_store_dir: Directory to persist ChromaDB data
        collection_name: Name of the ChromaDB collection
        similarity_threshold: Minimum similarity score for cross-references (0-1)
        max_results: Maximum number of search results to return
        batch_size: Batch size for embedding generation
        chunk_size: Maximum tokens per document chunk
        chunk_overlap: Number of overlapping tokens between chunks
        min_chunk_size: Minimum tokens required for a chunk
    """
    
    enabled: bool = True
    model_name: str = "all-mpnet-base-v2"
    model_cache_dir: Path = Path.home() / ".cache" / "torch" / "sentence_transformers"
    vector_store_dir: Path = Path(".chroma_db")
    collection_name: str = "study_notes"
    similarity_threshold: float = 0.3
    max_results: int = 5
    batch_size: int = 32
    chunk_size: int = 1000
    chunk_overlap: int = 50
    min_chunk_size: int = 50
    index_tracker_file: Path = Path(".rag_index_tracker.json")

    def __post_init__(self):
        """Ensure Path objects are properly initialized."""
        if not isinstance(self.model_cache_dir, Path):
            self.model_cache_dir = Path(self.model_cache_dir)
        if not isinstance(self.vector_store_dir, Path):
            self.vector_store_dir = Path(self.vector_store_dir)
        if not isinstance(self.index_tracker_file, Path):
            self.index_tracker_file = Path(self.index_tracker_file)


def load_config_from_env() -> RAGConfig:
    """Load RAG configuration from environment variables.
    
    Environment variables:
        RAG_ENABLED: Enable/disable RAG (default: true)
        RAG_MODEL: Sentence-transformer model name (default: all-mpnet-base-v2)
        RAG_MODEL_CACHE_DIR: Model cache directory path
        RAG_VECTOR_STORE_DIR: ChromaDB persistence directory
        RAG_COLLECTION_NAME: ChromaDB collection name (default: study_notes)
        RAG_SIMILARITY_THRESHOLD: Minimum similarity score (default: 0.3)
        RAG_MAX_RESULTS: Maximum search results (default: 5)
        RAG_BATCH_SIZE: Embedding batch size (default: 32)
        RAG_CHUNK_SIZE: Maximum tokens per chunk (default: 1000)
        RAG_CHUNK_OVERLAP: Overlapping tokens (default: 50)
        RAG_MIN_CHUNK_SIZE: Minimum chunk size (default: 50)
        
        # Legacy environment variables (for backwards compatibility)
        CHROMA_PERSIST_DIR: Alias for RAG_VECTOR_STORE_DIR
        MODEL_CACHE_DIR: Alias for RAG_MODEL_CACHE_DIR
    
    Returns:
        RAGConfig: Configuration object with values from environment
    """
    
    def str_to_bool(value: Optional[str], default: bool = True) -> bool:
        """Convert string to boolean, handling various formats."""
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def str_to_float(value: Optional[str], default: float) -> float:
        """Convert string to float with error handling."""
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default
    
    def str_to_int(value: Optional[str], default: int) -> int:
        """Convert string to int with error handling."""
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
    
    # Load configuration from environment
    enabled = str_to_bool(os.getenv('RAG_ENABLED'), default=True)
    model_name = os.getenv('RAG_MODEL', 'all-mpnet-base-v2')
    
    # Model cache directory (with legacy support)
    model_cache_dir_str = os.getenv('RAG_MODEL_CACHE_DIR') or os.getenv('MODEL_CACHE_DIR')
    if model_cache_dir_str:
        model_cache_dir = Path(model_cache_dir_str)
    else:
        model_cache_dir = Path.home() / ".cache" / "torch" / "sentence_transformers"
    
    # Vector store directory (with legacy support)
    vector_store_dir_str = os.getenv('RAG_VECTOR_STORE_DIR') or os.getenv('CHROMA_PERSIST_DIR')
    if vector_store_dir_str:
        vector_store_dir = Path(vector_store_dir_str)
    else:
        vector_store_dir = Path(".chroma_db")
    
    collection_name = os.getenv('RAG_COLLECTION_NAME', 'study_notes')
    similarity_threshold = str_to_float(os.getenv('RAG_SIMILARITY_THRESHOLD'), 0.3)
    max_results = str_to_int(os.getenv('RAG_MAX_RESULTS'), 5)
    batch_size = str_to_int(os.getenv('RAG_BATCH_SIZE'), 32)
    chunk_size = str_to_int(os.getenv('RAG_CHUNK_SIZE'), 1000)
    chunk_overlap = str_to_int(os.getenv('RAG_CHUNK_OVERLAP'), 50)
    min_chunk_size = str_to_int(os.getenv('RAG_MIN_CHUNK_SIZE'), 50)

    # Index tracker file
    index_tracker_str = os.getenv('RAG_INDEX_TRACKER_FILE')
    if index_tracker_str:
        index_tracker_file = Path(index_tracker_str)
    else:
        index_tracker_file = Path(".rag_index_tracker.json")

    return RAGConfig(
        enabled=enabled,
        model_name=model_name,
        model_cache_dir=model_cache_dir,
        vector_store_dir=vector_store_dir,
        collection_name=collection_name,
        similarity_threshold=similarity_threshold,
        max_results=max_results,
        batch_size=batch_size,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
        index_tracker_file=index_tracker_file,
    )
