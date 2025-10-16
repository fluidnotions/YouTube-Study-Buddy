"""Document chunking for RAG indexing.

This module provides markdown document chunking with metadata extraction,
section-based splitting, and token counting for efficient embedding generation.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import tiktoken


logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk.
    
    Attributes:
        video_id: YouTube video ID
        video_title: Title of the video
        subject: Subject/category of the content
        section_title: Title of the section this chunk belongs to
        section_level: Heading level (2 for ##, 3 for ###, etc.)
        token_count: Number of tokens in the chunk content
        created_at: ISO timestamp when chunk was created
    """
    
    video_id: str
    video_title: str
    subject: str
    section_title: str
    section_level: int
    token_count: int
    created_at: str


@dataclass
class Chunk:
    """A document chunk with content and metadata.
    
    Attributes:
        chunk_id: Unique identifier for the chunk
        content: The text content of the chunk
        metadata: Metadata about the chunk
    """
    
    chunk_id: str
    content: str
    metadata: ChunkMetadata


class DocumentChunker:
    """Chunks markdown documents for RAG indexing.
    
    This chunker splits documents based on markdown headings (## sections),
    preserves section hierarchy, adds overlap between chunks, and tracks
    metadata for each chunk.
    
    Attributes:
        chunk_size: Maximum number of tokens per chunk
        chunk_overlap: Number of overlapping tokens between chunks
        min_chunk_size: Minimum number of tokens required for a chunk
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,
    ):
        """Initialize the document chunker.
        
        Args:
            chunk_size: Maximum tokens per chunk (default: 1000)
            chunk_overlap: Overlap tokens between chunks (default: 50)
            min_chunk_size: Minimum tokens for a valid chunk (default: 50)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Initialize tokenizer (using cl100k_base for general text)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding: {e}, using approximate counting")
            self.tokenizer = None
    
    def chunk_markdown(
        self,
        content: str,
        metadata: Dict[str, str],
    ) -> List[Chunk]:
        """Chunk a markdown document into sections.
        
        This method splits the document on ## (H2) headings, preserves
        hierarchy (H3, H4 under H2), adds overlap, and generates metadata.
        
        Args:
            content: Markdown content to chunk
            metadata: Base metadata (video_id, video_title, subject)
        
        Returns:
            List of Chunk objects with content and metadata
        """
        # Extract base metadata
        video_id = metadata.get('video_id', 'unknown')
        video_title = metadata.get('video_title', 'Unknown Video')
        subject = metadata.get('subject', 'General')
        
        # Split content into sections based on ## headings
        sections = self._split_into_sections(content)
        
        if not sections:
            logger.warning(f"No sections found in document for video {video_id}")
            return []
        
        chunks = []
        for section in sections:
            # Create chunks for this section
            section_chunks = self._chunk_section(
                section_content=section['content'],
                section_title=section['title'],
                section_level=section['level'],
                video_id=video_id,
                video_title=video_title,
                subject=subject,
            )
            chunks.extend(section_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {len(sections)} sections for video {video_id}")
        return chunks
    
    def _split_into_sections(self, content: str) -> List[Dict[str, any]]:
        """Split markdown content into sections based on ## headings.
        
        Args:
            content: Markdown content
        
        Returns:
            List of dicts with 'title', 'level', and 'content' keys
        """
        sections = []
        
        # Pattern to match markdown headings
        heading_pattern = re.compile(r'^(#{2,6})\s+(.+)$', re.MULTILINE)
        
        # Find all headings
        matches = list(heading_pattern.finditer(content))
        
        if not matches:
            # No headings found, treat entire document as one section
            return [{
                'title': 'Document',
                'level': 2,
                'content': content.strip(),
            }]
        
        # Process each section
        for i, match in enumerate(matches):
            heading_level = len(match.group(1))
            section_title = match.group(2).strip()
            start_pos = match.end()
            
            # Find end of section (next heading at same or higher level, or end of document)
            if i < len(matches) - 1:
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)
            
            section_content = content[start_pos:end_pos].strip()
            
            # Only include sections at H2 level (##) as main sections
            # This preserves hierarchy (H3, H4 are included in their parent H2)
            if heading_level == 2 and section_content:
                sections.append({
                    'title': section_title,
                    'level': heading_level,
                    'content': section_content,
                })
        
        return sections
    
    def _chunk_section(
        self,
        section_content: str,
        section_title: str,
        section_level: int,
        video_id: str,
        video_title: str,
        subject: str,
    ) -> List[Chunk]:
        """Chunk a single section, handling large sections with overlap.
        
        Args:
            section_content: Content of the section
            section_title: Title of the section
            section_level: Heading level
            video_id: Video ID for metadata
            video_title: Video title for metadata
            subject: Subject for metadata
        
        Returns:
            List of Chunk objects for this section
        """
        # Count tokens in section
        token_count = self._count_tokens(section_content)
        
        # If section fits in one chunk, return it
        if token_count <= self.chunk_size:
            if token_count < self.min_chunk_size:
                logger.debug(f"Skipping small section '{section_title}' ({token_count} tokens)")
                return []
            
            return [self._create_chunk(
                content=section_content,
                section_title=section_title,
                section_level=section_level,
                video_id=video_id,
                video_title=video_title,
                subject=subject,
                token_count=token_count,
            )]
        
        # Section is too large, split with overlap
        chunks = []
        
        # Split by paragraphs to avoid breaking mid-sentence
        paragraphs = section_content.split('\n\n')
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._count_tokens(para)
            
            # If adding this paragraph exceeds chunk size, save current chunk
            if current_tokens + para_tokens > self.chunk_size and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    section_title=section_title,
                    section_level=section_level,
                    video_id=video_id,
                    video_title=video_title,
                    subject=subject,
                    token_count=current_tokens,
                ))
                
                # Start new chunk with overlap (keep last paragraph)
                if self.chunk_overlap > 0 and len(current_chunk) > 0:
                    current_chunk = [current_chunk[-1]]
                    current_tokens = self._count_tokens(current_chunk[0])
                else:
                    current_chunk = []
                    current_tokens = 0
            
            current_chunk.append(para)
            current_tokens += para_tokens
        
        # Add final chunk if it has content
        if current_chunk and current_tokens >= self.min_chunk_size:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append(self._create_chunk(
                content=chunk_content,
                section_title=section_title,
                section_level=section_level,
                video_id=video_id,
                video_title=video_title,
                subject=subject,
                token_count=current_tokens,
            ))
        
        return chunks
    
    def _create_chunk(
        self,
        content: str,
        section_title: str,
        section_level: int,
        video_id: str,
        video_title: str,
        subject: str,
        token_count: int,
    ) -> Chunk:
        """Create a Chunk object with metadata.
        
        Args:
            content: Chunk content
            section_title: Section title
            section_level: Heading level
            video_id: Video ID
            video_title: Video title
            subject: Subject category
            token_count: Number of tokens
        
        Returns:
            Chunk object with generated ID and metadata
        """
        # Generate unique chunk ID based on content hash
        chunk_id = self._generate_chunk_id(video_id, section_title, content)
        
        # Create metadata
        metadata = ChunkMetadata(
            video_id=video_id,
            video_title=video_title,
            subject=subject,
            section_title=section_title,
            section_level=section_level,
            token_count=token_count,
            created_at=datetime.utcnow().isoformat(),
        )
        
        return Chunk(
            chunk_id=chunk_id,
            content=content,
            metadata=metadata,
        )
    
    def _generate_chunk_id(self, video_id: str, section_title: str, content: str) -> str:
        """Generate a unique chunk ID.
        
        Args:
            video_id: Video ID
            section_title: Section title
            content: Chunk content
        
        Returns:
            Unique chunk identifier
        """
        # Create hash from video_id, section, and content
        hash_input = f"{video_id}:{section_title}:{content[:100]}"
        content_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"{video_id}_{content_hash}"
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens in
        
        Returns:
            Number of tokens
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.debug(f"Tokenizer error, using approximation: {e}")
        
        # Fallback: approximate token count (1 token ≈ 4 characters)
        return len(text) // 4
    
    def validate_chunk(self, chunk: Chunk) -> bool:
        """Validate that a chunk meets requirements.
        
        Args:
            chunk: Chunk to validate
        
        Returns:
            True if chunk is valid, False otherwise
        """
        # Check that required fields are present
        if not chunk.chunk_id or not chunk.content:
            return False
        
        # Check token count is within bounds
        token_count = chunk.metadata.token_count
        if token_count < self.min_chunk_size or token_count > self.chunk_size * 1.5:
            # Allow some overage for natural paragraph boundaries
            return False
        
        # Check metadata is complete
        metadata = chunk.metadata
        if not all([
            metadata.video_id,
            metadata.video_title,
            metadata.subject,
            metadata.section_title,
        ]):
            return False
        
        return True
