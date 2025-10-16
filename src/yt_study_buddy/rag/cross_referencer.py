"""RAG-based cross-reference generation for Obsidian linking.

This module provides high-level RAG query interface for finding semantically
similar content across study notes, with features like result ranking, filtering,
deduplication, and Obsidian link formatting.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

import numpy as np

from .config import RAGConfig
from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .types import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class CrossReference:
    """A cross-reference link to related content.

    Attributes:
        target_section: Title of the target section
        target_video_id: Video ID of the target
        target_video_title: Title of the target video
        similarity_score: Semantic similarity score (0-1)
        preview_text: Preview of the target content
        obsidian_link: Formatted Obsidian [[wiki]] link
    """

    target_section: str
    target_video_id: str
    target_video_title: str
    similarity_score: float
    preview_text: str
    obsidian_link: str = ""

    def __post_init__(self):
        """Generate Obsidian link if not provided."""
        if not self.obsidian_link:
            self.obsidian_link = self._format_obsidian_link()

    def _format_obsidian_link(self) -> str:
        """Format as Obsidian [[Video Title#Section]] link."""
        # Clean section title for Obsidian format
        section = self.target_section.replace('[[', '').replace(']]', '')
        video_title = self.target_video_title.replace('[[', '').replace(']]', '')

        # Format: [[Video Title#Section Title]]
        return f"[[{video_title}#{section}]]"


class RAGCrossReferencer:
    """High-level RAG interface for semantic cross-referencing.

    This class provides methods to find semantically similar content across
    study notes using vector embeddings and similarity search. It handles
    result ranking, filtering, deduplication, and link formatting.

    Attributes:
        embedding_service: Service for generating text embeddings
        vector_store: Vector database for similarity search
        config: RAG configuration settings
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        config: RAGConfig,
    ):
        """Initialize RAG cross-referencer.

        Args:
            embedding_service: Embedding generation service
            vector_store: Vector storage and search
            config: RAG configuration
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.config = config
        logger.info("RAGCrossReferencer initialized")

    def find_references(
        self,
        section_text: str,
        current_video_id: str,
        subject: Optional[str] = None,
        global_context: bool = False,
    ) -> List[CrossReference]:
        """Find semantically similar references for a section.

        This is the main entry point for finding cross-references. It:
        1. Generates embedding for the section text
        2. Queries vector store with appropriate filters
        3. Ranks results by similarity
        4. Applies threshold filtering
        5. Deduplicates results
        6. Returns formatted cross-references

        Args:
            section_text: Text content of the section to find references for
            current_video_id: Video ID of the current document (to exclude self-references)
            subject: Optional subject filter (e.g., "AI", "Math")
            global_context: If True, search across all subjects; if False, subject-specific

        Returns:
            List of CrossReference objects, sorted by similarity (highest first)
        """
        if not section_text or len(section_text.strip()) < 20:
            logger.debug("Section text too short for cross-referencing")
            return []

        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.embed_text(section_text)

            # Build metadata filters
            filters = self._build_filters(
                current_video_id=current_video_id,
                subject=subject if not global_context else None,
            )

            # Search vector store
            search_results = self.vector_store.search_similar(
                query_embedding=query_embedding,
                filters=filters,
                top_k=self.config.max_results * 2,  # Get extra for deduplication
            )

            if not search_results:
                logger.debug("No search results found")
                return []

            # Filter by similarity threshold
            filtered_results = self._filter_by_threshold(search_results)

            # Deduplicate results (same video, nearby sections)
            deduplicated_results = self._deduplicate_results(filtered_results)

            # Convert to CrossReference objects
            cross_references = self._create_cross_references(deduplicated_results)

            # Limit to max_results
            cross_references = cross_references[:self.config.max_results]

            logger.info(
                f"Found {len(cross_references)} cross-references for section "
                f"(from {len(search_results)} total results)"
            )

            return cross_references

        except Exception as e:
            logger.error(f"Error finding references: {e}", exc_info=True)
            return []

    def _build_filters(
        self,
        current_video_id: str,
        subject: Optional[str] = None,
    ) -> dict:
        """Build metadata filters for vector search.

        Args:
            current_video_id: Video ID to exclude from results
            subject: Optional subject to filter by

        Returns:
            Dictionary of filters for ChromaDB
        """
        filters = {}

        # Always exclude current video (avoid self-references)
        filters['video_id'] = {'$ne': current_video_id}

        # Add subject filter if specified
        if subject:
            filters['subject'] = subject

        return filters

    def _filter_by_threshold(
        self,
        results: List[SearchResult],
    ) -> List[SearchResult]:
        """Filter results by similarity threshold.

        Args:
            results: Search results from vector store

        Returns:
            Filtered list of results above threshold
        """
        return [
            result for result in results
            if result.similarity_score >= self.config.similarity_threshold
        ]

    def _deduplicate_results(
        self,
        results: List[SearchResult],
    ) -> List[SearchResult]:
        """Deduplicate search results.

        Removes duplicate references from the same video and nearby sections
        that are very similar (likely from the same broader topic).

        Args:
            results: Search results to deduplicate

        Returns:
            Deduplicated list of results
        """
        seen_videos: Set[str] = set()
        seen_sections: Set[Tuple[str, str]] = set()
        deduplicated = []

        for result in results:
            video_id = result.metadata.video_id
            section_title = result.metadata.section_title

            # Keep only one result per video (the highest scoring one)
            # This prevents over-linking to the same video
            if video_id in seen_videos:
                continue

            # Check if we've seen a very similar section title
            section_key = (video_id, section_title.lower().strip())
            if section_key in seen_sections:
                continue

            # Add to result list and mark as seen
            deduplicated.append(result)
            seen_videos.add(video_id)
            seen_sections.add(section_key)

        return deduplicated

    def _create_cross_references(
        self,
        results: List[SearchResult],
    ) -> List[CrossReference]:
        """Convert search results to CrossReference objects.

        Args:
            results: Search results from vector store

        Returns:
            List of CrossReference objects with formatted links
        """
        cross_refs = []

        for result in results:
            # Create preview text (first 150 chars)
            preview = result.content.strip()
            if len(preview) > 150:
                preview = preview[:150] + "..."

            cross_ref = CrossReference(
                target_section=result.metadata.section_title,
                target_video_id=result.metadata.video_id,
                target_video_title=result.metadata.video_title,
                similarity_score=result.similarity_score,
                preview_text=preview,
            )

            cross_refs.append(cross_ref)

        return cross_refs

    def format_as_obsidian_link(self, ref: CrossReference) -> str:
        """Format a cross-reference as an Obsidian wiki link.

        Args:
            ref: CrossReference to format

        Returns:
            Obsidian [[Video Title#Section]] link string
        """
        return ref.obsidian_link

    def batch_find_references(
        self,
        sections: List[Tuple[str, str]],  # List of (section_title, section_text)
        current_video_id: str,
        subject: Optional[str] = None,
        global_context: bool = False,
    ) -> dict:
        """Find references for multiple sections efficiently.

        This method processes multiple sections in batch mode, which can be
        more efficient for documents with many sections.

        Args:
            sections: List of (section_title, section_text) tuples
            current_video_id: Video ID of the current document
            subject: Optional subject filter
            global_context: If True, search across all subjects

        Returns:
            Dictionary mapping section titles to list of CrossReferences
        """
        results = {}

        for section_title, section_text in sections:
            cross_refs = self.find_references(
                section_text=section_text,
                current_video_id=current_video_id,
                subject=subject,
                global_context=global_context,
            )
            results[section_title] = cross_refs

        return results
