"""
Common data types for RAG modules.

These types define the interfaces between Agent 1 and Agent 2 components.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""

    video_id: str
    video_title: str
    subject: str
    section_title: str
    section_level: int
    token_count: int
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for ChromaDB."""
        return {
            'video_id': self.video_id,
            'video_title': self.video_title,
            'subject': self.subject,
            'section_title': self.section_title,
            'section_level': self.section_level,
            'token_count': self.token_count,
            'created_at': self.created_at,
        }


@dataclass
class Chunk:
    """A document chunk with content and metadata."""

    chunk_id: str
    content: str
    metadata: ChunkMetadata

    def __post_init__(self):
        """Validate chunk."""
        if not self.chunk_id:
            raise ValueError("chunk_id cannot be empty")
        if not self.content:
            raise ValueError("content cannot be empty")
        if self.metadata.token_count <= 0:
            raise ValueError("token_count must be positive")


@dataclass
class SearchResult:
    """Result from vector similarity search."""

    chunk_id: str
    content: str
    metadata: ChunkMetadata
    similarity_score: float
    distance: float  # ChromaDB returns distance (inverse of similarity)

    def __post_init__(self):
        """Validate search result."""
        if not 0 <= self.similarity_score <= 1:
            raise ValueError(f"similarity_score must be in [0,1], got {self.similarity_score}")


@dataclass
class ProcessResult:
    """Result from RAG pipeline stage processing."""

    success: bool
    video_id: str
    note_path: str
    chunks_created: int = 0
    embeddings_generated: int = 0
    processing_time_seconds: float = 0.0
    error_message: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'success': self.success,
            'video_id': self.video_id,
            'note_path': self.note_path,
            'chunks_created': self.chunks_created,
            'embeddings_generated': self.embeddings_generated,
            'processing_time_seconds': self.processing_time_seconds,
            'error_message': self.error_message,
            'skipped': self.skipped,
            'skip_reason': self.skip_reason,
        }
