# RAG Cross-Reference Enhancement - Agent Task

## Objective
Evaluate and implement RAG (Retrieval-Augmented Generation) to improve the cross-referencing feature in YouTube Study Buddy, which currently doesn't work effectively.

## Current State

### What Exists
- **ObsidianLinker** (`src/yt_study_buddy/obsidian_linker.py`): Creates `[[wiki-style]]` links in generated notes
- **Cross-reference scope**: Can search within subject or across all subjects
- **Simple keyword matching**: Uses basic text search to find related concepts
- **No embeddings**: No semantic understanding of concepts
- **No vector search**: Linear search through all notes

### The Problem
The current cross-reference system doesn't work well because:
1. **Keyword-only matching**: Misses semantic relationships (e.g., "neural networks" vs "deep learning")
2. **No context awareness**: Can't understand which connections are actually relevant
3. **Poor relevance ranking**: No way to rank connections by importance
4. **Scalability issues**: As note collection grows, linear search becomes slower
5. **Limited recall**: Miss connections that use different terminology

## Proposed Solution: RAG-based Cross-Referencing

### Phase 1: Research & Design (This Task)

#### 1. Evaluate RAG Approaches
Research and document:
- **Vector databases**: ChromaDB, FAISS, Qdrant, Weaviate
  - Pros/cons for local deployment
  - Docker compatibility
  - Memory/disk requirements
  - Query performance

- **Embedding models**:
  - Sentence transformers (already in requirements!)
  - Which model for educational content? (`all-MiniLM-L6-v2` vs `all-mpnet-base-v2`)
  - Embedding dimension vs performance tradeoff

- **Chunking strategies**:
  - Chunk by section? By concept? By paragraph?
  - Overlap requirements
  - Metadata to preserve (video_id, subject, timestamp)

#### 2. Design Document
Create `docs/rag-design.md` with:

**Architecture**:
```
┌─────────────────────────────────────────────────┐
│ Video Processing Pipeline                       │
│                                                  │
│ 1. Generate notes (Claude)                      │
│ 2. Extract concepts/sections                    │
│ 3. Generate embeddings (sentence-transformer)   │
│ 4. Store in vector DB                          │
│ 5. Query for similar concepts                  │
│ 6. Generate [[wiki-links]] using RAG results   │
└─────────────────────────────────────────────────┘
```

**Data Flow**:
1. Note generation → Concept extraction
2. Concept extraction → Embedding generation
3. Embeddings → Vector DB storage
4. Query time: Concept → Retrieve similar → Rank → Generate links

**Schema Design**:
```python
{
  "id": "video_id:section_id",
  "text": "Neural networks are...",
  "embedding": [0.123, 0.456, ...],
  "metadata": {
    "video_id": "abc123",
    "video_title": "...",
    "subject": "AI",
    "section_title": "Introduction to Neural Networks",
    "keywords": ["neural networks", "deep learning"],
    "created_at": "2025-10-17T12:00:00"
  }
}
```

#### 3. Proof of Concept
Create `scripts/rag_poc.py` that:
- Loads existing notes from `notes/` directory
- Chunks them appropriately
- Generates embeddings using sentence-transformer
- Stores in ChromaDB (or chosen vector DB)
- Queries for similar concepts
- Shows relevance scores
- Compares results vs current keyword-based approach

**Success metrics**:
- Retrieval accuracy: Does it find semantically similar concepts?
- Performance: Query time < 100ms for 1000+ notes
- Relevance: Top-5 results are actually related
- Coverage: Finds connections keyword search misses

#### 4. Integration Plan
Document in `docs/rag-integration.md`:
- Where to modify `ObsidianLinker`
- How to maintain backward compatibility
- Migration strategy for existing notes
- Docker volume for vector DB persistence
- Performance monitoring approach

### Phase 2: Implementation (Future Task)
- Implement chosen vector DB
- Update `ObsidianLinker` to use RAG
- Add embedding generation to pipeline
- Create migration script for existing notes
- Add monitoring/observability

### Phase 3: Evaluation (Future Task)
- A/B test: RAG vs keyword matching
- User feedback mechanism
- Performance benchmarks
- Cost analysis (compute/storage)

## Deliverables for This Task

1. **Research Summary** (`docs/rag-research.md`):
   - Vector DB comparison table
   - Embedding model evaluation
   - Chunking strategy analysis
   - Recommendation with justification

2. **Design Document** (`docs/rag-design.md`):
   - Architecture diagram
   - Data flow
   - Schema design
   - Integration points

3. **Proof of Concept** (`scripts/rag_poc.py`):
   - Working demo with existing notes
   - Performance metrics
   - Quality comparison vs current approach

4. **Integration Plan** (`docs/rag-integration.md`):
   - Step-by-step implementation guide
   - Risk assessment
   - Rollback strategy
   - Testing approach

## Technical Constraints

- **Must work in Docker**: All dependencies must be containerizable
- **Local-first**: Should work offline, no external API calls for embeddings
- **Memory efficient**: Target < 500MB RAM for vector DB
- **Fast queries**: < 100ms for similarity search
- **Existing stack**: Python 3.13, UV package manager, Docker Compose

## Files to Review

### Current Implementation
- `src/yt_study_buddy/obsidian_linker.py` - Current linking logic
- `src/yt_study_buddy/study_notes_generator.py` - Where notes are generated
- `src/yt_study_buddy/processing_pipeline.py` - Integration point

### Dependencies
- `pyproject.toml` - Already has `sentence-transformers`
- `Dockerfile` - Need to add vector DB
- `docker-compose.yml` - Need volume for embeddings

## Questions to Answer

1. **Vector DB Choice**:
   - ChromaDB (simple, Python-native) vs FAISS (fast, Facebook) vs Qdrant (feature-rich)?
   - Docker deployment complexity?
   - Persistence strategy?

2. **Embedding Model**:
   - `all-MiniLM-L6-v2` (fast, 384 dim) vs `all-mpnet-base-v2` (better, 768 dim)?
   - Fine-tuning needed for educational content?
   - Model size vs performance tradeoff?

3. **Chunking**:
   - Chunk by markdown sections (## headings)?
   - Fixed-size chunks with overlap?
   - Semantic chunking based on topics?

4. **When to Generate Embeddings**:
   - During note generation (synchronous)?
   - Background job after note creation (asynchronous)?
   - On-demand when querying?

5. **Cross-Reference Scope**:
   - How to implement global vs subject-specific search in vector space?
   - Filter by metadata vs separate collections?

6. **Quality Metrics**:
   - How to measure if RAG is better than keyword matching?
   - What constitutes a "good" cross-reference?
   - How to avoid over-linking (too many connections)?

## Success Criteria

This task is complete when:
1. ✅ All vector DB options evaluated with pros/cons
2. ✅ Clear recommendation made with justification
3. ✅ Working POC demonstrates improved cross-referencing
4. ✅ Performance metrics show < 100ms queries
5. ✅ Design doc provides clear implementation path
6. ✅ Integration plan addresses all technical constraints

## Getting Started

```bash
# Already in worktree: /home/justin/Documents/dev/python/PycharmProjects/rag-worktree
cd /home/justin/Documents/dev/python/PycharmProjects/rag-worktree

# Install any additional dependencies for research
uv add chromadb  # or other vector DB for POC

# Start research and documentation
mkdir -p docs scripts
touch docs/rag-research.md
touch docs/rag-design.md
touch docs/rag-integration.md
touch scripts/rag_poc.py

# Run existing code to understand current approach
uv run python -c "from src.yt_study_buddy.obsidian_linker import ObsidianLinker; help(ObsidianLinker)"
```

## Timeline Estimate

- Research: 2-3 hours
- POC development: 3-4 hours
- Design documentation: 2 hours
- Integration planning: 1-2 hours

**Total: 8-11 hours**

## Notes

- This is research and design phase only - no changes to production code yet
- Focus on finding the RIGHT approach before implementing
- Document tradeoffs clearly - there's no perfect solution
- POC should be convincing enough to justify full implementation
