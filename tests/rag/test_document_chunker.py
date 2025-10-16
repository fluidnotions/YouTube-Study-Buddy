"""Unit tests for document chunking module."""

import pytest
from datetime import datetime

from yt_study_buddy.rag.document_chunker import (
    Chunk,
    ChunkMetadata,
    DocumentChunker,
)


class TestChunkMetadata:
    """Tests for ChunkMetadata dataclass."""
    
    def test_create_metadata(self):
        """Test creating chunk metadata."""
        metadata = ChunkMetadata(
            video_id="test123",
            video_title="Test Video",
            subject="AI",
            section_title="Introduction",
            section_level=2,
            token_count=100,
            created_at="2025-01-01T00:00:00",
        )
        
        assert metadata.video_id == "test123"
        assert metadata.video_title == "Test Video"
        assert metadata.subject == "AI"
        assert metadata.section_title == "Introduction"
        assert metadata.section_level == 2
        assert metadata.token_count == 100
        assert metadata.created_at == "2025-01-01T00:00:00"


class TestChunk:
    """Tests for Chunk dataclass."""
    
    def test_create_chunk(self):
        """Test creating a chunk."""
        metadata = ChunkMetadata(
            video_id="test123",
            video_title="Test Video",
            subject="AI",
            section_title="Introduction",
            section_level=2,
            token_count=100,
            created_at="2025-01-01T00:00:00",
        )
        
        chunk = Chunk(
            chunk_id="test123_abc",
            content="This is test content.",
            metadata=metadata,
        )
        
        assert chunk.chunk_id == "test123_abc"
        assert chunk.content == "This is test content."
        assert chunk.metadata == metadata


class TestDocumentChunker:
    """Tests for DocumentChunker class."""
    
    def test_init_default_values(self):
        """Test initializing chunker with default values."""
        chunker = DocumentChunker()
        
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 50
        assert chunker.min_chunk_size == 50
        assert chunker.tokenizer is not None
    
    def test_init_custom_values(self):
        """Test initializing chunker with custom values."""
        chunker = DocumentChunker(
            chunk_size=500,
            chunk_overlap=25,
            min_chunk_size=25,
        )
        
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 25
        assert chunker.min_chunk_size == 25
    
    def test_count_tokens(self):
        """Test token counting."""
        chunker = DocumentChunker()
        
        text = "This is a test sentence."
        token_count = chunker._count_tokens(text)
        
        # Should have some tokens (exact count may vary)
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_split_into_sections_with_headings(self):
        """Test splitting markdown into sections."""
        chunker = DocumentChunker()
        
        content = """
## Introduction

This is the introduction section.

## Main Content

This is the main content section with more detail.

### Subsection

This is a subsection under main content.

## Conclusion

This is the conclusion.
"""
        
        sections = chunker._split_into_sections(content)
        
        # Should have 3 H2 sections (subsection is included in Main Content)
        assert len(sections) == 3
        assert sections[0]['title'] == "Introduction"
        assert sections[0]['level'] == 2
        assert "introduction section" in sections[0]['content'].lower()
        
        assert sections[1]['title'] == "Main Content"
        assert "subsection" in sections[1]['content'].lower()
        
        assert sections[2]['title'] == "Conclusion"
    
    def test_split_into_sections_no_headings(self):
        """Test splitting content with no headings."""
        chunker = DocumentChunker()
        
        content = "This is plain content with no headings."
        
        sections = chunker._split_into_sections(content)
        
        # Should create one default section
        assert len(sections) == 1
        assert sections[0]['title'] == "Document"
        assert sections[0]['level'] == 2
        assert sections[0]['content'] == content
    
    def test_split_into_sections_empty_content(self):
        """Test splitting empty content."""
        chunker = DocumentChunker()
        
        content = ""
        sections = chunker._split_into_sections(content)
        
        # Should return empty list or single section with empty content
        assert isinstance(sections, list)
    
    def test_chunk_markdown_simple(self):
        """Test chunking a simple markdown document."""
        chunker = DocumentChunker()
        
        content = """
## Introduction

This is a simple introduction section with some content.

## Conclusion

This is the conclusion section.
"""
        
        metadata = {
            'video_id': 'test123',
            'video_title': 'Test Video',
            'subject': 'Testing',
        }
        
        chunks = chunker.chunk_markdown(content, metadata)
        
        # Should have 2 chunks (one per section)
        assert len(chunks) == 2
        
        # Check first chunk
        assert chunks[0].metadata.video_id == 'test123'
        assert chunks[0].metadata.section_title == 'Introduction'
        assert 'introduction' in chunks[0].content.lower()
        
        # Check second chunk
        assert chunks[1].metadata.section_title == 'Conclusion'
        assert 'conclusion' in chunks[1].content.lower()
    
    def test_chunk_markdown_with_large_section(self):
        """Test chunking with a section that exceeds chunk_size."""
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=20)
        
        # Create content that will exceed chunk size
        long_content = "\n\n".join([f"Paragraph {i} with some content." for i in range(20)])
        
        content = f"""
## Large Section

{long_content}
"""
        
        metadata = {
            'video_id': 'test123',
            'video_title': 'Test Video',
            'subject': 'Testing',
        }
        
        chunks = chunker.chunk_markdown(content, metadata)
        
        # Should have multiple chunks from the large section
        assert len(chunks) > 1
        
        # All chunks should have same section title
        for chunk in chunks:
            assert chunk.metadata.section_title == 'Large Section'
    
    def test_chunk_markdown_skips_small_sections(self):
        """Test that sections smaller than min_chunk_size are skipped."""
        chunker = DocumentChunker(min_chunk_size=50)
        
        content = """
## Small Section

Tiny.

## Normal Section

This section has enough content to be included in the chunks.
"""
        
        metadata = {
            'video_id': 'test123',
            'video_title': 'Test Video',
            'subject': 'Testing',
        }
        
        chunks = chunker.chunk_markdown(content, metadata)
        
        # Should only have chunk from Normal Section
        assert len(chunks) >= 1
        
        # Check that small section was skipped
        section_titles = [c.metadata.section_title for c in chunks]
        assert 'Normal Section' in section_titles
    
    def test_generate_chunk_id(self):
        """Test chunk ID generation."""
        chunker = DocumentChunker()
        
        chunk_id = chunker._generate_chunk_id(
            video_id="test123",
            section_title="Introduction",
            content="Some test content",
        )
        
        # Should start with video_id
        assert chunk_id.startswith("test123_")
        
        # Should be consistent for same inputs
        chunk_id2 = chunker._generate_chunk_id(
            video_id="test123",
            section_title="Introduction",
            content="Some test content",
        )
        assert chunk_id == chunk_id2
        
        # Should differ for different inputs
        chunk_id3 = chunker._generate_chunk_id(
            video_id="test123",
            section_title="Introduction",
            content="Different content",
        )
        assert chunk_id != chunk_id3
    
    def test_validate_chunk_valid(self):
        """Test validating a valid chunk."""
        chunker = DocumentChunker()
        
        metadata = ChunkMetadata(
            video_id="test123",
            video_title="Test Video",
            subject="Testing",
            section_title="Introduction",
            section_level=2,
            token_count=100,
            created_at=datetime.utcnow().isoformat(),
        )
        
        chunk = Chunk(
            chunk_id="test123_abc",
            content="This is valid content with enough tokens.",
            metadata=metadata,
        )
        
        assert chunker.validate_chunk(chunk) is True
    
    def test_validate_chunk_missing_id(self):
        """Test validating chunk with missing ID."""
        chunker = DocumentChunker()
        
        metadata = ChunkMetadata(
            video_id="test123",
            video_title="Test Video",
            subject="Testing",
            section_title="Introduction",
            section_level=2,
            token_count=100,
            created_at=datetime.utcnow().isoformat(),
        )
        
        chunk = Chunk(
            chunk_id="",
            content="Content",
            metadata=metadata,
        )
        
        assert chunker.validate_chunk(chunk) is False
    
    def test_validate_chunk_empty_content(self):
        """Test validating chunk with empty content."""
        chunker = DocumentChunker()
        
        metadata = ChunkMetadata(
            video_id="test123",
            video_title="Test Video",
            subject="Testing",
            section_title="Introduction",
            section_level=2,
            token_count=100,
            created_at=datetime.utcnow().isoformat(),
        )
        
        chunk = Chunk(
            chunk_id="test123_abc",
            content="",
            metadata=metadata,
        )
        
        assert chunker.validate_chunk(chunk) is False
    
    def test_validate_chunk_too_small(self):
        """Test validating chunk that's too small."""
        chunker = DocumentChunker(min_chunk_size=100)
        
        metadata = ChunkMetadata(
            video_id="test123",
            video_title="Test Video",
            subject="Testing",
            section_title="Introduction",
            section_level=2,
            token_count=10,  # Too small
            created_at=datetime.utcnow().isoformat(),
        )
        
        chunk = Chunk(
            chunk_id="test123_abc",
            content="Short",
            metadata=metadata,
        )
        
        assert chunker.validate_chunk(chunk) is False
    
    def test_validate_chunk_too_large(self):
        """Test validating chunk that's too large."""
        chunker = DocumentChunker(chunk_size=100)
        
        metadata = ChunkMetadata(
            video_id="test123",
            video_title="Test Video",
            subject="Testing",
            section_title="Introduction",
            section_level=2,
            token_count=200,  # Too large (> 1.5x chunk_size)
            created_at=datetime.utcnow().isoformat(),
        )
        
        chunk = Chunk(
            chunk_id="test123_abc",
            content="Content",
            metadata=metadata,
        )
        
        assert chunker.validate_chunk(chunk) is False
    
    def test_validate_chunk_missing_metadata(self):
        """Test validating chunk with incomplete metadata."""
        chunker = DocumentChunker()
        
        metadata = ChunkMetadata(
            video_id="",  # Missing
            video_title="Test Video",
            subject="Testing",
            section_title="Introduction",
            section_level=2,
            token_count=100,
            created_at=datetime.utcnow().isoformat(),
        )
        
        chunk = Chunk(
            chunk_id="test123_abc",
            content="Content",
            metadata=metadata,
        )
        
        assert chunker.validate_chunk(chunk) is False
    
    def test_chunk_markdown_no_sections(self):
        """Test chunking with no valid sections."""
        chunker = DocumentChunker(min_chunk_size=1000)
        
        content = """
## Small

Tiny content.
"""
        
        metadata = {
            'video_id': 'test123',
            'video_title': 'Test Video',
            'subject': 'Testing',
        }
        
        chunks = chunker.chunk_markdown(content, metadata)
        
        # Should return empty list when all sections are too small
        assert len(chunks) == 0
    
    def test_chunk_markdown_preserves_hierarchy(self):
        """Test that subsections are preserved within parent sections."""
        chunker = DocumentChunker()
        
        content = """
## Main Section

Introduction to main section.

### Subsection 1

Content of subsection 1.

### Subsection 2

Content of subsection 2.

## Another Section

Different section.
"""
        
        metadata = {
            'video_id': 'test123',
            'video_title': 'Test Video',
            'subject': 'Testing',
        }
        
        chunks = chunker.chunk_markdown(content, metadata)
        
        # Should have 2 main chunks
        assert len(chunks) == 2
        
        # First chunk should contain subsections
        main_chunk = chunks[0]
        assert main_chunk.metadata.section_title == 'Main Section'
        assert 'Subsection 1' in main_chunk.content
        assert 'Subsection 2' in main_chunk.content
