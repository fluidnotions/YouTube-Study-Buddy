"""
RAG Pipeline Stage for video processing integration.

This module provides a pipeline stage that generates embeddings and indexes
notes into the vector store as part of the video processing workflow.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from .config import RAGConfig
from .document_chunker import DocumentChunker, Chunk
from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .index_tracker import IndexTracker
from .types import ProcessResult

logger = logging.getLogger(__name__)


class RAGPipelineStage:
    """
    Pipeline stage for RAG embedding generation and indexing.

    Integrates into the video processing pipeline to:
    1. Check if note needs indexing (modification time tracking)
    2. Load and chunk markdown content
    3. Generate embeddings
    4. Store in vector database
    5. Update index tracker

    Features:
    - Idempotent (can re-run safely)
    - Graceful degradation (errors don't fail pipeline)
    - Progress tracking and logging
    - Background processing support
    """

    def __init__(
        self,
        config: RAGConfig,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        chunker: Optional[DocumentChunker] = None,
        index_tracker: Optional[IndexTracker] = None,
    ):
        """
        Initialize RAG pipeline stage.

        Args:
            config: RAG configuration
            embedding_service: Optional embedding service (created if None)
            vector_store: Optional vector store (created if None)
            chunker: Optional document chunker (created if None)
            index_tracker: Optional index tracker (created if None)
        """
        self.config = config

        # Initialize components (lazy if not provided)
        try:
            self.embedding_service = embedding_service or EmbeddingService(
                model_name=config.model_name
            )
            logger.info(f"RAG embedding service initialized: {config.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            self.embedding_service = None

        try:
            self.vector_store = vector_store or VectorStore(
                persist_dir=str(config.vector_store_dir),
                collection_name=config.collection_name,
            )
            logger.info(f"RAG vector store initialized: {config.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            self.vector_store = None

        self.chunker = chunker or DocumentChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            min_chunk_size=config.min_chunk_size,
        )

        self.index_tracker = index_tracker or IndexTracker(
            tracker_file=config.index_tracker_file
        )

    def is_ready(self) -> bool:
        """
        Check if RAG pipeline is ready to process.

        Returns:
            True if all components are initialized
        """
        return (
            self.embedding_service is not None
            and self.vector_store is not None
            and self.chunker is not None
            and self.index_tracker is not None
        )

    def process_note(
        self,
        note_path: Path,
        video_metadata: Dict[str, str],
        force_reindex: bool = False,
    ) -> ProcessResult:
        """
        Process a note file through RAG pipeline.

        Workflow:
        1. Check if already indexed (skip if not modified)
        2. Load markdown content
        3. Chunk into sections
        4. Generate embeddings
        5. Store in vector database
        6. Update index tracker

        Args:
            note_path: Path to markdown note file
            video_metadata: Dict with 'video_id', 'title', 'subject'
            force_reindex: If True, reindex even if already indexed

        Returns:
            ProcessResult with success status and metrics
        """
        start_time = time.time()
        note_path = Path(note_path)
        video_id = video_metadata.get('video_id', 'unknown')

        # Validate inputs
        if not note_path.exists():
            return ProcessResult(
                success=False,
                video_id=video_id,
                note_path=str(note_path),
                error_message=f"Note file does not exist: {note_path}",
            )

        if not self.is_ready():
            return ProcessResult(
                success=False,
                video_id=video_id,
                note_path=str(note_path),
                error_message="RAG pipeline not ready (missing components)",
            )

        # Check if already indexed
        if not force_reindex and not self.index_tracker.needs_reindex(video_id, note_path):
            logger.info(f"Note already indexed and up-to-date: {video_id}")
            return ProcessResult(
                success=True,
                video_id=video_id,
                note_path=str(note_path),
                skipped=True,
                skip_reason="Already indexed and up-to-date",
                processing_time_seconds=time.time() - start_time,
            )

        try:
            # Load markdown content
            logger.debug(f"Loading note: {note_path}")
            content = note_path.read_text(encoding='utf-8')

            # Chunk document
            logger.debug(f"Chunking document: {video_id}")
            chunks = self.chunker.chunk_markdown(content, video_metadata)

            if not chunks:
                logger.warning(f"No chunks created for {video_id}")
                return ProcessResult(
                    success=True,
                    video_id=video_id,
                    note_path=str(note_path),
                    chunks_created=0,
                    embeddings_generated=0,
                    processing_time_seconds=time.time() - start_time,
                    skipped=True,
                    skip_reason="No valid chunks created",
                )

            # Generate embeddings
            logger.debug(f"Generating embeddings for {len(chunks)} chunks")
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.embed_batch(texts)

            # Store in vector database with embeddings
            logger.debug(f"Storing {len(chunks)} chunks in vector store")
            success = self.vector_store.add_chunks_with_embeddings(chunks, embeddings)

            if not success:
                return ProcessResult(
                    success=False,
                    video_id=video_id,
                    note_path=str(note_path),
                    chunks_created=len(chunks),
                    embeddings_generated=len(embeddings),
                    error_message="Failed to store chunks in vector database",
                    processing_time_seconds=time.time() - start_time,
                )

            # Update index tracker
            self.index_tracker.mark_indexed(
                video_id=video_id,
                note_path=note_path,
                chunks_created=len(chunks),
                metadata={
                    'video_title': video_metadata.get('title'),
                    'subject': video_metadata.get('subject'),
                }
            )

            processing_time = time.time() - start_time
            logger.info(
                f"Successfully indexed {video_id}: "
                f"{len(chunks)} chunks, {processing_time:.2f}s"
            )

            return ProcessResult(
                success=True,
                video_id=video_id,
                note_path=str(note_path),
                chunks_created=len(chunks),
                embeddings_generated=len(embeddings),
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            logger.error(f"Failed to process note {video_id}: {e}", exc_info=True)
            return ProcessResult(
                success=False,
                video_id=video_id,
                note_path=str(note_path),
                error_message=str(e),
                processing_time_seconds=time.time() - start_time,
            )

    def process_batch(
        self,
        notes: List[tuple[Path, Dict]],
        force_reindex: bool = False,
    ) -> List[ProcessResult]:
        """
        Process multiple notes in batch.

        Args:
            notes: List of (note_path, video_metadata) tuples
            force_reindex: If True, reindex all notes

        Returns:
            List of ProcessResult objects
        """
        results = []

        for note_path, video_metadata in notes:
            result = self.process_note(
                note_path=note_path,
                video_metadata=video_metadata,
                force_reindex=force_reindex,
            )
            results.append(result)

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        skipped = sum(1 for r in results if r.skipped)

        logger.info(
            f"Batch processing complete: "
            f"{successful} successful, {failed} failed, {skipped} skipped"
        )

        return results

    def is_note_indexed(self, video_id: str) -> bool:
        """
        Check if a note is indexed.

        Args:
            video_id: Video identifier

        Returns:
            True if indexed
        """
        return video_id in self.index_tracker.get_indexed_videos()

    def get_stats(self) -> Dict:
        """
        Get statistics about RAG indexing.

        Returns:
            Dictionary with statistics
        """
        tracker_stats = self.index_tracker.get_stats()
        vector_stats = {}

        if self.vector_store:
            try:
                vector_stats = self.vector_store.collection_stats()
            except Exception as e:
                logger.warning(f"Failed to get vector store stats: {e}")

        return {
            'ready': self.is_ready(),
            'tracker': tracker_stats,
            'vector_store': vector_stats,
            'config': {
                'enabled': self.config.enabled,
                'model': self.config.model_name,
                'collection': self.config.collection_name,
            }
        }
