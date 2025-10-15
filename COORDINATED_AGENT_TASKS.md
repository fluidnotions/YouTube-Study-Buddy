# RAG Implementation - Coordinated Agent Tasks

This document coordinates multiple agents working concurrently on different RAG features. Each agent has a dedicated workspace and clear interfaces to avoid conflicts.

## Project Structure

```
rag-worktree/
├── workspaces/
│   ├── core-infrastructure/       # Agent 1: Vector store & embeddings
│   ├── pipeline-integration/      # Agent 2: Pipeline changes
│   ├── obsidian-linker/          # Agent 3: Link generation
│   ├── docker-config/            # Agent 4: Docker setup
│   ├── migration-tooling/        # Agent 5: Migration scripts
│   └── documentation/            # Agent 6: Docs & README
├── docs/
│   ├── rag-research.md           # ✅ Complete
│   ├── rag-design.md             # ✅ Complete
│   └── rag-integration.md        # ✅ Complete
└── COORDINATED_AGENT_TASKS.md    # This file
```

## Execution Order

### Phase 1: Parallel Development (Agents 1-3)
These agents can work concurrently as they have minimal dependencies:
- **Agent 1**: Core Infrastructure (foundation)
- **Agent 2**: Pipeline Integration (uses Agent 1 interfaces)
- **Agent 3**: ObsidianLinker Enhancement (uses Agent 1 interfaces)

### Phase 2: Parallel Support (Agents 4-5)
Run after Phase 1 modules are defined:
- **Agent 4**: Docker Configuration (needs to know what to configure)
- **Agent 5**: Migration & Tooling (needs core modules to test against)

### Phase 3: Documentation (Agent 6)
Run last to document everything:
- **Agent 6**: Documentation Updates (needs all features complete)

## Agent Tasks

---

## Agent 1: Core RAG Infrastructure

**Workspace:** `workspaces/core-infrastructure/`
**Priority:** HIGH (Foundation for all other features)
**Estimated Time:** 4-6 hours

### Objective
Build the foundational RAG components that other features will depend on.

### Deliverables

#### 1. VectorStore Module (`src/yt_study_buddy/rag/vector_store.py`)

**Requirements:**
- ChromaDB client wrapper with connection pooling
- Collection management (create, get, delete)
- Document storage with metadata
- Similarity search with filtering
- Health checks and error handling
- Graceful degradation on failure

**Interface:**
```python
class VectorStore:
    def __init__(self, persist_dir: str, collection_name: str)
    def add_chunks(self, chunks: List[Chunk]) -> bool
    def search_similar(self, query_embedding: np.ndarray,
                      filters: Dict, top_k: int) -> List[SearchResult]
    def delete_by_video_id(self, video_id: str) -> bool
    def collection_stats(self) -> Dict[str, Any]
    def health_check(self) -> bool
```

**Key Features:**
- Metadata filtering (subject, video_id, date_range)
- Batch operations (add/delete multiple chunks)
- Error recovery (retry logic, connection reset)
- Logging and metrics

#### 2. EmbeddingService Module (`src/yt_study_buddy/rag/embedding_service.py`)

**Requirements:**
- Sentence-transformer model loader
- Embedding generation (single & batch)
- Model caching and lazy loading
- CPU/GPU detection and optimization
- Token counting and dimension info

**Interface:**
```python
class EmbeddingService:
    def __init__(self, model_name: str = "all-mpnet-base-v2")
    def embed_text(self, text: str) -> np.ndarray
    def embed_batch(self, texts: List[str]) -> np.ndarray
    def get_embedding_dim(self) -> int
    def model_info(self) -> Dict[str, Any]
```

**Key Features:**
- Lazy model loading (on first use)
- Batch processing for efficiency
- Error handling (out of memory, invalid input)
- Progress tracking for large batches

#### 3. DocumentChunker Module (`src/yt_study_buddy/rag/document_chunker.py`)

**Requirements:**
- Markdown section-based chunking
- Metadata extraction (section titles, hierarchy)
- Overlap handling for context preservation
- Token counting and size limits
- Handles malformed markdown gracefully

**Interface:**
```python
@dataclass
class Chunk:
    chunk_id: str
    content: str
    metadata: ChunkMetadata

@dataclass
class ChunkMetadata:
    video_id: str
    video_title: str
    subject: str
    section_title: str
    section_level: int
    token_count: int
    created_at: str

class DocumentChunker:
    def chunk_markdown(self, content: str, metadata: Dict) -> List[Chunk]
    def validate_chunk(self, chunk: Chunk) -> bool
```

**Chunking Strategy:**
- Split on `##` headings (H2 level)
- Preserve hierarchy (H3, H4 under H2)
- Add 50-token overlap between chunks
- Max chunk size: 1000 tokens
- Min chunk size: 50 tokens

#### 4. Configuration Module (`src/yt_study_buddy/rag/config.py`)

**Requirements:**
- Feature flags (enable/disable RAG)
- Model configuration (name, cache dir)
- Vector store settings (persist dir, collection name)
- Performance tuning (batch size, top_k)
- Environment variable loading

**Interface:**
```python
@dataclass
class RAGConfig:
    enabled: bool
    model_name: str
    model_cache_dir: Path
    vector_store_dir: Path
    collection_name: str
    similarity_threshold: float
    max_results: int
    batch_size: int

def load_config_from_env() -> RAGConfig
```

#### 5. Unit Tests

**Test Coverage:**
- `tests/rag/test_vector_store.py` - ChromaDB operations
- `tests/rag/test_embedding_service.py` - Embedding generation
- `tests/rag/test_document_chunker.py` - Chunking logic
- `tests/rag/test_config.py` - Configuration loading

**Target:** 85%+ code coverage

### Success Criteria
- [ ] All modules pass unit tests
- [ ] Embedding generation < 100ms per chunk
- [ ] Vector search < 50ms per query
- [ ] ChromaDB health check passes
- [ ] Graceful degradation on errors
- [ ] Code review ready

### Dependencies
- ChromaDB (already added via uv)
- sentence-transformers (already in dependencies)
- tiktoken (for token counting - needs to be added)

### Output Location
- Source: `src/yt_study_buddy/rag/`
- Tests: `tests/rag/`
- Workspace: `workspaces/core-infrastructure/`

---

## Agent 2: Pipeline Integration

**Workspace:** `workspaces/pipeline-integration/`
**Priority:** HIGH (Core functionality)
**Estimated Time:** 3-4 hours
**Depends On:** Agent 1 (needs core RAG modules)

### Objective
Integrate RAG embedding generation into the video processing pipeline.

### Deliverables

#### 1. RAGPipelineStage Module (`src/yt_study_buddy/rag/pipeline_stage.py`)

**Requirements:**
- Pipeline stage for embedding generation
- Asynchronous/background processing support
- Error handling with graceful degradation
- Progress tracking and logging
- Idempotent (can re-run safely)

**Interface:**
```python
class RAGPipelineStage:
    def __init__(self, config: RAGConfig,
                 embedding_service: EmbeddingService,
                 vector_store: VectorStore,
                 chunker: DocumentChunker)

    def process_note(self, note_path: Path,
                     video_metadata: Dict) -> ProcessResult

    def process_batch(self, notes: List[Path]) -> List[ProcessResult]

    def is_note_indexed(self, video_id: str) -> bool
```

**Functionality:**
1. Check if note already indexed (modification time tracking)
2. Load markdown content
3. Chunk using DocumentChunker
4. Generate embeddings using EmbeddingService
5. Store in VectorStore
6. Update index tracking file
7. Return success/failure status

#### 2. Processing Pipeline Modification (`src/yt_study_buddy/processing_pipeline.py`)

**Changes:**
- Add RAG stage after note generation
- Feature flag check (`if config.rag_enabled`)
- Background execution (don't block pipeline)
- Error logging (don't fail pipeline on RAG errors)

**Integration Points:**
```python
# In process_video_job() or equivalent
if rag_config.enabled:
    try:
        rag_stage = RAGPipelineStage(...)
        result = rag_stage.process_note(
            note_path=job.notes_filepath,
            video_metadata={
                'video_id': job.video_id,
                'title': job.video_title,
                'subject': job.subject
            }
        )
        logger.info(f"RAG indexing: {result.status}")
    except Exception as e:
        logger.warning(f"RAG indexing failed: {e}")
        # Continue pipeline - don't fail the job
```

#### 3. Index Tracking Module (`src/yt_study_buddy/rag/index_tracker.py`)

**Requirements:**
- Track which notes have been indexed
- Store modification times for incremental updates
- Detect when notes need re-indexing
- Persistent storage (JSON file)

**Interface:**
```python
class IndexTracker:
    def __init__(self, tracker_file: Path)
    def mark_indexed(self, video_id: str, note_path: Path)
    def is_indexed(self, video_id: str, note_path: Path) -> bool
    def needs_reindex(self, video_id: str, note_path: Path) -> bool
    def get_unindexed_notes(self, notes_dir: Path) -> List[Path]
```

#### 4. Unit Tests

**Test Coverage:**
- `tests/rag/test_pipeline_stage.py` - Pipeline stage logic
- `tests/rag/test_index_tracker.py` - Index tracking
- `tests/integration/test_pipeline_rag.py` - End-to-end pipeline

**Test Scenarios:**
- New note indexing
- Re-indexing modified notes
- Skipping already-indexed notes
- Error handling and graceful degradation
- Feature flag on/off behavior

### Success Criteria
- [ ] RAG stage integrates cleanly into pipeline
- [ ] No performance regression (<5s overhead)
- [ ] Pipeline still works with RAG disabled
- [ ] Errors don't break video processing
- [ ] Modification tracking works correctly
- [ ] Tests pass with 85%+ coverage

### Dependencies
- Agent 1 modules (VectorStore, EmbeddingService, DocumentChunker)

### Output Location
- Source: `src/yt_study_buddy/rag/pipeline_stage.py`
- Modifications: `src/yt_study_buddy/processing_pipeline.py`
- Tests: `tests/rag/` and `tests/integration/`
- Workspace: `workspaces/pipeline-integration/`

---

## Agent 3: ObsidianLinker Enhancement

**Workspace:** `workspaces/obsidian-linker/`
**Priority:** HIGH (User-facing feature)
**Estimated Time:** 3-4 hours
**Depends On:** Agent 1 (needs core RAG modules)

### Objective
Enhance ObsidianLinker to use RAG for semantic cross-referencing with fallback to existing fuzzy matching.

### Deliverables

#### 1. RAGCrossReferencer Module (`src/yt_study_buddy/rag/cross_referencer.py`)

**Requirements:**
- High-level RAG query interface
- Result ranking and filtering
- Deduplication logic
- Subject-specific vs global search
- Link formatting for Obsidian

**Interface:**
```python
@dataclass
class CrossReference:
    target_section: str
    target_video_id: str
    target_video_title: str
    similarity_score: float
    preview_text: str

class RAGCrossReferencer:
    def __init__(self, embedding_service: EmbeddingService,
                 vector_store: VectorStore,
                 config: RAGConfig)

    def find_references(self,
                       section_text: str,
                       current_video_id: str,
                       subject: Optional[str] = None,
                       global_context: bool = False) -> List[CrossReference]

    def format_as_obsidian_link(self, ref: CrossReference) -> str
```

**Functionality:**
1. Generate embedding for section text
2. Query vector store with filters (subject, exclude current video)
3. Rank results by similarity score
4. Filter by threshold (configurable)
5. Deduplicate (same video, nearby sections)
6. Format as `[[Video Title#Section]]` links

#### 2. ObsidianLinker Modifications (`src/yt_study_buddy/obsidian_linker.py`)

**Changes:**
- Add RAG backend initialization
- New method: `_find_links_rag()`
- Hybrid approach: Try RAG first, fallback to fuzzy
- Feature flag check
- Error handling

**Integration:**
```python
class ObsidianLinker:
    def __init__(self, ...):
        # ... existing code ...

        # Initialize RAG (if enabled)
        self.rag_config = load_config_from_env()
        if self.rag_config.enabled:
            try:
                self.rag_referencer = RAGCrossReferencer(...)
            except Exception as e:
                logger.warning(f"RAG init failed: {e}")
                self.rag_referencer = None

    def add_links(self, content: str, ...) -> str:
        if self.rag_config.enabled and self.rag_referencer:
            try:
                return self._add_links_rag(content, ...)
            except Exception as e:
                logger.warning(f"RAG linking failed: {e}, using fallback")

        # Fallback to existing fuzzy matching
        return self._add_links_fuzzy(content, ...)

    def _add_links_rag(self, content: str, ...) -> str:
        """New RAG-based linking logic"""
        sections = self._split_into_sections(content)

        for section in sections:
            # Find references using RAG
            refs = self.rag_referencer.find_references(
                section_text=section.text,
                current_video_id=self.current_video_id,
                subject=self.subject,
                global_context=self.global_context
            )

            # Insert links
            section.text = self._insert_links(section.text, refs)

        return self._merge_sections(sections)

    def _add_links_fuzzy(self, content: str, ...) -> str:
        """Existing fuzzy matching logic (unchanged)"""
        # ... existing implementation ...
```

#### 3. Link Quality Metrics (`src/yt_study_buddy/rag/metrics.py`)

**Requirements:**
- Track link generation statistics
- Compare RAG vs fuzzy matching
- Quality metrics (relevance, coverage)

**Metrics to Track:**
- Number of links generated (RAG vs fuzzy)
- Similarity score distribution
- Links per note (average, median)
- Fallback rate (when RAG fails)
- Query latency (p50, p95, p99)

#### 4. Unit Tests

**Test Coverage:**
- `tests/rag/test_cross_referencer.py` - RAG query logic
- `tests/test_obsidian_linker.py` - Enhanced linker (update existing tests)
- `tests/integration/test_rag_linking.py` - End-to-end linking

**Test Scenarios:**
- RAG linking with valid results
- Fallback when RAG unavailable
- Subject-specific vs global search
- Deduplication logic
- Obsidian link formatting
- Error handling

### Success Criteria
- [ ] RAG linking produces semantically relevant links
- [ ] Fallback to fuzzy matching works seamlessly
- [ ] Link quality metrics show improvement
- [ ] No breaking changes to existing API
- [ ] Query latency < 100ms per section
- [ ] Tests pass with 85%+ coverage

### Dependencies
- Agent 1 modules (EmbeddingService, VectorStore)

### Output Location
- Source: `src/yt_study_buddy/rag/cross_referencer.py`
- Modifications: `src/yt_study_buddy/obsidian_linker.py`
- Tests: `tests/rag/` and `tests/integration/`
- Workspace: `workspaces/obsidian-linker/`

---

## Agent 4: Docker Configuration

**Workspace:** `workspaces/docker-config/`
**Priority:** MEDIUM (Deployment infrastructure)
**Estimated Time:** 2-3 hours
**Depends On:** Agents 1-3 (needs to know what to configure)

### Objective
Update Docker configuration to support RAG components with proper persistence and resource limits.

### Deliverables

#### 1. Dockerfile Updates

**Changes:**
```dockerfile
# Add model pre-download (optional, speeds up first run)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-mpnet-base-v2')"

# Create ChromaDB directory
RUN mkdir -p /app/.chroma_db && chmod 777 /app/.chroma_db

# Create model cache directory
RUN mkdir -p /root/.cache/torch/sentence_transformers && \
    chmod 777 /root/.cache/torch/sentence_transformers
```

#### 2. docker-compose.yml Updates

**Changes:**
```yaml
services:
  youtube-study-buddy:
    volumes:
      - ./notes:/app/notes
      - tracker-data:/app/tracker
      - chroma_data:/app/.chroma_db          # NEW: Vector DB persistence
      - model_cache:/app/.cache              # NEW: Model cache

    environment:
      # Existing environment variables
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}

      # RAG Configuration (NEW)
      - RAG_ENABLED=true
      - RAG_MODEL=all-mpnet-base-v2
      - RAG_SIMILARITY_THRESHOLD=0.3
      - RAG_MAX_RESULTS=5
      - RAG_BATCH_SIZE=32
      - CHROMA_PERSIST_DIR=/app/.chroma_db
      - MODEL_CACHE_DIR=/app/.cache

    deploy:
      resources:
        limits:
          memory: 2G      # Increased from 1G
          cpus: '2.0'
        reservations:
          memory: 1G

volumes:
  tor-data:
    driver: local
  tracker-data:
    driver: local
  chroma_data:               # NEW: Vector database storage
    driver: local
  model_cache:               # NEW: Sentence transformer models
    driver: local
```

#### 3. docker-compose.dev.yml Updates

**Similar Changes:**
- Add development-specific volumes (chroma_data_dev, model_cache_dev)
- Source code mounting for hot reload
- Debug environment variables

#### 4. .env.example Updates

**New Variables:**
```bash
# RAG Configuration
RAG_ENABLED=true
RAG_MODEL=all-mpnet-base-v2
RAG_SIMILARITY_THRESHOLD=0.3
RAG_MAX_RESULTS=5
RAG_BATCH_SIZE=32
CHROMA_PERSIST_DIR=/app/.chroma_db
MODEL_CACHE_DIR=/app/.cache
```

#### 5. Volume Management Scripts

**Create:** `scripts/manage_rag_volumes.sh`
```bash
#!/bin/bash
# Backup, restore, and reset RAG volumes

backup_chroma() {
    docker run --rm \
        -v ytstudybuddy_chroma_data:/data \
        -v $(pwd):/backup alpine \
        tar czf /backup/chroma-backup-$(date +%Y%m%d).tar.gz -C /data .
}

restore_chroma() {
    docker run --rm \
        -v ytstudybuddy_chroma_data:/data \
        -v $(pwd):/backup alpine \
        tar xzf /backup/$1 -C /data
}

reset_chroma() {
    docker volume rm ytstudybuddy_chroma_data
    docker-compose up -d
}

# ... menu system ...
```

#### 6. Health Check Script

**Create:** `scripts/check_rag_health.sh`
```bash
#!/bin/bash
# Check RAG system health

docker exec youtube-study-buddy python -c "
from src.yt_study_buddy.rag.vector_store import VectorStore
from src.yt_study_buddy.rag.embedding_service import EmbeddingService

# Test vector store
vs = VectorStore('/app/.chroma_db', 'study_notes')
print(f'Vector store health: {vs.health_check()}')
print(f'Collection stats: {vs.collection_stats()}')

# Test embedding service
es = EmbeddingService('all-mpnet-base-v2')
print(f'Model loaded: {es.model_info()}')
print(f'Test embedding: {es.embed_text(\"test\").shape}')
"
```

#### 7. Documentation

**Update:** `README.md` Docker section
- Document new volumes
- Explain RAG configuration
- Volume backup/restore instructions
- Resource requirements (2GB RAM)

### Success Criteria
- [ ] Docker build succeeds
- [ ] All volumes persist correctly
- [ ] Environment variables work
- [ ] Resource limits appropriate
- [ ] Health check script works
- [ ] Documentation updated

### Dependencies
- Agents 1-3 (needs to know what modules exist)

### Output Location
- Modifications: `Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`
- Scripts: `scripts/manage_rag_volumes.sh`, `scripts/check_rag_health.sh`
- Workspace: `workspaces/docker-config/`

---

## Agent 5: Migration & Tooling

**Workspace:** `workspaces/migration-tooling/`
**Priority:** MEDIUM (Support infrastructure)
**Estimated Time:** 3-4 hours
**Depends On:** Agents 1-2 (needs core modules and pipeline)

### Objective
Create tools for migrating existing notes and evaluating RAG quality.

### Deliverables

#### 1. Migration Script (`scripts/migrate_notes_to_rag.py`)

**Requirements:**
- Scan notes directory for existing markdown files
- Index all unindexed notes
- Progress tracking with resume capability
- Batch processing for efficiency
- Error handling and logging
- Dry-run mode

**Features:**
```python
#!/usr/bin/env python3
"""
Migrate existing notes to RAG vector store.

Usage:
    # Dry run (show what would be indexed)
    python scripts/migrate_notes_to_rag.py --dry-run

    # Index all notes
    python scripts/migrate_notes_to_rag.py

    # Index specific subject
    python scripts/migrate_notes_to_rag.py --subject AI

    # Resume from checkpoint
    python scripts/migrate_notes_to_rag.py --resume
"""

class NoteMigrator:
    def scan_notes(self, notes_dir: Path) -> List[Path]
    def filter_unindexed(self, notes: List[Path]) -> List[Path]
    def migrate_batch(self, notes: List[Path], batch_size: int)
    def create_checkpoint(self)
    def resume_from_checkpoint(self) -> int
```

**Output:**
- Progress bar (tqdm)
- Statistics (notes processed, errors, time)
- Checkpoint file (for resume)
- Summary report

#### 2. RAG Evaluation Script (`scripts/evaluate_rag.py`)

**Requirements:**
- Compare RAG vs fuzzy matching quality
- Generate test queries
- Measure relevance, precision, recall
- Performance benchmarks
- Quality report

**Features:**
```python
#!/usr/bin/env python3
"""
Evaluate RAG cross-reference quality.

Usage:
    # Run full evaluation
    python scripts/evaluate_rag.py

    # Quick test (10 queries)
    python scripts/evaluate_rag.py --quick

    # Compare RAG vs fuzzy
    python scripts/evaluate_rag.py --compare
"""

class RAGEvaluator:
    def generate_test_queries(self, n: int) -> List[str]
    def evaluate_relevance(self, query: str, results: List) -> float
    def compare_methods(self, queries: List[str]) -> ComparisonReport
    def benchmark_performance(self, n_queries: int) -> PerfMetrics
```

**Metrics:**
- Precision@K (K=1,5,10)
- Recall
- NDCG (Normalized Discounted Cumulative Gain)
- Query latency (p50, p95, p99)
- Method comparison (RAG vs fuzzy)

#### 3. Vector Store Maintenance Script (`scripts/maintain_vector_store.py`)

**Requirements:**
- Rebuild entire vector store
- Remove stale entries (deleted notes)
- Optimize vector index
- Export/import functionality
- Health diagnostics

**Features:**
```bash
# Rebuild from scratch
python scripts/maintain_vector_store.py --rebuild

# Clean stale entries
python scripts/maintain_vector_store.py --clean

# Export for backup
python scripts/maintain_vector_store.py --export backup.json

# Import from backup
python scripts/maintain_vector_store.py --import backup.json

# Diagnostics
python scripts/maintain_vector_store.py --diagnose
```

#### 4. Interactive RAG Query Tool (`scripts/query_rag_interactive.py`)

**Requirements:**
- REPL for testing RAG queries
- Pretty-print results
- Filter by subject/video
- Explain similarity scores
- Export results

**Interface:**
```bash
$ python scripts/query_rag_interactive.py

RAG Query Tool
==============
> How do neural networks learn?

Found 5 results:

1. Introduction to Neural Networks - Learning Process (score: 0.85)
   Video: Deep Learning Fundamentals (dQw4w9W)
   Preview: "Neural networks learn through a process called backpropagation..."

2. Gradient Descent Explained (score: 0.72)
   Video: Optimization Algorithms (xyz123)
   Preview: "The learning process adjusts weights to minimize loss..."

[More results...]

> subject:AI backpropagation
...
```

#### 5. Update README Scripts Section

**Documentation:**
- Migration script usage
- Evaluation instructions
- Maintenance procedures
- Interactive query tool

### Success Criteria
- [ ] Migration script indexes all notes
- [ ] Resume capability works
- [ ] Evaluation shows quality improvements
- [ ] Maintenance scripts work correctly
- [ ] Interactive tool is user-friendly
- [ ] All scripts documented

### Dependencies
- Agent 1 (core modules)
- Agent 2 (pipeline integration)

### Output Location
- Scripts: `scripts/migrate_notes_to_rag.py`, `scripts/evaluate_rag.py`, `scripts/maintain_vector_store.py`, `scripts/query_rag_interactive.py`
- Workspace: `workspaces/migration-tooling/`

---

## Agent 6: Documentation & README

**Workspace:** `workspaces/documentation/`
**Priority:** HIGH (User understanding)
**Estimated Time:** 2-3 hours
**Depends On:** All previous agents

### Objective
Comprehensive documentation of RAG features for users and developers.

### Deliverables

#### 1. README.md Updates

**New Sections:**

**RAG Cross-Referencing:**
```markdown
## RAG-Powered Cross-Referencing

YouTube Study Buddy uses Retrieval-Augmented Generation (RAG) to find semantic connections between your notes.

### What is RAG?

RAG uses AI embeddings to understand the *meaning* of concepts, not just keywords:

- **Semantic Understanding:** "neural networks" ↔ "deep learning" are recognized as related
- **Relevance Ranking:** Most relevant connections appear first
- **Context-Aware:** Understands which connections matter for learning

### How It Works

1. **Note Processing:** After generating notes, content is chunked by sections
2. **Embedding Generation:** Each section gets a semantic "fingerprint" (768-dimensional vector)
3. **Vector Storage:** Fingerprints stored in ChromaDB for fast similarity search
4. **Cross-Referencing:** When creating links, RAG finds semantically similar content
5. **Link Generation:** Creates `[[Wiki-style]]` links to relevant sections

### Configuration

Control RAG behavior via environment variables:

```bash
RAG_ENABLED=true                    # Enable/disable RAG (default: true)
RAG_MODEL=all-mpnet-base-v2        # Embedding model (default)
RAG_SIMILARITY_THRESHOLD=0.3        # Minimum similarity score (0-1)
RAG_MAX_RESULTS=5                   # Max cross-references per section
```

### Performance

- **Query Speed:** < 100ms for similarity search
- **Memory:** ~500MB for model + 1000 notes
- **Storage:** ~1MB per note (embeddings)
- **Overhead:** ~3-5 seconds per video (background indexing)

### Fallback

If RAG is unavailable, the system automatically falls back to fuzzy matching (keyword-based).
```

**Docker Section Updates:**
```markdown
### Volumes

Four volumes for data persistence:

1. **./notes** - Study notes (bind mount to host)
2. **tracker-data** - Exit node tracker (named volume)
3. **chroma_data** - RAG vector database (named volume) 🆕
4. **model_cache** - Sentence transformer models (named volume) 🆕

#### Managing RAG Volumes

```bash
# Backup vector database
./scripts/manage_rag_volumes.sh backup

# Restore from backup
./scripts/manage_rag_volumes.sh restore chroma-backup-20251017.tar.gz

# Reset (clear all embeddings)
./scripts/manage_rag_volumes.sh reset

# Check RAG health
./scripts/check_rag_health.sh
```
```

#### 2. Developer Guide (`docs/RAG_DEVELOPER_GUIDE.md`)

**Contents:**
- Architecture overview
- Module documentation
- API reference
- Adding new features
- Testing guidelines
- Performance tuning
- Troubleshooting

**Sections:**
```markdown
# RAG Developer Guide

## Architecture

[High-level architecture diagram]

## Modules

### Core Infrastructure
- VectorStore: ChromaDB interface
- EmbeddingService: Sentence transformers
- DocumentChunker: Markdown processing
- Configuration: Feature flags and settings

### Integration
- RAGPipelineStage: Pipeline integration
- RAGCrossReferencer: Link generation
- ObsidianLinker: Enhanced with RAG

## API Reference

### VectorStore

[Detailed API documentation with examples]

### EmbeddingService

[Detailed API documentation with examples]

[... etc ...]

## Adding Features

How to extend RAG functionality...

## Testing

How to run tests, write new tests, etc...

## Performance Tuning

Optimization strategies...

## Troubleshooting

Common issues and solutions...
```

#### 3. User Guide (`docs/RAG_USER_GUIDE.md`)

**Contents:**
- What is RAG and why it matters
- How to enable/disable
- Configuration options
- Quality comparison examples
- Migration guide (existing notes)
- Troubleshooting for users

**Sections:**
```markdown
# RAG User Guide

## Introduction

Learn how RAG improves your study notes...

## Getting Started

### Docker Users

1. RAG is enabled by default
2. First run downloads ~80MB model (one-time)
3. Notes are automatically indexed

### CLI Users

[Instructions for non-Docker setup]

## Configuration

### Basic Settings

- Enable/disable RAG
- Adjust similarity threshold
- Change embedding model

### Advanced Settings

- Batch size optimization
- Subject-specific search
- Global vs local context

## Migrating Existing Notes

If you have notes from before RAG:

```bash
python scripts/migrate_notes_to_rag.py
```

[Detailed migration instructions]

## Quality Comparison

### Before RAG (Keyword Matching)

[Examples of keyword-only links]

### After RAG (Semantic Matching)

[Examples of improved RAG links]

## Troubleshooting

### RAG Not Working

1. Check Docker logs: `docker logs youtube-study-buddy`
2. Verify environment: `RAG_ENABLED=true`
3. Check health: `./scripts/check_rag_health.sh`

[More troubleshooting scenarios]
```

#### 4. API Documentation (`docs/RAG_API.md`)

**Contents:**
- Complete API reference for all RAG modules
- Code examples
- Type signatures
- Return values
- Error handling

#### 5. Update CHANGELOG.md

**Add:**
```markdown
## [Unreleased]

### Added
- RAG-powered semantic cross-referencing
- ChromaDB vector store integration
- Sentence-transformer embeddings
- Migration script for existing notes
- RAG evaluation and maintenance tools
- Comprehensive RAG documentation

### Changed
- ObsidianLinker now uses RAG with fuzzy fallback
- Docker setup includes RAG volumes and configuration
- Increased memory limit to 2GB for RAG components

### Performance
- Cross-reference quality: 40% → 75% recall, 60% → 85% precision
- Query speed: < 100ms per section
- Semantic understanding: Finds 50% more connections
```

#### 6. Update pyproject.toml Documentation

**Add:**
```toml
[project.optional-dependencies]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
    "mkdocstrings[python]>=0.24.0",
]
```

#### 7. Create Quickstart Guide (`docs/QUICKSTART.md`)

**Contents:**
- 5-minute setup guide
- First video processing
- Verify RAG is working
- Next steps

### Success Criteria
- [ ] README covers all RAG features
- [ ] Developer guide is comprehensive
- [ ] User guide is beginner-friendly
- [ ] API documentation is complete
- [ ] CHANGELOG updated
- [ ] All links work, no typos

### Dependencies
- All previous agents (needs complete picture)

### Output Location
- Updates: `README.md`, `CHANGELOG.md`
- New docs: `docs/RAG_DEVELOPER_GUIDE.md`, `docs/RAG_USER_GUIDE.md`, `docs/RAG_API.md`, `docs/QUICKSTART.md`
- Workspace: `workspaces/documentation/`

---

## Coordination & Communication

### Interface Contracts

All agents must follow these interface contracts:

**VectorStore Interface:**
```python
class VectorStore:
    def add_chunks(self, chunks: List[Chunk]) -> bool
    def search_similar(self, query_embedding: np.ndarray,
                      filters: Dict, top_k: int) -> List[SearchResult]
```

**EmbeddingService Interface:**
```python
class EmbeddingService:
    def embed_text(self, text: str) -> np.ndarray
    def embed_batch(self, texts: List[str]) -> np.ndarray
```

**Chunk Data Structure:**
```python
@dataclass
class Chunk:
    chunk_id: str
    content: str
    metadata: ChunkMetadata
```

### Shared Resources

**Configuration:**
- All agents use `src/yt_study_buddy/rag/config.py`
- Environment variables defined in `.env.example`

**Testing:**
- All agents contribute to `tests/rag/`
- Integration tests in `tests/integration/`

**Documentation:**
- Agent 6 consolidates docs from all agents
- Each agent provides docstrings and comments

### Error Handling

All agents must implement:
1. **Graceful degradation** - Don't break existing functionality
2. **Logging** - Use Python logging module
3. **Metrics** - Track key performance indicators
4. **Health checks** - Verify components are working

### Git Workflow

Each agent works in their workspace:
```bash
# Agent 1
cd workspaces/core-infrastructure
# ... develop ...
git add ../../src/yt_study_buddy/rag/
git commit -m "feat: add VectorStore module"

# Agent 2
cd workspaces/pipeline-integration
# ... develop ...
git add ../../src/yt_study_buddy/rag/pipeline_stage.py
git commit -m "feat: integrate RAG into pipeline"

# ... etc ...
```

**Merge Strategy:**
- Agents commit to `feature/rag-cross-reference` branch
- No merge conflicts (different files)
- Final review before merging to main

---

## Timeline

### Week 1: Core Development

**Days 1-2:** Agents 1, 2, 3 (parallel)
- Agent 1: Core infrastructure
- Agent 2: Pipeline integration
- Agent 3: ObsidianLinker enhancement

**Day 3:** Agent 4, 5 (parallel)
- Agent 4: Docker configuration
- Agent 5: Migration tooling

**Day 4:** Agent 6
- Documentation and README

**Day 5:** Integration testing, bug fixes, code review

### Week 2: Testing & Deployment

- Full integration testing
- Performance benchmarking
- Migration of existing notes
- Staging deployment
- Final documentation review

---

## Success Metrics

### Code Quality
- [ ] All tests pass (85%+ coverage)
- [ ] No linting errors
- [ ] Code review approved
- [ ] Documentation complete

### Performance
- [ ] Embedding generation < 100ms per chunk
- [ ] Vector search < 50ms per query
- [ ] Pipeline overhead < 5 seconds
- [ ] Memory < 2GB for 1000 notes

### Functionality
- [ ] RAG finds semantically similar content
- [ ] Graceful degradation works
- [ ] Migration script processes all notes
- [ ] Docker setup works out-of-box
- [ ] Health checks pass

### Documentation
- [ ] README covers all features
- [ ] Developer guide is comprehensive
- [ ] User guide is beginner-friendly
- [ ] All examples work

---

## Getting Started

### For Agents

1. **Read this document thoroughly**
2. **Check dependencies** - Can you start or must wait?
3. **Set up workspace:**
   ```bash
   cd /home/justin/Documents/dev/python/PycharmProjects/rag-worktree
   cd workspaces/[your-workspace]
   ```
4. **Follow your task deliverables**
5. **Commit work to main worktree** (not workspace subdirectory)
6. **Report completion** with summary

### For Coordinator

1. **Launch Phase 1 agents (1, 2, 3)** concurrently
2. **Wait for Phase 1 completion**
3. **Launch Phase 2 agents (4, 5)** concurrently
4. **Wait for Phase 2 completion**
5. **Launch Phase 3 agent (6)**
6. **Final integration review**
7. **Merge to main branch**

---

## Questions & Clarifications

If agents encounter ambiguities:

1. **Check design documents:**
   - `docs/rag-research.md`
   - `docs/rag-design.md`
   - `docs/rag-integration.md`

2. **Follow interface contracts** defined above

3. **Make reasonable decisions** and document them

4. **Flag blockers immediately** for coordinator

---

## Notes

- All agents work on the same branch: `feature/rag-cross-reference`
- Workspaces are for organization only, commits go to main worktree
- Interface contracts are STRICT - don't change signatures
- Graceful degradation is REQUIRED - RAG should never break the app
- Documentation is CRITICAL - users and developers need to understand RAG

---

**Estimated Total Time:** 20-26 hours (distributed across 6 agents)
**Estimated Calendar Time:** 1-2 weeks (with coordination overhead)
