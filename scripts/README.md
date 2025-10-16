# Scripts Directory

This folder contains helper scripts for local development and testing. **These are NOT needed for Docker usage.**

## RAG Management Scripts

**NEW: RAG (Retrieval-Augmented Generation) Tools**

These scripts help manage the RAG vector store and evaluate cross-reference quality.

### migrate_notes_to_rag.py

Migrate existing notes to the RAG vector store. Scans the notes directory and indexes markdown files for semantic search.

**Features:**
- Batch processing with progress tracking
- Resume capability (checkpoint-based)
- Dry-run mode to preview changes
- Subject filtering
- Error handling and logging

**Usage:**
```bash
# Dry run (show what would be indexed)
python scripts/migrate_notes_to_rag.py --dry-run

# Index all notes
python scripts/migrate_notes_to_rag.py

# Index specific subject
python scripts/migrate_notes_to_rag.py --subject AI

# Resume from checkpoint
python scripts/migrate_notes_to_rag.py --resume

# Custom notes directory
python scripts/migrate_notes_to_rag.py --notes-dir /path/to/notes

# Verbose output
python scripts/migrate_notes_to_rag.py --verbose
```

**Docker Usage:**
```bash
docker exec youtube-study-buddy python scripts/migrate_notes_to_rag.py --notes-dir /app/notes
```

### evaluate_rag.py

Evaluate RAG cross-reference quality by comparing semantic search against fuzzy matching.

**Features:**
- Generate test queries from existing notes
- Measure precision@k, recall, and relevance
- Performance benchmarking (latency metrics)
- Method comparison (RAG vs fuzzy)
- JSON report export

**Usage:**
```bash
# Run full evaluation (50 queries)
python scripts/evaluate_rag.py

# Quick test (10 queries)
python scripts/evaluate_rag.py --quick

# Compare RAG vs fuzzy matching
python scripts/evaluate_rag.py --compare

# Save results to file
python scripts/evaluate_rag.py --report-file evaluation.json

# Custom number of queries
python scripts/evaluate_rag.py --n-queries 100

# Verbose output
python scripts/evaluate_rag.py --verbose
```

**Metrics Reported:**
- Precision@1, @5, @10
- Average similarity scores
- Query latency (p50, p95, p99)
- Same-subject ratio
- Method improvement comparison

**Docker Usage:**
```bash
docker exec youtube-study-buddy python scripts/evaluate_rag.py --notes-dir /app/notes
```

### maintain_vector_store.py

Perform maintenance operations on the RAG vector store including cleanup, rebuild, and backup/restore.

**Features:**
- Collection statistics
- Health diagnostics
- Clean stale entries (deleted notes)
- Rebuild from scratch
- Export/import for backup
- Comprehensive health checks

**Usage:**
```bash
# Show collection statistics
python scripts/maintain_vector_store.py --stats

# Run health diagnostics
python scripts/maintain_vector_store.py --diagnose

# Clean stale entries (deleted notes)
python scripts/maintain_vector_store.py --clean

# Rebuild from scratch (with confirmation)
python scripts/maintain_vector_store.py --rebuild

# Export for backup
python scripts/maintain_vector_store.py --export backup.json

# Import from backup
python scripts/maintain_vector_store.py --import backup.json

# Verbose output
python scripts/maintain_vector_store.py --diagnose --verbose
```

**Health Checks:**
- Vector store connectivity
- Collection data integrity
- Embedding service functionality
- Index tracker status
- Directory permissions
- Model cache availability

**Docker Usage:**
```bash
# Run diagnostics
docker exec youtube-study-buddy python scripts/maintain_vector_store.py --diagnose

# Export backup
docker exec youtube-study-buddy python scripts/maintain_vector_store.py --export /app/backup.json
docker cp youtube-study-buddy:/app/backup.json ./backup.json
```

### query_rag_interactive.py

Interactive REPL (Read-Eval-Print Loop) for testing RAG queries with pretty-printed results.

**Features:**
- Interactive query interface
- Subject and video filtering
- Global vs local search
- Similarity score visualization
- Result export to JSON
- Vector store statistics

**Usage:**
```bash
# Start interactive session
python scripts/query_rag_interactive.py

# With custom notes directory
python scripts/query_rag_interactive.py --notes-dir /path/to/notes

# Verbose logging
python scripts/query_rag_interactive.py --verbose
```

**Interactive Commands:**
```
> How do neural networks learn?              # Basic query
> subject:AI backpropagation                 # Filter by subject
> video:note_intro <query>                   # Filter by video ID
> global gradient descent                    # Search all subjects
> stats                                      # Show statistics
> export results.json                        # Export last results
> help                                       # Show help
> quit                                       # Exit
```

**Docker Usage:**
```bash
docker exec -it youtube-study-buddy python scripts/query_rag_interactive.py --notes-dir /app/notes
```

## Local Tor Setup Scripts

**⚠️ Only needed if running locally WITHOUT Docker**

- `setup_tor_control.sh` - Interactive Tor control port setup for local development
- `setup_tor_control_auto.sh` - Non-interactive version for automation
- `run_with_tor.sh` - Helper to run commands with debian-tor group permissions

### Usage

```bash
# Setup Tor for local development
./scripts/setup_tor_control.sh

# Then run app with Tor group permissions
./scripts/run_with_tor.sh uv run streamlit run streamlit_app.py
```

## Test Scripts

### Development/Testing
- `test_simple.py` - Simple 2-video test to verify Tor circuit rotation
- `test_transcript.py` - Comprehensive transcript fetching test with different configs
- `test_parallel_processing.py` - Test parallel worker setup
- `test_parallel_optimization.py` - Parallel processing optimization tests
- `test_exit_node_tracking.py` - Test exit node tracker functionality
- `test_fallback.py` - Test fallback mechanisms
- `test_tor_in_group.sh` - Test Tor access with group permissions
- `fix_and_test.sh` - Quick test and fix script

### Diagnostic Tools
- `diagnose_tor.py` - Test Tor connection and exit node diversity
- `diagnose_failures.py` - Analyze failure patterns in processing logs
- `check_failures.py` - Quick failure check utility

### Example Scripts
- `example_job_logging.py` - Example of job logging functionality
- `debug_cli.py` - Debug wrapper for CLI commands (PyCharm debugging)

### Usage

```bash
# Run simple test
./scripts/run_with_tor.sh python scripts/test_simple.py

# Run comprehensive test
./scripts/run_with_tor.sh python scripts/test_transcript.py

# Diagnose Tor connection
uv run python scripts/diagnose_tor.py

# Check for failed jobs
uv run python scripts/check_failures.py
```

## Docker Users

**If you're using Docker, you don't need any of these scripts!**

Just use:
```bash
docker run -d --name youtube-study-buddy -p 8501:8501 --env-file .env youtube-study-buddy:python-tor
```

Or the convenience script in project root:
```bash
./run-docker.sh
```
