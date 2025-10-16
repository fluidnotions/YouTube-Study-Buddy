"""Vector store implementation using ChromaDB.

This module provides a wrapper around ChromaDB for storing and searching
document embeddings with metadata filtering and error handling.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
import numpy as np

from .document_chunker import Chunk


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from a similarity search.
    
    Attributes:
        chunk_id: Unique identifier for the chunk
        content: Text content of the chunk
        metadata: Metadata dictionary
        similarity_score: Similarity score (0-1, higher is more similar)
        distance: Distance metric from query (lower is more similar)
    """
    
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    distance: float


class VectorStore:
    """ChromaDB-based vector store for document embeddings.
    
    This store handles document storage, similarity search with filtering,
    collection management, and error handling for RAG applications.
    
    Attributes:
        persist_dir: Directory to persist ChromaDB data
        collection_name: Name of the ChromaDB collection
    """
    
    def __init__(
        self,
        persist_dir: str,
        collection_name: str = "study_notes",
        embedding_function: Optional[Any] = None,
    ):
        """Initialize the vector store.
        
        Args:
            persist_dir: Directory to persist ChromaDB data
            collection_name: Name of the collection (default: study_notes)
            embedding_function: Optional custom embedding function for ChromaDB
        """
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self._client: Optional[chromadb.Client] = None
        self._collection: Optional[chromadb.Collection] = None
        self.embedding_function = embedding_function
        
        # Ensure persist directory exists
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"VectorStore initialized: persist_dir={persist_dir}, collection={collection_name}")
    
    @property
    def client(self) -> chromadb.Client:
        """Lazy-load ChromaDB client.
        
        Returns:
            ChromaDB client instance
        
        Raises:
            RuntimeError: If client initialization fails
        """
        if self._client is None:
            try:
                logger.info("Initializing ChromaDB client")
                self._client = chromadb.Client(
                    Settings(
                        persist_directory=str(self.persist_dir),
                        anonymized_telemetry=False,
                    )
                )
                logger.info("ChromaDB client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise RuntimeError(f"Could not initialize ChromaDB: {e}") from e
        
        return self._client
    
    @property
    def collection(self) -> chromadb.Collection:
        """Get or create the ChromaDB collection.
        
        Returns:
            ChromaDB collection instance
        
        Raises:
            RuntimeError: If collection access fails
        """
        if self._collection is None:
            try:
                logger.info(f"Getting or creating collection: {self.collection_name}")
                self._collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "YouTube study notes embeddings"},
                )
                logger.info(f"Collection ready: {self.collection_name}")
            except Exception as e:
                logger.error(f"Failed to get/create collection: {e}")
                raise RuntimeError(f"Could not access collection: {e}") from e
        
        return self._collection
    
    def add_chunks(self, chunks: List[Chunk]) -> bool:
        """Add document chunks to the vector store.
        
        Args:
            chunks: List of Chunk objects to add
        
        Returns:
            True if successful, False otherwise
        
        Raises:
            ValueError: If chunks list is empty or invalid
        """
        if not chunks:
            raise ValueError("Chunks list cannot be empty")
        
        try:
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for chunk in chunks:
                ids.append(chunk.chunk_id)
                documents.append(chunk.content)
                
                # Convert metadata to dict (ChromaDB requires dict)
                metadata_dict = {
                    "video_id": chunk.metadata.video_id,
                    "video_title": chunk.metadata.video_title,
                    "subject": chunk.metadata.subject,
                    "section_title": chunk.metadata.section_title,
                    "section_level": chunk.metadata.section_level,
                    "token_count": chunk.metadata.token_count,
                    "created_at": chunk.metadata.created_at,
                }
                metadatas.append(metadata_dict)
            
            # Add to collection (embeddings will be generated by ChromaDB if not provided)
            logger.info(f"Adding {len(chunks)} chunks to vector store")
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            
            logger.info(f"Successfully added {len(chunks)} chunks")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add chunks: {e}")
            return False
    
    def add_chunks_with_embeddings(
        self,
        chunks: List[Chunk],
        embeddings: np.ndarray,
    ) -> bool:
        """Add document chunks with pre-computed embeddings.
        
        Args:
            chunks: List of Chunk objects
            embeddings: Numpy array of embeddings (n_chunks, embedding_dim)
        
        Returns:
            True if successful, False otherwise
        
        Raises:
            ValueError: If chunks and embeddings don't match
        """
        if not chunks:
            raise ValueError("Chunks list cannot be empty")
        
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Number of chunks ({len(chunks)}) must match number of embeddings ({len(embeddings)})"
            )
        
        try:
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embedding_list = []
            
            for chunk, embedding in zip(chunks, embeddings):
                ids.append(chunk.chunk_id)
                documents.append(chunk.content)
                
                # Convert metadata to dict
                metadata_dict = {
                    "video_id": chunk.metadata.video_id,
                    "video_title": chunk.metadata.video_title,
                    "subject": chunk.metadata.subject,
                    "section_title": chunk.metadata.section_title,
                    "section_level": chunk.metadata.section_level,
                    "token_count": chunk.metadata.token_count,
                    "created_at": chunk.metadata.created_at,
                }
                metadatas.append(metadata_dict)
                
                # Convert numpy array to list for ChromaDB
                embedding_list.append(embedding.tolist())
            
            # Add to collection with embeddings
            logger.info(f"Adding {len(chunks)} chunks with embeddings to vector store")
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embedding_list,
            )
            
            logger.info(f"Successfully added {len(chunks)} chunks with embeddings")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add chunks with embeddings: {e}")
            return False
    
    def search_similar(
        self,
        query_embedding: np.ndarray,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Search for similar documents using embedding vector.
        
        Args:
            query_embedding: Query embedding vector
            filters: Optional metadata filters (e.g., {"subject": "AI"})
            top_k: Number of results to return (default: 5)
        
        Returns:
            List of SearchResult objects, sorted by similarity
        
        Raises:
            ValueError: If query_embedding is invalid
        """
        if query_embedding is None or len(query_embedding) == 0:
            raise ValueError("Query embedding cannot be empty")
        
        try:
            # Convert numpy array to list for ChromaDB
            query_list = query_embedding.tolist()
            
            # Build where clause for filtering
            where = None
            if filters:
                where = self._build_where_clause(filters)
            
            # Query the collection
            logger.debug(f"Searching for top {top_k} similar chunks with filters: {filters}")
            results = self.collection.query(
                query_embeddings=[query_list],
                n_results=top_k,
                where=where,
            )
            
            # Parse results into SearchResult objects
            search_results = []
            
            if results and results['ids'] and len(results['ids']) > 0:
                ids = results['ids'][0]
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                for i in range(len(ids)):
                    # Convert distance to similarity score (0-1, higher is more similar)
                    # ChromaDB uses L2 distance, convert to similarity
                    distance = distances[i]
                    similarity = 1.0 / (1.0 + distance)
                    
                    search_results.append(SearchResult(
                        chunk_id=ids[i],
                        content=documents[i],
                        metadata=metadatas[i],
                        similarity_score=similarity,
                        distance=distance,
                    ))
            
            logger.debug(f"Found {len(search_results)} similar chunks")
            return search_results
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Similarity search failed: {e}") from e
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build ChromaDB where clause from filters.
        
        Args:
            filters: Filter dictionary (e.g., {"subject": "AI", "video_id": {"$ne": "abc123"}})
        
        Returns:
            ChromaDB where clause
        """
        where = {}
        
        for key, value in filters.items():
            if isinstance(value, dict):
                # Handle operators like $ne, $in, etc.
                where[key] = value
            else:
                # Simple equality filter
                where[key] = {"$eq": value}
        
        return where
    
    def delete_by_video_id(self, video_id: str) -> bool:
        """Delete all chunks for a specific video.
        
        Args:
            video_id: Video ID to delete chunks for
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting chunks for video_id: {video_id}")
            
            # Query for chunks with this video_id
            results = self.collection.get(
                where={"video_id": {"$eq": video_id}}
            )
            
            if results and results['ids']:
                ids_to_delete = results['ids']
                logger.info(f"Found {len(ids_to_delete)} chunks to delete")
                
                # Delete the chunks
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks for video {video_id}")
            else:
                logger.info(f"No chunks found for video {video_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete chunks for video {video_id}: {e}")
            return False
    
    def collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            stats = {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "persist_dir": str(self.persist_dir),
            }
            
            # Try to get more detailed stats
            try:
                # Get sample to analyze
                if count > 0:
                    sample = self.collection.get(limit=100)
                    if sample and sample['metadatas']:
                        # Count unique videos
                        video_ids = set(m.get('video_id') for m in sample['metadatas'] if m.get('video_id'))
                        stats["sample_videos"] = len(video_ids)
                        
                        # Count subjects
                        subjects = set(m.get('subject') for m in sample['metadatas'] if m.get('subject'))
                        stats["sample_subjects"] = list(subjects)
            except Exception as e:
                logger.debug(f"Could not get detailed stats: {e}")
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "collection_name": self.collection_name,
                "error": str(e),
            }
    
    def health_check(self) -> bool:
        """Check if the vector store is healthy and accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to access collection
            _ = self.collection
            
            # Try a simple count operation
            count = self.collection.count()
            
            logger.info(f"Health check passed: collection has {count} chunks")
            return True
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def reset_collection(self) -> bool:
        """Delete and recreate the collection (use with caution).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.warning(f"Resetting collection: {self.collection_name}")
            
            # Delete collection
            self.client.delete_collection(name=self.collection_name)
            
            # Reset cached collection
            self._collection = None
            
            # Recreate collection
            _ = self.collection
            
            logger.info("Collection reset successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False
