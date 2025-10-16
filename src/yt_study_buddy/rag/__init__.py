"""RAG (Retrieval-Augmented Generation) infrastructure for YouTube Study Buddy.

This package provides semantic cross-referencing capabilities using vector embeddings
and similarity search to find related content across study notes.

Core Components:
- config: Configuration management for RAG features
- document_chunker: Markdown document chunking with metadata extraction
- embedding_service: Text embedding generation using sentence-transformers
- vector_store: ChromaDB wrapper for vector storage and similarity search
- cross_referencer: High-level RAG interface for semantic cross-referencing
- metrics: Link quality metrics and performance tracking
- pipeline_stage: Pipeline integration for RAG indexing
- index_tracker: Track indexed notes for incremental updates
"""

from .config import RAGConfig, load_config_from_env
from .document_chunker import Chunk, ChunkMetadata, DocumentChunker
from .embedding_service import EmbeddingService
from .vector_store import VectorStore, SearchResult
from .cross_referencer import RAGCrossReferencer, CrossReference
from .metrics import MetricsCollector, LinkingMetrics, get_metrics_collector
from .pipeline_stage import RAGPipelineStage
from .index_tracker import IndexTracker

__all__ = [
    "RAGConfig",
    "load_config_from_env",
    "Chunk",
    "ChunkMetadata",
    "DocumentChunker",
    "EmbeddingService",
    "VectorStore",
    "SearchResult",
    "RAGCrossReferencer",
    "CrossReference",
    "MetricsCollector",
    "LinkingMetrics",
    "get_metrics_collector",
    "RAGPipelineStage",
    "IndexTracker",
]
