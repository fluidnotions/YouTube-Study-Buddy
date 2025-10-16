# RAG Developer Guide

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Modules](#core-modules)
4. [Pipeline Integration](#pipeline-integration)
5. [Development Setup](#development-setup)
6. [Testing](#testing)
7. [Performance Tuning](#performance-tuning)
8. [Adding Features](#adding-features)
9. [Troubleshooting](#troubleshooting)
10. [API Quick Reference](#api-quick-reference)

---

## Overview

The RAG (Retrieval-Augmented Generation) system adds semantic cross-referencing to YouTube Study Buddy. It uses sentence transformers to generate embeddings and ChromaDB for vector similarity search.

### Key Components

- **VectorStore**: ChromaDB wrapper for storing and searching embeddings
- **EmbeddingService**: Sentence-transformer interface for generating embeddings
- **DocumentChunker**: Markdown section-based chunking with metadata
- **RAGPipelineStage**: Pipeline integration for automatic indexing
- **RAGCrossReferencer**: High-level interface for finding semantic links
- **IndexTracker**: Modification tracking for incremental updates

### Design Principles

1. **Graceful Degradation**: RAG failures never break the core application
2. **Feature Flags**: RAG can be enabled/disabled via `RAG_ENABLED`
3. **Lazy Loading**: Models and connections initialized only when needed
4. **Separation of Concerns**: Each module has a single responsibility
5. **Error Handling**: All components handle errors and log appropriately

---

## Architecture

### High-Level Flow

```
┌─────────────────┐
│  Video Process  │
└────────┬────────┘
         │
         ├──> Generate Study Notes (Existing)
         │
         └──> RAG Pipeline Stage (NEW)
              │
              ├──> DocumentChunker
              │    └──> Split notes into sections
              │
              ├──> EmbeddingService
              │    └──> Generate embeddings
              │
              ├──> VectorStore
              │    └──> Store in ChromaDB
              │
              └──> IndexTracker
                   └──> Track indexed notes

┌──────────────────┐
│  Cross-Reference │
└────────┬─────────┘
         │
         └──> RAGCrossReferencer
              │
              ├──> EmbeddingService
              │    └──> Embed query text
              │
              ├──> VectorStore
              │    └──> Similarity search
              │
              └──> Format as [[Obsidian Links]]
```

### Data Flow

1. **Indexing** (happens after note generation):
   ```
   Markdown Note → DocumentChunker → Chunks with Metadata
                                    ↓
   EmbeddingService ← Text Chunks
          ↓
   Embeddings (768-dim vectors)
          ↓
   VectorStore (ChromaDB) ← Store with metadata
   ```

2. **Querying** (happens during cross-referencing):
   ```
   Section Text → EmbeddingService → Query Embedding
                                    ↓
   VectorStore → Similarity Search → SearchResults
                                    ↓
   RAGCrossReferencer → Filter/Rank → CrossReferences
                                    ↓
   [[Obsidian Links]]
   ```

### Directory Structure

```
src/yt_study_buddy/rag/
├── __init__.py              # Package exports
├── config.py                # Configuration & env loading
├── types.py                 # Shared type definitions
├── vector_store.py          # ChromaDB wrapper
├── embedding_service.py     # Sentence-transformer wrapper
├── document_chunker.py      # Markdown chunking
├── pipeline_stage.py        # Pipeline integration
├── index_tracker.py         # Modification tracking
├── cross_referencer.py      # Semantic link generation
└── metrics.py               # Quality metrics collection

tests/rag/
├── test_vector_store.py
├── test_embedding_service.py
├── test_document_chunker.py
├── test_pipeline_stage.py
├── test_index_tracker.py
├── test_cross_referencer.py
└── test_config.py

scripts/
├── migrate_notes_to_rag.py     # Migration tool
├── evaluate_rag.py             # Quality evaluation
├── maintain_vector_store.py    # Maintenance operations
├── query_rag_interactive.py    # Interactive REPL
├── manage_rag_volumes.sh       # Volume backup/restore
└── check_rag_health.sh         # Health checks
```

---

## Core Modules

### VectorStore (`vector_store.py`)

**Purpose**: Wrapper around ChromaDB for storing and searching document embeddings.

**Key Features**:
- Lazy client initialization
- Collection management (create/get/delete)
- Batch operations (add/delete multiple chunks)
- Metadata filtering (subject, video_id, date_range)
- Error recovery and health checks

**Example Usage**:
```python
from yt_study_buddy.rag.vector_store import VectorStore
from yt_study_buddy.rag.document_chunker import Chunk

# Initialize
store = VectorStore(
    persist_dir="/path/to/.chroma_db",
    collection_name="study_notes"
)

# Add chunks
chunks = [...]  # List of Chunk objects
success = store.add_chunks(chunks)

# Search
results = store.search_similar(
    query_embedding=embedding_vector,
    filters={"subject": "AI"},
    top_k=5
)

# Health check
if store.health_check():
    print("Vector store is operational")
```

**Implementation Details**:
- Uses ChromaDB's persistent client
- Embeddings stored with metadata for filtering
- Automatic retry logic on transient failures
- Distance metric: Cosine similarity (converted to 0-1 score)

---

### EmbeddingService (`embedding_service.py`)

**Purpose**: Generate text embeddings using sentence-transformers.

**Key Features**:
- Lazy model loading (on first use)
- Batch processing for efficiency
- CPU/GPU/MPS device detection
- Model caching to disk
- Error handling for OOM and invalid input

**Example Usage**:
```python
from yt_study_buddy.rag.embedding_service import EmbeddingService

# Initialize
service = EmbeddingService(
    model_name="all-mpnet-base-v2",
    cache_dir="/path/to/.cache"
)

# Single embedding
embedding = service.embed_text("Neural networks learn from data")
print(embedding.shape)  # (768,)

# Batch embeddings (more efficient)
texts = ["text1", "text2", "text3"]
embeddings = service.embed_batch(texts)
print(embeddings.shape)  # (3, 768)

# Model info
info = service.model_info()
print(f"Model: {info['model_name']}, Dim: {info['embedding_dim']}")
```

**Model Selection**:
- **Default**: `all-mpnet-base-v2` (768 dimensions, ~80MB)
  - Best quality/performance balance
  - Trained on 1B+ sentence pairs
  - F1 score: ~0.85 on semantic similarity tasks

- **Alternatives**:
  - `all-MiniLM-L6-v2`: Faster, smaller (384 dim, ~40MB), lower quality
  - `all-distilroberta-v1`: Slightly better quality, slower

**Performance**:
- Single embedding: ~10-50ms (CPU)
- Batch of 32: ~100-300ms (CPU)
- GPU acceleration: 5-10x faster if available

---

### DocumentChunker (`document_chunker.py`)

**Purpose**: Split markdown notes into semantically meaningful chunks.

**Key Features**:
- Section-based chunking (H2 headings)
- Preserves hierarchy (H3, H4 under H2)
- Configurable overlap for context
- Token counting with tiktoken
- Metadata extraction (section titles, hierarchy)

**Example Usage**:
```python
from yt_study_buddy.rag.document_chunker import DocumentChunker

# Initialize
chunker = DocumentChunker(
    chunk_size=1000,      # Max tokens per chunk
    chunk_overlap=50,     # Overlap between chunks
    min_chunk_size=50     # Min tokens to include
)

# Chunk a note
content = "## Introduction\n\nNeural networks...\n\n## Architecture\n\n..."
metadata = {
    "video_id": "abc123",
    "video_title": "Deep Learning Basics",
    "subject": "AI"
}

chunks = chunker.chunk_markdown(content, metadata)

for chunk in chunks:
    print(f"Section: {chunk.metadata.section_title}")
    print(f"Tokens: {chunk.metadata.token_count}")
    print(f"Content: {chunk.content[:100]}...")
```

**Chunking Strategy**:
1. Split on H2 (`##`) headings
2. Include all child sections (H3, H4, etc.)
3. If section > `chunk_size`, split further
4. Add `chunk_overlap` tokens from previous chunk
5. Discard chunks < `min_chunk_size`

**Metadata Structure**:
```python
@dataclass
class ChunkMetadata:
    video_id: str
    video_title: str
    subject: str
    section_title: str
    section_level: int
    token_count: int
    created_at: str
```

---

### RAGConfig (`config.py`)

**Purpose**: Centralized configuration management with environment variable loading.

**Configuration Options**:
```python
@dataclass
class RAGConfig:
    enabled: bool = True                    # Enable/disable RAG
    model_name: str = "all-mpnet-base-v2"  # Sentence-transformer model
    model_cache_dir: Path = ...            # Model cache location
    vector_store_dir: Path = ".chroma_db"  # ChromaDB persistence
    collection_name: str = "study_notes"   # Collection name
    similarity_threshold: float = 0.3      # Min similarity score
    max_results: int = 5                   # Max search results
    batch_size: int = 32                   # Embedding batch size
    chunk_size: int = 1000                 # Max tokens per chunk
    chunk_overlap: int = 50                # Overlap between chunks
    min_chunk_size: int = 50               # Min chunk size
    index_tracker_file: Path = ...         # Index tracking file
```

**Environment Variables**:
```bash
RAG_ENABLED=true
RAG_MODEL=all-mpnet-base-v2
RAG_SIMILARITY_THRESHOLD=0.3
RAG_MAX_RESULTS=5
RAG_BATCH_SIZE=32
CHROMA_PERSIST_DIR=/app/.chroma_db
MODEL_CACHE_DIR=/app/.cache
```

**Example Usage**:
```python
from yt_study_buddy.rag.config import load_config_from_env

# Load from environment
config = load_config_from_env()

# Use configuration
if config.enabled:
    print(f"RAG enabled with model: {config.model_name}")
```

---

## Pipeline Integration

### RAGPipelineStage (`pipeline_stage.py`)

**Purpose**: Integrate RAG indexing into the video processing pipeline.

**Key Features**:
- Idempotent (safe to re-run)
- Background processing (non-blocking)
- Error handling with graceful degradation
- Progress tracking and logging
- Modification time checking

**Example Usage**:
```python
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage
from yt_study_buddy.rag.config import load_config_from_env

# Initialize
config = load_config_from_env()
stage = RAGPipelineStage(config)

# Process a single note
result = stage.process_note(
    note_path=Path("notes/AI/Deep Learning.md"),
    video_metadata={
        "video_id": "abc123",
        "video_title": "Deep Learning Basics",
        "subject": "AI"
    }
)

if result.success:
    print(f"Indexed {result.chunks_added} chunks in {result.duration_ms}ms")
else:
    print(f"Indexing failed: {result.error}")
```

**Integration Point**:
```python
# In processing_pipeline.py
from yt_study_buddy.rag.config import load_config_from_env
from yt_study_buddy.rag.pipeline_stage import RAGPipelineStage

rag_config = load_config_from_env()

def process_video(video_id: str, subject: str):
    # ... existing note generation ...

    # Add RAG indexing (with feature flag)
    if rag_config.enabled:
        try:
            rag_stage = RAGPipelineStage(rag_config)
            result = rag_stage.process_note(
                note_path=note_path,
                video_metadata={
                    "video_id": video_id,
                    "video_title": title,
                    "subject": subject
                }
            )
            logger.info(f"RAG indexing: {result.status}")
        except Exception as e:
            # Don't fail the pipeline on RAG errors
            logger.warning(f"RAG indexing failed: {e}")
```

---

### IndexTracker (`index_tracker.py`)

**Purpose**: Track which notes have been indexed and detect modifications.

**Key Features**:
- Persistent JSON storage
- Modification time tracking
- Incremental update detection
- Batch status queries

**Example Usage**:
```python
from yt_study_buddy.rag.index_tracker import IndexTracker

# Initialize
tracker = IndexTracker(tracker_file=Path(".rag_index_tracker.json"))

# Mark as indexed
tracker.mark_indexed(
    video_id="abc123",
    note_path=Path("notes/AI/Deep Learning.md")
)

# Check if needs re-indexing
if tracker.needs_reindex("abc123", note_path):
    print("Note has been modified, needs re-indexing")

# Get all unindexed notes
unindexed = tracker.get_unindexed_notes(notes_dir=Path("notes"))
print(f"Found {len(unindexed)} unindexed notes")
```

---

### RAGCrossReferencer (`cross_referencer.py`)

**Purpose**: Find semantic cross-references and generate Obsidian links.

**Key Features**:
- Semantic similarity search
- Result ranking by score
- Deduplication logic
- Subject filtering (local vs global search)
- Obsidian link formatting

**Example Usage**:
```python
from yt_study_buddy.rag.cross_referencer import RAGCrossReferencer

# Initialize
referencer = RAGCrossReferencer(
    embedding_service=embedding_service,
    vector_store=vector_store,
    config=config
)

# Find references for a section
refs = referencer.find_references(
    section_text="Neural networks use backpropagation to learn...",
    current_video_id="abc123",
    subject="AI",           # Optional: filter by subject
    global_context=False    # False = same subject only
)

# Use the references
for ref in refs:
    print(f"Similarity: {ref.similarity_score:.2f}")
    print(f"Link: {ref.obsidian_link}")
    print(f"Preview: {ref.preview_text[:100]}...")
```

**Result Structure**:
```python
@dataclass
class CrossReference:
    target_section: str          # "Introduction to Neural Networks"
    target_video_id: str         # "xyz789"
    target_video_title: str      # "Deep Learning Fundamentals"
    similarity_score: float      # 0.85
    preview_text: str            # First 200 chars of content
    obsidian_link: str           # "[[Deep Learning Fundamentals#Introduction]]"
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- UV package manager
- Docker (optional, for containerized development)

### Local Setup

```bash
# Clone and navigate to worktree
cd /path/to/rag-worktree

# Install dependencies (UV)
uv sync

# Set environment variables
cp .env.example .env
# Edit .env and set RAG_ENABLED=true

# Run tests
uv run pytest tests/rag/ -v

# Run type checking
uv run mypy src/yt_study_buddy/rag/
```

### Docker Development

```bash
# Build and start with dev configuration
docker-compose -f docker-compose.dev.yml up --build

# Source code is mounted, changes take effect immediately
# Logs show DEBUG level output
docker logs -f youtube-study-buddy

# Run tests inside container
docker exec youtube-study-buddy pytest tests/rag/ -v
```

### Development Workflow

1. **Make changes** to RAG modules
2. **Write tests** for new functionality
3. **Run tests** locally: `uv run pytest tests/rag/`
4. **Type check**: `uv run mypy src/yt_study_buddy/rag/`
5. **Test in Docker**: `docker-compose -f docker-compose.dev.yml up --build`
6. **Commit**: `git add ... && git commit -m "feat: ..."`

---

## Testing

### Unit Tests

Located in `tests/rag/`, each module has comprehensive test coverage.

**Run all RAG tests**:
```bash
uv run pytest tests/rag/ -v
```

**Run specific test file**:
```bash
uv run pytest tests/rag/test_vector_store.py -v
```

**Run with coverage**:
```bash
uv run pytest tests/rag/ --cov=src/yt_study_buddy/rag --cov-report=html
```

### Integration Tests

Located in `tests/integration/`, these test end-to-end flows.

**Run integration tests**:
```bash
uv run pytest tests/integration/test_rag_pipeline.py -v
```

### Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

```python
import pytest
from pathlib import Path

@pytest.fixture
def temp_chroma_dir(tmp_path):
    """Temporary ChromaDB directory."""
    return tmp_path / ".chroma_db"

@pytest.fixture
def rag_config(temp_chroma_dir, tmp_path):
    """RAG configuration for testing."""
    from yt_study_buddy.rag.config import RAGConfig
    return RAGConfig(
        enabled=True,
        vector_store_dir=temp_chroma_dir,
        model_cache_dir=tmp_path / ".cache",
        batch_size=4  # Small batch for testing
    )

@pytest.fixture
def sample_note():
    """Sample markdown note content."""
    return """
## Introduction

This is an introduction to neural networks.

## Architecture

Neural networks have layers...
"""
```

### Writing Tests

**Example test**:
```python
def test_vector_store_add_and_search(rag_config):
    """Test adding chunks and searching."""
    from yt_study_buddy.rag.vector_store import VectorStore
    from yt_study_buddy.rag.document_chunker import Chunk, ChunkMetadata
    import numpy as np

    # Initialize
    store = VectorStore(
        persist_dir=str(rag_config.vector_store_dir),
        collection_name="test_collection"
    )

    # Create test chunk
    chunk = Chunk(
        chunk_id="test_001",
        content="Neural networks learn from data",
        metadata=ChunkMetadata(
            video_id="test_video",
            video_title="Test Video",
            subject="AI",
            section_title="Introduction",
            section_level=2,
            token_count=10,
            created_at="2025-10-17T00:00:00"
        )
    )

    # Add chunk
    assert store.add_chunks([chunk])

    # Search
    query_embedding = np.random.rand(768)  # Mock embedding
    results = store.search_similar(
        query_embedding=query_embedding,
        filters={"subject": "AI"},
        top_k=1
    )

    assert len(results) == 1
    assert results[0].chunk_id == "test_001"
```

---

## Performance Tuning

### Embedding Generation

**Optimize batch size**:
```bash
# Larger batches = faster, but more memory
RAG_BATCH_SIZE=64  # Default: 32
```

**Use GPU if available**:
```python
# EmbeddingService auto-detects GPU
# Force CPU for debugging:
service = EmbeddingService(device="cpu")
```

### Vector Search

**Adjust result limit**:
```bash
RAG_MAX_RESULTS=10  # Default: 5
# More results = slower search, more memory
```

**Tune similarity threshold**:
```bash
RAG_SIMILARITY_THRESHOLD=0.4  # Default: 0.3
# Higher = fewer but more relevant results
```

### ChromaDB

**Collection size monitoring**:
```python
stats = vector_store.collection_stats()
print(f"Documents: {stats['count']}")
print(f"Size: {stats['size_mb']:.2f} MB")
```

**Rebuild for optimization**:
```bash
# Periodically rebuild the index
python scripts/maintain_vector_store.py --rebuild
```

### Memory Management

**Docker memory limits**:
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G  # Increase if needed
```

**Model selection**:
- `all-mpnet-base-v2`: 768 dim, ~500MB RAM
- `all-MiniLM-L6-v2`: 384 dim, ~250MB RAM (less accurate)

### Profiling

**Time embedding generation**:
```python
import time

start = time.time()
embeddings = service.embed_batch(texts)
duration = time.time() - start
print(f"Batch of {len(texts)} took {duration*1000:.2f}ms")
```

**Monitor ChromaDB queries**:
```python
import time

start = time.time()
results = store.search_similar(query_embedding, filters={}, top_k=10)
duration = time.time() - start
print(f"Search took {duration*1000:.2f}ms")
```

---

## Adding Features

### Adding a New Embedding Model

1. **Update config**:
```python
# config.py
DEFAULT_MODELS = {
    "fast": "all-MiniLM-L6-v2",
    "balanced": "all-mpnet-base-v2",
    "accurate": "all-roberta-large-v1"
}
```

2. **Test the model**:
```python
service = EmbeddingService(model_name="all-roberta-large-v1")
embedding = service.embed_text("test")
print(f"Dimensions: {embedding.shape}")
```

3. **Update documentation** (this file and RAG_USER_GUIDE.md)

### Adding Custom Metadata Filters

1. **Update ChunkMetadata**:
```python
# document_chunker.py
@dataclass
class ChunkMetadata:
    # ... existing fields ...
    difficulty: str = "beginner"  # New field
```

2. **Add filter support**:
```python
# vector_store.py
def search_similar(self, ..., difficulty: Optional[str] = None):
    where = self._build_filter(subject, video_id, difficulty)
    # ...
```

3. **Write tests** for new filter
4. **Document** the new feature

### Extending RAGCrossReferencer

**Example: Add relevance boosting**:
```python
class RAGCrossReferencer:
    def _boost_same_subject(self, refs: List[CrossReference],
                           subject: str) -> List[CrossReference]:
        """Boost scores for same-subject references."""
        for ref in refs:
            if ref.metadata.get("subject") == subject:
                ref.similarity_score *= 1.2  # 20% boost
        return sorted(refs, key=lambda r: r.similarity_score, reverse=True)
```

---

## Troubleshooting

### RAG Not Indexing Notes

**Symptoms**: New notes aren't appearing in search results

**Solutions**:
1. Check if RAG is enabled:
   ```bash
   docker exec youtube-study-buddy printenv RAG_ENABLED
   ```

2. Check pipeline stage logs:
   ```bash
   docker logs youtube-study-buddy | grep RAG
   ```

3. Verify vector store health:
   ```bash
   ./scripts/check_rag_health.sh
   ```

4. Manually re-index:
   ```bash
   docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py
   ```

### Model Download Fails

**Symptoms**: "Failed to load model" error

**Solutions**:
1. Check internet connectivity
2. Verify cache directory exists and is writable:
   ```bash
   docker exec youtube-study-buddy ls -la /app/.cache
   ```

3. Manually download model:
   ```bash
   docker exec youtube-study-buddy python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"
   ```

4. Use pre-cached model in Docker image (rebuild):
   ```bash
   docker-compose build --no-cache
   ```

### ChromaDB Connection Errors

**Symptoms**: "Could not connect to ChromaDB" or similar

**Solutions**:
1. Check directory permissions:
   ```bash
   docker exec youtube-study-buddy ls -la /app/.chroma_db
   ```

2. Reset ChromaDB volume:
   ```bash
   ./scripts/manage_rag_volumes.sh reset
   ```

3. Verify ChromaDB installed:
   ```bash
   docker exec youtube-study-buddy python -c "import chromadb; print(chromadb.__version__)"
   ```

### Out of Memory

**Symptoms**: Container crashes or OOM errors

**Solutions**:
1. Reduce batch size:
   ```bash
   RAG_BATCH_SIZE=16  # Down from 32
   ```

2. Use smaller model:
   ```bash
   RAG_MODEL=all-MiniLM-L6-v2
   ```

3. Increase Docker memory:
   ```yaml
   # docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 3G
   ```

### Poor Search Quality

**Symptoms**: Irrelevant results, missing connections

**Solutions**:
1. Lower similarity threshold:
   ```bash
   RAG_SIMILARITY_THRESHOLD=0.2  # Down from 0.3
   ```

2. Increase max results:
   ```bash
   RAG_MAX_RESULTS=10  # Up from 5
   ```

3. Try a better model:
   ```bash
   RAG_MODEL=all-distilroberta-v1
   ```

4. Evaluate quality:
   ```bash
   docker exec youtube-study-buddy python scripts/evaluate_rag.py --compare
   ```

---

## API Quick Reference

### VectorStore

```python
store = VectorStore(persist_dir, collection_name)
store.add_chunks(chunks: List[Chunk]) -> bool
store.search_similar(query_embedding, filters, top_k) -> List[SearchResult]
store.delete_by_video_id(video_id: str) -> bool
store.collection_stats() -> Dict[str, Any]
store.health_check() -> bool
```

### EmbeddingService

```python
service = EmbeddingService(model_name, cache_dir, device)
service.embed_text(text: str) -> np.ndarray
service.embed_batch(texts: List[str]) -> np.ndarray
service.get_embedding_dim() -> int
service.model_info() -> Dict[str, Any]
```

### DocumentChunker

```python
chunker = DocumentChunker(chunk_size, chunk_overlap, min_chunk_size)
chunker.chunk_markdown(content: str, metadata: Dict) -> List[Chunk]
chunker.validate_chunk(chunk: Chunk) -> bool
```

### RAGPipelineStage

```python
stage = RAGPipelineStage(config: RAGConfig)
stage.process_note(note_path: Path, video_metadata: Dict) -> ProcessResult
stage.process_batch(notes: List[Path]) -> List[ProcessResult]
stage.is_note_indexed(video_id: str) -> bool
```

### IndexTracker

```python
tracker = IndexTracker(tracker_file: Path)
tracker.mark_indexed(video_id: str, note_path: Path)
tracker.is_indexed(video_id: str, note_path: Path) -> bool
tracker.needs_reindex(video_id: str, note_path: Path) -> bool
tracker.get_unindexed_notes(notes_dir: Path) -> List[Path]
```

### RAGCrossReferencer

```python
referencer = RAGCrossReferencer(embedding_service, vector_store, config)
referencer.find_references(
    section_text: str,
    current_video_id: str,
    subject: Optional[str] = None,
    global_context: bool = False
) -> List[CrossReference]
```

### Configuration

```python
config = load_config_from_env()  # Loads from environment variables
# Or create manually:
config = RAGConfig(
    enabled=True,
    model_name="all-mpnet-base-v2",
    similarity_threshold=0.3,
    ...
)
```

---

## Additional Resources

- [RAG User Guide](RAG_USER_GUIDE.md) - User-focused documentation
- [RAG API Documentation](RAG_API.md) - Complete API reference with examples
- [Quickstart Guide](QUICKSTART.md) - 5-minute setup guide
- [RAG Design Document](rag-design.md) - Architecture and design decisions
- [RAG Integration Plan](rag-integration.md) - Integration roadmap
- [RAG Research](rag-research.md) - Vector database comparison

---

## Contributing

When contributing to RAG features:

1. **Follow interface contracts** - Don't break existing APIs
2. **Add tests** - Maintain 85%+ coverage
3. **Document changes** - Update this guide and RAG_API.md
4. **Graceful degradation** - Errors shouldn't break the app
5. **Feature flags** - Make features configurable
6. **Performance** - Profile and optimize critical paths

---

**Last Updated**: October 17, 2025
**Version**: 1.0.0 (Initial RAG Implementation)
