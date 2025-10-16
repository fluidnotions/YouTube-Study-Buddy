# RAG API Reference

Complete API documentation for all RAG modules with code examples and type signatures.

## Table of Contents

1. [Core Types](#core-types)
2. [Configuration](#configuration)
3. [VectorStore](#vectorstore)
4. [EmbeddingService](#embeddingservice)
5. [DocumentChunker](#documentchunker)
6. [RAGPipelineStage](#ragpipelinestage)
7. [IndexTracker](#indextracker)
8. [RAGCrossReferencer](#ragcrossreferencer)
9. [Metrics](#metrics)
10. [Usage Examples](#usage-examples)

---

## Core Types

All shared data types are defined in `src/yt_study_buddy/rag/types.py`.

### ChunkMetadata

Metadata attached to each document chunk.

```python
@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""

    video_id: str              # Video identifier
    video_title: str           # Title of the video
    subject: str               # Subject category (e.g., "AI", "Math")
    section_title: str         # Title of the section in the note
    section_level: int         # Heading level (2 for H2, 3 for H3, etc.)
    token_count: int           # Number of tokens in the chunk
    created_at: str            # ISO 8601 timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for ChromaDB storage."""
```

**Example**:
```python
from yt_study_buddy.rag.types import ChunkMetadata

metadata = ChunkMetadata(
    video_id="abc123",
    video_title="Introduction to Neural Networks",
    subject="AI",
    section_title="Backpropagation",
    section_level=2,
    token_count=245,
    created_at="2025-10-17T12:00:00"
)

# Convert to dict for storage
metadata_dict = metadata.to_dict()
```

---

### Chunk

A document chunk with content and metadata.

```python
@dataclass
class Chunk:
    """A document chunk with content and metadata."""

    chunk_id: str              # Unique identifier (format: video_id_section_hash)
    content: str               # Text content of the chunk
    metadata: ChunkMetadata    # Associated metadata

    def __post_init__(self):
        """Validates chunk on creation."""
```

**Validation**:
- `chunk_id` must be non-empty
- `content` must be non-empty
- `metadata.token_count` must be positive

**Example**:
```python
from yt_study_buddy.rag.types import Chunk, ChunkMetadata

chunk = Chunk(
    chunk_id="abc123_intro_a8f2",
    content="Neural networks are inspired by biological neurons...",
    metadata=ChunkMetadata(
        video_id="abc123",
        video_title="Neural Networks 101",
        subject="AI",
        section_title="Introduction",
        section_level=2,
        token_count=150,
        created_at="2025-10-17T12:00:00"
    )
)
```

---

### SearchResult

Result from a vector similarity search.

```python
@dataclass
class SearchResult:
    """Result from vector similarity search."""

    chunk_id: str              # Unique chunk identifier
    content: str               # Chunk text content
    metadata: ChunkMetadata    # Chunk metadata
    similarity_score: float    # Similarity score (0-1, higher = more similar)
    distance: float            # Distance metric from ChromaDB (inverse of similarity)

    def __post_init__(self):
        """Validates similarity_score is in [0, 1]."""
```

**Example**:
```python
# SearchResult is typically returned by VectorStore.search_similar()
results = vector_store.search_similar(
    query_embedding=embedding,
    filters={"subject": "AI"},
    top_k=5
)

for result in results:
    print(f"Score: {result.similarity_score:.2f}")
    print(f"Section: {result.metadata.section_title}")
    print(f"Content: {result.content[:100]}...")
```

---

### ProcessResult

Result from RAG pipeline stage processing.

```python
@dataclass
class ProcessResult:
    """Result from RAG pipeline stage processing."""

    success: bool                          # Whether processing succeeded
    video_id: str                          # Video identifier
    note_path: str                         # Path to the note file
    chunks_created: int = 0                # Number of chunks created
    embeddings_generated: int = 0          # Number of embeddings generated
    processing_time_seconds: float = 0.0   # Time taken for processing
    error_message: Optional[str] = None    # Error message if failed
    skipped: bool = False                  # Whether processing was skipped
    skip_reason: Optional[str] = None      # Reason for skipping

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
```

**Example**:
```python
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage

stage = RAGPipelineStage(config)
result = stage.process_note(
    note_path=Path("notes/AI/Neural Networks.md"),
    video_metadata={
        "video_id": "abc123",
        "video_title": "Neural Networks 101",
        "subject": "AI"
    }
)

if result.success:
    print(f"✓ Indexed {result.chunks_created} chunks in {result.processing_time_seconds:.2f}s")
else:
    print(f"✗ Failed: {result.error_message}")

# Log result
logger.info(result.to_dict())
```

---

## Configuration

### RAGConfig

Configuration dataclass for RAG system.

```python
@dataclass
class RAGConfig:
    """Configuration for RAG system."""

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
        """Ensures Path objects are properly initialized."""
```

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | True | Enable/disable RAG features |
| `model_name` | str | "all-mpnet-base-v2" | Sentence-transformer model |
| `model_cache_dir` | Path | ~/.cache/torch/... | Model cache location |
| `vector_store_dir` | Path | .chroma_db | ChromaDB persistence directory |
| `collection_name` | str | "study_notes" | ChromaDB collection name |
| `similarity_threshold` | float | 0.3 | Minimum similarity for cross-refs (0-1) |
| `max_results` | int | 5 | Maximum search results |
| `batch_size` | int | 32 | Embedding batch size |
| `chunk_size` | int | 1000 | Max tokens per chunk |
| `chunk_overlap` | int | 50 | Overlapping tokens between chunks |
| `min_chunk_size` | int | 50 | Minimum chunk size |
| `index_tracker_file` | Path | .rag_index_tracker.json | Index tracker file path |

**Example**:
```python
from yt_study_buddy.rag.config import RAGConfig

# Default configuration
config = RAGConfig()

# Custom configuration
config = RAGConfig(
    enabled=True,
    model_name="all-MiniLM-L6-v2",
    similarity_threshold=0.4,
    max_results=10
)
```

---

### load_config_from_env()

Load configuration from environment variables.

```python
def load_config_from_env() -> RAGConfig:
    """
    Load RAG configuration from environment variables.

    Environment Variables:
        RAG_ENABLED: Enable/disable RAG (default: true)
        RAG_MODEL: Sentence-transformer model (default: all-mpnet-base-v2)
        RAG_MODEL_CACHE_DIR: Model cache directory
        RAG_VECTOR_STORE_DIR: ChromaDB directory
        RAG_COLLECTION_NAME: Collection name (default: study_notes)
        RAG_SIMILARITY_THRESHOLD: Min similarity (default: 0.3)
        RAG_MAX_RESULTS: Max results (default: 5)
        RAG_BATCH_SIZE: Batch size (default: 32)
        RAG_CHUNK_SIZE: Max chunk tokens (default: 1000)
        RAG_CHUNK_OVERLAP: Overlap tokens (default: 50)
        RAG_MIN_CHUNK_SIZE: Min chunk tokens (default: 50)
        RAG_INDEX_TRACKER_FILE: Tracker file path

        # Legacy aliases:
        CHROMA_PERSIST_DIR: Alias for RAG_VECTOR_STORE_DIR
        MODEL_CACHE_DIR: Alias for RAG_MODEL_CACHE_DIR

    Returns:
        RAGConfig with values from environment
    """
```

**Example**:
```python
from yt_study_buddy.rag.config import load_config_from_env
import os

# Set environment variables
os.environ['RAG_ENABLED'] = 'true'
os.environ['RAG_MODEL'] = 'all-mpnet-base-v2'
os.environ['RAG_SIMILARITY_THRESHOLD'] = '0.4'

# Load configuration
config = load_config_from_env()

print(f"RAG enabled: {config.enabled}")
print(f"Model: {config.model_name}")
print(f"Threshold: {config.similarity_threshold}")
```

---

## VectorStore

ChromaDB wrapper for storing and searching document embeddings.

### Constructor

```python
class VectorStore:
    def __init__(
        self,
        persist_dir: str,
        collection_name: str = "study_notes",
        embedding_function: Optional[Any] = None,
    ):
        """
        Initialize vector store.

        Args:
            persist_dir: Directory to persist ChromaDB data
            collection_name: Name of the collection (default: study_notes)
            embedding_function: Optional custom embedding function
        """
```

**Example**:
```python
from yt_study_buddy.rag.vector_store import VectorStore

store = VectorStore(
    persist_dir="/path/to/.chroma_db",
    collection_name="study_notes"
)
```

---

### add_chunks()

Add chunks to the vector store.

```python
def add_chunks(self, chunks: List[Chunk]) -> bool:
    """
    Add document chunks to the vector store.

    Args:
        chunks: List of Chunk objects to add

    Returns:
        True if successful, False otherwise

    Raises:
        RuntimeError: If vector store is not initialized
    """
```

**Example**:
```python
from yt_study_buddy.rag.types import Chunk, ChunkMetadata

chunks = [
    Chunk(
        chunk_id="abc123_intro_001",
        content="Neural networks are computational models...",
        metadata=ChunkMetadata(
            video_id="abc123",
            video_title="Neural Networks 101",
            subject="AI",
            section_title="Introduction",
            section_level=2,
            token_count=120,
            created_at="2025-10-17T12:00:00"
        )
    ),
    # More chunks...
]

success = store.add_chunks(chunks)
if success:
    print(f"Added {len(chunks)} chunks to vector store")
```

---

### search_similar()

Search for similar chunks using an embedding vector.

```python
def search_similar(
    self,
    query_embedding: np.ndarray,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
) -> List[SearchResult]:
    """
    Search for similar chunks.

    Args:
        query_embedding: Query embedding vector (numpy array)
        filters: Optional metadata filters (e.g., {"subject": "AI"})
        top_k: Number of results to return (default: 5)

    Returns:
        List of SearchResult objects, sorted by similarity (highest first)

    Raises:
        RuntimeError: If vector store is not initialized
    """
```

**Filter Options**:
- `subject`: Filter by subject (e.g., "AI", "Math")
- `video_id`: Filter by video ID
- `section_title`: Filter by section title

**Example**:
```python
import numpy as np

# Get query embedding from embedding service
query_text = "How do neural networks learn?"
query_embedding = embedding_service.embed_text(query_text)

# Search with filters
results = store.search_similar(
    query_embedding=query_embedding,
    filters={"subject": "AI"},
    top_k=5
)

for result in results:
    print(f"Similarity: {result.similarity_score:.2f}")
    print(f"Video: {result.metadata.video_title}")
    print(f"Section: {result.metadata.section_title}")
    print(f"Preview: {result.content[:100]}...")
    print()
```

---

### delete_by_video_id()

Delete all chunks for a specific video.

```python
def delete_by_video_id(self, video_id: str) -> bool:
    """
    Delete all chunks associated with a video.

    Args:
        video_id: Video identifier

    Returns:
        True if successful, False otherwise
    """
```

**Example**:
```python
# Delete all chunks for a video (e.g., when re-indexing)
success = store.delete_by_video_id("abc123")
if success:
    print("Deleted all chunks for video abc123")
```

---

### collection_stats()

Get statistics about the collection.

```python
def collection_stats(self) -> Dict[str, Any]:
    """
    Get collection statistics.

    Returns:
        Dictionary with stats:
        - count: Number of documents
        - subjects: Set of unique subjects
        - videos: Set of unique video IDs
    """
```

**Example**:
```python
stats = store.collection_stats()
print(f"Total chunks: {stats['count']}")
print(f"Subjects: {', '.join(stats['subjects'])}")
print(f"Videos indexed: {len(stats['videos'])}")
```

---

### health_check()

Check if the vector store is operational.

```python
def health_check(self) -> bool:
    """
    Check if vector store is healthy.

    Returns:
        True if operational, False otherwise
    """
```

**Example**:
```python
if store.health_check():
    print("✓ Vector store is operational")
else:
    print("✗ Vector store is not responding")
```

---

## EmbeddingService

Sentence-transformer wrapper for generating text embeddings.

### Constructor

```python
class EmbeddingService:
    def __init__(
        self,
        model_name: str = "all-mpnet-base-v2",
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize embedding service.

        Args:
            model_name: Sentence-transformer model name
            cache_dir: Model cache directory (default: None, uses default)
            device: Device to run on ("cuda", "mps", "cpu", or None for auto)
        """
```

**Example**:
```python
from yt_study_buddy.rag.embedding_service import EmbeddingService

# Auto-detect device
service = EmbeddingService(model_name="all-mpnet-base-v2")

# Force CPU
service = EmbeddingService(model_name="all-mpnet-base-v2", device="cpu")

# Custom cache directory
service = EmbeddingService(
    model_name="all-mpnet-base-v2",
    cache_dir="/custom/cache/dir"
)
```

---

### embed_text()

Generate embedding for a single text.

```python
def embed_text(self, text: str) -> np.ndarray:
    """
    Generate embedding for a single text.

    Args:
        text: Text to embed

    Returns:
        Numpy array containing the embedding vector

    Raises:
        ValueError: If text is empty
        RuntimeError: If embedding generation fails
    """
```

**Example**:
```python
text = "Neural networks learn through backpropagation"
embedding = service.embed_text(text)

print(f"Embedding shape: {embedding.shape}")  # (768,) for all-mpnet-base-v2
print(f"Embedding type: {type(embedding)}")   # numpy.ndarray
```

---

### embed_batch()

Generate embeddings for multiple texts (more efficient).

```python
def embed_batch(
    self,
    texts: List[str],
    batch_size: Optional[int] = None,
    show_progress: bool = False,
) -> np.ndarray:
    """
    Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed
        batch_size: Batch size (default: None, uses model default)
        show_progress: Show progress bar (default: False)

    Returns:
        Numpy array of shape (n_texts, embedding_dim)

    Raises:
        ValueError: If texts is empty
        RuntimeError: If embedding generation fails
    """
```

**Example**:
```python
texts = [
    "Neural networks learn from data",
    "Backpropagation adjusts weights",
    "Gradient descent minimizes loss"
]

embeddings = service.embed_batch(texts, show_progress=True)

print(f"Shape: {embeddings.shape}")  # (3, 768)
print(f"First embedding: {embeddings[0][:5]}")
```

---

### get_embedding_dim()

Get the dimensionality of embeddings.

```python
def get_embedding_dim(self) -> int:
    """
    Get embedding dimensionality.

    Returns:
        Embedding dimension (e.g., 768 for all-mpnet-base-v2)
    """
```

**Example**:
```python
dim = service.get_embedding_dim()
print(f"Embedding dimension: {dim}")  # 768
```

---

### model_info()

Get information about the loaded model.

```python
def model_info(self) -> Dict[str, Any]:
    """
    Get model information.

    Returns:
        Dictionary with model info:
        - model_name: Name of the model
        - embedding_dim: Embedding dimensionality
        - device: Device model is running on
        - max_seq_length: Maximum sequence length
    """
```

**Example**:
```python
info = service.model_info()
print(f"Model: {info['model_name']}")
print(f"Dimension: {info['embedding_dim']}")
print(f"Device: {info['device']}")
print(f"Max length: {info['max_seq_length']}")
```

---

## DocumentChunker

Markdown document chunker with section-based splitting.

### Constructor

```python
class DocumentChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,
    ):
        """
        Initialize document chunker.

        Args:
            chunk_size: Maximum tokens per chunk (default: 1000)
            chunk_overlap: Overlapping tokens between chunks (default: 50)
            min_chunk_size: Minimum tokens for a valid chunk (default: 50)
        """
```

**Example**:
```python
from yt_study_buddy.rag.document_chunker import DocumentChunker

chunker = DocumentChunker(
    chunk_size=1000,
    chunk_overlap=50,
    min_chunk_size=50
)
```

---

### chunk_markdown()

Chunk a markdown document by sections.

```python
def chunk_markdown(
    self,
    content: str,
    metadata: Dict[str, Any],
) -> List[Chunk]:
    """
    Chunk markdown content by sections.

    Args:
        content: Markdown content to chunk
        metadata: Metadata dict with:
            - video_id: Video identifier
            - video_title: Title of video
            - subject: Subject category

    Returns:
        List of Chunk objects

    Raises:
        ValueError: If required metadata is missing
    """
```

**Example**:
```python
content = """
## Introduction

Neural networks are computational models inspired by biological brains.
They consist of interconnected nodes (neurons) organized in layers.

## Architecture

A typical neural network has three types of layers:
- Input layer: Receives data
- Hidden layers: Process information
- Output layer: Produces results

## Training

Training adjusts weights using backpropagation and gradient descent.
"""

metadata = {
    "video_id": "abc123",
    "video_title": "Neural Networks 101",
    "subject": "AI"
}

chunks = chunker.chunk_markdown(content, metadata)

for chunk in chunks:
    print(f"Section: {chunk.metadata.section_title}")
    print(f"Tokens: {chunk.metadata.token_count}")
    print(f"Content: {chunk.content[:100]}...")
    print()
```

---

### validate_chunk()

Validate a chunk meets requirements.

```python
def validate_chunk(self, chunk: Chunk) -> bool:
    """
    Validate a chunk.

    Args:
        chunk: Chunk to validate

    Returns:
        True if valid, False otherwise
    """
```

**Example**:
```python
if chunker.validate_chunk(chunk):
    print("✓ Chunk is valid")
else:
    print("✗ Chunk is invalid (too small or malformed)")
```

---

## RAGPipelineStage

Pipeline stage for integrating RAG into video processing.

### Constructor

```python
class RAGPipelineStage:
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
            chunker: Optional chunker (created if None)
            index_tracker: Optional index tracker (created if None)
        """
```

**Example**:
```python
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage
from yt_study_buddy.rag.config import load_config_from_env

config = load_config_from_env()
stage = RAGPipelineStage(config)

# Or with custom components
stage = RAGPipelineStage(
    config=config,
    embedding_service=my_embedding_service,
    vector_store=my_vector_store
)
```

---

### process_note()

Process a single note (index into RAG).

```python
def process_note(
    self,
    note_path: Path,
    video_metadata: Dict[str, str],
    force: bool = False,
) -> ProcessResult:
    """
    Process a note and add to vector store.

    Args:
        note_path: Path to markdown note
        video_metadata: Dict with:
            - video_id: Video identifier
            - video_title: Video title
            - subject: Subject category
        force: Force reprocessing even if already indexed

    Returns:
        ProcessResult with success status and stats
    """
```

**Example**:
```python
result = stage.process_note(
    note_path=Path("notes/AI/Neural Networks.md"),
    video_metadata={
        "video_id": "abc123",
        "video_title": "Neural Networks 101",
        "subject": "AI"
    }
)

if result.success:
    print(f"✓ Indexed {result.chunks_created} chunks")
    print(f"  Duration: {result.processing_time_seconds:.2f}s")
else:
    print(f"✗ Failed: {result.error_message}")
```

---

### process_batch()

Process multiple notes in batch.

```python
def process_batch(
    self,
    notes: List[Tuple[Path, Dict[str, str]]],
    show_progress: bool = True,
) -> List[ProcessResult]:
    """
    Process multiple notes in batch.

    Args:
        notes: List of (note_path, video_metadata) tuples
        show_progress: Show progress bar

    Returns:
        List of ProcessResult objects
    """
```

**Example**:
```python
notes = [
    (Path("notes/AI/Note1.md"), {"video_id": "abc123", "video_title": "...", "subject": "AI"}),
    (Path("notes/AI/Note2.md"), {"video_id": "def456", "video_title": "...", "subject": "AI"}),
]

results = stage.process_batch(notes, show_progress=True)

successful = sum(1 for r in results if r.success)
print(f"Processed {successful}/{len(results)} notes successfully")
```

---

### is_note_indexed()

Check if a note is already indexed.

```python
def is_note_indexed(self, video_id: str) -> bool:
    """
    Check if a note is indexed.

    Args:
        video_id: Video identifier

    Returns:
        True if indexed, False otherwise
    """
```

**Example**:
```python
if stage.is_note_indexed("abc123"):
    print("Note is already indexed")
else:
    print("Note needs indexing")
```

---

### is_ready()

Check if the pipeline stage is ready.

```python
def is_ready(self) -> bool:
    """
    Check if pipeline is ready to process.

    Returns:
        True if all components initialized, False otherwise
    """
```

**Example**:
```python
if stage.is_ready():
    print("✓ RAG pipeline ready")
else:
    print("✗ RAG pipeline not ready (component initialization failed)")
```

---

## IndexTracker

Tracks which notes have been indexed for incremental updates.

### Constructor

```python
class IndexTracker:
    def __init__(self, tracker_file: Path):
        """
        Initialize index tracker.

        Args:
            tracker_file: Path to JSON file for storing tracking data
        """
```

**Example**:
```python
from yt_study_buddy.rag.index_tracker import IndexTracker

tracker = IndexTracker(tracker_file=Path(".rag_index_tracker.json"))
```

---

### mark_indexed()

Mark a note as indexed.

```python
def mark_indexed(
    self,
    video_id: str,
    note_path: Path,
    chunks_created: int = 0,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Mark a note as indexed.

    Args:
        video_id: Video identifier
        note_path: Path to note file
        chunks_created: Number of chunks created (default: 0)
        metadata: Optional additional metadata to store
    """
```

**Example**:
```python
tracker.mark_indexed(
    video_id="abc123",
    note_path=Path("notes/AI/Neural Networks.md"),
    chunks_created=12
)
```

---

### is_indexed()

Check if a note is indexed.

```python
def is_indexed(self, video_id: str, note_path: Path) -> bool:
    """
    Check if a note is indexed.

    Args:
        video_id: Video identifier
        note_path: Path to note file

    Returns:
        True if indexed, False otherwise
    """
```

**Example**:
```python
if tracker.is_indexed("abc123", Path("notes/AI/Neural Networks.md")):
    print("Note is indexed")
```

---

### needs_reindex()

Check if a note needs re-indexing (modified).

```python
def needs_reindex(self, video_id: str, note_path: Path) -> bool:
    """
    Check if a note needs re-indexing.

    Compares file modification time with tracked modification time.

    Args:
        video_id: Video identifier
        note_path: Path to note file

    Returns:
        True if needs re-indexing, False otherwise
    """
```

**Example**:
```python
if tracker.needs_reindex("abc123", note_path):
    print("Note has been modified, needs re-indexing")
    # Re-index the note...
```

---

### get_unindexed_notes()

Get all unindexed notes in a directory.

```python
def get_unindexed_notes(self, notes_dir: Path) -> List[Path]:
    """
    Get list of unindexed notes.

    Args:
        notes_dir: Directory to scan for notes

    Returns:
        List of paths to unindexed markdown files
    """
```

**Example**:
```python
unindexed = tracker.get_unindexed_notes(Path("notes"))
print(f"Found {len(unindexed)} unindexed notes:")
for note in unindexed:
    print(f"  - {note}")
```

---

## RAGCrossReferencer

High-level interface for semantic cross-referencing.

### Constructor

```python
class RAGCrossReferencer:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        config: RAGConfig,
    ):
        """
        Initialize RAG cross-referencer.

        Args:
            embedding_service: Embedding generation service
            vector_store: Vector storage and search
            config: RAG configuration
        """
```

**Example**:
```python
from yt_study_buddy.rag.cross_referencer import RAGCrossReferencer

referencer = RAGCrossReferencer(
    embedding_service=embedding_service,
    vector_store=vector_store,
    config=config
)
```

---

### find_references()

Find semantic cross-references for a section.

```python
def find_references(
    self,
    section_text: str,
    current_video_id: str,
    subject: Optional[str] = None,
    global_context: bool = False,
) -> List[CrossReference]:
    """
    Find semantically similar references.

    Args:
        section_text: Text of the current section
        current_video_id: Current video ID (to exclude self-references)
        subject: Optional subject filter (e.g., "AI")
        global_context: If True, search all subjects; if False, same subject only

    Returns:
        List of CrossReference objects, sorted by relevance
    """
```

**Example**:
```python
from yt_study_buddy.rag.cross_referencer import RAGCrossReferencer

refs = referencer.find_references(
    section_text="Neural networks use backpropagation to learn...",
    current_video_id="abc123",
    subject="AI",
    global_context=False
)

for ref in refs:
    print(f"Score: {ref.similarity_score:.2f}")
    print(f"Link: {ref.obsidian_link}")
    print(f"Preview: {ref.preview_text}")
    print()
```

---

### CrossReference

Result object from find_references().

```python
@dataclass
class CrossReference:
    """A cross-reference link to related content."""

    target_section: str         # Title of target section
    target_video_id: str        # Video ID of target
    target_video_title: str     # Title of target video
    similarity_score: float     # Semantic similarity (0-1)
    preview_text: str           # Preview of target content
    obsidian_link: str          # Formatted [[Wiki Link]]
```

**Example**:
```python
# CrossReference is returned by find_references()
for ref in refs:
    # Use in your notes
    link = ref.obsidian_link  # "[[Neural Networks 101#Backpropagation]]"

    # Display info
    print(f"Link to: {ref.target_video_title}")
    print(f"Section: {ref.target_section}")
    print(f"Relevance: {ref.similarity_score:.2%}")
```

---

## Metrics

Quality metrics for RAG cross-referencing.

### MetricsCollector

```python
class MetricsCollector:
    """Collects quality metrics for RAG operations."""

    def track_query(
        self,
        query_text: str,
        results: List[SearchResult],
        query_time_ms: float,
    ) -> None:
        """Track a query and its results."""

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""

    def reset(self) -> None:
        """Reset all metrics."""
```

**Example**:
```python
from yt_study_buddy.rag.metrics import MetricsCollector

collector = MetricsCollector()

# Track queries
collector.track_query(
    query_text="neural networks",
    results=search_results,
    query_time_ms=45.2
)

# Get statistics
stats = collector.get_stats()
print(f"Queries: {stats['total_queries']}")
print(f"Avg latency: {stats['avg_latency_ms']:.2f}ms")
print(f"Avg similarity: {stats['avg_similarity']:.2f}")
```

---

## Usage Examples

### Complete End-to-End Example

```python
from pathlib import Path
from yt_study_buddy.rag.config import load_config_from_env
from yt_study_buddy.rag.vector_store import VectorStore
from yt_study_buddy.rag.embedding_service import EmbeddingService
from yt_study_buddy.rag.document_chunker import DocumentChunker
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage
from yt_study_buddy.rag.cross_referencer import RAGCrossReferencer

# 1. Load configuration
config = load_config_from_env()

# 2. Initialize components
embedding_service = EmbeddingService(model_name=config.model_name)
vector_store = VectorStore(
    persist_dir=str(config.vector_store_dir),
    collection_name=config.collection_name
)
chunker = DocumentChunker(
    chunk_size=config.chunk_size,
    chunk_overlap=config.chunk_overlap,
    min_chunk_size=config.min_chunk_size
)

# 3. Index a note
pipeline = RAGPipelineStage(config)
result = pipeline.process_note(
    note_path=Path("notes/AI/Neural Networks.md"),
    video_metadata={
        "video_id": "abc123",
        "video_title": "Neural Networks 101",
        "subject": "AI"
    }
)

if result.success:
    print(f"✓ Indexed {result.chunks_created} chunks")

# 4. Find cross-references
referencer = RAGCrossReferencer(
    embedding_service=embedding_service,
    vector_store=vector_store,
    config=config
)

refs = referencer.find_references(
    section_text="Backpropagation adjusts weights...",
    current_video_id="abc123",
    subject="AI"
)

# 5. Use the references
for ref in refs:
    print(f"See also: {ref.obsidian_link} ({ref.similarity_score:.2f})")
```

---

### Migration Script Example

```python
from pathlib import Path
from yt_study_buddy.rag.config import load_config_from_env
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage

# Load configuration
config = load_config_from_env()
stage = RAGPipelineStage(config)

# Find all markdown notes
notes_dir = Path("notes")
note_files = list(notes_dir.rglob("*.md"))

print(f"Found {len(note_files)} notes to index")

# Process each note
for note_path in note_files:
    # Extract metadata from path
    subject = note_path.parent.name
    video_title = note_path.stem
    video_id = f"migrated_{note_path.stem.lower().replace(' ', '_')}"

    # Index the note
    result = stage.process_note(
        note_path=note_path,
        video_metadata={
            "video_id": video_id,
            "video_title": video_title,
            "subject": subject
        }
    )

    if result.success:
        print(f"✓ {note_path.name}: {result.chunks_created} chunks")
    else:
        print(f"✗ {note_path.name}: {result.error_message}")

print("Migration complete!")
```

---

### Query Tool Example

```python
from yt_study_buddy.rag.config import load_config_from_env
from yt_study_buddy.rag.embedding_service import EmbeddingService
from yt_study_buddy.rag.vector_store import VectorStore

# Initialize
config = load_config_from_env()
service = EmbeddingService(model_name=config.model_name)
store = VectorStore(
    persist_dir=str(config.vector_store_dir),
    collection_name=config.collection_name
)

# Interactive query loop
while True:
    query = input("\nQuery (or 'quit'): ")
    if query.lower() == 'quit':
        break

    # Generate embedding
    embedding = service.embed_text(query)

    # Search
    results = store.search_similar(
        query_embedding=embedding,
        filters={},
        top_k=5
    )

    # Display results
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.metadata.video_title} - {result.metadata.section_title}")
        print(f"   Score: {result.similarity_score:.2f}")
        print(f"   Preview: {result.content[:100]}...")
```

---

## Error Handling

All RAG modules follow consistent error handling patterns:

### Common Exceptions

- `ValueError`: Invalid arguments (empty text, invalid config)
- `RuntimeError`: Component initialization or operation failures
- `IOError`: File system operations (read/write failures)

### Error Handling Pattern

```python
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage

try:
    stage = RAGPipelineStage(config)

    if not stage.is_ready():
        logger.warning("RAG pipeline not ready, skipping")
        # Use fallback mechanism
    else:
        result = stage.process_note(note_path, metadata)
        if result.success:
            logger.info(f"Indexed successfully: {result.chunks_created} chunks")
        else:
            logger.error(f"Indexing failed: {result.error_message}")
            # Handle failure (e.g., retry, skip, alert)

except Exception as e:
    logger.exception(f"Unexpected error in RAG pipeline: {e}")
    # Graceful degradation - continue without RAG
```

---

## Type Hints

All RAG modules use comprehensive type hints for better IDE support:

```python
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from pathlib import Path

def process_note(
    note_path: Path,
    video_metadata: Dict[str, str],
    force: bool = False,
) -> ProcessResult:
    """Fully type-hinted function signature."""
    ...
```

Use a type checker like mypy for validation:
```bash
mypy src/yt_study_buddy/rag/
```

---

**Last Updated**: October 17, 2025
**Version**: 1.0.0 (Initial RAG Implementation)
