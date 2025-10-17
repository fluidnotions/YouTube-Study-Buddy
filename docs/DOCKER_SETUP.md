# Docker Setup with RAG Support

Complete guide for running YouTube Study Buddy in Docker with RAG (Retrieval-Augmented Generation) capabilities.

## Quick Start

```bash
# 1. Set your Claude API key and RAG configuration in .env
cp .env.example .env
# Edit .env and add your CLAUDE_API_KEY

# 2. Start services
docker-compose up -d

# 3. Open browser
open http://localhost:8501
```

## Volumes

The docker-compose configuration uses **five volumes** (two new for RAG):

1. **`./notes`** (bind mount) - Study notes output
   - Appears on host at `./notes/`
   - Organized by subject
   - Contains markdown files and PDFs

2. **`tracker-data`** (named volume) - Exit node tracker persistence
   - Tracks which Tor exit IPs were used
   - Enforces 24-hour cooldown
   - Survives container restarts

3. **`tor-data`** (named volume) - Tor configuration
   - Tor circuit state
   - Docker managed volume

4. **`chroma_data`** (named volume) - RAG vector database
   - ChromaDB persistent storage
   - Stores semantic embeddings of note sections
   - Enables fast similarity search
   - Docker managed volume

5. **`model_cache`** (named volume) - Sentence transformer models
   - Cached ML models (~80MB for all-mpnet-base-v2)
   - Downloaded once, persists across rebuilds
   - Docker managed volume

## RAG Configuration

Control RAG behavior via environment variables in `.env`:

```bash
# Enable/disable RAG (default: true)
RAG_ENABLED=true

# Embedding model (all-mpnet-base-v2 recommended for quality)
RAG_MODEL=all-mpnet-base-v2

# Minimum similarity score threshold (0-1, lower = more results)
RAG_SIMILARITY_THRESHOLD=0.3

# Maximum cross-references per section
RAG_MAX_RESULTS=5

# Batch size for embedding generation (higher = faster but more memory)
RAG_BATCH_SIZE=32

# Persistence directories (pre-configured for Docker)
CHROMA_PERSIST_DIR=/app/.chroma_db
MODEL_CACHE_DIR=/app/.cache
```

## Managing RAG Volumes

Use the provided management script for backup, restore, and reset operations:

```bash
# Backup all RAG volumes (ChromaDB + models)
./scripts/manage_rag_volumes.sh backup

# Backup only ChromaDB
./scripts/manage_rag_volumes.sh backup-chroma

# Backup only model cache
./scripts/manage_rag_volumes.sh backup-models

# Restore ChromaDB from backup
./scripts/manage_rag_volumes.sh restore backups/rag-volumes/chroma-backup-20251017-143022.tar.gz

# Reset all RAG data (requires confirmation)
./scripts/manage_rag_volumes.sh reset

# List available backups
./scripts/manage_rag_volumes.sh list

# Show volume information
./scripts/manage_rag_volumes.sh info
```

## Health Checks

Verify RAG components are working correctly:

```bash
# Full health check
./scripts/check_rag_health.sh

# Quick check (basic connectivity only)
./scripts/check_rag_health.sh --quick

# Verbose output with details
./scripts/check_rag_health.sh --verbose
```

The health check verifies:
- ✓ Container is running
- ✓ RAG is enabled
- ✓ Environment variables are set
- ✓ Directories exist
- ✓ Python dependencies installed
- ✓ VectorStore is operational
- ✓ EmbeddingService is working
- ✓ Disk space usage

## Resource Requirements

**Memory Limits:**
- Production: 2GB limit, 1GB reservation
- Development: Same as production
- RAG components require ~500MB for model + embeddings

**CPU:**
- 2.0 CPUs allocated
- CPU-optimized PyTorch (no CUDA)

**Disk Space:**
- Model cache: ~80-100MB (one-time download)
- ChromaDB: ~1MB per note (embeddings)
- Example: 1000 notes ≈ 1GB vector database

## First Run

On first run, the container will:
1. **Download sentence-transformer model** (~80MB, one-time)
   - Pre-cached in image if model pre-download succeeded during build
   - Otherwise downloads on first embedding generation
2. **Create ChromaDB collection** (if RAG enabled)
3. **Index existing notes** (if migration script run)

This may take 1-2 minutes depending on network speed.

## Development Mode

For development with source code mounting:

```bash
# Build and start with source mounting
docker-compose -f docker-compose.dev.yml up --build

# Separate dev volumes (won't affect production data)
# - chroma_data_dev
# - model_cache_dev
# - tracker-data-dev
```

Development mode includes:
- Source code hot-reload (`./src` mounted)
- Debug logging (`LOG_LEVEL=DEBUG`)
- Unbuffered Python output
- Separate volumes from production

## Troubleshooting

### RAG Not Working

1. **Check container logs:**
   ```bash
   docker logs youtube-study-buddy
   ```

2. **Verify RAG is enabled:**
   ```bash
   docker exec youtube-study-buddy printenv RAG_ENABLED
   ```

3. **Run health check:**
   ```bash
   ./scripts/check_rag_health.sh
   ```

### Model Download Failed

If model download fails during build:
```bash
# Model will download on first use (fallback)
# Or manually download:
docker exec -it youtube-study-buddy python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"
```

### ChromaDB Connection Error

```bash
# Check directory permissions
docker exec youtube-study-buddy ls -la /app/.chroma_db

# Reset ChromaDB volume
./scripts/manage_rag_volumes.sh reset

# Restart containers
docker-compose restart
```

### Out of Memory

If container runs out of memory:

1. **Increase memory limit in docker-compose.yml:**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 3G  # Increase from 2G
   ```

2. **Reduce batch size in .env:**
   ```bash
   RAG_BATCH_SIZE=16  # Reduce from 32
   ```

3. **Use smaller model:**
   ```bash
   RAG_MODEL=all-MiniLM-L6-v2  # Smaller but less accurate
   ```

## Migration from Non-RAG Setup

If you have existing notes from before RAG:

1. **Enable RAG in .env:**
   ```bash
   RAG_ENABLED=true
   ```

2. **Run migration script:**
   ```bash
   docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py --notes-dir /app/notes
   ```

3. **Verify indexing:**
   ```bash
   ./scripts/check_rag_health.sh --verbose
   ```

See `scripts/migrate_notes_to_rag.py --help` for options.

### Migration Script Options

```bash
# Dry run (preview what will be indexed)
docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py --notes-dir /app/notes --dry-run

# Index specific subject only
docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py --notes-dir /app/notes --subject AI

# Resume from checkpoint (if interrupted)
docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py --notes-dir /app/notes --resume

# Batch size (default: 10)
docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py --notes-dir /app/notes --batch-size 20
```

## RAG Management & Evaluation

### Interactive Query Tool

Test RAG queries interactively with the REPL tool:

```bash
docker exec -it youtube-study-buddy python scripts/query_rag_interactive.py --notes-dir /app/notes
```

Commands available in the REPL:
- Basic query: `How do neural networks learn?`
- Subject filter: `subject:AI backpropagation`
- Global search: `global gradient descent`
- Show stats: `stats`
- Export results: `export results.json`
- Help: `help`
- Quit: `quit`

### Evaluate RAG Quality

Compare RAG semantic search against fuzzy matching:

```bash
# Quick evaluation (10 test queries)
docker exec youtube-study-buddy python scripts/evaluate_rag.py --notes-dir /app/notes --quick

# Full evaluation with comparison (50 queries)
docker exec youtube-study-buddy python scripts/evaluate_rag.py --notes-dir /app/notes --compare

# Save detailed report
docker exec youtube-study-buddy python scripts/evaluate_rag.py --notes-dir /app/notes --report-file /app/evaluation.json
docker cp youtube-study-buddy:/app/evaluation.json ./evaluation.json
```

Metrics reported:
- Precision@1, @5, @10 (how relevant are the top results)
- Query latency (p50, p95, p99)
- Average similarity scores
- RAG vs fuzzy improvement comparison

### Vector Store Maintenance

Perform maintenance operations on the RAG vector store:

```bash
# Show collection statistics
docker exec youtube-study-buddy python scripts/maintain_vector_store.py --stats

# Run health diagnostics
docker exec youtube-study-buddy python scripts/maintain_vector_store.py --diagnose

# Clean stale entries (deleted notes)
docker exec youtube-study-buddy python scripts/maintain_vector_store.py --clean --notes-dir /app/notes

# Export for backup
docker exec youtube-study-buddy python scripts/maintain_vector_store.py --export /app/backup.json
docker cp youtube-study-buddy:/app/backup.json ./backup.json

# Import from backup
docker cp ./backup.json youtube-study-buddy:/app/backup.json
docker exec youtube-study-buddy python scripts/maintain_vector_store.py --import /app/backup.json

# Rebuild from scratch (requires confirmation)
docker exec -it youtube-study-buddy python scripts/maintain_vector_store.py --rebuild --notes-dir /app/notes
```

See [scripts/README.md](../scripts/README.md) for detailed documentation of all scripts.

## Related Documentation

- [RAG Research](rag-research.md) - Vector DB comparison and technology evaluation
- [RAG Design](rag-design.md) - Architecture design and implementation details
- [RAG Integration](rag-integration.md) - Integration roadmap and migration guide
